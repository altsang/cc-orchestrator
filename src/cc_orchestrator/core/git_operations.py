"""Git operations for worktree management."""

import os
import re
import shutil
from datetime import datetime
from enum import Enum
from pathlib import Path

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from ..utils.logging import LogContext, get_logger

logger = get_logger(__name__, LogContext.WORKTREE)


class GitWorktreeError(Exception):
    """Base exception for git worktree operations."""

    pass


class BranchStrategy(Enum):
    """Branch naming strategies for worktrees."""

    FEATURE = "feature"
    HOTFIX = "hotfix"
    BUGFIX = "bugfix"
    RELEASE = "release"
    EXPERIMENT = "experiment"


class ConflictType(Enum):
    """Types of conflicts that can occur during worktree creation."""

    BRANCH_EXISTS = "branch_exists"
    PATH_EXISTS = "path_exists"
    UNCOMMITTED_CHANGES = "uncommitted_changes"
    MERGE_CONFLICT = "merge_conflict"
    REMOTE_DIVERGED = "remote_diverged"


class BranchValidator:
    """Validates branch names and enforces naming conventions."""

    # Branch name patterns for different strategies
    STRATEGY_PATTERNS = {
        BranchStrategy.FEATURE: r"^feature/[a-z0-9-]+(?:/[a-z0-9-]+)*$",
        BranchStrategy.HOTFIX: r"^hotfix/[a-z0-9-]+(?:/[a-z0-9-]+)*$",
        BranchStrategy.BUGFIX: r"^bugfix/[a-z0-9-]+(?:/[a-z0-9-]+)*$",
        BranchStrategy.RELEASE: r"^release/v?\d+\.\d+(?:\.\d+)?(?:-[a-z0-9-]+)*$",
        BranchStrategy.EXPERIMENT: r"^experiment/[a-z0-9-]+(?:/[a-z0-9-]+)*$",
    }

    @classmethod
    def generate_branch_name(
        cls,
        strategy: BranchStrategy,
        identifier: str,
        suffix: str | None = None,
    ) -> str:
        """Generate a branch name following naming conventions.

        Args:
            strategy: Branch strategy to use
            identifier: Main identifier (e.g., issue number, feature name)
            suffix: Optional suffix for additional context

        Returns:
            Generated branch name

        Raises:
            GitWorktreeError: If identifier is invalid
        """
        # Sanitize identifier
        clean_id = cls._sanitize_identifier(identifier)
        if not clean_id:
            raise GitWorktreeError(f"Invalid identifier: {identifier}")

        # Build branch name
        if suffix:
            clean_suffix = cls._sanitize_identifier(suffix)
            branch_name = f"{strategy.value}/{clean_id}/{clean_suffix}"
        else:
            branch_name = f"{strategy.value}/{clean_id}"

        # Validate against pattern
        if not cls.validate_branch_name(branch_name, strategy):
            raise GitWorktreeError(
                f"Generated branch name doesn't match pattern: {branch_name}"
            )

        return branch_name

    @classmethod
    def validate_branch_name(cls, branch_name: str, strategy: BranchStrategy) -> bool:
        """Validate if branch name follows the strategy's naming convention.

        Args:
            branch_name: Branch name to validate
            strategy: Expected branch strategy

        Returns:
            True if branch name is valid
        """
        pattern = cls.STRATEGY_PATTERNS.get(strategy)
        if not pattern:
            return False

        return bool(re.match(pattern, branch_name))

    @classmethod
    def detect_strategy(cls, branch_name: str) -> BranchStrategy | None:
        """Detect the branch strategy from a branch name.

        Args:
            branch_name: Branch name to analyze

        Returns:
            Detected strategy or None if no pattern matches
        """
        for strategy, pattern in cls.STRATEGY_PATTERNS.items():
            if re.match(pattern, branch_name):
                return strategy
        return None

    @staticmethod
    def _sanitize_identifier(identifier: str) -> str:
        """Sanitize identifier for use in branch names.

        Args:
            identifier: Raw identifier

        Returns:
            Sanitized identifier safe for git branch names
        """
        # Convert to lowercase
        clean = identifier.lower()

        # Replace spaces and underscores with hyphens
        clean = re.sub(r"[_\s]+", "-", clean)

        # Remove non-alphanumeric characters except hyphens and slashes
        clean = re.sub(r"[^a-z0-9-/]", "", clean)

        # Remove leading/trailing hyphens
        clean = clean.strip("-")

        # Collapse multiple hyphens
        clean = re.sub(r"-+", "-", clean)

        return clean


