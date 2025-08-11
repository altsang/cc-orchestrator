"""Comprehensive tests for git operations module to maximize coverage.

This test suite covers all Git operations including error scenarios,
edge cases, and exception handling to achieve maximum code coverage.
"""

import os
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from typing import Any

import pytest
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from cc_orchestrator.core.git_operations import (
    GitWorktreeError,
    GitWorktreeManager,
)


class TestGitWorktreeManagerComprehensive:
    """Comprehensive test cases for GitWorktreeManager to maximize coverage."""

    @pytest.fixture
    def mock_repo(self):
        """Create a mock Git repository for testing."""
        repo = Mock(spec=Repo)
        repo.git = Mock()
        repo.active_branch = Mock()
        repo.active_branch.name = "main"
        repo.head = Mock()
        repo.head.commit = Mock()
        repo.head.commit.hexsha = "abcd1234567890"
        repo.is_dirty.return_value = False
        repo.untracked_files = []
        repo.index = Mock()
        repo.index.diff.return_value = []
        return repo

    @pytest.fixture
    def manager_with_mock_repo(self, mock_repo):
        """Create a GitWorktreeManager with a mock repository."""
        manager = GitWorktreeManager("/test/repo")
        manager._repo = mock_repo
        return manager

    def test_init_defaults_to_current_directory(self):
        """Test that manager uses current directory when no path provided."""
        with patch("os.getcwd", return_value="/current/dir"):
            manager = GitWorktreeManager()
            assert manager.repo_path == "/current/dir"

    def test_init_with_explicit_path(self):
        """Test manager initialization with explicit repository path."""
        manager = GitWorktreeManager("/explicit/path")
        assert manager.repo_path == "/explicit/path"

    def test_repo_property_creates_repository(self):
        """Test that repo property creates Repo instance on first access."""
        manager = GitWorktreeManager("/test/path")
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_repo_instance = Mock(spec=Repo)
            mock_repo_class.return_value = mock_repo_instance
            
            repo = manager.repo
            
            assert repo is mock_repo_instance
            assert manager._repo is mock_repo_instance
            mock_repo_class.assert_called_once_with("/test/path")

    def test_repo_property_caches_instance(self):
        """Test that repo property caches the repository instance."""
        manager = GitWorktreeManager("/test/path")
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_repo_instance = Mock(spec=Repo)
            mock_repo_class.return_value = mock_repo_instance
            
            repo1 = manager.repo
            repo2 = manager.repo
            
            assert repo1 is repo2
            mock_repo_class.assert_called_once()

    def test_repo_property_invalid_git_repository_error(self):
        """Test repo property raises GitWorktreeError for invalid repository."""
        manager = GitWorktreeManager("/invalid/path")
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_repo_class.side_effect = InvalidGitRepositoryError("Invalid repo")
            
            with pytest.raises(GitWorktreeError, match="Invalid git repository at /invalid/path"):
                _ = manager.repo

    def test_list_worktrees_empty_output(self, manager_with_mock_repo):
        """Test list_worktrees with empty git output."""
        manager_with_mock_repo.repo.git.worktree.return_value = ""
        
        result = manager_with_mock_repo.list_worktrees()
        
        assert result == []

    def test_list_worktrees_single_worktree(self, manager_with_mock_repo):
        """Test list_worktrees with single worktree."""
        output = "worktree /path/to/main\nHEAD abcd1234\nbranch refs/heads/main"
        manager_with_mock_repo.repo.git.worktree.return_value = output
        
        result = manager_with_mock_repo.list_worktrees()
        
        assert len(result) == 1
        assert result[0]["path"] == "/path/to/main"
        assert result[0]["commit"] == "abcd1234"
        assert result[0]["branch"] == "refs/heads/main"

    def test_list_worktrees_multiple_with_different_statuses(self, manager_with_mock_repo):
        """Test list_worktrees with multiple worktrees having different statuses."""
        output = """worktree /path/to/main
HEAD abcd1234
branch refs/heads/main

worktree /path/to/detached
HEAD efgh5678
detached

worktree /path/to/bare
HEAD ijkl9012
bare

worktree /path/to/feature
HEAD mnop3456
branch refs/heads/feature-branch"""
        
        manager_with_mock_repo.repo.git.worktree.return_value = output
        
        result = manager_with_mock_repo.list_worktrees()
        
        assert len(result) == 4
        assert result[0]["path"] == "/path/to/main"
        assert result[0]["branch"] == "refs/heads/main"
        assert "status" not in result[0]  # No status for normal branch
        
        assert result[1]["path"] == "/path/to/detached"
        assert result[1]["status"] == "detached"
        
        assert result[2]["path"] == "/path/to/bare"
        assert result[2]["status"] == "bare"
        
        assert result[3]["path"] == "/path/to/feature"
        assert result[3]["branch"] == "refs/heads/feature-branch"

    def test_list_worktrees_with_empty_lines(self, manager_with_mock_repo):
        """Test list_worktrees handling empty lines properly."""
        output = """worktree /path/to/main
HEAD abcd1234
branch refs/heads/main



worktree /path/to/feature
HEAD efgh5678
branch refs/heads/feature

"""
        
        manager_with_mock_repo.repo.git.worktree.return_value = output
        
        result = manager_with_mock_repo.list_worktrees()
        
        assert len(result) == 2

    def test_list_worktrees_git_command_error(self, manager_with_mock_repo):
        """Test list_worktrees with GitCommandError."""
        manager_with_mock_repo.repo.git.worktree.side_effect = GitCommandError(
            "worktree list", 128, "fatal: not a git repository"
        )
        
        with pytest.raises(GitWorktreeError, match="Failed to list worktrees"):
            manager_with_mock_repo.list_worktrees()

    def test_create_worktree_success_with_main_branch(self, manager_with_mock_repo, tmp_path):
        """Test successful worktree creation with main branch detection."""
        worktree_path = str(tmp_path / "new_worktree")
        
        # Mock show_ref to succeed for main branch
        manager_with_mock_repo.repo.git.show_ref.return_value = "refs/heads/main"
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_worktree_repo = Mock(spec=Repo)
            mock_worktree_repo.head.commit.hexsha = "def456"
            mock_repo_class.return_value = mock_worktree_repo
            
            result = manager_with_mock_repo.create_worktree(
                path=worktree_path,
                branch="new-feature"
            )
            
            assert result["path"] == os.path.abspath(worktree_path)
            assert result["branch"] == "new-feature"
            assert result["commit"] == "def456"
            assert result["status"] == "active"
            
            # Verify git commands
            manager_with_mock_repo.repo.git.show_ref.assert_called_with("refs/heads/main")
            manager_with_mock_repo.repo.git.worktree.assert_called_with(
                "add", "-b", "new-feature", os.path.abspath(worktree_path), "main"
            )

    def test_create_worktree_fallback_to_master_branch(self, manager_with_mock_repo, tmp_path):
        """Test worktree creation falls back to master when main doesn't exist."""
        worktree_path = str(tmp_path / "new_worktree")
        
        # Mock show_ref to fail for main, succeed for master
        def show_ref_side_effect(ref):
            if ref == "refs/heads/main":
                raise GitCommandError("show-ref", 1, "not found")
            elif ref == "refs/heads/master":
                return "refs/heads/master"
            
        manager_with_mock_repo.repo.git.show_ref.side_effect = show_ref_side_effect
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_worktree_repo = Mock(spec=Repo)
            mock_worktree_repo.head.commit.hexsha = "abc123"
            mock_repo_class.return_value = mock_worktree_repo
            
            result = manager_with_mock_repo.create_worktree(
                path=worktree_path,
                branch="new-feature"
            )
            
            assert result["branch"] == "new-feature"
            
            # Verify both show_ref calls
            expected_calls = [call("refs/heads/main"), call("refs/heads/master")]
            manager_with_mock_repo.repo.git.show_ref.assert_has_calls(expected_calls)
            
            # Verify worktree creation with master
            manager_with_mock_repo.repo.git.worktree.assert_called_with(
                "add", "-b", "new-feature", os.path.abspath(worktree_path), "master"
            )

    def test_create_worktree_fallback_to_current_branch(self, manager_with_mock_repo, tmp_path):
        """Test worktree creation falls back to current branch when main/master don't exist."""
        worktree_path = str(tmp_path / "new_worktree")
        
        # Mock show_ref to fail for both main and master
        manager_with_mock_repo.repo.git.show_ref.side_effect = GitCommandError(
            "show-ref", 1, "not found"
        )
        
        # Mock active_branch
        manager_with_mock_repo.repo.active_branch.name = "current-branch"
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_worktree_repo = Mock(spec=Repo)
            mock_worktree_repo.head.commit.hexsha = "xyz789"
            mock_repo_class.return_value = mock_worktree_repo
            
            result = manager_with_mock_repo.create_worktree(
                path=worktree_path,
                branch="new-feature"
            )
            
            assert result["branch"] == "new-feature"
            
            # Verify worktree creation with current branch
            manager_with_mock_repo.repo.git.worktree.assert_called_with(
                "add", "-b", "new-feature", os.path.abspath(worktree_path), "current-branch"
            )

    def test_create_worktree_with_explicit_checkout_branch(self, manager_with_mock_repo, tmp_path):
        """Test worktree creation with explicitly specified checkout branch."""
        worktree_path = str(tmp_path / "new_worktree")
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_worktree_repo = Mock(spec=Repo)
            mock_worktree_repo.head.commit.hexsha = "explicit123"
            mock_repo_class.return_value = mock_worktree_repo
            
            result = manager_with_mock_repo.create_worktree(
                path=worktree_path,
                branch="new-feature",
                checkout_branch="explicit-branch"
            )
            
            assert result["branch"] == "new-feature"
            
            # Should not call show_ref when checkout_branch is explicit
            manager_with_mock_repo.repo.git.show_ref.assert_not_called()
            
            # Verify worktree creation with explicit branch
            manager_with_mock_repo.repo.git.worktree.assert_called_with(
                "add", "-b", "new-feature", os.path.abspath(worktree_path), "explicit-branch"
            )

    def test_create_worktree_path_exists_no_force(self, manager_with_mock_repo, tmp_path):
        """Test worktree creation fails when path exists and force=False."""
        existing_path = tmp_path / "existing"
        existing_path.mkdir()
        
        with pytest.raises(GitWorktreeError, match="already exists"):
            manager_with_mock_repo.create_worktree(
                path=str(existing_path),
                branch="new-feature"
            )

    def test_create_worktree_path_exists_with_force(self, manager_with_mock_repo, tmp_path):
        """Test worktree creation succeeds when path exists and force=True."""
        existing_path = tmp_path / "existing"
        existing_path.mkdir()
        
        manager_with_mock_repo.repo.git.show_ref.return_value = "refs/heads/main"
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_worktree_repo = Mock(spec=Repo)
            mock_worktree_repo.head.commit.hexsha = "force123"
            mock_repo_class.return_value = mock_worktree_repo
            
            result = manager_with_mock_repo.create_worktree(
                path=str(existing_path),
                branch="new-feature",
                force=True
            )
            
            assert result["branch"] == "new-feature"
            
            # Verify --force flag is used
            manager_with_mock_repo.repo.git.worktree.assert_called_with(
                "add", "--force", "-b", "new-feature", str(existing_path), "main"
            )

    def test_create_worktree_git_command_error(self, manager_with_mock_repo, tmp_path):
        """Test worktree creation with GitCommandError."""
        worktree_path = str(tmp_path / "new_worktree")
        
        manager_with_mock_repo.repo.git.show_ref.return_value = "refs/heads/main"
        manager_with_mock_repo.repo.git.worktree.side_effect = GitCommandError(
            "worktree add", 128, "fatal: branch already exists"
        )
        
        with pytest.raises(GitWorktreeError, match="Failed to create worktree"):
            manager_with_mock_repo.create_worktree(
                path=worktree_path,
                branch="existing-feature"
            )

    def test_create_worktree_unexpected_exception(self, manager_with_mock_repo, tmp_path):
        """Test worktree creation with unexpected exception."""
        worktree_path = str(tmp_path / "new_worktree")
        
        manager_with_mock_repo.repo.git.show_ref.return_value = "refs/heads/main"
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_repo_class.side_effect = PermissionError("Access denied")
            
            with pytest.raises(GitWorktreeError, match="Unexpected error creating worktree"):
                manager_with_mock_repo.create_worktree(
                    path=worktree_path,
                    branch="new-feature"
                )

    def test_remove_worktree_success(self, manager_with_mock_repo, tmp_path):
        """Test successful worktree removal."""
        worktree_path = tmp_path / "test_worktree"
        worktree_path.mkdir()
        
        # Create .git file (worktree marker)
        git_file = worktree_path / ".git"
        git_file.write_text("gitdir: /main/repo/.git/worktrees/test")
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_worktree_repo = Mock(spec=Repo)
            mock_repo_class.return_value = mock_worktree_repo
            
            result = manager_with_mock_repo.remove_worktree(str(worktree_path))
            
            assert result is True
            manager_with_mock_repo.repo.git.worktree.assert_called_once_with(
                "remove", str(worktree_path)
            )

    def test_remove_worktree_with_force(self, manager_with_mock_repo, tmp_path):
        """Test worktree removal with force flag."""
        worktree_path = tmp_path / "test_worktree"
        worktree_path.mkdir()
        
        git_file = worktree_path / ".git"
        git_file.write_text("gitdir: /main/repo/.git/worktrees/test")
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_worktree_repo = Mock(spec=Repo)
            mock_repo_class.return_value = mock_worktree_repo
            
            result = manager_with_mock_repo.remove_worktree(str(worktree_path), force=True)
            
            assert result is True
            manager_with_mock_repo.repo.git.worktree.assert_called_once_with(
                "remove", "--force", str(worktree_path)
            )

    def test_remove_worktree_path_not_exists(self, manager_with_mock_repo):
        """Test removing non-existent worktree path."""
        result = manager_with_mock_repo.remove_worktree("/nonexistent/path")
        
        assert result is False
        manager_with_mock_repo.repo.git.worktree.assert_not_called()

    def test_remove_worktree_not_git_worktree_no_git_file(self, manager_with_mock_repo, tmp_path):
        """Test removing path that's not a worktree (no .git file)."""
        worktree_path = tmp_path / "not_worktree"
        worktree_path.mkdir()
        
        # Create .git directory instead of file (main repo, not worktree)
        git_dir = worktree_path / ".git"
        git_dir.mkdir()
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_worktree_repo = Mock(spec=Repo)
            mock_repo_class.return_value = mock_worktree_repo
            
            result = manager_with_mock_repo.remove_worktree(str(worktree_path))
            
            assert result is False
            manager_with_mock_repo.repo.git.worktree.assert_not_called()

    def test_remove_worktree_invalid_git_repository(self, manager_with_mock_repo, tmp_path):
        """Test removing path that's not a valid git repository."""
        worktree_path = tmp_path / "invalid_repo"
        worktree_path.mkdir()
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_repo_class.side_effect = InvalidGitRepositoryError("Invalid repo")
            
            result = manager_with_mock_repo.remove_worktree(str(worktree_path))
            
            assert result is False
            manager_with_mock_repo.repo.git.worktree.assert_not_called()

    def test_remove_worktree_cleanup_remaining_directory(self, manager_with_mock_repo, tmp_path):
        """Test cleanup of remaining directory after worktree removal."""
        worktree_path = tmp_path / "test_worktree"
        worktree_path.mkdir()
        
        git_file = worktree_path / ".git"
        git_file.write_text("gitdir: /main/repo/.git/worktrees/test")
        
        with (
            patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class,
            patch("shutil.rmtree") as mock_rmtree
        ):
            mock_worktree_repo = Mock(spec=Repo)
            mock_repo_class.return_value = mock_worktree_repo
            
            # Simulate directory still exists after git remove
            with patch("os.path.exists", return_value=True):
                result = manager_with_mock_repo.remove_worktree(str(worktree_path))
            
            assert result is True
            mock_rmtree.assert_called_once_with(str(worktree_path))

    def test_remove_worktree_cleanup_directory_fails(self, manager_with_mock_repo, tmp_path):
        """Test handling cleanup failure when removing remaining directory."""
        worktree_path = tmp_path / "test_worktree"
        worktree_path.mkdir()
        
        git_file = worktree_path / ".git"
        git_file.write_text("gitdir: /main/repo/.git/worktrees/test")
        
        with (
            patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class,
            patch("shutil.rmtree") as mock_rmtree
        ):
            mock_worktree_repo = Mock(spec=Repo)
            mock_repo_class.return_value = mock_worktree_repo
            mock_rmtree.side_effect = PermissionError("Access denied")
            
            with patch("os.path.exists", return_value=True):
                result = manager_with_mock_repo.remove_worktree(str(worktree_path))
            
            assert result is True  # Still succeeds despite cleanup failure
            mock_rmtree.assert_called_once_with(str(worktree_path))

    def test_remove_worktree_git_command_error(self, manager_with_mock_repo, tmp_path):
        """Test worktree removal with GitCommandError."""
        worktree_path = tmp_path / "test_worktree"
        worktree_path.mkdir()
        
        git_file = worktree_path / ".git"
        git_file.write_text("gitdir: /main/repo/.git/worktrees/test")
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_worktree_repo = Mock(spec=Repo)
            mock_repo_class.return_value = mock_worktree_repo
            
            manager_with_mock_repo.repo.git.worktree.side_effect = GitCommandError(
                "worktree remove", 128, "fatal: worktree locked"
            )
            
            with pytest.raises(GitWorktreeError, match="Failed to remove worktree"):
                manager_with_mock_repo.remove_worktree(str(worktree_path))

    def test_remove_worktree_unexpected_exception(self, manager_with_mock_repo, tmp_path):
        """Test worktree removal with unexpected exception."""
        worktree_path = tmp_path / "test_worktree"
        worktree_path.mkdir()
        
        git_file = worktree_path / ".git"
        git_file.write_text("gitdir: /main/repo/.git/worktrees/test")
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_repo_class.side_effect = RuntimeError("Unexpected error")
            
            with pytest.raises(GitWorktreeError, match="Unexpected error removing worktree"):
                manager_with_mock_repo.remove_worktree(str(worktree_path))

    def test_cleanup_worktrees_no_worktrees(self, manager_with_mock_repo):
        """Test cleanup when there are no worktrees to clean."""
        with patch.object(manager_with_mock_repo, "list_worktrees", return_value=[]):
            result = manager_with_mock_repo.cleanup_worktrees()
            
            assert result == []
            manager_with_mock_repo.repo.git.worktree.assert_not_called()

    def test_cleanup_worktrees_only_main_repo(self, manager_with_mock_repo):
        """Test cleanup when only main repository exists."""
        worktrees = [{"path": manager_with_mock_repo.repo_path}]
        
        with patch.object(manager_with_mock_repo, "list_worktrees", return_value=worktrees):
            result = manager_with_mock_repo.cleanup_worktrees()
            
            assert result == []
            manager_with_mock_repo.repo.git.worktree.assert_not_called()

    def test_cleanup_worktrees_with_valid_worktrees(self, manager_with_mock_repo):
        """Test cleanup when all worktrees exist (no cleanup needed)."""
        worktrees = [
            {"path": manager_with_mock_repo.repo_path},
            {"path": "/existing/worktree1"},
            {"path": "/existing/worktree2"},
        ]
        
        with (
            patch.object(manager_with_mock_repo, "list_worktrees", return_value=worktrees),
            patch("os.path.exists", return_value=True)
        ):
            result = manager_with_mock_repo.cleanup_worktrees()
            
            assert result == []
            manager_with_mock_repo.repo.git.worktree.assert_not_called()

    def test_cleanup_worktrees_with_stale_references(self, manager_with_mock_repo):
        """Test cleanup with stale worktree references."""
        worktrees = [
            {"path": manager_with_mock_repo.repo_path},
            {"path": "/stale/worktree1"},
            {"path": "/stale/worktree2"},
            {"path": "/existing/worktree"},
        ]
        
        def exists_side_effect(path):
            return path in [manager_with_mock_repo.repo_path, "/existing/worktree"]
        
        with (
            patch.object(manager_with_mock_repo, "list_worktrees", return_value=worktrees),
            patch("os.path.exists", side_effect=exists_side_effect)
        ):
            result = manager_with_mock_repo.cleanup_worktrees()
            
            assert "/stale/worktree1" in result
            assert "/stale/worktree2" in result
            assert len(result) == 2
            
            # Should call prune for stale worktrees
            manager_with_mock_repo.repo.git.worktree.assert_called_with("prune")

    def test_cleanup_worktrees_no_path_in_worktree(self, manager_with_mock_repo):
        """Test cleanup with worktree entry missing path."""
        worktrees = [
            {"path": manager_with_mock_repo.repo_path},
            {"commit": "abc123"},  # Missing path
            {"path": "/valid/worktree"},
        ]
        
        with (
            patch.object(manager_with_mock_repo, "list_worktrees", return_value=worktrees),
            patch("os.path.exists", return_value=True)
        ):
            result = manager_with_mock_repo.cleanup_worktrees()
            
            assert result == []

    def test_cleanup_worktrees_prune_error(self, manager_with_mock_repo):
        """Test cleanup handling error during prune operation."""
        worktrees = [
            {"path": manager_with_mock_repo.repo_path},
            {"path": "/stale/worktree"},
        ]
        
        with (
            patch.object(manager_with_mock_repo, "list_worktrees", return_value=worktrees),
            patch("os.path.exists", side_effect=lambda path: path == manager_with_mock_repo.repo_path)
        ):
            manager_with_mock_repo.repo.git.worktree.side_effect = GitCommandError(
                "worktree prune", 1, "error"
            )
            
            result = manager_with_mock_repo.cleanup_worktrees()
            
            # Should not add to cleaned paths due to error
            assert result == []

    def test_cleanup_worktrees_git_command_error(self, manager_with_mock_repo):
        """Test cleanup with GitCommandError from list_worktrees."""
        with patch.object(manager_with_mock_repo, "list_worktrees") as mock_list:
            mock_list.side_effect = GitCommandError("worktree list", 128, "error")
            
            with pytest.raises(GitWorktreeError, match="Failed to cleanup worktrees"):
                manager_with_mock_repo.cleanup_worktrees()

    def test_cleanup_worktrees_unexpected_exception(self, manager_with_mock_repo):
        """Test cleanup with unexpected exception."""
        with patch.object(manager_with_mock_repo, "list_worktrees") as mock_list:
            mock_list.side_effect = RuntimeError("Unexpected error")
            
            with pytest.raises(GitWorktreeError, match="Unexpected error during cleanup"):
                manager_with_mock_repo.cleanup_worktrees()

    def test_get_worktree_status_path_not_exists(self, manager_with_mock_repo):
        """Test get_worktree_status with non-existent path."""
        with pytest.raises(GitWorktreeError, match="does not exist"):
            manager_with_mock_repo.get_worktree_status("/nonexistent/path")

    def test_get_worktree_status_basic_info(self, manager_with_mock_repo, tmp_path):
        """Test get_worktree_status returns basic worktree information."""
        worktree_path = tmp_path / "test_worktree"
        worktree_path.mkdir()
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_worktree_repo = Mock(spec=Repo)
            mock_worktree_repo.active_branch.name = "feature-branch"
            mock_worktree_repo.head.commit.hexsha = "abcd1234"
            mock_worktree_repo.is_dirty.return_value = False
            mock_worktree_repo.untracked_files = []
            mock_worktree_repo.index.diff.return_value = []
            mock_worktree_repo.active_branch.tracking_branch.return_value = None
            
            mock_repo_class.return_value = mock_worktree_repo
            
            status = manager_with_mock_repo.get_worktree_status(str(worktree_path))
            
            assert status["path"] == str(worktree_path)
            assert status["branch"] == "feature-branch"
            assert status["commit"] == "abcd1234"
            assert status["has_changes"] is False
            assert status["is_dirty"] is False
            assert status["ahead"] == 0
            assert status["behind"] == 0

    def test_get_worktree_status_with_dirty_working_directory(self, manager_with_mock_repo, tmp_path):
        """Test get_worktree_status with dirty working directory."""
        worktree_path = tmp_path / "test_worktree"
        worktree_path.mkdir()
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_worktree_repo = Mock(spec=Repo)
            mock_worktree_repo.active_branch.name = "feature-branch"
            mock_worktree_repo.head.commit.hexsha = "abcd1234"
            mock_worktree_repo.is_dirty.return_value = True
            mock_worktree_repo.untracked_files = []
            mock_worktree_repo.index.diff.return_value = []
            mock_worktree_repo.active_branch.tracking_branch.return_value = None
            
            mock_repo_class.return_value = mock_worktree_repo
            
            status = manager_with_mock_repo.get_worktree_status(str(worktree_path))
            
            assert status["has_changes"] is True
            assert status["is_dirty"] is True

    def test_get_worktree_status_with_untracked_files(self, manager_with_mock_repo, tmp_path):
        """Test get_worktree_status with untracked files."""
        worktree_path = tmp_path / "test_worktree"
        worktree_path.mkdir()
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_worktree_repo = Mock(spec=Repo)
            mock_worktree_repo.active_branch.name = "feature-branch"
            mock_worktree_repo.head.commit.hexsha = "abcd1234"
            mock_worktree_repo.is_dirty.return_value = False
            mock_worktree_repo.untracked_files = ["new_file.txt", "another_file.py"]
            mock_worktree_repo.index.diff.return_value = []
            mock_worktree_repo.active_branch.tracking_branch.return_value = None
            
            mock_repo_class.return_value = mock_worktree_repo
            
            status = manager_with_mock_repo.get_worktree_status(str(worktree_path))
            
            assert status["has_changes"] is True
            assert status["is_dirty"] is False

    def test_get_worktree_status_with_staged_changes(self, manager_with_mock_repo, tmp_path):
        """Test get_worktree_status with staged changes."""
        worktree_path = tmp_path / "test_worktree"
        worktree_path.mkdir()
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_worktree_repo = Mock(spec=Repo)
            mock_worktree_repo.active_branch.name = "feature-branch"
            mock_worktree_repo.head.commit.hexsha = "abcd1234"
            mock_worktree_repo.is_dirty.return_value = False
            mock_worktree_repo.untracked_files = []
            
            # Mock staged changes
            mock_diff = Mock()
            mock_worktree_repo.index.diff.return_value = [mock_diff]
            mock_worktree_repo.active_branch.tracking_branch.return_value = None
            
            mock_repo_class.return_value = mock_worktree_repo
            
            status = manager_with_mock_repo.get_worktree_status(str(worktree_path))
            
            assert status["has_changes"] is True
            assert status["is_dirty"] is False

    def test_get_worktree_status_with_remote_tracking(self, manager_with_mock_repo, tmp_path):
        """Test get_worktree_status with remote tracking branch information."""
        worktree_path = tmp_path / "test_worktree"
        worktree_path.mkdir()
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_worktree_repo = Mock(spec=Repo)
            mock_worktree_repo.active_branch.name = "feature-branch"
            mock_worktree_repo.head.commit.hexsha = "abcd1234"
            mock_worktree_repo.is_dirty.return_value = False
            mock_worktree_repo.untracked_files = []
            mock_worktree_repo.index.diff.return_value = []
            
            # Mock tracking branch
            mock_tracking_branch = Mock()
            mock_worktree_repo.active_branch.tracking_branch.return_value = mock_tracking_branch
            
            # Mock ahead commits
            mock_ahead_commits = [Mock(), Mock()]  # 2 commits ahead
            mock_behind_commits = [Mock()]  # 1 commit behind
            
            def iter_commits_side_effect(range_spec):
                if "feature-branch" in range_spec and ".." in range_spec:
                    if range_spec.startswith(str(mock_tracking_branch)):
                        return mock_ahead_commits
                    else:
                        return mock_behind_commits
                return []
            
            mock_worktree_repo.iter_commits.side_effect = iter_commits_side_effect
            
            mock_repo_class.return_value = mock_worktree_repo
            
            status = manager_with_mock_repo.get_worktree_status(str(worktree_path))
            
            assert status["ahead"] == 2
            assert status["behind"] == 1

    def test_get_worktree_status_tracking_branch_error(self, manager_with_mock_repo, tmp_path):
        """Test get_worktree_status handles tracking branch errors gracefully."""
        worktree_path = tmp_path / "test_worktree"
        worktree_path.mkdir()
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_worktree_repo = Mock(spec=Repo)
            mock_worktree_repo.active_branch.name = "feature-branch"
            mock_worktree_repo.head.commit.hexsha = "abcd1234"
            mock_worktree_repo.is_dirty.return_value = False
            mock_worktree_repo.untracked_files = []
            mock_worktree_repo.index.diff.return_value = []
            
            # Mock tracking branch but iter_commits raises error
            mock_tracking_branch = Mock()
            mock_worktree_repo.active_branch.tracking_branch.return_value = mock_tracking_branch
            mock_worktree_repo.iter_commits.side_effect = GitCommandError("iter_commits", 1, "error")
            
            mock_repo_class.return_value = mock_worktree_repo
            
            status = manager_with_mock_repo.get_worktree_status(str(worktree_path))
            
            # Should default to 0 when tracking info fails
            assert status["ahead"] == 0
            assert status["behind"] == 0

    def test_get_worktree_status_invalid_git_repository_error(self, manager_with_mock_repo, tmp_path):
        """Test get_worktree_status with InvalidGitRepositoryError."""
        worktree_path = tmp_path / "invalid_repo"
        worktree_path.mkdir()
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_repo_class.side_effect = InvalidGitRepositoryError("Invalid repo")
            
            with pytest.raises(GitWorktreeError, match="Invalid git repository"):
                manager_with_mock_repo.get_worktree_status(str(worktree_path))

    def test_get_worktree_status_unexpected_exception(self, manager_with_mock_repo, tmp_path):
        """Test get_worktree_status with unexpected exception."""
        worktree_path = tmp_path / "test_worktree"
        worktree_path.mkdir()
        
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_repo_class.side_effect = RuntimeError("Unexpected error")
            
            with pytest.raises(GitWorktreeError, match="Failed to get worktree status"):
                manager_with_mock_repo.get_worktree_status(str(worktree_path))

    def test_generate_worktree_path_no_conflicts(self, manager_with_mock_repo, tmp_path):
        """Test generate_worktree_path with no existing conflicts."""
        base_dir = str(tmp_path)
        name = "new-worktree"
        
        path = manager_with_mock_repo.generate_worktree_path(base_dir, name)
        
        assert path == str(tmp_path / name)

    def test_generate_worktree_path_single_conflict(self, manager_with_mock_repo, tmp_path):
        """Test generate_worktree_path with single existing conflict."""
        base_dir = str(tmp_path)
        name = "existing-worktree"
        
        # Create conflicting path
        (tmp_path / name).mkdir()
        
        path = manager_with_mock_repo.generate_worktree_path(base_dir, name)
        
        assert path == str(tmp_path / f"{name}-1")

    def test_generate_worktree_path_multiple_conflicts(self, manager_with_mock_repo, tmp_path):
        """Test generate_worktree_path with multiple existing conflicts."""
        base_dir = str(tmp_path)
        name = "popular-name"
        
        # Create multiple conflicting paths
        (tmp_path / name).mkdir()
        (tmp_path / f"{name}-1").mkdir()
        (tmp_path / f"{name}-2").mkdir()
        (tmp_path / f"{name}-3").mkdir()
        
        path = manager_with_mock_repo.generate_worktree_path(base_dir, name)
        
        assert path == str(tmp_path / f"{name}-4")

    def test_generate_worktree_path_with_pathlib(self, manager_with_mock_repo, tmp_path):
        """Test generate_worktree_path uses Path objects correctly."""
        base_dir = str(tmp_path)
        name = "test-path"
        
        path = manager_with_mock_repo.generate_worktree_path(base_dir, name)
        
        # Verify the path is constructed correctly
        expected_path = str(tmp_path / name)
        assert path == expected_path


class TestGitWorktreeError:
    """Test cases for GitWorktreeError exception."""

    def test_git_worktree_error_inheritance(self):
        """Test that GitWorktreeError inherits from Exception."""
        error = GitWorktreeError("test message")
        
        assert isinstance(error, Exception)
        assert str(error) == "test message"

    def test_git_worktree_error_with_message(self):
        """Test GitWorktreeError with custom message."""
        message = "Custom error message"
        error = GitWorktreeError(message)
        
        assert str(error) == message

    def test_git_worktree_error_chaining(self):
        """Test GitWorktreeError exception chaining."""
        original_error = ValueError("Original error")
        
        try:
            raise GitWorktreeError("Chained error") from original_error
        except GitWorktreeError as e:
            assert str(e) == "Chained error"
            assert e.__cause__ is original_error


