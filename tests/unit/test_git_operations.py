"""Unit tests for git operations module."""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from git import Repo
from git.exc import GitCommandError

from cc_orchestrator.core.git_operations import (
    GitWorktreeError,
    GitWorktreeManager,
)


class TestGitWorktreeManager:
    """Test cases for GitWorktreeManager."""

    @pytest.fixture
    def temp_git_repo(self, tmp_path):
        """Create a temporary git repository for testing."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Initialize git repository
        repo = Repo.init(repo_path)

        # Create initial commit
        test_file = repo_path / "README.md"
        test_file.write_text("# Test Repository")
        repo.index.add([str(test_file)])
        repo.index.commit("Initial commit")

        return str(repo_path)

    @pytest.fixture
    def manager(self, temp_git_repo):
        """Create GitWorktreeManager instance for testing."""
        return GitWorktreeManager(temp_git_repo)

    def test_init_with_repo_path(self, temp_git_repo):
        """Test manager initialization with repository path."""
        manager = GitWorktreeManager(temp_git_repo)
        assert manager.repo_path == temp_git_repo

    def test_init_with_current_directory(self):
        """Test manager initialization with current directory."""
        with patch("os.getcwd", return_value="/test/path"):
            manager = GitWorktreeManager()
            assert manager.repo_path == "/test/path"

    def test_repo_property_invalid_repository(self, tmp_path):
        """Test repo property with invalid repository."""
        manager = GitWorktreeManager(str(tmp_path))

        with pytest.raises(GitWorktreeError, match="Invalid git repository"):
            _ = manager.repo

    def test_list_worktrees_empty(self, manager):
        """Test listing worktrees when none exist."""
        with patch.object(manager.repo, "git") as mock_git:
            mock_git.worktree.return_value = (
                "worktree /path/to/main\nHEAD abcd1234\nbranch refs/heads/main"
            )

            worktrees = manager.list_worktrees()

            assert len(worktrees) == 1
            assert worktrees[0]["path"] == "/path/to/main"
            assert worktrees[0]["commit"] == "abcd1234"
            assert worktrees[0]["branch"] == "refs/heads/main"

    def test_list_worktrees_multiple(self, manager):
        """Test listing multiple worktrees."""
        output = """worktree /path/to/main
HEAD abcd1234
branch refs/heads/main