class GitWorktreeManager:
    """Manages git worktree operations using GitPython."""

    def __init__(self, repo_path: str | None = None):
        """Initialize the GitWorktreeManager.

        Args:
            repo_path: Path to the git repository. If None, uses current directory.
        """
        self.repo_path = repo_path or os.getcwd()
        self._repo: Repo | None = None

    @property
    def repo(self) -> Repo:
        """Get the Git repository object."""
        if self._repo is None:
            try:
                self._repo = Repo(self.repo_path)
            except InvalidGitRepositoryError as e:
                raise GitWorktreeError(
                    f"Invalid git repository at {self.repo_path}"
                ) from e
        return self._repo

    def list_worktrees(self) -> list[dict[str, str]]:
        """List all git worktrees.

        Returns:
            List of dictionaries containing worktree information:
            - path: Full path to the worktree
            - branch: Branch name
            - commit: Current commit SHA
            - status: Status (bare, detached, etc.)
        """
        try:
            # Use git worktree list command
            worktree_output = self.repo.git.worktree("list", "--porcelain")

            worktrees = []
            current_worktree = {}

            for line in worktree_output.split("\n"):
                if not line.strip():
                    if current_worktree:
                        worktrees.append(current_worktree)
                        current_worktree = {}
                    continue

                if line.startswith("worktree "):
                    current_worktree["path"] = line[9:]  # Remove "worktree " prefix
                elif line.startswith("HEAD "):
                    current_worktree["commit"] = line[5:]
                elif line.startswith("branch "):
                    current_worktree["branch"] = line[7:]  # Remove "branch " prefix
                elif line.startswith("detached"):
                    current_worktree["status"] = "detached"
                elif line.startswith("bare"):
                    current_worktree["status"] = "bare"

            # Add the last worktree if exists
            if current_worktree:
                worktrees.append(current_worktree)

            logger.info(f"Found {len(worktrees)} worktrees")
            return worktrees

        except GitCommandError as e:
            logger.error(f"Failed to list worktrees: {e}")
            raise GitWorktreeError(f"Failed to list worktrees: {e}") from e

    def create_worktree(
        self,
        path: str,
        branch: str,
        checkout_branch: str | None = None,
        force: bool = False,
    ) -> dict[str, str]:
        """Create a new git worktree.

        Args:
            path: Path where the worktree should be created
            branch: Name of the new branch to create for the worktree
            checkout_branch: Existing branch to checkout (defaults to main/master)
            force: Force creation even if path exists

        Returns:
            Dictionary with worktree information:
            - path: Full path to the created worktree
            - branch: Branch name
            - commit: Current commit SHA

        Raises:
            GitWorktreeError: If worktree creation fails
        """
        try:
            # Resolve absolute path
            abs_path = os.path.abspath(path)

            # Check if path already exists
            if os.path.exists(abs_path) and not force:
                raise GitWorktreeError(f"Path {abs_path} already exists")

            # Determine checkout branch if not specified
            if checkout_branch is None:
                # Try to find main or master branch
                try:
                    checkout_branch = "main"
                    self.repo.git.show_ref("refs/heads/main")
                except GitCommandError:
                    try:
                        checkout_branch = "master"
                        self.repo.git.show_ref("refs/heads/master")
                    except GitCommandError:
                        # Use the current branch
                        checkout_branch = self.repo.active_branch.name

            # Create the worktree
            logger.info(f"Creating worktree at {abs_path} with branch {branch}")

            cmd_args = ["add"]
            if force:
                cmd_args.append("--force")
            cmd_args.extend(["-b", branch, abs_path, checkout_branch])

            self.repo.git.worktree(*cmd_args)

            # Get the commit SHA of the created worktree
            worktree_repo = Repo(abs_path)
            commit_sha = worktree_repo.head.commit.hexsha

            result = {
                "path": abs_path,
                "branch": branch,
                "commit": commit_sha,
                "status": "active",
            }

            logger.info(f"Successfully created worktree: {result}")
            return result

        except GitCommandError as e:
            logger.error(f"Failed to create worktree: {e}")
            raise GitWorktreeError(f"Failed to create worktree: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error creating worktree: {e}")
            raise GitWorktreeError(f"Unexpected error creating worktree: {e}") from e

    def remove_worktree(self, path: str, force: bool = False) -> bool:
        """Remove a git worktree.

        Args:
            path: Path to the worktree to remove
            force: Force removal even if worktree has uncommitted changes

        Returns:
            True if worktree was successfully removed

        Raises:
            GitWorktreeError: If worktree removal fails
        """
        try:
            abs_path = os.path.abspath(path)

            # Check if worktree exists
            if not os.path.exists(abs_path):
                logger.warning(f"Worktree path {abs_path} does not exist")
                return False

            # Check if it's actually a worktree
            try:
                Repo(abs_path)
                # Verify it's a worktree by checking if it has a .git file (not directory)
                git_path = os.path.join(abs_path, ".git")
                if not os.path.isfile(git_path):
                    logger.warning(f"Path {abs_path} is not a git worktree")
                    return False
            except InvalidGitRepositoryError:
                logger.warning(f"Path {abs_path} is not a valid git repository")
                return False

            logger.info(f"Removing worktree at {abs_path}")

            # Remove the worktree
            cmd_args = ["remove"]
            if force:
                cmd_args.append("--force")
            cmd_args.append(abs_path)

            self.repo.git.worktree(*cmd_args)

            # Clean up any remaining directory if it still exists
            if os.path.exists(abs_path):
                try:
                    shutil.rmtree(abs_path)
                    logger.info(f"Cleaned up remaining directory at {abs_path}")
                except Exception as e:
                    logger.warning(f"Could not clean up directory {abs_path}: {e}")

            logger.info(f"Successfully removed worktree at {abs_path}")
            return True

        except GitCommandError as e:
            logger.error(f"Failed to remove worktree: {e}")
            raise GitWorktreeError(f"Failed to remove worktree: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error removing worktree: {e}")
            raise GitWorktreeError(f"Unexpected error removing worktree: {e}") from e

    def cleanup_worktrees(self) -> list[str]:
        """Clean up stale worktree references.

        This removes worktree entries that point to non-existent directories.

        Returns:
            List of cleaned up worktree paths

        Raises:
            GitWorktreeError: If cleanup fails
        """
        try:
            logger.info("Cleaning up stale worktree references")

            # Get list of current worktrees
            worktrees = self.list_worktrees()
            cleaned_paths = []

            for worktree in worktrees:
                path = worktree.get("path")
                if not path:
                    continue

                # Skip the main repository
                if path == self.repo_path:
                    continue

                # Check if the path exists
                if not os.path.exists(path):
                    logger.info(f"Found stale worktree reference: {path}")
                    try:
                        # Use prune to clean up the reference
                        self.repo.git.worktree("prune")
                        cleaned_paths.append(path)
                        logger.info(f"Cleaned up stale reference: {path}")
                    except GitCommandError as e:
                        logger.warning(f"Could not clean up {path}: {e}")

            if not cleaned_paths:
                logger.info("No stale worktree references found")
            else:
                logger.info(f"Cleaned up {len(cleaned_paths)} stale references")

            return cleaned_paths

        except GitCommandError as e:
            logger.error(f"Failed to cleanup worktrees: {e}")
            raise GitWorktreeError(f"Failed to cleanup worktrees: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during cleanup: {e}")
            raise GitWorktreeError(f"Unexpected error during cleanup: {e}") from e

    def get_worktree_status(self, path: str) -> dict[str, any]:
        """Get detailed status of a worktree.

        Args:
            path: Path to the worktree

        Returns:
            Dictionary with status information:
            - path: Worktree path
            - branch: Current branch
            - commit: Current commit SHA
            - has_changes: Whether there are uncommitted changes
            - is_dirty: Whether working directory is dirty
            - ahead: Number of commits ahead of remote
            - behind: Number of commits behind remote

        Raises:
            GitWorktreeError: If status check fails
        """
        try:
            abs_path = os.path.abspath(path)

            if not os.path.exists(abs_path):
                raise GitWorktreeError(f"Worktree path {abs_path} does not exist")

            # Get repository for this worktree
            worktree_repo = Repo(abs_path)

            # Get basic information
            current_branch = worktree_repo.active_branch.name
            current_commit = worktree_repo.head.commit.hexsha
            is_dirty = worktree_repo.is_dirty()

            # Check for uncommitted changes (including untracked files)
            has_changes = (
                is_dirty
                or len(worktree_repo.untracked_files) > 0
                or len(list(worktree_repo.index.diff("HEAD"))) > 0
            )

            # Try to get remote tracking info
            ahead = 0
            behind = 0
            try:
                if worktree_repo.active_branch.tracking_branch():
                    commits_ahead_behind = list(
                        worktree_repo.iter_commits(
                            f"{worktree_repo.active_branch.tracking_branch()}..{current_branch}"
                        )
                    )
                    ahead = len(commits_ahead_behind)

                    commits_behind = list(
                        worktree_repo.iter_commits(
                            f"{current_branch}..{worktree_repo.active_branch.tracking_branch()}"
                        )
                    )
                    behind = len(commits_behind)
            except Exception as e:
                logger.debug(f"Could not get remote tracking info for {path}: {e}")

            status = {
                "path": abs_path,
                "branch": current_branch,
                "commit": current_commit,
                "has_changes": has_changes,
                "is_dirty": is_dirty,
                "ahead": ahead,
                "behind": behind,
            }

            logger.debug(f"Worktree status for {path}: {status}")
            return status

        except InvalidGitRepositoryError as e:
            raise GitWorktreeError(f"Invalid git repository at {path}") from e
        except Exception as e:
            logger.error(f"Failed to get worktree status for {path}: {e}")
            raise GitWorktreeError(f"Failed to get worktree status: {e}") from e

    def generate_worktree_path(self, base_dir: str, name: str) -> str:
        """Generate a unique worktree path.

        Args:
            base_dir: Base directory for worktrees
            name: Desired name for the worktree

        Returns:
            Full path for the worktree
        """
        base_path = Path(base_dir) / name
        counter = 1

        # Make sure we don't conflict with existing paths
        while base_path.exists():
            base_path = Path(base_dir) / f"{name}-{counter}"
            counter += 1

        return str(base_path)

    def check_worktree_conflicts(
        self,
        path: str,
        branch: str,
        checkout_branch: str | None = None,
    ) -> list[dict[str, str]]:
        """Check for potential conflicts before creating a worktree.

        Args:
            path: Path where the worktree would be created
            branch: Name of the new branch to create
            checkout_branch: Existing branch to checkout from

        Returns:
            List of conflict dictionaries with 'type' and 'message' keys

        Raises:
            GitWorktreeError: If conflict check fails
        """
        conflicts = []

        try:
            # Check if path already exists
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                conflicts.append(
                    {
                        "type": ConflictType.PATH_EXISTS.value,
                        "message": f"Path already exists: {abs_path}",
                    }
                )

            # Check if branch already exists
            try:
                self.repo.git.show_ref(f"refs/heads/{branch}")
                conflicts.append(
                    {
                        "type": ConflictType.BRANCH_EXISTS.value,
                        "message": f"Branch already exists: {branch}",
                    }
                )
            except GitCommandError:
                # Branch doesn't exist, which is what we want
                pass

            # Check for uncommitted changes in main repo
            if self.repo.is_dirty() or self.repo.untracked_files:
                conflicts.append(
                    {
                        "type": ConflictType.UNCOMMITTED_CHANGES.value,
                        "message": "Repository has uncommitted changes",
                    }
                )

            # Check for merge conflicts with checkout branch
            if checkout_branch:
                try:
                    # Test merge to see if there would be conflicts
                    merge_base = self.repo.merge_base(
                        self.repo.active_branch.commit,
                        self.repo.refs[checkout_branch].commit,
                    )

                    if merge_base:
                        # Check if branches have diverged significantly
                        commits_ahead = list(
                            self.repo.iter_commits(
                                f"{checkout_branch}..{self.repo.active_branch.name}"
                            )
                        )
                        commits_behind = list(
                            self.repo.iter_commits(
                                f"{self.repo.active_branch.name}..{checkout_branch}"
                            )
                        )

                        if len(commits_ahead) > 10 or len(commits_behind) > 10:
                            conflicts.append(
                                {
                                    "type": ConflictType.REMOTE_DIVERGED.value,
                                    "message": f"Branches have diverged significantly: {len(commits_ahead)} ahead, {len(commits_behind)} behind",
                                }
                            )

                        # Try to simulate merge to detect conflicts
                        try:
                            # This is a dry run - we're not actually merging
                            self.repo.git.merge_tree(
                                merge_base[0].hexsha,
                                self.repo.active_branch.commit.hexsha,
                                self.repo.refs[checkout_branch].commit.hexsha,
                            )
                        except GitCommandError as e:
                            if "conflicts" in str(e).lower():
                                conflicts.append(
                                    {
                                        "type": ConflictType.MERGE_CONFLICT.value,
                                        "message": f"Potential merge conflicts detected with {checkout_branch}",
                                    }
                                )

                except (GitCommandError, KeyError) as e:
                    logger.warning(f"Could not check merge conflicts: {e}")

            logger.info(
                f"Found {len(conflicts)} potential conflicts for worktree {path}"
            )
            return conflicts

        except Exception as e:
            logger.error(f"Failed to check worktree conflicts: {e}")
            raise GitWorktreeError(f"Failed to check conflicts: {e}") from e

    def validate_branch_strategy(
        self,
        branch_name: str,
        expected_strategy: BranchStrategy | None = None,
    ) -> dict[str, any]:
        """Validate branch name against naming conventions.

        Args:
            branch_name: Branch name to validate
            expected_strategy: Expected branch strategy (optional)

        Returns:
            Dictionary with validation results:
            - valid: Whether branch name is valid
            - strategy: Detected or expected strategy
            - message: Validation message
        """
        try:
            detected_strategy = BranchValidator.detect_strategy(branch_name)

            if expected_strategy:
                # Validate against expected strategy
                is_valid = BranchValidator.validate_branch_name(
                    branch_name, expected_strategy
                )
                if is_valid:
                    return {
                        "valid": True,
                        "strategy": expected_strategy.value,
                        "message": f"Branch name follows {expected_strategy.value} convention",
                    }
                else:
                    return {
                        "valid": False,
                        "strategy": expected_strategy.value,
                        "message": f"Branch name doesn't follow {expected_strategy.value} convention",
                    }
            else:
                # Auto-detect strategy
                if detected_strategy:
                    return {
                        "valid": True,
                        "strategy": detected_strategy.value,
                        "message": f"Branch name follows {detected_strategy.value} convention",
                    }
                else:
                    return {
                        "valid": False,
                        "strategy": None,
                        "message": "Branch name doesn't follow any recognized convention",
                    }

        except Exception as e:
            logger.error(f"Failed to validate branch strategy: {e}")
            return {
                "valid": False,
                "strategy": None,
                "message": f"Validation error: {e}",
            }

    def suggest_branch_name(
        self,
        strategy: BranchStrategy,
        identifier: str,
        suffix: str | None = None,
    ) -> str:
        """Suggest a branch name following conventions.

        Args:
            strategy: Branch strategy to use
            identifier: Main identifier
            suffix: Optional suffix

        Returns:
            Suggested branch name

        Raises:
            GitWorktreeError: If suggestion fails
        """
        try:
            suggested_name = BranchValidator.generate_branch_name(
                strategy, identifier, suffix
            )

            # Check if suggested branch already exists
            counter = 1
            original_name = suggested_name

            while True:
                try:
                    self.repo.git.show_ref(f"refs/heads/{suggested_name}")
                    # Branch exists, try with counter
                    if suffix:
                        suggested_name = f"{original_name}-{counter}"
                    else:
                        suggested_name = f"{original_name}-{counter}"
                    counter += 1

                    if counter > 99:  # Prevent infinite loop
                        raise GitWorktreeError("Too many branch name collisions")

                except GitCommandError:
                    # Branch doesn't exist, we can use this name
                    break

            return suggested_name

        except Exception as e:
            logger.error(f"Failed to suggest branch name: {e}")
            raise GitWorktreeError(f"Failed to suggest branch name: {e}") from e

    def cleanup_stale_branches(
        self,
        days_old: int = 30,
        dry_run: bool = True,
    ) -> dict[str, list[str]]:
        """Clean up stale branches that are no longer needed.

        Args:
            days_old: Age threshold in days for considering branches stale
            dry_run: If True, only identify branches without deleting

        Returns:
            Dictionary with cleanup results:
            - stale_branches: List of branches identified as stale
            - deleted: List of branches actually deleted (empty if dry_run=True)
            - protected: List of protected branches that won't be deleted
        """
        stale_branches = []
        deleted = []
        protected = ["main", "master", "develop", "dev"]

        try:
            cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)

            # Get all local branches
            for branch in self.repo.branches:
                if branch.name in protected:
                    continue

                # Check if branch has recent activity
                last_commit_time = branch.commit.committed_date

                if last_commit_time < cutoff_time:
                    # Check if branch is associated with any active worktrees
                    worktrees = self.list_worktrees()
                    is_active = any(wt.get("branch") == branch.name for wt in worktrees)

                    if not is_active:
                        stale_branches.append(branch.name)

                        if not dry_run:
                            try:
                                self.repo.git.branch("-D", branch.name)
                                deleted.append(branch.name)
                                logger.info(f"Deleted stale branch: {branch.name}")
                            except GitCommandError as e:
                                logger.warning(
                                    f"Could not delete branch {branch.name}: {e}"
                                )

            result = {
                "stale_branches": stale_branches,
                "deleted": deleted,
                "protected": protected,
            }

            logger.info(
                f"Branch cleanup: {len(stale_branches)} stale, {len(deleted)} deleted"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to cleanup branches: {e}")
            raise GitWorktreeError(f"Failed to cleanup branches: {e}") from e
