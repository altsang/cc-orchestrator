"""Comprehensive unit tests for CLI worktrees module."""

import json
from datetime import datetime
from unittest.mock import Mock, patch

from click.testing import CliRunner

from cc_orchestrator.cli.main import main
from cc_orchestrator.core.worktree_service import WorktreeServiceError


class TestWorktreesCLI:
    """Test suite for worktree CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_worktrees_help(self):
        """Test worktrees command group help."""
        result = self.runner.invoke(main, ["worktrees", "--help"])
        assert result.exit_code == 0
        assert "Manage git worktrees" in result.output

    # List command tests
    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_list_no_worktrees_table_format(self, mock_service_class):
        """Test list command with no worktrees in table format."""
        # Setup mock service
        mock_service = Mock()
        mock_service.list_worktrees.return_value = []
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "list"])
        assert result.exit_code == 0
        assert "No worktrees found." in result.output
        mock_service.list_worktrees.assert_called_once_with(sync_with_git=True)

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_list_worktrees_table_format(self, mock_service_class):
        """Test list command with worktrees in table format."""
        # Setup mock service with worktree data
        mock_service = Mock()
        mock_worktrees = [
            {
                "id": 1,
                "name": "test-worktree",
                "branch": "feature-test",
                "status": "active",
                "path": "/path/to/worktree",
            },
            {
                "id": 2,
                "name": "another-wt",
                "branch": "bug-fix",
                "status": "stale",
                "path": "/path/to/another",
            },
        ]
        mock_service.list_worktrees.return_value = mock_worktrees
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "list", "--format", "table"])
        assert result.exit_code == 0
        assert (
            "ID  | Name             | Branch           | Status   | Path"
            in result.output
        )
        assert (
            "1   | test-worktree   | feature-test    | active   | /path/to/worktree"
            in result.output
        )
        assert (
            "2   | another-wt      | bug-fix         | stale    | /path/to/another"
            in result.output
        )
        mock_service.list_worktrees.assert_called_once_with(sync_with_git=True)

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_list_worktrees_json_format_with_datetime(self, mock_service_class):
        """Test list command with JSON format and datetime serialization."""
        # Setup mock service with datetime objects
        mock_service = Mock()
        test_datetime = datetime(2023, 12, 25, 10, 30, 0)
        mock_worktrees = [
            {
                "id": 1,
                "name": "test-worktree",
                "branch": "feature-test",
                "status": "active",
                "path": "/path/to/worktree",
                "created_at": test_datetime,
                "last_sync": test_datetime,
            }
        ]
        mock_service.list_worktrees.return_value = mock_worktrees
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "list", "--format", "json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert len(output_data) == 1
        assert output_data[0]["id"] == 1
        assert output_data[0]["name"] == "test-worktree"
        # Check that datetime was converted to ISO format
        assert output_data[0]["created_at"] == "2023-12-25T10:30:00"
        assert output_data[0]["last_sync"] == "2023-12-25T10:30:00"

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_list_no_sync_option(self, mock_service_class):
        """Test list command with --no-sync option."""
        mock_service = Mock()
        mock_service.list_worktrees.return_value = []
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "list", "--no-sync"])
        assert result.exit_code == 0
        mock_service.list_worktrees.assert_called_once_with(sync_with_git=False)

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_list_service_error(self, mock_service_class):
        """Test list command WorktreeServiceError handling."""
        mock_service = Mock()
        mock_service.list_worktrees.side_effect = WorktreeServiceError(
            "Test service error"
        )
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "list"])
        assert result.exit_code == 1  # click.Abort()
        assert "Error: Test service error" in result.output

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_list_unexpected_error(self, mock_service_class):
        """Test list command general Exception handling."""
        mock_service = Mock()
        mock_service.list_worktrees.side_effect = Exception("Unexpected error")
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "list"])
        assert result.exit_code == 1  # click.Abort()
        assert "Unexpected error: Unexpected error" in result.output

    # Create command tests
    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_create_worktree_table_format(self, mock_service_class):
        """Test create command with table format output."""
        mock_service = Mock()
        mock_worktree = {
            "name": "test-worktree",
            "path": "/path/to/worktree",
            "branch": "feature-test",
            "commit": "abcd1234567890",
            "instance_id": None,
        }
        mock_service.create_worktree.return_value = mock_worktree
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(
            main, ["worktrees", "create", "test-worktree", "feature-test"]
        )
        assert result.exit_code == 0
        assert "✓ Created worktree 'test-worktree'" in result.output
        assert "Path: /path/to/worktree" in result.output
        assert "Branch: feature-test" in result.output
        assert "Commit: abcd1234..." in result.output
        # Instance ID should not appear when None
        assert "Instance:" not in result.output

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_create_worktree_table_format_with_instance_id(self, mock_service_class):
        """Test create command with table format output including instance_id."""
        mock_service = Mock()
        mock_worktree = {
            "name": "test-worktree",
            "path": "/path/to/worktree",
            "branch": "feature-test",
            "commit": "abcd1234567890",
            "instance_id": 123,
        }
        mock_service.create_worktree.return_value = mock_worktree
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(
            main, ["worktrees", "create", "test-worktree", "feature-test"]
        )
        assert result.exit_code == 0
        assert "✓ Created worktree 'test-worktree'" in result.output
        assert "Instance: 123" in result.output

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_create_worktree_json_format(self, mock_service_class):
        """Test create command with JSON format output."""
        mock_service = Mock()
        mock_worktree = {
            "name": "test-worktree",
            "path": "/path/to/worktree",
            "branch": "feature-test",
            "commit": "abcd1234567890",
            "instance_id": None,
        }
        mock_service.create_worktree.return_value = mock_worktree
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(
            main,
            [
                "worktrees",
                "create",
                "test-worktree",
                "feature-test",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data["name"] == "test-worktree"
        assert output_data["path"] == "/path/to/worktree"
        assert output_data["branch"] == "feature-test"

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_create_worktree_all_options(self, mock_service_class):
        """Test create command with all options."""
        mock_service = Mock()
        mock_worktree = {
            "name": "test-worktree",
            "path": "/custom/path",
            "branch": "feature-test",
            "commit": "abcd1234567890",
            "instance_id": 456,
        }
        mock_service.create_worktree.return_value = mock_worktree
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(
            main,
            [
                "worktrees",
                "create",
                "test-worktree",
                "feature-test",
                "--path",
                "/custom/path",
                "--from-branch",
                "main",
                "--instance-id",
                "456",
                "--force",
            ],
        )
        assert result.exit_code == 0

        mock_service.create_worktree.assert_called_once_with(
            name="test-worktree",
            branch="feature-test",
            checkout_branch="main",
            custom_path="/custom/path",
            instance_id=456,
            force=True,
        )

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_create_service_error(self, mock_service_class):
        """Test create command WorktreeServiceError handling."""
        mock_service = Mock()
        mock_service.create_worktree.side_effect = WorktreeServiceError(
            "Creation failed"
        )
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(
            main, ["worktrees", "create", "test-worktree", "feature-test"]
        )
        assert result.exit_code == 1
        assert "Error: Creation failed" in result.output

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_create_unexpected_error(self, mock_service_class):
        """Test create command general Exception handling."""
        mock_service = Mock()
        mock_service.create_worktree.side_effect = Exception(
            "Unexpected creation error"
        )
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(
            main, ["worktrees", "create", "test-worktree", "feature-test"]
        )
        assert result.exit_code == 1
        assert "Unexpected error: Unexpected creation error" in result.output

    # Remove command tests
    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_remove_worktree_by_id(self, mock_service_class):
        """Test remove command with ID parsing."""
        mock_service = Mock()
        mock_service.remove_worktree.return_value = True
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "remove", "123"])
        assert result.exit_code == 0
        assert "✓ Successfully removed worktree: 123" in result.output
        mock_service.remove_worktree.assert_called_once_with(123, force=False)

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_remove_worktree_by_path(self, mock_service_class):
        """Test remove command with path."""
        mock_service = Mock()
        mock_service.remove_worktree.return_value = True
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "remove", "/path/to/worktree"])
        assert result.exit_code == 0
        assert "✓ Successfully removed worktree: /path/to/worktree" in result.output
        mock_service.remove_worktree.assert_called_once_with(
            "/path/to/worktree", force=False
        )

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_remove_worktree_with_force(self, mock_service_class):
        """Test remove command with force option."""
        mock_service = Mock()
        mock_service.remove_worktree.return_value = True
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "remove", "123", "--force"])
        assert result.exit_code == 0
        mock_service.remove_worktree.assert_called_once_with(123, force=True)

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_remove_worktree_failure(self, mock_service_class):
        """Test remove command failure path."""
        mock_service = Mock()
        mock_service.remove_worktree.return_value = False
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "remove", "123"])
        assert result.exit_code == 1
        assert "Failed to remove worktree: 123" in result.output

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_remove_service_error(self, mock_service_class):
        """Test remove command WorktreeServiceError handling."""
        mock_service = Mock()
        mock_service.remove_worktree.side_effect = WorktreeServiceError("Remove failed")
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "remove", "123"])
        assert result.exit_code == 1
        assert "Error: Remove failed" in result.output

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_remove_unexpected_error(self, mock_service_class):
        """Test remove command general Exception handling."""
        mock_service = Mock()
        mock_service.remove_worktree.side_effect = Exception("Unexpected remove error")
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "remove", "123"])
        assert result.exit_code == 1
        assert "Unexpected error: Unexpected remove error" in result.output

    # Cleanup command tests
    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_cleanup_no_cleanup_needed(self, mock_service_class):
        """Test cleanup command when no cleanup is needed."""
        mock_service = Mock()
        mock_service.cleanup_worktrees.return_value = {
            "git_cleaned": [],
            "db_cleaned": [],
        }
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "cleanup"])
        assert result.exit_code == 0
        assert "✓ No cleanup needed - all worktrees are up to date" in result.output

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_cleanup_with_results(self, mock_service_class):
        """Test cleanup command with git and db cleanup results."""
        mock_service = Mock()
        mock_service.cleanup_worktrees.return_value = {
            "git_cleaned": ["/path/to/stale1", "/path/to/stale2"],
            "db_cleaned": ["/path/to/db1"],
        }
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "cleanup"])
        assert result.exit_code == 0
        assert "✓ Cleanup completed:" in result.output
        assert "Git references cleaned: 2" in result.output
        assert "- /path/to/stale1" in result.output
        assert "- /path/to/stale2" in result.output
        assert "Database records cleaned: 1" in result.output
        assert "- /path/to/db1" in result.output

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_cleanup_json_format(self, mock_service_class):
        """Test cleanup command with JSON format."""
        mock_service = Mock()
        cleanup_result = {
            "git_cleaned": ["/path/to/stale1"],
            "db_cleaned": ["/path/to/db1"],
        }
        mock_service.cleanup_worktrees.return_value = cleanup_result
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "cleanup", "--format", "json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data == cleanup_result

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_cleanup_service_error(self, mock_service_class):
        """Test cleanup command WorktreeServiceError handling."""
        mock_service = Mock()
        mock_service.cleanup_worktrees.side_effect = WorktreeServiceError(
            "Cleanup failed"
        )
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "cleanup"])
        assert result.exit_code == 1
        assert "Error: Cleanup failed" in result.output

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_cleanup_unexpected_error(self, mock_service_class):
        """Test cleanup command general Exception handling."""
        mock_service = Mock()
        mock_service.cleanup_worktrees.side_effect = Exception(
            "Unexpected cleanup error"
        )
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "cleanup"])
        assert result.exit_code == 1
        assert "Unexpected error: Unexpected cleanup error" in result.output

    # Status command tests
    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_status_by_id(self, mock_service_class):
        """Test status command with ID parsing."""
        mock_service = Mock()
        mock_status = {
            "id": 123,
            "name": "test-worktree",
            "path": "/path/to/worktree",
            "branch": "feature-test",
            "db_status": "active",
            "git_status": {
                "commit": "abcd1234567890",
                "has_changes": False,
                "is_dirty": False,
                "ahead": 0,
                "behind": 0,
            },
            "instance_id": None,
        }
        mock_service.get_worktree_status.return_value = mock_status
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "status", "123"])
        assert result.exit_code == 0
        assert "Worktree: test-worktree (ID: 123)" in result.output
        assert "Path: /path/to/worktree" in result.output
        assert "Branch: feature-test" in result.output
        assert "Database Status: active" in result.output
        assert "Current Commit: abcd1234..." in result.output
        assert "Has Changes: No" in result.output
        assert "Is Dirty: No" in result.output
        mock_service.get_worktree_status.assert_called_once_with(123)

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_status_by_path(self, mock_service_class):
        """Test status command with path."""
        mock_service = Mock()
        mock_status = {
            "id": 456,
            "name": "test-worktree",
            "path": "/path/to/worktree",
            "branch": "feature-test",
            "db_status": "active",
            "git_status": {
                "commit": "abcd1234567890",
                "has_changes": True,
                "is_dirty": True,
                "ahead": 2,
                "behind": 1,
            },
            "instance_id": 789,
        }
        mock_service.get_worktree_status.return_value = mock_status
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "status", "/path/to/worktree"])
        assert result.exit_code == 0
        assert "Has Changes: Yes" in result.output
        assert "Is Dirty: Yes" in result.output
        assert "Ahead by: 2 commits" in result.output
        assert "Behind by: 1 commits" in result.output
        assert "Instance: 789" in result.output
        mock_service.get_worktree_status.assert_called_once_with("/path/to/worktree")

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_status_json_format_with_datetime(self, mock_service_class):
        """Test status command JSON format with datetime serialization."""
        mock_service = Mock()
        test_datetime = datetime(2023, 12, 25, 10, 30, 0)
        mock_status = {
            "id": 123,
            "name": "test-worktree",
            "path": "/path/to/worktree",
            "branch": "feature-test",
            "db_status": "active",
            "git_status": {
                "commit": "abcd1234567890",
                "has_changes": False,
                "is_dirty": False,
                "ahead": 0,
                "behind": 0,
            },
            "instance_id": None,
            "created_at": test_datetime,
            "last_sync": test_datetime,
        }
        mock_service.get_worktree_status.return_value = mock_status
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(
            main, ["worktrees", "status", "123", "--format", "json"]
        )
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data["id"] == 123
        assert output_data["name"] == "test-worktree"
        # Check that datetime was converted to ISO format
        assert output_data["created_at"] == "2023-12-25T10:30:00"
        assert output_data["last_sync"] == "2023-12-25T10:30:00"

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_status_service_error(self, mock_service_class):
        """Test status command WorktreeServiceError handling."""
        mock_service = Mock()
        mock_service.get_worktree_status.side_effect = WorktreeServiceError(
            "Status failed"
        )
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "status", "123"])
        assert result.exit_code == 1
        assert "Error: Status failed" in result.output

    @patch("cc_orchestrator.cli.worktrees.WorktreeService")
    def test_status_unexpected_error(self, mock_service_class):
        """Test status command general Exception handling."""
        mock_service = Mock()
        mock_service.get_worktree_status.side_effect = Exception(
            "Unexpected status error"
        )
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(main, ["worktrees", "status", "123"])
        assert result.exit_code == 1
        assert "Unexpected error: Unexpected status error" in result.output
