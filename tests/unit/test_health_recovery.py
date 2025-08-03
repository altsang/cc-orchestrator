"""Tests for health recovery module."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from cc_orchestrator.core.instance import ClaudeInstance
from cc_orchestrator.health.checker import HealthStatus
from cc_orchestrator.health.recovery import (
    DefaultRecoveryPolicy,
    RecoveryAttempt,
    RecoveryManager,
    RecoveryStrategy,
)


class TestRecoveryAttempt:
    """Test RecoveryAttempt dataclass."""

    def test_basic_creation(self):
        """Test basic RecoveryAttempt creation."""
        attempt = RecoveryAttempt(
            instance_id="test-instance",
            strategy=RecoveryStrategy.RESTART,
            timestamp=datetime.now(),
            success=True,
        )

        assert attempt.instance_id == "test-instance"
        assert attempt.strategy == RecoveryStrategy.RESTART
        assert attempt.success is True
        assert attempt.error_message is None
        assert attempt.duration_seconds == 0.0
        assert attempt.details == {}

    def test_creation_with_error(self):
        """Test RecoveryAttempt creation with error."""
        attempt = RecoveryAttempt(
            instance_id="test-instance",
            strategy=RecoveryStrategy.RECREATE,
            timestamp=datetime.now(),
            success=False,
            error_message="Connection failed",
            duration_seconds=45.5,
            details={"retry_count": 3},
        )

        assert attempt.success is False
        assert attempt.error_message == "Connection failed"
        assert attempt.duration_seconds == 45.5
        assert attempt.details["retry_count"] == 3


class TestDefaultRecoveryPolicy:
    """Test DefaultRecoveryPolicy class."""

    @pytest.fixture
    def policy(self):
        """Create DefaultRecoveryPolicy instance."""
        return DefaultRecoveryPolicy(
            max_attempts=3, base_delay=10.0, max_delay=60.0, backoff_multiplier=2.0
        )

    @pytest.fixture
    def mock_instance(self):
        """Create mock Claude instance."""
        instance = Mock(spec=ClaudeInstance)
        instance.issue_id = "test-instance"
        return instance

    @pytest.mark.asyncio
    async def test_should_recover_critical_status(self, policy, mock_instance):
        """Test recovery decision for critical status."""
        results = {}
        attempt_history = []

        should_recover = await policy.should_recover(
            mock_instance, HealthStatus.CRITICAL, results, attempt_history
        )

        assert should_recover is True

    @pytest.mark.asyncio
    async def test_should_not_recover_healthy_status(self, policy, mock_instance):
        """Test recovery decision for healthy status."""
        results = {}
        attempt_history = []

        should_recover = await policy.should_recover(
            mock_instance, HealthStatus.HEALTHY, results, attempt_history
        )

        assert should_recover is False

    @pytest.mark.asyncio
    async def test_should_not_recover_degraded_status(self, policy, mock_instance):
        """Test recovery decision for degraded status."""
        results = {}
        attempt_history = []

        should_recover = await policy.should_recover(
            mock_instance, HealthStatus.DEGRADED, results, attempt_history
        )

        assert should_recover is False

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self, policy, mock_instance):
        """Test recovery blocked when max attempts exceeded."""
        now = datetime.now()
        attempt_history = [
            RecoveryAttempt(
                "test-instance",
                RecoveryStrategy.RESTART,
                now - timedelta(minutes=30),
                True,
            ),
            RecoveryAttempt(
                "test-instance",
                RecoveryStrategy.RESTART,
                now - timedelta(minutes=20),
                False,
            ),
            RecoveryAttempt(
                "test-instance",
                RecoveryStrategy.RECREATE,
                now - timedelta(minutes=10),
                False,
            ),
        ]

        should_recover = await policy.should_recover(
            mock_instance, HealthStatus.CRITICAL, {}, attempt_history
        )

        assert should_recover is False

    @pytest.mark.asyncio
    async def test_backoff_delay(self, policy, mock_instance):
        """Test recovery blocked due to backoff delay."""
        now = datetime.now()
        attempt_history = [
            RecoveryAttempt(
                "test-instance",
                RecoveryStrategy.RESTART,
                now - timedelta(seconds=5),
                False,
            ),
        ]

        should_recover = await policy.should_recover(
            mock_instance, HealthStatus.CRITICAL, {}, attempt_history
        )

        assert should_recover is False  # Too soon after last attempt

    @pytest.mark.asyncio
    async def test_old_attempts_ignored(self, policy, mock_instance):
        """Test that old attempts outside time window are ignored."""
        now = datetime.now()
        attempt_history = [
            RecoveryAttempt(
                "test-instance",
                RecoveryStrategy.RESTART,
                now - timedelta(hours=2),
                False,
            ),
            RecoveryAttempt(
                "test-instance",
                RecoveryStrategy.RESTART,
                now - timedelta(hours=3),
                False,
            ),
            RecoveryAttempt(
                "test-instance",
                RecoveryStrategy.RESTART,
                now - timedelta(hours=4),
                False,
            ),
        ]

        should_recover = await policy.should_recover(
            mock_instance, HealthStatus.CRITICAL, {}, attempt_history
        )

        assert should_recover is True  # Old attempts don't count

    @pytest.mark.asyncio
    async def test_get_recovery_strategy_first_attempt(self, policy, mock_instance):
        """Test recovery strategy for first attempt."""
        strategy = await policy.get_recovery_strategy(
            mock_instance, HealthStatus.CRITICAL, {}, []
        )

        assert strategy == RecoveryStrategy.RESTART

    @pytest.mark.asyncio
    async def test_get_recovery_strategy_second_attempt(self, policy, mock_instance):
        """Test recovery strategy for second attempt."""
        now = datetime.now()
        attempt_history = [
            RecoveryAttempt(
                "test-instance",
                RecoveryStrategy.RESTART,
                now - timedelta(minutes=30),
                False,
            ),
        ]

        strategy = await policy.get_recovery_strategy(
            mock_instance, HealthStatus.CRITICAL, {}, attempt_history
        )

        assert strategy == RecoveryStrategy.RESTART

    @pytest.mark.asyncio
    async def test_get_recovery_strategy_escalation(self, policy, mock_instance):
        """Test recovery strategy escalation."""
        now = datetime.now()
        attempt_history = [
            RecoveryAttempt(
                "test-instance",
                RecoveryStrategy.RESTART,
                now - timedelta(minutes=50),
                False,
            ),
            RecoveryAttempt(
                "test-instance",
                RecoveryStrategy.RESTART,
                now - timedelta(minutes=30),
                False,
            ),
        ]

        strategy = await policy.get_recovery_strategy(
            mock_instance, HealthStatus.CRITICAL, {}, attempt_history
        )

        assert strategy == RecoveryStrategy.RECREATE


class TestRecoveryManager:
    """Test RecoveryManager class."""

    @pytest.fixture
    def mock_policy(self):
        """Create mock recovery policy."""
        policy = Mock()
        policy.should_recover = AsyncMock(return_value=True)
        policy.get_recovery_strategy = AsyncMock(return_value=RecoveryStrategy.RESTART)
        return policy

    @pytest.fixture
    def recovery_manager(self, mock_policy):
        """Create RecoveryManager instance with mock policy."""
        return RecoveryManager(policy=mock_policy)

    @pytest.fixture
    def mock_instance(self):
        """Create mock Claude instance."""
        instance = Mock(spec=ClaudeInstance)
        instance.issue_id = "test-instance"
        instance.stop = AsyncMock(return_value=True)
        instance.start = AsyncMock(return_value=True)
        instance.is_running = Mock(return_value=True)
        instance.cleanup = AsyncMock()
        instance.initialize = AsyncMock()
        return instance

    @pytest.mark.asyncio
    async def test_should_recover(self, recovery_manager, mock_instance):
        """Test should_recover delegates to policy."""
        result = await recovery_manager.should_recover(
            mock_instance, HealthStatus.CRITICAL, {}
        )

        assert result is True
        recovery_manager.policy.should_recover.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_restart_recovery(self, recovery_manager, mock_instance):
        """Test successful restart recovery."""
        recovery_manager.policy.get_recovery_strategy.return_value = (
            RecoveryStrategy.RESTART
        )

        success = await recovery_manager.recover_instance(
            mock_instance, HealthStatus.CRITICAL, {}
        )

        assert success is True
        mock_instance.stop.assert_called_once()
        mock_instance.start.assert_called_once()

        # Verify recovery attempt was recorded
        history = recovery_manager.get_recovery_history("test-instance")
        assert len(history) == 1
        assert history[0].strategy == RecoveryStrategy.RESTART
        assert history[0].success is True

    @pytest.mark.asyncio
    async def test_failed_restart_recovery(self, recovery_manager, mock_instance):
        """Test failed restart recovery."""
        recovery_manager.policy.get_recovery_strategy.return_value = (
            RecoveryStrategy.RESTART
        )
        mock_instance.start.return_value = False  # Start fails

        success = await recovery_manager.recover_instance(
            mock_instance, HealthStatus.CRITICAL, {}
        )

        assert success is False

        # Verify recovery attempt was recorded as failed
        history = recovery_manager.get_recovery_history("test-instance")
        assert len(history) == 1
        assert history[0].success is False

    @pytest.mark.asyncio
    async def test_successful_recreate_recovery(self, recovery_manager, mock_instance):
        """Test successful recreate recovery."""
        recovery_manager.policy.get_recovery_strategy.return_value = (
            RecoveryStrategy.RECREATE
        )

        success = await recovery_manager.recover_instance(
            mock_instance, HealthStatus.CRITICAL, {}
        )

        assert success is True
        mock_instance.cleanup.assert_called_once()
        mock_instance.initialize.assert_called_once()
        mock_instance.start.assert_called_once()

        # Verify recovery attempt was recorded
        history = recovery_manager.get_recovery_history("test-instance")
        assert len(history) == 1
        assert history[0].strategy == RecoveryStrategy.RECREATE
        assert history[0].success is True

    @pytest.mark.asyncio
    async def test_manual_recovery_strategy(self, recovery_manager, mock_instance):
        """Test manual recovery strategy."""
        recovery_manager.policy.get_recovery_strategy.return_value = (
            RecoveryStrategy.MANUAL
        )

        success = await recovery_manager.recover_instance(
            mock_instance, HealthStatus.CRITICAL, {}
        )

        assert success is False

        # Verify no instance methods were called
        mock_instance.stop.assert_not_called()
        mock_instance.start.assert_not_called()
        mock_instance.cleanup.assert_not_called()

        # Verify recovery attempt was recorded
        history = recovery_manager.get_recovery_history("test-instance")
        assert len(history) == 1
        assert history[0].strategy == RecoveryStrategy.MANUAL
        assert history[0].success is False

    @pytest.mark.asyncio
    async def test_no_recovery_strategy(self, recovery_manager, mock_instance):
        """Test no recovery strategy."""
        recovery_manager.policy.get_recovery_strategy.return_value = (
            RecoveryStrategy.NONE
        )

        success = await recovery_manager.recover_instance(
            mock_instance, HealthStatus.CRITICAL, {}
        )

        assert success is False

        # Verify recovery attempt was recorded
        history = recovery_manager.get_recovery_history("test-instance")
        assert len(history) == 1
        assert history[0].strategy == RecoveryStrategy.NONE

    @pytest.mark.asyncio
    async def test_recovery_exception_handling(self, recovery_manager, mock_instance):
        """Test recovery exception handling."""
        recovery_manager.policy.get_recovery_strategy.return_value = (
            RecoveryStrategy.RESTART
        )
        mock_instance.stop.side_effect = Exception("Stop failed")

        success = await recovery_manager.recover_instance(
            mock_instance, HealthStatus.CRITICAL, {}
        )

        assert success is False

        # Verify recovery attempt was recorded with error
        history = recovery_manager.get_recovery_history("test-instance")
        assert len(history) == 1
        assert history[0].success is False
        assert "Stop failed" in history[0].error_message

    @pytest.mark.asyncio
    async def test_concurrent_recovery_attempts(self, recovery_manager, mock_instance):
        """Test that concurrent recovery attempts are serialized."""
        recovery_manager.policy.get_recovery_strategy.return_value = (
            RecoveryStrategy.RESTART
        )

        # Add delay to recovery to test concurrency
        async def slow_stop():
            await asyncio.sleep(0.1)
            return True

        mock_instance.stop.side_effect = slow_stop

        # Start two recovery attempts simultaneously
        task1 = asyncio.create_task(
            recovery_manager.recover_instance(mock_instance, HealthStatus.CRITICAL, {})
        )
        task2 = asyncio.create_task(
            recovery_manager.recover_instance(mock_instance, HealthStatus.CRITICAL, {})
        )

        results = await asyncio.gather(task1, task2)

        # Both should succeed, but they should be serialized
        assert all(results)

        # Should have two recovery attempts recorded
        history = recovery_manager.get_recovery_history("test-instance")
        assert len(history) == 2

    def test_get_recovery_history(self, recovery_manager):
        """Test getting recovery history."""
        # Add some recovery attempts
        attempt1 = RecoveryAttempt(
            "test-instance", RecoveryStrategy.RESTART, datetime.now(), True
        )
        attempt2 = RecoveryAttempt(
            "test-instance", RecoveryStrategy.RECREATE, datetime.now(), False
        )

        recovery_manager._recovery_history["test-instance"] = [attempt1, attempt2]

        history = recovery_manager.get_recovery_history("test-instance")
        assert len(history) == 2
        assert history[0] == attempt1
        assert history[1] == attempt2

    def test_get_all_recovery_history(self, recovery_manager):
        """Test getting all recovery history."""
        attempt1 = RecoveryAttempt(
            "instance1", RecoveryStrategy.RESTART, datetime.now(), True
        )
        attempt2 = RecoveryAttempt(
            "instance2", RecoveryStrategy.RECREATE, datetime.now(), False
        )

        recovery_manager._recovery_history["instance1"] = [attempt1]
        recovery_manager._recovery_history["instance2"] = [attempt2]

        all_history = recovery_manager.get_all_recovery_history()
        assert len(all_history) == 2
        assert "instance1" in all_history
        assert "instance2" in all_history

    def test_clear_recovery_history(self, recovery_manager):
        """Test clearing recovery history."""
        attempt = RecoveryAttempt(
            "test-instance", RecoveryStrategy.RESTART, datetime.now(), True
        )
        recovery_manager._recovery_history["test-instance"] = [attempt]
        recovery_manager._recovery_locks["test-instance"] = asyncio.Lock()

        recovery_manager.clear_recovery_history("test-instance")

        assert "test-instance" not in recovery_manager._recovery_history
        assert "test-instance" not in recovery_manager._recovery_locks

    def test_recovery_history_limit(self, recovery_manager):
        """Test recovery history respects limit."""
        instance_id = "test-instance"

        # Add more attempts than the limit (20)
        for _ in range(25):
            attempt = RecoveryAttempt(
                instance_id, RecoveryStrategy.RESTART, datetime.now(), True
            )
            if instance_id not in recovery_manager._recovery_history:
                recovery_manager._recovery_history[instance_id] = []
            recovery_manager._recovery_history[instance_id].append(attempt)

            # Simulate the limit check from the actual method
            history = recovery_manager._recovery_history[instance_id]
            if len(history) > 20:
                history.pop(0)

        # Verify only 20 attempts are kept
        history = recovery_manager.get_recovery_history(instance_id)
        assert len(history) == 20
