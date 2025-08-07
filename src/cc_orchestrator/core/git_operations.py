"""Git operations for worktree management."""

import os
import shutil
from pathlib import Path
from typing import Any

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from ..utils.logging import LogContext, get_logger

logger = get_logger(__name__, LogContext.WORKTREE)


class GitWorktreeError(Exception):
    """Base exception for git worktree operations."""

    pass


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
            current_worktree: dict[str, str] = {}

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

    def get_worktree_status(self, path: str) -> dict[str, Any]:
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
