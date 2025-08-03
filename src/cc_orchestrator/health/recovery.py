"""Recovery management for unhealthy Claude instances."""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from ..core.instance import ClaudeInstance
from ..utils.logging import LogContext, get_logger
from .checker import HealthCheckResult, HealthStatus

logger = get_logger(__name__, LogContext.HEALTH)


class RecoveryStrategy(Enum):
    """Recovery strategies for unhealthy instances."""

    RESTART = "restart"
    RECREATE = "recreate"
    MANUAL = "manual"
    NONE = "none"


@dataclass
class RecoveryAttempt:
    """Information about a recovery attempt."""

    instance_id: str
    strategy: RecoveryStrategy
    timestamp: datetime
    success: bool
    error_message: str | None = None
    duration_seconds: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


class RecoveryPolicy(ABC):
    """Abstract base class for recovery policies."""

    @abstractmethod
    async def should_recover(
        self,
        instance: ClaudeInstance,
        status: HealthStatus,
        results: dict[str, HealthCheckResult],
        attempt_history: list[RecoveryAttempt],
    ) -> bool:
        """Determine if recovery should be attempted.

        Args:
            instance: Instance to evaluate
            status: Current health status
            results: Health check results
            attempt_history: Previous recovery attempts

        Returns:
            True if recovery should be attempted
        """
        pass

    @abstractmethod
    async def get_recovery_strategy(
        self,
        instance: ClaudeInstance,
        status: HealthStatus,
        results: dict[str, HealthCheckResult],
        attempt_history: list[RecoveryAttempt],
    ) -> RecoveryStrategy:
        """Get the recovery strategy to use.

        Args:
            instance: Instance to recover
            status: Current health status
            results: Health check results
            attempt_history: Previous recovery attempts

        Returns:
            Recovery strategy to use
        """
        pass


class DefaultRecoveryPolicy(RecoveryPolicy):
    """Default recovery policy with exponential backoff."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 60.0,  # seconds
        max_delay: float = 3600.0,  # 1 hour
        backoff_multiplier: float = 2.0,
    ):
        """Initialize recovery policy.

        Args:
            max_attempts: Maximum recovery attempts within time window
            base_delay: Base delay between attempts in seconds
            max_delay: Maximum delay between attempts in seconds
            backoff_multiplier: Multiplier for exponential backoff
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.time_window = timedelta(hours=1)  # Reset attempt count after 1 hour

    async def should_recover(
        self,
        instance: ClaudeInstance,
        status: HealthStatus,
        results: dict[str, HealthCheckResult],
        attempt_history: list[RecoveryAttempt],
    ) -> bool:
        """Check if recovery should be attempted."""
        # Don't recover if status is not critical enough
        if status not in [HealthStatus.CRITICAL, HealthStatus.UNHEALTHY]:
            return False

        # Filter recent attempts
        now = datetime.now()
        recent_attempts = [
            attempt
            for attempt in attempt_history
            if (now - attempt.timestamp) <= self.time_window
        ]

        # Check if we've exceeded max attempts
        if len(recent_attempts) >= self.max_attempts:
            logger.info(
                "Recovery attempts exceeded",
                instance_id=instance.issue_id,
                recent_attempts=len(recent_attempts),
                max_attempts=self.max_attempts,
            )
            return False

        # Check if we need to wait due to backoff
        if recent_attempts:
            last_attempt = max(recent_attempts, key=lambda x: x.timestamp)
            attempt_count = len(recent_attempts)

            # Calculate required delay
            delay = min(
                self.base_delay * (self.backoff_multiplier ** (attempt_count - 1)),
                self.max_delay,
            )

            time_since_last = (now - last_attempt.timestamp).total_seconds()
            if time_since_last < delay:
                logger.debug(
                    "Recovery delayed due to backoff",
                    instance_id=instance.issue_id,
                    time_since_last=time_since_last,
                    required_delay=delay,
                )
                return False

        return True

    async def get_recovery_strategy(
        self,
        instance: ClaudeInstance,
        status: HealthStatus,
        results: dict[str, HealthCheckResult],
        attempt_history: list[RecoveryAttempt],
    ) -> RecoveryStrategy:
        """Determine recovery strategy based on status and history."""
        # Filter recent attempts
        now = datetime.now()
        recent_attempts = [
            attempt
            for attempt in attempt_history
            if (now - attempt.timestamp) <= self.time_window
        ]

        # Escalate strategy based on attempt count
        if not recent_attempts:
            # First attempt - try restart
            return RecoveryStrategy.RESTART
        elif len(recent_attempts) == 1:
            # Second attempt - try restart again
            return RecoveryStrategy.RESTART
        else:
            # Further attempts - try recreate
            return RecoveryStrategy.RECREATE


