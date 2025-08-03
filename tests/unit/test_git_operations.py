"""Unit tests for git operations module."""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from git import Repo
from git.exc import GitCommandError

from cc_orchestrator.core.git_operations import (
    BranchStrategy,
    BranchValidator,
    ConflictType,
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


class TestBranchValidator:
    """Test cases for BranchValidator."""

    def test_generate_branch_name_feature(self):
        """Test generating feature branch names."""
        result = BranchValidator.generate_branch_name(
            BranchStrategy.FEATURE, "issue-123"
        )
        assert result == "feature/issue-123"

    def test_generate_branch_name_with_suffix(self):
        """Test generating branch names with suffix."""
        result = BranchValidator.generate_branch_name(
            BranchStrategy.FEATURE, "issue-123", "authentication"
        )
        assert result == "feature/issue-123/authentication"

    def test_generate_branch_name_sanitized(self):
        """Test generating branch names with sanitization."""
        result = BranchValidator.generate_branch_name(
            BranchStrategy.FEATURE, "Issue #123: Fix Authentication"
        )
        assert result == "feature/issue-123-fix-authentication"

    def test_validate_branch_name_valid_feature(self):
        """Test validating valid feature branch name."""
        result = BranchValidator.validate_branch_name(
            "feature/issue-123", BranchStrategy.FEATURE
        )
        assert result is True

    def test_validate_branch_name_invalid_feature(self):
        """Test validating invalid feature branch name."""
        result = BranchValidator.validate_branch_name(
            "hotfix/issue-123", BranchStrategy.FEATURE
        )
        assert result is False

    def test_detect_strategy_feature(self):
        """Test detecting feature strategy."""
        result = BranchValidator.detect_strategy("feature/add-login")
        assert result == BranchStrategy.FEATURE

    def test_detect_strategy_hotfix(self):
        """Test detecting hotfix strategy."""
        result = BranchValidator.detect_strategy("hotfix/critical-bug")
        assert result == BranchStrategy.HOTFIX

    def test_detect_strategy_release(self):
        """Test detecting release strategy."""
        result = BranchValidator.detect_strategy("release/v1.2.3")
        assert result == BranchStrategy.RELEASE

    def test_detect_strategy_none(self):
        """Test detecting no strategy."""
        result = BranchValidator.detect_strategy("random-branch-name")
        assert result is None

    def test_sanitize_identifier(self):
        """Test identifier sanitization."""
        result = BranchValidator._sanitize_identifier("Issue #123: Fix Authentication!")
        assert result == "issue-123-fix-authentication"

    def test_sanitize_identifier_spaces_underscores(self):
        """Test sanitizing spaces and underscores."""
        result = BranchValidator._sanitize_identifier("test_feature with spaces")
        assert result == "test-feature-with-spaces"

    def test_generate_branch_name_invalid_identifier(self):
        """Test generating branch name with invalid identifier."""
        with pytest.raises(GitWorktreeError, match="Invalid identifier"):
            BranchValidator.generate_branch_name(BranchStrategy.FEATURE, "")

    def test_all_strategies_have_patterns(self):
        """Test that all strategies have regex patterns defined."""
        for strategy in BranchStrategy:
            assert strategy in BranchValidator.STRATEGY_PATTERNS

    def test_hotfix_pattern(self):
        """Test hotfix branch pattern validation."""
        valid_names = [
            "hotfix/critical-issue",
            "hotfix/security-patch",
            "hotfix/bug-123",
        ]
        invalid_names = [
            "hotfix/",
            "hotfix/UPPERCASE",
            "hotfix/with spaces",
            "feature/not-hotfix",
        ]

        for name in valid_names:
            assert BranchValidator.validate_branch_name(name, BranchStrategy.HOTFIX)

        for name in invalid_names:
            assert not BranchValidator.validate_branch_name(name, BranchStrategy.HOTFIX)

    def test_release_pattern(self):
        """Test release branch pattern validation."""
        valid_names = [
            "release/v1.0.0",
            "release/1.2.3",
            "release/v2.0.0-beta",
            "release/v1.0.0-alpha-1",
        ]
        invalid_names = [
            "release/",
            "release/not-a-version",
            "release/v1",
            "feature/v1.0.0",
        ]

        for name in valid_names:
            assert BranchValidator.validate_branch_name(name, BranchStrategy.RELEASE)

        for name in invalid_names:
            assert not BranchValidator.validate_branch_name(
                name, BranchStrategy.RELEASE
            )


class TestGitWorktreeManagerEnhanced:
    """Test cases for enhanced GitWorktreeManager functionality."""

    @pytest.fixture
    def manager(self):
        """Create GitWorktreeManager instance for testing."""
        with patch("cc_orchestrator.core.git_operations.Repo") as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            manager = GitWorktreeManager("/test/repo")
            manager._repo = mock_repo
            return manager

    def test_check_worktree_conflicts_no_conflicts(self, manager):
        """Test conflict checking with no conflicts."""
        path = "/test/worktree"
        branch = "feature/test"

        with (
            patch("os.path.exists", return_value=False),
            patch.object(manager.repo, "git") as mock_git,
        ):
            mock_git.show_ref.side_effect = GitCommandError("show-ref", 1, "not found")
            manager.repo.is_dirty.return_value = False
            manager.repo.untracked_files = []

            conflicts = manager.check_worktree_conflicts(path, branch)

            assert conflicts == []

    def test_check_worktree_conflicts_path_exists(self, manager):
        """Test conflict checking when path exists."""
        path = "/test/worktree"
        branch = "feature/test"

        with (
            patch("os.path.exists", return_value=True),
            patch.object(manager.repo, "git") as mock_git,
        ):
            # Mock other checks to not trigger conflicts
            mock_git.show_ref.side_effect = GitCommandError("show-ref", 1, "not found")
            manager.repo.is_dirty.return_value = False
            manager.repo.untracked_files = []

            conflicts = manager.check_worktree_conflicts(path, branch)

            assert len(conflicts) == 1
            assert conflicts[0]["type"] == ConflictType.PATH_EXISTS.value
            assert "already exists" in conflicts[0]["message"]

    def test_check_worktree_conflicts_branch_exists(self, manager):
        """Test conflict checking when branch exists."""
        path = "/test/worktree"
        branch = "feature/existing"

        with (
            patch("os.path.exists", return_value=False),
            patch.object(manager.repo, "git") as mock_git,
        ):
            mock_git.show_ref.return_value = "some output"  # Branch exists
            manager.repo.is_dirty.return_value = False
            manager.repo.untracked_files = []

            conflicts = manager.check_worktree_conflicts(path, branch)

            assert len(conflicts) == 1
            assert conflicts[0]["type"] == ConflictType.BRANCH_EXISTS.value

    def test_check_worktree_conflicts_uncommitted_changes(self, manager):
        """Test conflict checking with uncommitted changes."""
        path = "/test/worktree"
        branch = "feature/test"

        with (
            patch("os.path.exists", return_value=False),
            patch.object(manager.repo, "git") as mock_git,
        ):
            mock_git.show_ref.side_effect = GitCommandError("show-ref", 1, "not found")
            manager.repo.is_dirty.return_value = True
            manager.repo.untracked_files = ["untracked.txt"]

            conflicts = manager.check_worktree_conflicts(path, branch)

            assert len(conflicts) == 1
            assert conflicts[0]["type"] == ConflictType.UNCOMMITTED_CHANGES.value

    def test_validate_branch_strategy_valid(self, manager):
        """Test branch strategy validation with valid branch."""
        result = manager.validate_branch_strategy(
            "feature/test-123", BranchStrategy.FEATURE
        )

        assert result["valid"] is True
        assert result["strategy"] == "feature"
        assert "follows feature convention" in result["message"]

    def test_validate_branch_strategy_invalid(self, manager):
        """Test branch strategy validation with invalid branch."""
        result = manager.validate_branch_strategy(
            "hotfix/test-123", BranchStrategy.FEATURE
        )

        assert result["valid"] is False
        assert result["strategy"] == "feature"
        assert "doesn't follow feature convention" in result["message"]

    def test_validate_branch_strategy_auto_detect(self, manager):
        """Test branch strategy validation with auto-detection."""
        result = manager.validate_branch_strategy("hotfix/critical-fix")

        assert result["valid"] is True
        assert result["strategy"] == "hotfix"
        assert "follows hotfix convention" in result["message"]

    def test_suggest_branch_name_unique(self, manager):
        """Test suggesting unique branch name."""
        with patch.object(manager.repo, "git") as mock_git:
            mock_git.show_ref.side_effect = GitCommandError("show-ref", 1, "not found")

            result = manager.suggest_branch_name(BranchStrategy.FEATURE, "test-123")

            assert result == "feature/test-123"

    def test_suggest_branch_name_with_collision(self, manager):
        """Test suggesting branch name with collision."""
        with patch.object(manager.repo, "git") as mock_git:
            # First call succeeds (branch exists), second fails (doesn't exist)
            mock_git.show_ref.side_effect = [
                "some output",  # First attempt - branch exists
                GitCommandError("show-ref", 1, "not found"),  # Second - doesn't exist
            ]

            result = manager.suggest_branch_name(BranchStrategy.FEATURE, "test-123")

            assert result == "feature/test-123-1"

    def test_cleanup_stale_branches_dry_run(self, manager):
        """Test cleaning up stale branches in dry-run mode."""
        # Mock branches with very old timestamps
        mock_branch1 = Mock()
        mock_branch1.name = "feature/old-branch"
        mock_branch1.commit.committed_date = 1000000  # Very old timestamp

        mock_branch2 = Mock()
        mock_branch2.name = "main"
        mock_branch2.commit.committed_date = 1000000

        with (
            patch.object(manager, "list_worktrees", return_value=[]),
            patch("cc_orchestrator.core.git_operations.datetime") as mock_datetime,
        ):
            # Mock current time to be much later (current timestamp is around 1.7 billion)
            mock_now = Mock()
            mock_now.timestamp.return_value = 1700000000  # Much more recent time
            mock_datetime.now.return_value = mock_now

            manager.repo.branches = [mock_branch1, mock_branch2]

            result = manager.cleanup_stale_branches(days_old=30, dry_run=True)

            assert "feature/old-branch" in result["stale_branches"]
            assert "main" not in result["stale_branches"]  # Protected
            assert result["deleted"] == []  # Dry run

    def test_cleanup_stale_branches_with_active_worktree(self, manager):
        """Test cleanup excludes branches with active worktrees."""
        mock_branch = Mock()
        mock_branch.name = "feature/active-branch"
        mock_branch.commit.committed_date = 1000000

        with (
            patch.object(manager, "list_worktrees") as mock_list,
            patch("cc_orchestrator.core.git_operations.datetime") as mock_datetime,
        ):
            mock_now = Mock()
            mock_now.timestamp.return_value = 1700000000  # Much more recent time
            mock_datetime.now.return_value = mock_now

            mock_list.return_value = [{"branch": "feature/active-branch"}]
            manager.repo.branches = [mock_branch]

            result = manager.cleanup_stale_branches(days_old=30, dry_run=True)

            assert result["stale_branches"] == []  # Should be excluded