worktree /path/to/feature
HEAD efgh5678
branch refs/heads/feature-branch"""

        with patch.object(manager.repo, "git") as mock_git:
            mock_git.worktree.return_value = output

            worktrees = manager.list_worktrees()

            assert len(worktrees) == 2
            assert worktrees[0]["path"] == "/path/to/main"
            assert worktrees[1]["path"] == "/path/to/feature"
            assert worktrees[1]["branch"] == "refs/heads/feature-branch"

    def test_list_worktrees_git_error(self, manager):
        """Test list_worktrees with git command error."""
        with patch.object(manager.repo, "git") as mock_git:
            mock_git.worktree.side_effect = GitCommandError("worktree", 1, "error")

            with pytest.raises(GitWorktreeError, match="Failed to list worktrees"):
                manager.list_worktrees()

    def test_create_worktree_success(self, manager, tmp_path):
        """Test successful worktree creation."""
        worktree_path = str(tmp_path / "test_worktree")

        with (
            patch.object(manager.repo, "git") as mock_git,
            patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class,
        ):

            # Mock the git worktree add command
            mock_git.show_ref.return_value = None  # main branch exists

            # Mock the new worktree repo
            mock_worktree_repo = Mock()
            mock_worktree_repo.head.commit.hexsha = "abcd1234"
            mock_repo_class.return_value = mock_worktree_repo

            result = manager.create_worktree(path=worktree_path, branch="test-branch")

            assert result["path"] == os.path.abspath(worktree_path)
            assert result["branch"] == "test-branch"
            assert result["commit"] == "abcd1234"
            assert result["status"] == "active"

            # Verify git commands were called
            mock_git.worktree.assert_called_once()

    def test_create_worktree_path_exists(self, manager, tmp_path):
        """Test worktree creation when path already exists."""
        existing_path = tmp_path / "existing"
        existing_path.mkdir()

        with pytest.raises(GitWorktreeError, match="already exists"):
            manager.create_worktree(str(existing_path), "test-branch")

    def test_create_worktree_path_exists_force(self, manager, tmp_path):
        """Test worktree creation with force when path exists."""
        existing_path = tmp_path / "existing"
        existing_path.mkdir()

        with (
            patch.object(manager.repo, "git") as mock_git,
            patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class,
        ):

            mock_git.show_ref.return_value = None
            mock_worktree_repo = Mock()
            mock_worktree_repo.head.commit.hexsha = "abcd1234"
            mock_repo_class.return_value = mock_worktree_repo

            result = manager.create_worktree(
                path=str(existing_path), branch="test-branch", force=True
            )

            assert result["path"] == str(existing_path)

    def test_create_worktree_git_error(self, manager, tmp_path):
        """Test worktree creation with git command error."""
        worktree_path = str(tmp_path / "test_worktree")

        with patch.object(manager.repo, "git") as mock_git:
            mock_git.worktree.side_effect = GitCommandError("worktree", 1, "error")

            with pytest.raises(GitWorktreeError, match="Failed to create worktree"):
                manager.create_worktree(worktree_path, "test-branch")

    def test_remove_worktree_success(self, manager, tmp_path):
        """Test successful worktree removal."""
        worktree_path = tmp_path / "test_worktree"
        worktree_path.mkdir()

        # Create .git file to simulate worktree
        git_file = worktree_path / ".git"
        git_file.write_text("gitdir: /path/to/main/.git/worktrees/test")

        with (
            patch.object(manager.repo, "git") as mock_git,
            patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class,
        ):

            mock_repo_class.return_value = Mock()  # Valid worktree repo

            result = manager.remove_worktree(str(worktree_path))

            assert result is True
            mock_git.worktree.assert_called_once_with("remove", str(worktree_path))

    def test_remove_worktree_not_exists(self, manager, tmp_path):
        """Test removing non-existent worktree."""
        worktree_path = str(tmp_path / "nonexistent")

        result = manager.remove_worktree(worktree_path)
        assert result is False

    def test_remove_worktree_force(self, manager, tmp_path):
        """Test worktree removal with force."""
        worktree_path = tmp_path / "test_worktree"
        worktree_path.mkdir()

        git_file = worktree_path / ".git"
        git_file.write_text("gitdir: /path/to/main/.git/worktrees/test")

        with (
            patch.object(manager.repo, "git") as mock_git,
            patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class,
        ):

            mock_repo_class.return_value = Mock()

            result = manager.remove_worktree(str(worktree_path), force=True)

            assert result is True
            mock_git.worktree.assert_called_once_with(
                "remove", "--force", str(worktree_path)
            )

    def test_remove_worktree_git_error(self, manager, tmp_path):
        """Test worktree removal with git command error."""
        worktree_path = tmp_path / "test_worktree"
        worktree_path.mkdir()

        git_file = worktree_path / ".git"
        git_file.write_text("gitdir: /path/to/main/.git/worktrees/test")

        with (
            patch.object(manager.repo, "git") as mock_git,
            patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class,
        ):

            mock_repo_class.return_value = Mock()
            mock_git.worktree.side_effect = GitCommandError("worktree", 1, "error")

            with pytest.raises(GitWorktreeError, match="Failed to remove worktree"):
                manager.remove_worktree(str(worktree_path))

    def test_cleanup_worktrees_no_stale(self, manager):
        """Test cleanup when no stale worktrees exist."""
        with patch.object(manager, "list_worktrees") as mock_list:
            mock_list.return_value = [{"path": manager.repo_path}]  # Only main repo

            result = manager.cleanup_worktrees()

            assert result == []

    def test_cleanup_worktrees_with_stale(self, manager):
        """Test cleanup with stale worktree references."""
        stale_paths = ["/nonexistent/path1", "/nonexistent/path2"]

        with (
            patch.object(manager, "list_worktrees") as mock_list,
            patch.object(manager.repo, "git") as mock_git,
        ):

            mock_list.return_value = [
                {"path": manager.repo_path},  # Main repo
                {"path": stale_paths[0]},
                {"path": stale_paths[1]},
            ]

            result = manager.cleanup_worktrees()

            assert len(result) == 2
            mock_git.worktree.assert_called_with("prune")

    def test_get_worktree_status_success(self, manager, tmp_path):
        """Test getting worktree status successfully."""
        worktree_path = tmp_path / "test_worktree"
        worktree_path.mkdir()

        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            # Mock worktree repository
            mock_worktree_repo = Mock()
            mock_worktree_repo.active_branch.name = "feature-branch"
            mock_worktree_repo.head.commit.hexsha = "abcd1234"
            mock_worktree_repo.is_dirty.return_value = True
            mock_worktree_repo.untracked_files = ["new_file.txt"]
            mock_worktree_repo.index.diff.return_value = []
            mock_worktree_repo.active_branch.tracking_branch.return_value = None

            mock_repo_class.return_value = mock_worktree_repo

            status = manager.get_worktree_status(str(worktree_path))

            assert status["path"] == str(worktree_path)
            assert status["branch"] == "feature-branch"
            assert status["commit"] == "abcd1234"
            assert status["has_changes"] is True
            assert status["is_dirty"] is True
            assert status["ahead"] == 0
            assert status["behind"] == 0

    def test_get_worktree_status_nonexistent(self, manager):
        """Test getting status of non-existent worktree."""
        with pytest.raises(GitWorktreeError, match="does not exist"):
            manager.get_worktree_status("/nonexistent/path")

    def test_generate_worktree_path_unique(self, manager, tmp_path):
        """Test generating unique worktree path."""
        base_dir = str(tmp_path)

        path1 = manager.generate_worktree_path(base_dir, "test")
        assert path1 == str(tmp_path / "test")

        # Create the first path
        Path(path1).mkdir()

        # Should generate unique path
        path2 = manager.generate_worktree_path(base_dir, "test")
        assert path2 == str(tmp_path / "test-1")

    def test_generate_worktree_path_multiple_conflicts(self, manager, tmp_path):
        """Test generating path with multiple conflicts."""
        base_dir = str(tmp_path)

        # Create conflicting directories
        (tmp_path / "test").mkdir()
        (tmp_path / "test-1").mkdir()
        (tmp_path / "test-2").mkdir()

        path = manager.generate_worktree_path(base_dir, "test")
        assert path == str(tmp_path / "test-3")