class RecoveryManager:
    """Manages recovery of unhealthy Claude instances."""

    def __init__(self, policy: RecoveryPolicy | None = None):
        """Initialize recovery manager.

        Args:
            policy: Recovery policy to use (creates default if None)
        """
        self.policy = policy or DefaultRecoveryPolicy()
        self._recovery_history: dict[str, list[RecoveryAttempt]] = {}
        self._recovery_locks: dict[str, asyncio.Lock] = {}

        logger.info("Recovery manager initialized")

    async def should_recover(
        self,
        instance: ClaudeInstance,
        status: HealthStatus,
        results: dict[str, HealthCheckResult],
    ) -> bool:
        """Check if instance should be recovered.

        Args:
            instance: Instance to evaluate
            status: Current health status
            results: Health check results

        Returns:
            True if recovery should be attempted
        """
        instance_id = instance.issue_id
        attempt_history = self._recovery_history.get(instance_id, [])

        return await self.policy.should_recover(
            instance, status, results, attempt_history
        )

    async def recover_instance(
        self,
        instance: ClaudeInstance,
        status: HealthStatus,
        results: dict[str, HealthCheckResult],
    ) -> bool:
        """Attempt to recover an unhealthy instance.

        Args:
            instance: Instance to recover
            status: Current health status
            results: Health check results

        Returns:
            True if recovery was successful
        """
        instance_id = instance.issue_id

        # Ensure only one recovery attempt at a time per instance
        if instance_id not in self._recovery_locks:
            self._recovery_locks[instance_id] = asyncio.Lock()

        async with self._recovery_locks[instance_id]:
            return await self._perform_recovery(instance, status, results)

    async def _perform_recovery(
        self,
        instance: ClaudeInstance,
        status: HealthStatus,
        results: dict[str, HealthCheckResult],
    ) -> bool:
        """Perform the actual recovery attempt.

        Args:
            instance: Instance to recover
            status: Current health status
            results: Health check results

        Returns:
            True if recovery was successful
        """
        instance_id = instance.issue_id
        start_time = time.time()

        logger.info("Starting recovery attempt", instance_id=instance_id)

        # Get recovery strategy
        attempt_history = self._recovery_history.get(instance_id, [])
        strategy = await self.policy.get_recovery_strategy(
            instance, status, results, attempt_history
        )

        # Perform recovery based on strategy
        success = False
        error_message = None
        recovery_details = {"strategy": strategy.value}

        try:
            if strategy == RecoveryStrategy.RESTART:
                success = await self._restart_instance(instance)
                recovery_details["action"] = "restart"
            elif strategy == RecoveryStrategy.RECREATE:
                success = await self._recreate_instance(instance)
                recovery_details["action"] = "recreate"
            elif strategy == RecoveryStrategy.MANUAL:
                logger.warning("Manual recovery required", instance_id=instance_id)
                recovery_details["action"] = "manual_required"
                success = False
            else:
                logger.info("No recovery strategy available", instance_id=instance_id)
                recovery_details["action"] = "none"
                success = False

        except Exception as e:
            error_message = str(e)
            logger.error(
                "Recovery attempt failed",
                instance_id=instance_id,
                strategy=strategy.value,
                error=error_message,
            )

        # Record recovery attempt
        duration = time.time() - start_time
        attempt = RecoveryAttempt(
            instance_id=instance_id,
            strategy=strategy,
            timestamp=datetime.now(),
            success=success,
            error_message=error_message,
            duration_seconds=duration,
            details=recovery_details,
        )

        if instance_id not in self._recovery_history:
            self._recovery_history[instance_id] = []
        self._recovery_history[instance_id].append(attempt)

        # Limit history size
        history = self._recovery_history[instance_id]
        if len(history) > 20:  # Keep last 20 attempts
            history.pop(0)

        logger.info(
            "Recovery attempt completed",
            instance_id=instance_id,
            strategy=strategy.value,
            success=success,
            duration=duration,
        )

        return success

    async def _restart_instance(self, instance: ClaudeInstance) -> bool:
        """Restart an instance.

        Args:
            instance: Instance to restart

        Returns:
            True if restart was successful
        """
        instance_id = instance.issue_id
        logger.info("Restarting instance", instance_id=instance_id)

        try:
            # Stop the instance
            stop_success = await instance.stop()
            if not stop_success:
                logger.error(
                    "Failed to stop instance during restart", instance_id=instance_id
                )
                return False

            # Wait a bit before restart
            await asyncio.sleep(5.0)

            # Start the instance
            start_success = await instance.start()
            if not start_success:
                logger.error(
                    "Failed to start instance during restart", instance_id=instance_id
                )
                return False

            # Wait for instance to stabilize
            await asyncio.sleep(10.0)

            # Verify instance is running
            if instance.is_running():
                logger.info("Instance restart successful", instance_id=instance_id)
                return True
            else:
                logger.error(
                    "Instance not running after restart", instance_id=instance_id
                )
                return False

        except Exception as e:
            logger.error(
                "Error during instance restart", instance_id=instance_id, error=str(e)
            )
            raise  # Re-raise the exception to be caught by outer handler

    async def _recreate_instance(self, instance: ClaudeInstance) -> bool:
        """Recreate an instance (stop, cleanup, reinitialize, start).

        Args:
            instance: Instance to recreate

        Returns:
            True if recreation was successful
        """
        instance_id = instance.issue_id
        logger.info("Recreating instance", instance_id=instance_id)

        try:
            # Stop and cleanup the instance
            await instance.cleanup()

            # Wait for cleanup to complete
            await asyncio.sleep(10.0)

            # Reinitialize the instance
            await instance.initialize()

            # Start the instance
            start_success = await instance.start()
            if not start_success:
                logger.error(
                    "Failed to start recreated instance", instance_id=instance_id
                )
                return False

            # Wait for instance to stabilize
            await asyncio.sleep(15.0)

            # Verify instance is running
            if instance.is_running():
                logger.info("Instance recreation successful", instance_id=instance_id)
                return True
            else:
                logger.error(
                    "Instance not running after recreation", instance_id=instance_id
                )
                return False

        except Exception as e:
            logger.error(
                "Error during instance recreation",
                instance_id=instance_id,
                error=str(e),
            )
            raise  # Re-raise the exception to be caught by outer handler

    def get_recovery_history(self, instance_id: str) -> list[RecoveryAttempt]:
        """Get recovery history for an instance.

        Args:
            instance_id: Instance identifier

        Returns:
            List of recovery attempts
        """
        return self._recovery_history.get(instance_id, []).copy()

    def get_all_recovery_history(self) -> dict[str, list[RecoveryAttempt]]:
        """Get recovery history for all instances.

        Returns:
            Dictionary mapping instance IDs to recovery attempt lists
        """
        return {
            instance_id: attempts.copy()
            for instance_id, attempts in self._recovery_history.items()
        }

    def clear_recovery_history(self, instance_id: str) -> None:
        """Clear recovery history for an instance.

        Args:
            instance_id: Instance identifier
        """
        if instance_id in self._recovery_history:
            del self._recovery_history[instance_id]

        if instance_id in self._recovery_locks:
            del self._recovery_locks[instance_id]

        logger.info("Recovery history cleared", instance_id=instance_id)
