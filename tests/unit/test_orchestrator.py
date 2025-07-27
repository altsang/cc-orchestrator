"""Unit tests for Orchestrator class."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from cc_orchestrator.core.instance import ClaudeInstance
from cc_orchestrator.core.orchestrator import Orchestrator


class TestOrchestrator:
    """Test suite for Orchestrator class."""

    def test_init_default(self):
        """Test orchestrator initialization with defaults."""
        orchestrator = Orchestrator()
        assert orchestrator.config_path is None
        assert orchestrator.instances == {}
        assert orchestrator._initialized is False

    def test_init_with_config(self):
        """Test orchestrator initialization with config path."""
        config_path = "/path/to/config.yaml"
        orchestrator = Orchestrator(config_path=config_path)
        assert orchestrator.config_path == config_path
        assert orchestrator.instances == {}
        assert orchestrator._initialized is False

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test orchestrator initialization."""
        orchestrator = Orchestrator()
        await orchestrator.initialize()
        assert orchestrator._initialized is True

    def test_get_instance_existing(self):
        """Test getting an existing instance."""
        orchestrator = Orchestrator()
        mock_instance = Mock(spec=ClaudeInstance)
        mock_instance.issue_id = "test-123"
        orchestrator.instances["test-123"] = mock_instance

        result = orchestrator.get_instance("test-123")
        assert result == mock_instance

    def test_get_instance_nonexistent(self):
        """Test getting a non-existent instance."""
        orchestrator = Orchestrator()
        result = orchestrator.get_instance("nonexistent")
        assert result is None

    def test_list_instances_empty(self):
        """Test listing instances when none exist."""
        orchestrator = Orchestrator()
        result = orchestrator.list_instances()
        assert result == []

    def test_list_instances_with_data(self):
        """Test listing instances with data."""
        orchestrator = Orchestrator()
        mock_instance1 = Mock(spec=ClaudeInstance)
        mock_instance2 = Mock(spec=ClaudeInstance)
        orchestrator.instances = {
            "issue-1": mock_instance1,
            "issue-2": mock_instance2,
        }

        result = orchestrator.list_instances()
        assert len(result) == 2
        assert mock_instance1 in result
        assert mock_instance2 in result

    @pytest.mark.asyncio
    async def test_create_instance_success(self):
        """Test successful instance creation."""
        orchestrator = Orchestrator()

        with patch(
            "cc_orchestrator.core.orchestrator.ClaudeInstance"
        ) as mock_claude_instance_class:
            mock_instance = AsyncMock()
            mock_instance.issue_id = "test-123"
            mock_claude_instance_class.return_value = mock_instance

            result = await orchestrator.create_instance(
                "test-123", workspace_path="/tmp/test"
            )

            assert result == mock_instance
            assert orchestrator.instances["test-123"] == mock_instance
            mock_instance.initialize.assert_called_once()
            mock_claude_instance_class.assert_called_once_with(
                issue_id="test-123", workspace_path="/tmp/test"
            )

    @pytest.mark.asyncio
    async def test_create_instance_already_exists(self):
        """Test creating instance that already exists."""
        orchestrator = Orchestrator()
        mock_instance = Mock(spec=ClaudeInstance)
        orchestrator.instances["test-123"] = mock_instance

        with pytest.raises(
            ValueError, match="Instance for issue test-123 already exists"
        ):
            await orchestrator.create_instance("test-123")

    @pytest.mark.asyncio
    async def test_destroy_instance_success(self):
        """Test successful instance destruction."""
        orchestrator = Orchestrator()
        mock_instance = AsyncMock()
        orchestrator.instances["test-123"] = mock_instance

        result = await orchestrator.destroy_instance("test-123")

        assert result is True
        assert "test-123" not in orchestrator.instances
        mock_instance.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_destroy_instance_not_found(self):
        """Test destroying non-existent instance."""
        orchestrator = Orchestrator()

        result = await orchestrator.destroy_instance("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test orchestrator cleanup."""
        orchestrator = Orchestrator()
        mock_instance1 = AsyncMock()
        mock_instance2 = AsyncMock()
        orchestrator.instances = {
            "issue-1": mock_instance1,
            "issue-2": mock_instance2,
        }

        await orchestrator.cleanup()

        assert orchestrator.instances == {}
        mock_instance1.cleanup.assert_called_once()
        mock_instance2.cleanup.assert_called_once()
