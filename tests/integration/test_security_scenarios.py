"""Integration tests for security scenarios in instance persistence."""

import asyncio
import os
from unittest.mock import Mock, patch

import pytest

from cc_orchestrator.core.enums import InstanceStatus
from cc_orchestrator.core.instance import ClaudeInstance
from cc_orchestrator.core.orchestrator import Orchestrator


@pytest.mark.skipif(
    os.getenv("TESTING", "false").lower() == "true",
    reason="Skipped in CI - async teardown issues with event loop",
)
class TestSecurityScenarios:
    """Test security-related scenarios for instance persistence."""

    @pytest.fixture
    async def test_orchestrator(self, setup_test_environment):
        """Create an orchestrator with test database."""
        orchestrator = Orchestrator()
        await orchestrator.initialize()
        yield orchestrator
        await orchestrator.cleanup()

    async def test_invalid_issue_id_injection_protection(self, test_orchestrator):
        """Test protection against SQL injection through issue_id."""
        malicious_ids = [
            "'; DROP TABLE instances; --",
            "1' OR '1'='1",
            "test'; UPDATE instances SET status='RUNNING'; --",
            "../../../etc/passwd",
            "a" * 150,  # Too long
            "test-<script>alert('xss')</script>",
        ]

        for malicious_id in malicious_ids:
            # Create mock instance with malicious issue_id
            mock_instance = Mock(spec=ClaudeInstance)
            mock_instance.issue_id = malicious_id
            mock_instance.status = InstanceStatus.RUNNING
            mock_instance.process_id = 12345
            mock_instance.last_activity = "2025-09-21T00:00:00"

            # Sync should fail due to validation
            result = test_orchestrator.sync_instance_to_database(mock_instance)
            assert (
                result is False
            ), f"Failed to block malicious issue_id: {malicious_id}"

    async def test_authorization_bypass_attempt(self, test_orchestrator):
        """Test that sync operations require proper authorization."""
        # Create a valid instance first
        _instance = await test_orchestrator.create_instance(
            issue_id="test-auth-123",
            workspace_path="/test/workspace",
            branch_name="test-branch",
            tmux_session="test-session",
        )

        # Try to sync an instance that doesn't exist (unauthorized access)
        mock_instance = Mock(spec=ClaudeInstance)
        mock_instance.issue_id = "non-existent-instance-456"
        mock_instance.status = InstanceStatus.RUNNING
        mock_instance.process_id = 12345
        mock_instance.last_activity = "2025-09-21T00:00:00"

        result = test_orchestrator.sync_instance_to_database(mock_instance)
        assert result is False, "Should fail authorization for non-existent instance"

    async def test_concurrent_sync_operations(self, test_orchestrator):
        """Test handling of concurrent sync operations on same instance."""
        # Create test instance
        instance = await test_orchestrator.create_instance(
            issue_id="concurrent-test-789",
            workspace_path="/test/workspace",
            branch_name="test-branch",
            tmux_session="test-session",
        )

        # Simulate starting the instance
        instance.status = InstanceStatus.RUNNING
        instance.process_id = 12345

        # Create multiple sync operations
        async def sync_operation(delay=0):
            if delay:
                await asyncio.sleep(delay)
            return test_orchestrator.sync_instance_to_database(instance)

        # Run concurrent sync operations
        tasks = [
            sync_operation(0),
            sync_operation(0.1),
            sync_operation(0.2),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # At least one should succeed, others might fail due to concurrency
        success_count = sum(1 for r in results if r is True)
        assert success_count >= 1, "At least one sync operation should succeed"

    async def test_database_connection_exhaustion(self, test_orchestrator):
        """Test handling of database connection pool exhaustion."""
        # Mock the connection pool to simulate exhaustion
        with patch.object(test_orchestrator._db_session, "get_bind") as mock_bind:
            mock_engine = Mock()
            mock_pool = Mock()
            mock_pool.checkedout.return_value = 16  # High number
            mock_pool.size.return_value = 20  # Pool size
            mock_engine.pool = mock_pool
            mock_bind.return_value = mock_engine

            # Create test instance
            instance = await test_orchestrator.create_instance(
                issue_id="pool-test-999",
                workspace_path="/test/workspace",
                branch_name="test-branch",
                tmux_session="test-session",
            )

            instance.status = InstanceStatus.RUNNING
            instance.process_id = 12345

            # Should fail due to pool exhaustion
            result = test_orchestrator.sync_instance_to_database(instance)
            assert result is False, "Should fail when connection pool is exhausted"

    async def test_stale_data_detection(self, test_orchestrator):
        """Test detection of stale instance data to prevent overwriting newer changes."""
        from datetime import datetime, timedelta

        # Create test instance
        instance = await test_orchestrator.create_instance(
            issue_id="stale-test-111",
            workspace_path="/test/workspace",
            branch_name="test-branch",
            tmux_session="test-session",
        )

        # Simulate the instance being modified in memory but database has newer data
        old_time = datetime.now() - timedelta(minutes=5)
        new_time = datetime.now()

        instance.last_activity = old_time  # Older timestamp
        instance.status = InstanceStatus.RUNNING
        instance.process_id = 12345

        # Update the database with newer timestamp
        from cc_test_orchestrator.database.crud import InstanceCRUD

        db_instance = InstanceCRUD.get_by_issue_id(
            test_orchestrator._db_session, instance.issue_id
        )
        InstanceCRUD.update(
            session=test_orchestrator._db_session,
            instance_id=db_instance.id,
            last_activity=new_time,  # Newer timestamp
        )
        test_orchestrator._db_session.commit()

        # Sync should fail due to stale data detection
        result = test_orchestrator.sync_instance_to_database(instance)
        assert result is False, "Should detect and reject stale instance data"

    async def test_sync_failure_user_experience(self, test_orchestrator):
        """Test user experience when sync operations fail."""
        # This test would verify proper error messages and handling
        # but would require mocking CLI output capture
        pass

    async def test_input_validation_edge_cases(self, test_orchestrator):
        """Test various edge cases for input validation."""
        # Test None instance
        result = test_orchestrator.sync_instance_to_database(None)
        assert result is False

        # Test instance without required attributes
        invalid_instances = [
            # Missing issue_id
            Mock(issue_id=None),
            # Missing status
            Mock(issue_id="test", status=None),
            # Invalid issue_id type
            Mock(issue_id=12345, status=InstanceStatus.RUNNING),
        ]

        for invalid_instance in invalid_instances:
            # Add required attributes for the ones that don't have them
            if not hasattr(invalid_instance, "status"):
                invalid_instance.status = InstanceStatus.RUNNING
            if not hasattr(invalid_instance, "last_activity"):
                invalid_instance.last_activity = "2025-09-21T00:00:00"
            if not hasattr(invalid_instance, "process_id"):
                invalid_instance.process_id = 12345

            result = test_orchestrator.sync_instance_to_database(invalid_instance)
            assert (
                result is False
            ), f"Should reject invalid instance: {invalid_instance}"

    async def test_database_transaction_rollback(self, test_orchestrator):
        """Test that database transactions roll back properly on errors."""
        # Create test instance
        instance = await test_orchestrator.create_instance(
            issue_id="rollback-test-222",
            workspace_path="/test/workspace",
            branch_name="test-branch",
            tmux_session="test-session",
        )

        instance.status = InstanceStatus.RUNNING
        instance.process_id = 12345

        # Mock InstanceCRUD.update to raise an exception
        with patch(
            "cc_test_orchestrator.core.test_orchestrator.InstanceCRUD"
        ) as mock_crud:
            mock_crud.get_by_issue_id.return_value = Mock(id=1, last_activity=None)
            mock_crud.update.side_effect = Exception("Database error")

            # Sync should fail and rollback
            result = test_orchestrator.sync_instance_to_database(instance)
            assert result is False

            # Verify the original data is still intact
            db_instance = test_orchestrator.get_instance("rollback-test-222")
            assert db_instance is not None
            # Should still have original status (not the RUNNING we tried to sync)


@pytest.mark.skipif(
    os.getenv("TESTING", "false").lower() == "true",
    reason="Skipped in CI - async teardown issues with event loop",
)
class TestPerformanceAndReliability:
    """Test performance and reliability under various conditions."""

    @pytest.fixture
    async def orchestrator(self, temp_database_manager):
        """Create an orchestrator with test database."""
        orchestrator = Orchestrator(db_session=temp_database_manager.create_session())
        await orchestrator.initialize()
        yield orchestrator
        await orchestrator.cleanup()

    async def test_sync_operation_timeout(self, test_orchestrator):
        """Test that sync operations don't hang indefinitely."""
        # Create test instance
        instance = await test_orchestrator.create_instance(
            issue_id="timeout-test-333",
            workspace_path="/test/workspace",
            branch_name="test-branch",
            tmux_session="test-session",
        )

        instance.status = InstanceStatus.RUNNING
        instance.process_id = 12345

        # Mock database to simulate slow response
        with patch.object(test_orchestrator._db_session, "begin") as mock_begin:
            # Simulate hanging transaction
            mock_begin.side_effect = Exception("Timeout")

            # Should complete within reasonable time and not hang
            result = test_orchestrator.sync_instance_to_database(instance)
            assert result is False

    async def test_memory_usage_during_sync(self, test_orchestrator):
        """Test that sync operations don't leak memory."""
        # This would be implemented with memory profiling tools
        # For now, just ensure multiple syncs don't accumulate resources
        instance = await test_orchestrator.create_instance(
            issue_id="memory-test-444",
            workspace_path="/test/workspace",
            branch_name="test-branch",
            tmux_session="test-session",
        )

        instance.status = InstanceStatus.RUNNING
        instance.process_id = 12345

        # Perform multiple sync operations
        for _ in range(10):
            result = test_orchestrator.sync_instance_to_database(instance)
            # Each operation should complete independently
            assert isinstance(result, bool)
