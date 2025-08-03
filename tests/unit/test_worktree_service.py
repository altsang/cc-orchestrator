"""Unit tests for worktree service module."""

import os
from unittest.mock import Mock, patch

import pytest

from cc_orchestrator.core.worktree_service import (
    WorktreeService,
    WorktreeServiceError,
)
from cc_orchestrator.database.models import WorktreeStatus


class TestWorktreeService:
    """Test cases for WorktreeService."""

    @pytest.fixture
    def mock_git_manager(self):
        """Mock GitWorktreeManager for testing."""
        with patch(
            "cc_orchestrator.core.worktree_service.GitWorktreeManager"
        ) as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            mock_instance.repo_path = "/test/repo"
            yield mock_instance

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        with patch(
            "cc_orchestrator.core.worktree_service.get_db_session"
        ) as mock_session:
            session = Mock()
            mock_session.return_value.__enter__.return_value = session
            yield session

    @pytest.fixture
    def service(self, mock_git_manager):
        """Create WorktreeService instance for testing."""
        with patch("os.makedirs"):
            return WorktreeService("/test/repo", "/test/worktrees")

    def test_init_default_paths(self):
        """Test service initialization with default paths."""
        with (
            patch(
                "cc_orchestrator.core.worktree_service.GitWorktreeManager"
            ) as mock_git,
            patch("os.makedirs") as mock_makedirs,
        ):

            mock_git.return_value.repo_path = "/test/repo"

            service = WorktreeService()

            mock_makedirs.assert_called_once()
            assert "/worktrees" in service.base_worktree_dir

    def test_init_custom_paths(self, mock_git_manager):
        """Test service initialization with custom paths."""
        with patch("os.makedirs") as mock_makedirs:
            service = WorktreeService("/custom/repo", "/custom/worktrees")

            assert service.base_worktree_dir == "/custom/worktrees"
            mock_makedirs.assert_called_once_with("/custom/worktrees", exist_ok=True)

    def test_list_worktrees_no_sync(self, service, mock_db_session):
        """Test listing worktrees without git sync."""
        # Mock database worktrees
        mock_worktree = Mock()
        mock_worktree.id = 1
        mock_worktree.name = "test-worktree"
        mock_worktree.path = "/test/path"
        mock_worktree.branch_name = "feature-branch"
        mock_worktree.status = WorktreeStatus.ACTIVE
        mock_worktree.repository_url = "https://github.com/test/repo.git"
        mock_worktree.current_commit = "abcd1234"
        mock_worktree.has_uncommitted_changes = False
        mock_worktree.created_at = "2023-01-01T00:00:00"
        mock_worktree.last_sync = None
        mock_worktree.instance_id = None

        with patch("cc_orchestrator.core.worktree_service.WorktreeCRUD") as mock_crud:
            mock_crud.list_all.return_value = [mock_worktree]

            result = service.list_worktrees(sync_with_git=False)

            assert len(result) == 1
            assert result[0]["id"] == 1
            assert result[0]["name"] == "test-worktree"
            assert result[0]["branch"] == "feature-branch"
            assert result[0]["status"] == "active"

    def test_list_worktrees_with_sync(self, service, mock_db_session):
        """Test listing worktrees with git sync."""
        with (
            patch.object(service, "sync_worktrees") as mock_sync,
            patch("cc_orchestrator.core.worktree_service.WorktreeCRUD") as mock_crud,
        ):

            mock_crud.list_all.return_value = []

            result = service.list_worktrees(sync_with_git=True)

            mock_sync.assert_called_once()
            assert result == []

    def test_create_worktree_success(self, service, mock_git_manager, mock_db_session):
        """Test successful worktree creation."""
        # Mock git operations
        mock_git_manager.generate_worktree_path.return_value = (
            "/test/worktrees/test-worktree"
        )
        mock_git_manager.create_worktree.return_value = {
            "path": "/test/worktrees/test-worktree",
            "branch": "feature-branch",
            "commit": "abcd1234",
            "status": "active",
        }

        # Mock database operations
        mock_worktree = Mock()
        mock_worktree.id = 1
        mock_worktree.name = "test-worktree"
        mock_worktree.path = "/test/worktrees/test-worktree"
        mock_worktree.branch_name = "feature-branch"
        mock_worktree.status = WorktreeStatus.ACTIVE
        mock_worktree.instance_id = None

        with (
            patch("cc_orchestrator.core.worktree_service.WorktreeCRUD") as mock_crud,
            patch.object(
                service,
                "_get_repository_url",
                return_value="https://github.com/test/repo.git",
            ),
        ):

            mock_crud.create.return_value = mock_worktree
            mock_crud.update_status.return_value = mock_worktree

            result = service.create_worktree(
                name="test-worktree", branch="feature-branch"
            )

            assert result["id"] == 1
            assert result["name"] == "test-worktree"
            assert result["branch"] == "feature-branch"
            assert result["commit"] == "abcd1234"

            # Verify git operations were called
            mock_git_manager.create_worktree.assert_called_once()
            mock_crud.create.assert_called_once()

    def test_create_worktree_custom_path(
        self, service, mock_git_manager, mock_db_session
    ):
        """Test worktree creation with custom path."""
        custom_path = "/custom/path/worktree"

        mock_git_manager.create_worktree.return_value = {
            "path": custom_path,
            "branch": "feature-branch",
            "commit": "abcd1234",
            "status": "active",
        }

        mock_worktree = Mock()
        mock_worktree.id = 1

        with (
            patch("cc_orchestrator.core.worktree_service.WorktreeCRUD") as mock_crud,
            patch.object(service, "_get_repository_url"),
        ):

            mock_crud.create.return_value = mock_worktree
            mock_crud.update_status.return_value = mock_worktree

            service.create_worktree(
                name="test-worktree", branch="feature-branch", custom_path=custom_path
            )

            # Should use custom path instead of generating one
            mock_git_manager.generate_worktree_path.assert_not_called()
            mock_git_manager.create_worktree.assert_called_once_with(
                path=custom_path,
                branch="feature-branch",
                checkout_branch=None,
                force=False,
            )

    def test_create_worktree_git_error(
        self, service, mock_git_manager, mock_db_session
    ):
        """Test worktree creation with git error."""
        from cc_orchestrator.core.git_operations import GitWorktreeError

        mock_git_manager.generate_worktree_path.return_value = "/test/path"
        mock_git_manager.create_worktree.side_effect = GitWorktreeError("Git error")

        with pytest.raises(WorktreeServiceError, match="Failed to create worktree"):
            service.create_worktree("test", "branch")

    def test_remove_worktree_by_id_success(
        self, service, mock_git_manager, mock_db_session
    ):
        """Test successful worktree removal by ID."""
        mock_worktree = Mock()
        mock_worktree.id = 1
        mock_worktree.name = "test-worktree"
        mock_worktree.path = "/test/path"

        mock_git_manager.remove_worktree.return_value = True

        with patch("cc_orchestrator.core.worktree_service.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_id.return_value = mock_worktree

            result = service.remove_worktree(1)

            assert result is True
            mock_crud.get_by_id.assert_called_once_with(mock_db_session, 1)
            mock_git_manager.remove_worktree.assert_called_once_with(
                "/test/path", force=False
            )
            mock_crud.delete.assert_called_once_with(mock_db_session, 1)

    def test_remove_worktree_by_path_success(
        self, service, mock_git_manager, mock_db_session
    ):
        """Test successful worktree removal by path."""
        test_path = "/test/path"
        mock_worktree = Mock()
        mock_worktree.id = 1

        mock_git_manager.remove_worktree.return_value = True

        with patch("cc_orchestrator.core.worktree_service.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_path.return_value = mock_worktree

            result = service.remove_worktree(test_path)

            assert result is True
            mock_crud.get_by_path.assert_called_once_with(
                mock_db_session, os.path.abspath(test_path)
            )

    def test_remove_worktree_git_failed(
        self, service, mock_git_manager, mock_db_session
    ):
        """Test worktree removal when git removal fails."""
        mock_worktree = Mock()
        mock_worktree.path = "/test/path"

        mock_git_manager.remove_worktree.return_value = False

        with patch("cc_orchestrator.core.worktree_service.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_id.return_value = mock_worktree

            result = service.remove_worktree(1)

            assert result is False
            # Database should not be updated if git removal failed
            mock_crud.delete.assert_not_called()

    def test_remove_worktree_force(self, service, mock_git_manager, mock_db_session):
        """Test forced worktree removal."""
        mock_worktree = Mock()
        mock_worktree.id = 1
        mock_worktree.path = "/test/path"

        # Git removal fails but force is True
        mock_git_manager.remove_worktree.return_value = False

        with patch("cc_orchestrator.core.worktree_service.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_id.return_value = mock_worktree

            result = service.remove_worktree(1, force=True)

            assert result is True
            mock_git_manager.remove_worktree.assert_called_once_with(
                "/test/path", force=True
            )
            mock_crud.delete.assert_called_once_with(mock_db_session, 1)

    def test_cleanup_worktrees_success(
        self, service, mock_git_manager, mock_db_session
    ):
        """Test successful worktree cleanup."""
        # Mock git cleanup
        mock_git_manager.cleanup_worktrees.return_value = ["/stale/path1"]

        # Mock database cleanup
        mock_worktree = Mock()
        mock_worktree.id = 1
        mock_worktree.path = "/missing/path"

        with (
            patch("cc_orchestrator.core.worktree_service.WorktreeCRUD") as mock_crud,
            patch("os.path.exists") as mock_exists,
        ):

            mock_crud.list_all.return_value = [mock_worktree]
            mock_exists.return_value = False  # Path doesn't exist

            result = service.cleanup_worktrees()

            assert result["git_cleaned"] == ["/stale/path1"]
            assert result["db_cleaned"] == ["/missing/path"]
            mock_crud.delete.assert_called_once_with(mock_db_session, 1)

    def test_sync_worktrees_success(self, service, mock_git_manager, mock_db_session):
        """Test successful worktree synchronization."""
        # Mock git worktrees
        mock_git_manager.list_worktrees.return_value = [
            {"path": "/test/path1", "commit": "abcd1234", "has_changes": False}
        ]
        mock_git_manager.get_worktree_status.return_value = {
            "commit": "abcd1234",
            "has_changes": False,
        }

        # Mock database worktrees
        mock_worktree = Mock()
        mock_worktree.id = 1
        mock_worktree.path = "/test/path1"
        mock_worktree.status = WorktreeStatus.DIRTY  # Different from git status
        mock_worktree.current_commit = "old_commit"
        mock_worktree.has_uncommitted_changes = True

        with patch("cc_orchestrator.core.worktree_service.WorktreeCRUD") as mock_crud:
            mock_crud.list_all.return_value = [mock_worktree]
            mock_crud.update_status.return_value = mock_worktree

            result = service.sync_worktrees()

            assert result["updated"] == 1
            assert result["added"] == 0
            assert result["marked_missing"] == 0

            # Verify update was called
            mock_crud.update_status.assert_called_once()

    def test_get_worktree_status_by_id(
        self, service, mock_git_manager, mock_db_session
    ):
        """Test getting worktree status by ID."""
        mock_worktree = Mock()
        mock_worktree.id = 1
        mock_worktree.name = "test-worktree"
        mock_worktree.path = "/test/path"
        mock_worktree.branch_name = "feature-branch"
        mock_worktree.status = WorktreeStatus.ACTIVE
        mock_worktree.repository_url = "https://github.com/test/repo.git"
        mock_worktree.instance_id = None
        mock_worktree.created_at = "2023-01-01T00:00:00"
        mock_worktree.last_sync = None

        git_status = {
            "commit": "abcd1234",
            "has_changes": False,
            "is_dirty": False,
            "ahead": 0,
            "behind": 0,
        }

        mock_git_manager.get_worktree_status.return_value = git_status

        with patch("cc_orchestrator.core.worktree_service.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_id.return_value = mock_worktree

            result = service.get_worktree_status(1)

            assert result["id"] == 1
            assert result["name"] == "test-worktree"
            assert result["db_status"] == "active"
            assert result["git_status"] == git_status

            mock_crud.get_by_id.assert_called_once_with(mock_db_session, 1)

    def test_get_worktree_status_by_path(
        self, service, mock_git_manager, mock_db_session
    ):
        """Test getting worktree status by path."""
        test_path = "/test/path"
        mock_worktree = Mock()

        with patch("cc_orchestrator.core.worktree_service.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_path.return_value = mock_worktree
            mock_git_manager.get_worktree_status.return_value = {}

            service.get_worktree_status(test_path)

            mock_crud.get_by_path.assert_called_once_with(
                mock_db_session, os.path.abspath(test_path)
            )

    def test_get_repository_url_with_remote(self, service, mock_git_manager):
        """Test getting repository URL when remote exists."""
        mock_remote = Mock()
        mock_remote.url = "https://github.com/test/repo.git"
        mock_git_manager.repo.remotes = [mock_remote]

        url = service._get_repository_url()

        assert url == "https://github.com/test/repo.git"

    def test_get_repository_url_no_remote(self, service, mock_git_manager):
        """Test getting repository URL when no remote exists."""
        mock_git_manager.repo.remotes = []

        url = service._get_repository_url()

        assert url is None
