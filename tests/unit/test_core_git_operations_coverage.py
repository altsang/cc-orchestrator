"""Comprehensive tests for core.git_operations module to achieve 100% coverage."""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from cc_orchestrator.core.git_operations import (
    GitWorktreeError,
    GitWorktreeManager,
)


class TestGitWorktreeError:
    """Test GitWorktreeError exception class."""

    def test_git_worktree_error_basic(self):
        """Test basic GitWorktreeError creation."""
        error = GitWorktreeError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_git_worktree_error_inheritance(self):
        """Test GitWorktreeError inherits from Exception."""
        error = GitWorktreeError("Test error")
        assert isinstance(error, Exception)
        assert error.__class__.__name__ == "GitWorktreeError"


class TestGitWorktreeManager:
    """Test GitWorktreeManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield tmp_dir

    @pytest.fixture
    def mock_repo(self):
        """Create a mock Git repository."""
        repo = Mock(spec=Repo)
        repo.git = Mock()
        repo.head = Mock()
        repo.head.commit = Mock()
        repo.head.commit.hexsha = "abc123def456"
        repo.active_branch = Mock()
        repo.active_branch.name = "main"
        repo.active_branch.tracking_branch = Mock(return_value=None)
        repo.is_dirty = Mock(return_value=False)
        repo.untracked_files = []
        repo.index = Mock()
        repo.index.diff = Mock(return_value=[])
        repo.iter_commits = Mock(return_value=[])
        return repo

    def test_init_with_repo_path(self, temp_dir):
        """Test GitWorktreeManager initialization with repo path."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        assert manager.repo_path == temp_dir
        assert manager._repo is None

    def test_init_without_repo_path(self):
        """Test GitWorktreeManager initialization without repo path."""
        with patch("os.getcwd", return_value="/test/path"):
            manager = GitWorktreeManager()
            assert manager.repo_path == "/test/path"
            assert manager._repo is None

    def test_repo_property_success(self, temp_dir, mock_repo):
        """Test repo property successful initialization."""
        manager = GitWorktreeManager(repo_path=temp_dir)

        with patch("cc_orchestrator.core.git_operations.Repo", return_value=mock_repo):
            repo = manager.repo
            assert repo is mock_repo
            assert manager._repo is mock_repo

            # Second access should return cached repo
            repo2 = manager.repo
            assert repo2 is mock_repo

    def test_repo_property_invalid_repository(self, temp_dir):
        """Test repo property with invalid repository."""
        manager = GitWorktreeManager(repo_path=temp_dir)

        with patch(
            "cc_orchestrator.core.git_operations.Repo",
            side_effect=InvalidGitRepositoryError("Invalid repo"),
        ):
            with pytest.raises(GitWorktreeError, match="Invalid git repository"):
                _ = manager.repo

    def test_list_worktrees_success(self, temp_dir, mock_repo):
        """Test successful worktree listing."""
        manager = GitWorktreeManager(repo_path=temp_dir)

        # Mock git worktree list output
        worktree_output = """worktree /path/to/main
HEAD abc123
branch refs/heads/main

worktree /path/to/feature
HEAD def456
branch refs/heads/feature-branch

worktree /path/to/detached
HEAD ghi789
detached

worktree /path/to/bare
HEAD jkl012
bare"""

        mock_repo.git.worktree.return_value = worktree_output

        with patch.object(manager, "_repo", mock_repo):
            worktrees = manager.list_worktrees()

            assert len(worktrees) == 4

            # Check main worktree
            assert worktrees[0]["path"] == "/path/to/main"
            assert worktrees[0]["commit"] == "abc123"
            assert worktrees[0]["branch"] == "refs/heads/main"

            # Check feature worktree
            assert worktrees[1]["path"] == "/path/to/feature"
            assert worktrees[1]["commit"] == "def456"
            assert worktrees[1]["branch"] == "refs/heads/feature-branch"

            # Check detached worktree
            assert worktrees[2]["path"] == "/path/to/detached"
            assert worktrees[2]["commit"] == "ghi789"
            assert worktrees[2]["status"] == "detached"

            # Check bare worktree
            assert worktrees[3]["path"] == "/path/to/bare"
            assert worktrees[3]["commit"] == "jkl012"
            assert worktrees[3]["status"] == "bare"

    def test_list_worktrees_empty_output(self, temp_dir, mock_repo):
        """Test worktree listing with empty output."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        mock_repo.git.worktree.return_value = ""

        with patch.object(manager, "_repo", mock_repo):
            worktrees = manager.list_worktrees()
            assert worktrees == []

    def test_list_worktrees_single_worktree(self, temp_dir, mock_repo):
        """Test worktree listing with single worktree (no trailing newline)."""
        manager = GitWorktreeManager(repo_path=temp_dir)

        worktree_output = """worktree /single/path
