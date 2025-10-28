"""Worktree service that integrates git operations with database management."""

import os
from pathlib import Path
from typing import Any

from ..database.connection import get_db_session
from ..database.crud import WorktreeCRUD
from ..database.models import WorktreeStatus
from ..utils.logging import LogContext, get_logger
from .git_operations import GitWorktreeError, GitWorktreeManager

logger = get_logger(__name__, LogContext.WORKTREE)


class WorktreeServiceError(Exception):
    """Base exception for worktree service operations."""

    pass


class WorktreeService:
    """Service for managing git worktrees with database persistence."""

    def __init__(
        self, repo_path: str | None = None, base_worktree_dir: str | None = None
    ):
        """Initialize the WorktreeService.

        Args:
            repo_path: Path to the git repository. If None, uses current directory.
            base_worktree_dir: Base directory for creating worktrees.
                             If None, uses ../worktrees relative to repo.
        """
        self.git_manager = GitWorktreeManager(repo_path)

        if base_worktree_dir is None:
            repo_parent = Path(self.git_manager.repo_path).parent
            self.base_worktree_dir = str(repo_parent / "worktrees")
        else:
            self.base_worktree_dir = base_worktree_dir

        # Ensure base directory exists
        os.makedirs(self.base_worktree_dir, exist_ok=True)
        logger.info(
            f"Worktree service initialized with base directory: {self.base_worktree_dir}"
        )

    def list_worktrees(self, sync_with_git: bool = True) -> list[dict[str, Any]]:
        """List all worktrees from database, optionally syncing with git.

        Args:
            sync_with_git: Whether to sync database with actual git worktrees

        Returns:
            List of worktree information dictionaries
        """
        if sync_with_git:
            self.sync_worktrees()

        with get_db_session() as session:
            worktrees = WorktreeCRUD.list_all(session)

            result = []
            for worktree in worktrees:
                result.append(
                    {
                        "id": worktree.id,
                        "name": worktree.name,
                        "path": worktree.path,
                        "branch": worktree.branch_name,
                        "status": worktree.status.value,
                        "repository_url": worktree.repository_url,
                        "commit": worktree.current_commit,
                        "has_changes": worktree.has_uncommitted_changes,
                        "created_at": worktree.created_at,
                        "last_sync": worktree.last_sync,
                        "instance_id": worktree.instance_id,
                    }
                )

            logger.info(f"Listed {len(result)} worktrees from database")
            return result

    def create_worktree(
        self,
        name: str,
        branch: str,
        checkout_branch: str | None = None,
        custom_path: str | None = None,
        instance_id: int | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Create a new git worktree and register it in the database.

        Args:
            name: Name for the worktree
            branch: Name of the new branch to create
            checkout_branch: Existing branch to checkout from
            custom_path: Custom path for the worktree (overrides default)
            instance_id: Associate with an instance
            force: Force creation even if path exists

        Returns:
            Dictionary with created worktree information

        Raises:
            WorktreeServiceError: If creation fails
        """
        try:
            # Determine the worktree path
            if custom_path:
                worktree_path = os.path.abspath(custom_path)
            else:
                worktree_path = self.git_manager.generate_worktree_path(
                    self.base_worktree_dir, name
                )

            logger.info(f"Creating worktree '{name}' at {worktree_path}")

            # Create the git worktree
            git_info = self.git_manager.create_worktree(
                path=worktree_path,
                branch=branch,
                checkout_branch=checkout_branch,
                force=force,
            )

            # Store in database
            with get_db_session() as session:
                worktree = WorktreeCRUD.create(
                    session=session,
                    name=name,
                    path=worktree_path,
                    branch_name=branch,
                    repository_url=self._get_repository_url(),
                    instance_id=instance_id,
                    git_config={
                        "checkout_branch": checkout_branch,
                        "created_from": checkout_branch or "HEAD",
                    },
                )

                # Update with git information
                WorktreeCRUD.update_status(
                    session=session,
                    worktree_id=worktree.id,
                    status=WorktreeStatus.ACTIVE,
                    current_commit=git_info["commit"],
                    has_uncommitted_changes=False,
                )

                session.commit()

                result = {
                    "id": worktree.id,
                    "name": worktree.name,
                    "path": worktree.path,
                    "branch": worktree.branch_name,
                    "status": worktree.status.value,
                    "commit": git_info["commit"],
                    "instance_id": worktree.instance_id,
                }

                logger.info(f"Successfully created worktree: {result}")
                return result

        except GitWorktreeError as e:
            logger.error(f"Git worktree creation failed: {e}")
            raise WorktreeServiceError(f"Failed to create worktree: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error creating worktree: {e}")
            raise WorktreeServiceError(f"Unexpected error: {e}") from e

    def remove_worktree(self, path_or_id: str | int, force: bool = False) -> bool:
        """Remove a worktree and its database record.

        Args:
            path_or_id: Worktree name, path, or database ID
            force: Force removal even with uncommitted changes

        Returns:
            True if successfully removed

        Raises:
            WorktreeServiceError: If removal fails
        """
        try:
            with get_db_session() as session:
                # Get worktree record
                worktree = None
                if isinstance(path_or_id, int):
                    worktree = WorktreeCRUD.get_by_id(session, path_or_id)
                else:
                    # Try lookup by name first
                    worktree = WorktreeCRUD.get_by_name(session, path_or_id)

                    # If not found by name, try as absolute path
                    if worktree is None:
                        worktree_path = os.path.abspath(path_or_id)
                        worktree = WorktreeCRUD.get_by_path(session, worktree_path)

                if worktree is None:
                    raise WorktreeServiceError(f"Worktree '{path_or_id}' not found")

                # Use the path from database record
                worktree_path = worktree.path

                logger.info(f"Removing worktree '{worktree.name}' at {worktree_path}")

                # Remove from git
                git_removed = self.git_manager.remove_worktree(
                    worktree_path, force=force
                )

                if git_removed or force:
                    # Remove from database
                    WorktreeCRUD.delete(session, worktree.id)
                    session.commit()
                    logger.info(f"Successfully removed worktree '{worktree.name}'")
                    return True
                else:
                    logger.warning(f"Git worktree removal failed for {worktree_path}")
                    return False

        except GitWorktreeError as e:
            logger.error(f"Git worktree removal failed: {e}")
            raise WorktreeServiceError(f"Failed to remove worktree: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error removing worktree: {e}")
            raise WorktreeServiceError(f"Unexpected error: {e}") from e

    def cleanup_worktrees(self) -> dict[str, list[str]]:
        """Clean up stale worktree references and orphaned database records.

        Returns:
            Dictionary with cleanup results:
            - git_cleaned: List of git references cleaned up
            - db_cleaned: List of database records cleaned up
        """
        git_cleaned = []
        db_cleaned = []

        try:
            # Clean up git references
            git_cleaned = self.git_manager.cleanup_worktrees()

            # Clean up database records for non-existent paths
            with get_db_session() as session:
                all_worktrees = WorktreeCRUD.list_all(session)

                for worktree in all_worktrees:
                    if not os.path.exists(worktree.path):
                        logger.info(
                            f"Cleaning up database record for non-existent worktree: {worktree.path}"
                        )
                        WorktreeCRUD.delete(session, worktree.id)
                        db_cleaned.append(worktree.path)

                if db_cleaned:
                    session.commit()

            result = {"git_cleaned": git_cleaned, "db_cleaned": db_cleaned}

            logger.info(
                f"Cleanup completed: {len(git_cleaned)} git refs, {len(db_cleaned)} db records"
            )
            return result

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            raise WorktreeServiceError(f"Cleanup failed: {e}") from e

    def sync_worktrees(self) -> dict[str, int]:
        """Sync database worktrees with actual git worktrees.

        Returns:
            Dictionary with sync statistics:
            - updated: Number of worktrees updated with new status
            - added: Number of new worktrees found and added
            - marked_missing: Number of worktrees marked as missing
        """
        updated = 0
        added = 0
        marked_missing = 0

        try:
            # Get current git worktrees
            git_worktrees = self.git_manager.list_worktrees()
            git_paths = {wt.get("path") for wt in git_worktrees if wt.get("path")}

            with get_db_session() as session:
                # Get database worktrees
                db_worktrees = WorktreeCRUD.list_all(session)

                # Update existing worktrees with current status
                for worktree in db_worktrees:
                    if worktree.path in git_paths:
                        # Get detailed status
                        try:
                            status_info = self.git_manager.get_worktree_status(
                                worktree.path
                            )

                            # Determine status
                            if status_info["has_changes"]:
                                new_status = WorktreeStatus.DIRTY
                            else:
                                new_status = WorktreeStatus.ACTIVE

                            # Update if changed
                            if (
                                worktree.status != new_status
                                or worktree.current_commit != status_info["commit"]
                                or worktree.has_uncommitted_changes
                                != status_info["has_changes"]
                            ):
                                WorktreeCRUD.update_status(
                                    session=session,
                                    worktree_id=worktree.id,
                                    status=new_status,
                                    current_commit=status_info["commit"],
                                    has_uncommitted_changes=status_info["has_changes"],
                                )
                                updated += 1

                        except Exception as e:
                            logger.warning(
                                f"Could not get status for {worktree.path}: {e}"
                            )
                    else:
                        # Mark as missing/inactive
                        if worktree.status != WorktreeStatus.INACTIVE:
                            WorktreeCRUD.update_status(
                                session=session,
                                worktree_id=worktree.id,
                                status=WorktreeStatus.INACTIVE,
                            )
                            marked_missing += 1

                # TODO: Add logic to discover new worktrees not in database
                # This would require additional logic to determine names and metadata

                session.commit()

            result = {
                "updated": updated,
                "added": added,
                "marked_missing": marked_missing,
            }

            logger.info(
                f"Sync completed: {updated} updated, {added} added, {marked_missing} marked missing"
            )
            return result

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise WorktreeServiceError(f"Sync failed: {e}") from e

    def get_worktree_status(self, path_or_id: str | int) -> dict[str, Any]:
        """Get detailed status of a worktree.

        Args:
            path_or_id: Worktree name, path, or database ID

        Returns:
            Dictionary with detailed worktree status
        """
        try:
            with get_db_session() as session:
                # Get worktree record
                worktree = None
                if isinstance(path_or_id, int):
                    worktree = WorktreeCRUD.get_by_id(session, path_or_id)
                else:
                    # Try lookup by name first
                    worktree = WorktreeCRUD.get_by_name(session, path_or_id)

                    # If not found by name, try as absolute path
                    if worktree is None:
                        worktree_path = os.path.abspath(path_or_id)
                        worktree = WorktreeCRUD.get_by_path(session, worktree_path)

                if worktree is None:
                    raise WorktreeServiceError(f"Worktree '{path_or_id}' not found")

                # Get git status using the path from database record
                git_status = self.git_manager.get_worktree_status(worktree.path)

                # Combine database and git information
                result = {
                    "id": worktree.id,
                    "name": worktree.name,
                    "path": worktree.path,
                    "branch": worktree.branch_name,
                    "db_status": worktree.status.value,
                    "git_status": git_status,
                    "repository_url": worktree.repository_url,
                    "instance_id": worktree.instance_id,
                    "created_at": worktree.created_at,
                    "last_sync": worktree.last_sync,
                }

                return result

        except Exception as e:
            logger.error(f"Failed to get worktree status: {e}")
            raise WorktreeServiceError(f"Failed to get status: {e}") from e

    def _get_repository_url(self) -> str | None:
        """Get the repository URL from git config."""
        try:
            remotes = list(self.git_manager.repo.remotes)
            if remotes:
                return remotes[0].url
        except Exception as e:
            logger.debug(f"Could not get repository URL: {e}")
        return None