HEAD single123
branch refs/heads/single"""

        mock_repo.git.worktree.return_value = worktree_output

        with patch.object(manager, "_repo", mock_repo):
            worktrees = manager.list_worktrees()

            assert len(worktrees) == 1
            assert worktrees[0]["path"] == "/single/path"
            assert worktrees[0]["commit"] == "single123"
            assert worktrees[0]["branch"] == "refs/heads/single"

    def test_list_worktrees_git_error(self, temp_dir, mock_repo):
        """Test worktree listing with Git command error."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        mock_repo.git.worktree.side_effect = GitCommandError("worktree list failed")

        with patch.object(manager, "_repo", mock_repo):
            with pytest.raises(GitWorktreeError, match="Failed to list worktrees"):
                manager.list_worktrees()

    def test_create_worktree_success_with_main(self, temp_dir, mock_repo):
        """Test successful worktree creation with main branch."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "new-worktree")

        # Mock successful main branch detection
        mock_repo.git.show_ref.return_value = "refs/heads/main"
        mock_repo.git.worktree.return_value = None

        # Mock worktree repo
        mock_worktree_repo = Mock(spec=Repo)
        mock_worktree_repo.head = Mock()
        mock_worktree_repo.head.commit = Mock()
        mock_worktree_repo.head.commit.hexsha = "new123commit"

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=False):
                with patch("os.path.abspath", return_value=target_path):
                    with patch(
                        "cc_orchestrator.core.git_operations.Repo",
                        return_value=mock_worktree_repo,
                    ):
                        result = manager.create_worktree(
                            path=target_path, branch="feature-123"
                        )

                        assert result["path"] == target_path
                        assert result["branch"] == "feature-123"
                        assert result["commit"] == "new123commit"
                        assert result["status"] == "active"

                        # Verify git commands called correctly
                        mock_repo.git.show_ref.assert_called_with("refs/heads/main")
                        mock_repo.git.worktree.assert_called_with(
                            "add", "-b", "feature-123", target_path, "main"
                        )

    def test_create_worktree_success_with_master(self, temp_dir, mock_repo):
        """Test successful worktree creation falling back to master branch."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "new-worktree")

        # Mock main branch not found, master found
        mock_repo.git.show_ref.side_effect = [
            GitCommandError("main not found"),  # main fails
            "refs/heads/master",  # master succeeds
        ]
        mock_repo.git.worktree.return_value = None

        # Mock worktree repo
        mock_worktree_repo = Mock(spec=Repo)
        mock_worktree_repo.head = Mock()
        mock_worktree_repo.head.commit = Mock()
        mock_worktree_repo.head.commit.hexsha = "master123commit"

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=False):
                with patch("os.path.abspath", return_value=target_path):
                    with patch(
                        "cc_orchestrator.core.git_operations.Repo",
                        return_value=mock_worktree_repo,
                    ):
                        result = manager.create_worktree(
                            path=target_path, branch="feature-456"
                        )

                        assert result["branch"] == "feature-456"
                        assert result["commit"] == "master123commit"

                        # Verify fallback to master
                        assert mock_repo.git.show_ref.call_count == 2
                        mock_repo.git.worktree.assert_called_with(
                            "add", "-b", "feature-456", target_path, "master"
                        )

    def test_create_worktree_fallback_to_current_branch(self, temp_dir, mock_repo):
        """Test worktree creation falling back to current branch."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "new-worktree")

        # Mock both main and master not found
        mock_repo.git.show_ref.side_effect = [
            GitCommandError("main not found"),
            GitCommandError("master not found"),
        ]
        mock_repo.active_branch.name = "develop"
        mock_repo.git.worktree.return_value = None

        # Mock worktree repo
        mock_worktree_repo = Mock(spec=Repo)
        mock_worktree_repo.head = Mock()
        mock_worktree_repo.head.commit = Mock()
        mock_worktree_repo.head.commit.hexsha = "develop123commit"

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=False):
                with patch("os.path.abspath", return_value=target_path):
                    with patch(
                        "cc_orchestrator.core.git_operations.Repo",
                        return_value=mock_worktree_repo,
                    ):
                        result = manager.create_worktree(
                            path=target_path, branch="feature-789"
                        )

                        assert result["branch"] == "feature-789"
                        assert result["commit"] == "develop123commit"

                        # Verify fallback to current branch
                        mock_repo.git.worktree.assert_called_with(
                            "add", "-b", "feature-789", target_path, "develop"
                        )

    def test_create_worktree_with_checkout_branch(self, temp_dir, mock_repo):
        """Test worktree creation with explicit checkout branch."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "new-worktree")

        mock_repo.git.worktree.return_value = None

        # Mock worktree repo
        mock_worktree_repo = Mock(spec=Repo)
        mock_worktree_repo.head = Mock()
        mock_worktree_repo.head.commit = Mock()
        mock_worktree_repo.head.commit.hexsha = "custom123commit"

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=False):
                with patch("os.path.abspath", return_value=target_path):
                    with patch(
                        "cc_orchestrator.core.git_operations.Repo",
                        return_value=mock_worktree_repo,
                    ):
                        result = manager.create_worktree(
                            path=target_path,
                            branch="feature-custom",
                            checkout_branch="custom-base",
                        )

                        assert result["branch"] == "feature-custom"
                        assert result["commit"] == "custom123commit"

                        # Should not call show_ref when checkout_branch is provided
                        mock_repo.git.show_ref.assert_not_called()
                        mock_repo.git.worktree.assert_called_with(
                            "add", "-b", "feature-custom", target_path, "custom-base"
                        )

    def test_create_worktree_with_force(self, temp_dir, mock_repo):
        """Test worktree creation with force flag."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "existing-path")

        mock_repo.git.show_ref.return_value = "refs/heads/main"
        mock_repo.git.worktree.return_value = None

        # Mock worktree repo
        mock_worktree_repo = Mock(spec=Repo)
        mock_worktree_repo.head = Mock()
        mock_worktree_repo.head.commit = Mock()
        mock_worktree_repo.head.commit.hexsha = "force123commit"

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=True):  # Path exists
                with patch("os.path.abspath", return_value=target_path):
                    with patch(
                        "cc_orchestrator.core.git_operations.Repo",
                        return_value=mock_worktree_repo,
                    ):
                        result = manager.create_worktree(
                            path=target_path, branch="feature-force", force=True
                        )

                        assert result["branch"] == "feature-force"
                        assert result["commit"] == "force123commit"

                        # Verify force flag passed to git worktree
                        mock_repo.git.worktree.assert_called_with(
                            "add", "--force", "-b", "feature-force", target_path, "main"
                        )

    def test_create_worktree_path_exists_no_force(self, temp_dir, mock_repo):
        """Test worktree creation failure when path exists without force."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "existing-path")

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.abspath", return_value=target_path):
                    with pytest.raises(GitWorktreeError, match="already exists"):
                        manager.create_worktree(path=target_path, branch="feature-fail")

    def test_create_worktree_git_command_error(self, temp_dir, mock_repo):
        """Test worktree creation with Git command error."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "new-worktree")

        mock_repo.git.show_ref.return_value = "refs/heads/main"
        mock_repo.git.worktree.side_effect = GitCommandError("Worktree creation failed")

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=False):
                with patch("os.path.abspath", return_value=target_path):
                    with pytest.raises(
                        GitWorktreeError, match="Failed to create worktree"
                    ):
                        manager.create_worktree(
                            path=target_path, branch="feature-error"
                        )

    def test_create_worktree_unexpected_error(self, temp_dir, mock_repo):
        """Test worktree creation with unexpected error."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "new-worktree")

        mock_repo.git.show_ref.return_value = "refs/heads/main"
        mock_repo.git.worktree.return_value = None

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=False):
                with patch("os.path.abspath", return_value=target_path):
                    with patch(
                        "cc_orchestrator.core.git_operations.Repo",
                        side_effect=Exception("Unexpected error"),
                    ):
                        with pytest.raises(
                            GitWorktreeError, match="Unexpected error creating worktree"
                        ):
                            manager.create_worktree(
                                path=target_path, branch="feature-unexpected"
                            )

    def test_remove_worktree_success(self, temp_dir, mock_repo):
        """Test successful worktree removal."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "worktree-to-remove")

        # Mock worktree repo
        mock_worktree_repo = Mock(spec=Repo)

        mock_repo.git.worktree.return_value = None

        with patch.object(manager, "_repo", mock_repo):
            with patch(
                "os.path.exists", side_effect=[True, False]
            ):  # Exists initially, gone after removal
                with patch("os.path.abspath", return_value=target_path):
                    with patch(
                        "os.path.isfile", return_value=True
                    ):  # .git is a file (worktree)
                        with patch(
                            "cc_orchestrator.core.git_operations.Repo",
                            return_value=mock_worktree_repo,
                        ):
                            result = manager.remove_worktree(target_path)

                            assert result is True
                            mock_repo.git.worktree.assert_called_with(
                                "remove", target_path
                            )

    def test_remove_worktree_with_force(self, temp_dir, mock_repo):
        """Test worktree removal with force flag."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "worktree-to-force-remove")

        # Mock worktree repo
        mock_worktree_repo = Mock(spec=Repo)
        mock_repo.git.worktree.return_value = None

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", side_effect=[True, False]):
                with patch("os.path.abspath", return_value=target_path):
                    with patch("os.path.isfile", return_value=True):
                        with patch(
                            "cc_orchestrator.core.git_operations.Repo",
                            return_value=mock_worktree_repo,
                        ):
                            result = manager.remove_worktree(target_path, force=True)

                            assert result is True
                            mock_repo.git.worktree.assert_called_with(
                                "remove", "--force", target_path
                            )

    def test_remove_worktree_path_not_exists(self, temp_dir, mock_repo):
        """Test worktree removal when path doesn't exist."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "nonexistent")

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=False):
                with patch("os.path.abspath", return_value=target_path):
                    result = manager.remove_worktree(target_path)

                    assert result is False
                    mock_repo.git.worktree.assert_not_called()

    def test_remove_worktree_not_a_worktree_file(self, temp_dir, mock_repo):
        """Test worktree removal when .git is not a file (not a worktree)."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "not-worktree")

        # Mock worktree repo
        mock_worktree_repo = Mock(spec=Repo)

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.abspath", return_value=target_path):
                    with patch(
                        "os.path.isfile", return_value=False
                    ):  # .git is not a file
                        with patch(
                            "cc_orchestrator.core.git_operations.Repo",
                            return_value=mock_worktree_repo,
                        ):
                            result = manager.remove_worktree(target_path)

                            assert result is False
                            mock_repo.git.worktree.assert_not_called()

    def test_remove_worktree_invalid_repo(self, temp_dir, mock_repo):
        """Test worktree removal with invalid repository."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "invalid-repo")

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.abspath", return_value=target_path):
                    with patch(
                        "cc_orchestrator.core.git_operations.Repo",
                        side_effect=InvalidGitRepositoryError("Invalid"),
                    ):
                        result = manager.remove_worktree(target_path)

                        assert result is False
                        mock_repo.git.worktree.assert_not_called()

    def test_remove_worktree_with_cleanup(self, temp_dir, mock_repo):
        """Test worktree removal with directory cleanup."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "worktree-with-cleanup")

        # Mock worktree repo
        mock_worktree_repo = Mock(spec=Repo)
        mock_repo.git.worktree.return_value = None

        with patch.object(manager, "_repo", mock_repo):
            with patch(
                "os.path.exists", side_effect=[True, True]
            ):  # Still exists after git removal
                with patch("os.path.abspath", return_value=target_path):
                    with patch("os.path.isfile", return_value=True):
                        with patch(
                            "cc_orchestrator.core.git_operations.Repo",
                            return_value=mock_worktree_repo,
                        ):
                            with patch("shutil.rmtree") as mock_rmtree:
                                result = manager.remove_worktree(target_path)

                                assert result is True
                                mock_rmtree.assert_called_once_with(target_path)

    def test_remove_worktree_cleanup_error(self, temp_dir, mock_repo):
        """Test worktree removal with cleanup error."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "worktree-cleanup-error")

        # Mock worktree repo
        mock_worktree_repo = Mock(spec=Repo)
        mock_repo.git.worktree.return_value = None

        with patch.object(manager, "_repo", mock_repo):
            with patch(
                "os.path.exists", side_effect=[True, True]
            ):  # Still exists after git removal
                with patch("os.path.abspath", return_value=target_path):
                    with patch("os.path.isfile", return_value=True):
                        with patch(
                            "cc_orchestrator.core.git_operations.Repo",
                            return_value=mock_worktree_repo,
                        ):
                            with patch(
                                "shutil.rmtree", side_effect=Exception("Cleanup failed")
                            ):
                                result = manager.remove_worktree(target_path)

                                # Should still return True despite cleanup error
                                assert result is True

    def test_remove_worktree_git_command_error(self, temp_dir, mock_repo):
        """Test worktree removal with Git command error."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "worktree-git-error")

        # Mock worktree repo
        mock_worktree_repo = Mock(spec=Repo)
        mock_repo.git.worktree.side_effect = GitCommandError("Remove failed")

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.abspath", return_value=target_path):
                    with patch("os.path.isfile", return_value=True):
                        with patch(
                            "cc_orchestrator.core.git_operations.Repo",
                            return_value=mock_worktree_repo,
                        ):
                            with pytest.raises(
                                GitWorktreeError, match="Failed to remove worktree"
                            ):
                                manager.remove_worktree(target_path)

    def test_remove_worktree_unexpected_error(self, temp_dir, mock_repo):
        """Test worktree removal with unexpected error."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "worktree-unexpected-error")

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=True):
                with patch(
                    "os.path.abspath", side_effect=Exception("Unexpected error")
                ):
                    with pytest.raises(
                        GitWorktreeError, match="Unexpected error removing worktree"
                    ):
                        manager.remove_worktree(target_path)

    def test_cleanup_worktrees_success(self, temp_dir, mock_repo):
        """Test successful worktree cleanup."""
        manager = GitWorktreeManager(repo_path=temp_dir)

        # Mock list_worktrees to return some worktrees
        mock_worktrees = [
            {"path": temp_dir},  # Main repo - should be skipped
            {"path": "/existing/path"},  # Existing path - should be skipped
            {"path": "/stale/path1"},  # Stale path - should be cleaned
            {"path": "/stale/path2"},  # Stale path - should be cleaned
            {"path": ""},  # Empty path - should be skipped
        ]

        mock_repo.git.worktree.return_value = None

        with patch.object(manager, "_repo", mock_repo):
            with patch.object(manager, "list_worktrees", return_value=mock_worktrees):
                with patch(
                    "os.path.exists",
                    side_effect=lambda p: p in [temp_dir, "/existing/path"],
                ):
                    cleaned = manager.cleanup_worktrees()

                    assert len(cleaned) == 2
                    assert "/stale/path1" in cleaned
                    assert "/stale/path2" in cleaned

                    # Verify prune was called
                    mock_repo.git.worktree.assert_called_with("prune")

    def test_cleanup_worktrees_no_stale(self, temp_dir, mock_repo):
        """Test worktree cleanup with no stale references."""
        manager = GitWorktreeManager(repo_path=temp_dir)

        # Mock list_worktrees to return only existing paths
        mock_worktrees = [
            {"path": temp_dir},  # Main repo
            {"path": "/existing/path"},  # Existing path
        ]

        with patch.object(manager, "_repo", mock_repo):
            with patch.object(manager, "list_worktrees", return_value=mock_worktrees):
                with patch("os.path.exists", return_value=True):  # All paths exist
                    cleaned = manager.cleanup_worktrees()

                    assert cleaned == []
                    mock_repo.git.worktree.assert_not_called()

    def test_cleanup_worktrees_prune_error(self, temp_dir, mock_repo):
        """Test worktree cleanup with prune error."""
        manager = GitWorktreeManager(repo_path=temp_dir)

        # Mock list_worktrees to return stale worktree
        mock_worktrees = [
            {"path": "/stale/path"},
        ]

        mock_repo.git.worktree.side_effect = GitCommandError("Prune failed")

        with patch.object(manager, "_repo", mock_repo):
            with patch.object(manager, "list_worktrees", return_value=mock_worktrees):
                with patch("os.path.exists", return_value=False):  # Stale path
                    cleaned = manager.cleanup_worktrees()

                    # Should return empty list due to prune error
                    assert cleaned == []

    def test_cleanup_worktrees_git_command_error(self, temp_dir, mock_repo):
        """Test worktree cleanup with Git command error in list_worktrees."""
        manager = GitWorktreeManager(repo_path=temp_dir)

        with patch.object(manager, "_repo", mock_repo):
            with patch.object(
                manager, "list_worktrees", side_effect=GitCommandError("List failed")
            ):
                with pytest.raises(
                    GitWorktreeError, match="Failed to cleanup worktrees"
                ):
                    manager.cleanup_worktrees()

    def test_cleanup_worktrees_unexpected_error(self, temp_dir, mock_repo):
        """Test worktree cleanup with unexpected error."""
        manager = GitWorktreeManager(repo_path=temp_dir)

        with patch.object(manager, "_repo", mock_repo):
            with patch.object(
                manager, "list_worktrees", side_effect=Exception("Unexpected error")
            ):
                with pytest.raises(
                    GitWorktreeError, match="Unexpected error during cleanup"
                ):
                    manager.cleanup_worktrees()

    def test_get_worktree_status_success(self, temp_dir, mock_repo):
        """Test successful worktree status retrieval."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "status-worktree")

        # Mock worktree repo
        mock_worktree_repo = Mock(spec=Repo)
        mock_worktree_repo.active_branch = Mock()
        mock_worktree_repo.active_branch.name = "feature-branch"
        mock_worktree_repo.active_branch.tracking_branch = Mock(return_value=None)
        mock_worktree_repo.head = Mock()
        mock_worktree_repo.head.commit = Mock()
        mock_worktree_repo.head.commit.hexsha = "status123commit"
        mock_worktree_repo.is_dirty = Mock(return_value=False)
        mock_worktree_repo.untracked_files = []
        mock_worktree_repo.index = Mock()
        mock_worktree_repo.index.diff = Mock(return_value=[])

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.abspath", return_value=target_path):
                    with patch(
                        "cc_orchestrator.core.git_operations.Repo",
                        return_value=mock_worktree_repo,
                    ):
                        status = manager.get_worktree_status(target_path)

                        assert status["path"] == target_path
                        assert status["branch"] == "feature-branch"
                        assert status["commit"] == "status123commit"
                        assert status["has_changes"] is False
                        assert status["is_dirty"] is False
                        assert status["ahead"] == 0
                        assert status["behind"] == 0

    def test_get_worktree_status_with_changes(self, temp_dir, mock_repo):
        """Test worktree status with changes."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "changed-worktree")

        # Mock worktree repo with changes
        mock_worktree_repo = Mock(spec=Repo)
        mock_worktree_repo.active_branch = Mock()
        mock_worktree_repo.active_branch.name = "feature-branch"
        mock_worktree_repo.active_branch.tracking_branch = Mock(return_value=None)
        mock_worktree_repo.head = Mock()
        mock_worktree_repo.head.commit = Mock()
        mock_worktree_repo.head.commit.hexsha = "changed123commit"
        mock_worktree_repo.is_dirty = Mock(return_value=True)
        mock_worktree_repo.untracked_files = ["new_file.txt"]
        mock_worktree_repo.index = Mock()
        mock_worktree_repo.index.diff = Mock(return_value=["diff1", "diff2"])

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.abspath", return_value=target_path):
                    with patch(
                        "cc_orchestrator.core.git_operations.Repo",
                        return_value=mock_worktree_repo,
                    ):
                        status = manager.get_worktree_status(target_path)

                        assert status["has_changes"] is True
                        assert status["is_dirty"] is True

    def test_get_worktree_status_with_tracking(self, temp_dir, mock_repo):
        """Test worktree status with remote tracking."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "tracking-worktree")

        # Mock tracking branch
        mock_tracking_branch = Mock()

        # Mock worktree repo with tracking
        mock_worktree_repo = Mock(spec=Repo)
        mock_worktree_repo.active_branch = Mock()
        mock_worktree_repo.active_branch.name = "feature-branch"
        mock_worktree_repo.active_branch.tracking_branch = Mock(
            return_value=mock_tracking_branch
        )
        mock_worktree_repo.head = Mock()
        mock_worktree_repo.head.commit = Mock()
        mock_worktree_repo.head.commit.hexsha = "tracking123commit"
        mock_worktree_repo.is_dirty = Mock(return_value=False)
        mock_worktree_repo.untracked_files = []
        mock_worktree_repo.index = Mock()
        mock_worktree_repo.index.diff = Mock(return_value=[])

        # Mock ahead/behind commits
        mock_worktree_repo.iter_commits = Mock(
            side_effect=[
                ["commit1", "commit2"],  # 2 commits ahead
                ["commit3"],  # 1 commit behind
            ]
        )

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.abspath", return_value=target_path):
                    with patch(
                        "cc_orchestrator.core.git_operations.Repo",
                        return_value=mock_worktree_repo,
                    ):
                        status = manager.get_worktree_status(target_path)

                        assert status["ahead"] == 2
                        assert status["behind"] == 1

    def test_get_worktree_status_tracking_error(self, temp_dir, mock_repo):
        """Test worktree status with remote tracking error."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "tracking-error-worktree")

        # Mock tracking branch with error
        mock_tracking_branch = Mock()

        # Mock worktree repo
        mock_worktree_repo = Mock(spec=Repo)
        mock_worktree_repo.active_branch = Mock()
        mock_worktree_repo.active_branch.name = "feature-branch"
        mock_worktree_repo.active_branch.tracking_branch = Mock(
            return_value=mock_tracking_branch
        )
        mock_worktree_repo.head = Mock()
        mock_worktree_repo.head.commit = Mock()
        mock_worktree_repo.head.commit.hexsha = "error123commit"
        mock_worktree_repo.is_dirty = Mock(return_value=False)
        mock_worktree_repo.untracked_files = []
        mock_worktree_repo.index = Mock()
        mock_worktree_repo.index.diff = Mock(return_value=[])

        # Mock iter_commits to raise error
        mock_worktree_repo.iter_commits = Mock(side_effect=Exception("Tracking error"))

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.abspath", return_value=target_path):
                    with patch(
                        "cc_orchestrator.core.git_operations.Repo",
                        return_value=mock_worktree_repo,
                    ):
                        status = manager.get_worktree_status(target_path)

                        # Should default to 0 when tracking fails
                        assert status["ahead"] == 0
                        assert status["behind"] == 0

    def test_get_worktree_status_path_not_exists(self, temp_dir, mock_repo):
        """Test worktree status when path doesn't exist."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "nonexistent")

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=False):
                with patch("os.path.abspath", return_value=target_path):
                    with pytest.raises(GitWorktreeError, match="does not exist"):
                        manager.get_worktree_status(target_path)

    def test_get_worktree_status_invalid_repo(self, temp_dir, mock_repo):
        """Test worktree status with invalid repository."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "invalid-repo")

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.abspath", return_value=target_path):
                    with patch(
                        "cc_orchestrator.core.git_operations.Repo",
                        side_effect=InvalidGitRepositoryError("Invalid"),
                    ):
                        with pytest.raises(
                            GitWorktreeError, match="Invalid git repository"
                        ):
                            manager.get_worktree_status(target_path)

    def test_get_worktree_status_unexpected_error(self, temp_dir, mock_repo):
        """Test worktree status with unexpected error."""
        manager = GitWorktreeManager(repo_path=temp_dir)
        target_path = os.path.join(temp_dir, "unexpected-error")

        with patch.object(manager, "_repo", mock_repo):
            with patch("os.path.exists", return_value=True):
                with patch(
                    "os.path.abspath", side_effect=Exception("Unexpected error")
                ):
                    with pytest.raises(
                        GitWorktreeError, match="Failed to get worktree status"
                    ):
                        manager.get_worktree_status(target_path)

    def test_generate_worktree_path_unique(self, temp_dir):
        """Test worktree path generation with unique name."""
        manager = GitWorktreeManager(repo_path=temp_dir)

        with patch("pathlib.Path.exists", return_value=False):
            path = manager.generate_worktree_path(temp_dir, "unique-name")
            expected = os.path.join(temp_dir, "unique-name")
            assert path == expected

    def test_generate_worktree_path_with_conflict(self, temp_dir):
        """Test worktree path generation with naming conflicts."""
        manager = GitWorktreeManager(repo_path=temp_dir)

        # Mock exists to return True for base name and first increment, False for second
        with patch("pathlib.Path.exists", side_effect=[True, True, False]):
            path = manager.generate_worktree_path(temp_dir, "conflicted-name")
            expected = os.path.join(temp_dir, "conflicted-name-2")
            assert path == expected

    def test_generate_worktree_path_multiple_conflicts(self, temp_dir):
        """Test worktree path generation with multiple conflicts."""
        manager = GitWorktreeManager(repo_path=temp_dir)

        # Mock exists to return True for multiple attempts
        with patch("pathlib.Path.exists", side_effect=[True, True, True, True, False]):
            path = manager.generate_worktree_path(temp_dir, "very-conflicted")
            expected = os.path.join(temp_dir, "very-conflicted-4")
            assert path == expected
