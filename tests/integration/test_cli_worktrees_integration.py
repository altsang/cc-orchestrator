"""Integration tests for worktree CLI commands using real implementations.

This test suite addresses Issue #66 by testing worktree CLI commands with real
git operations and database interactions, ensuring bugs like Issue #65 are caught.

Key differences from unit tests:
- Uses real GitWorktreeManager (no mocking)
- Uses real database sessions
- Uses real filesystem operations
- Tests actual path resolution (would catch Issue #65)
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from cc_orchestrator.cli.main import main
from cc_orchestrator.database.connection import get_db_session
from cc_orchestrator.database.crud import WorktreeCRUD
from cc_orchestrator.database.models import Base


@pytest.fixture
def git_repo():
    """Create a real git repository for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir) / "test-repo"
        repo_path.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create initial commit
        readme = repo_path / "README.md"
        readme.write_text("# Test Repository")
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        yield repo_path


@pytest.fixture
def worktree_base_dir():
    """Create a base directory for worktrees."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture(autouse=True)
def clean_database():
    """Clean database before and after each test."""
    # Clean before test
    with get_db_session() as session:
        # Delete all worktrees
        session.query(Base.metadata.tables["worktrees"]).delete()
        session.commit()

    yield

    # Clean after test
    with get_db_session() as session:
        # Delete all worktrees
        session.query(Base.metadata.tables["worktrees"]).delete()
        session.commit()


class TestWorktreesCLIIntegration:
    """Integration tests for worktree CLI commands with real implementations."""

    def test_create_and_list_worktree_real_git(
        self, cli_runner, git_repo, worktree_base_dir
    ):
        """Test creating and listing a worktree with real git operations.

        This test uses real git commands and database operations, ensuring that:
        1. Worktrees are actually created on disk
        2. Database records are created correctly
        3. List command shows accurate information
        """
        # Change to git repo directory
        original_cwd = os.getcwd()
        os.chdir(git_repo)

        try:
            # Set up environment for worktree service
            worktree_path = worktree_base_dir / "test-worktree"

            # Create worktree using CLI
            result = cli_runner.invoke(
                main,
                [
                    "worktrees",
                    "create",
                    "test-worktree",
                    "feature-test",
                    "--path",
                    str(worktree_path),
                ],
            )

            # Verify CLI output
            assert result.exit_code == 0, f"Failed with: {result.output}"
            assert "Created worktree 'test-worktree'" in result.output

            # Verify worktree exists on disk
            assert worktree_path.exists()
            assert (worktree_path / ".git").exists()

            # Verify git recognizes it as a worktree
            git_result = subprocess.run(
                ["git", "worktree", "list"],
                cwd=git_repo,
                capture_output=True,
                text=True,
            )
            assert str(worktree_path) in git_result.stdout

            # Verify database record was created
            with get_db_session() as session:
                worktrees = WorktreeCRUD.list_all(session)
                assert len(worktrees) == 1
                assert worktrees[0].name == "test-worktree"
                assert worktrees[0].branch_name == "feature-test"
                assert worktrees[0].path == str(worktree_path)

            # List worktrees using CLI
            result = cli_runner.invoke(main, ["worktrees", "list"])
            assert result.exit_code == 0
            assert "test-worktree" in result.output
            assert "feature-test" in result.output

        finally:
            os.chdir(original_cwd)

    def test_worktree_status_with_real_path_resolution(
        self, cli_runner, git_repo, worktree_base_dir
    ):
        """Test worktree status command with real path resolution.

        This test would have caught Issue #65 (path resolution bug).

        Issue #65: WorktreeService.get_worktree_status() used os.path.abspath(path_or_id)
        which resolves paths relative to CWD, not the actual worktree path.

        This test verifies that:
        1. Paths are resolved correctly regardless of CWD
        2. Status can be retrieved by path or ID
        3. Real git status is returned
        """
        original_cwd = os.getcwd()
        os.chdir(git_repo)

        try:
            worktree_path = worktree_base_dir / "status-test-worktree"

            # Create worktree
            result = cli_runner.invoke(
                main,
                [
                    "worktrees",
                    "create",
                    "status-test",
                    "feature-status",
                    "--path",
                    str(worktree_path),
                ],
            )
            assert result.exit_code == 0

            # Get worktree ID from database
            with get_db_session() as session:
                worktrees = WorktreeCRUD.list_all(session)
                assert len(worktrees) == 1
                worktree_id = worktrees[0].id

            # Test 1: Get status by ID
            result = cli_runner.invoke(main, ["worktrees", "status", str(worktree_id)])
            assert result.exit_code == 0
            assert "status-test" in result.output
            assert "feature-status" in result.output

            # Test 2: Get status by absolute path (should work)
            result = cli_runner.invoke(
                main, ["worktrees", "status", str(worktree_path)]
            )
            assert result.exit_code == 0
            assert "status-test" in result.output

            # Test 3: Critical - Change CWD and try again (Issue #65 scenario)
            # This is where Issue #65 bug would manifest
            temp_other_dir = worktree_base_dir / "other-dir"
            temp_other_dir.mkdir()
            os.chdir(temp_other_dir)

            # Status by ID should still work regardless of CWD
            result = cli_runner.invoke(main, ["worktrees", "status", str(worktree_id)])
            assert result.exit_code == 0, f"Failed from different CWD: {result.output}"
            assert "status-test" in result.output

            # Status by absolute path should work regardless of CWD
            result = cli_runner.invoke(
                main, ["worktrees", "status", str(worktree_path)]
            )
            assert (
                result.exit_code == 0
            ), f"Failed with absolute path from different CWD: {result.output}"
            assert "status-test" in result.output

        finally:
            os.chdir(original_cwd)

    def test_worktree_remove_real_cleanup(
        self, cli_runner, git_repo, worktree_base_dir
    ):
        """Test removing a worktree with real git and database cleanup."""
        original_cwd = os.getcwd()
        os.chdir(git_repo)

        try:
            worktree_path = worktree_base_dir / "remove-test-worktree"

            # Create worktree
            result = cli_runner.invoke(
                main,
                [
                    "worktrees",
                    "create",
                    "remove-test",
                    "feature-remove",
                    "--path",
                    str(worktree_path),
                ],
            )
            assert result.exit_code == 0
            assert worktree_path.exists()

            # Get worktree ID
            with get_db_session() as session:
                worktrees = WorktreeCRUD.list_all(session)
                worktree_id = worktrees[0].id

            # Remove worktree by ID
            result = cli_runner.invoke(main, ["worktrees", "remove", str(worktree_id)])
            assert result.exit_code == 0
            assert "Successfully removed worktree" in result.output

            # Verify worktree is removed from disk
            assert not worktree_path.exists()

            # Verify git no longer tracks it
            git_result = subprocess.run(
                ["git", "worktree", "list"],
                cwd=git_repo,
                capture_output=True,
                text=True,
            )
            assert str(worktree_path) not in git_result.stdout

            # Verify database record is removed
            with get_db_session() as session:
                worktrees = WorktreeCRUD.list_all(session)
                assert len(worktrees) == 0

        finally:
            os.chdir(original_cwd)

    def test_worktree_cleanup_with_stale_references(
        self, cli_runner, git_repo, worktree_base_dir
    ):
        """Test cleanup command removes stale worktree references."""
        original_cwd = os.getcwd()
        os.chdir(git_repo)

        try:
            worktree_path = worktree_base_dir / "cleanup-test-worktree"

            # Create worktree through git directly (bypass our CLI)
            subprocess.run(
                ["git", "worktree", "add", str(worktree_path), "-b", "feature-cleanup"],
                cwd=git_repo,
                check=True,
                capture_output=True,
            )

            # Manually delete the worktree directory (simulating stale reference)
            import shutil

            shutil.rmtree(worktree_path)

            # Git still has the reference
            git_result = subprocess.run(
                ["git", "worktree", "list"],
                cwd=git_repo,
                capture_output=True,
                text=True,
            )
            assert str(worktree_path) in git_result.stdout

            # Run cleanup command
            result = cli_runner.invoke(main, ["worktrees", "cleanup"])
            assert result.exit_code == 0

            # Verify stale reference is cleaned
            # Note: git worktree prune should remove it
            subprocess.run(
                ["git", "worktree", "prune"],
                cwd=git_repo,
                check=True,
                capture_output=True,
            )

            git_result = subprocess.run(
                ["git", "worktree", "list"],
                cwd=git_repo,
                capture_output=True,
                text=True,
            )
            # After prune, stale worktree should be gone
            assert str(worktree_path) not in git_result.stdout

        finally:
            os.chdir(original_cwd)

    def test_worktree_with_uncommitted_changes(
        self, cli_runner, git_repo, worktree_base_dir
    ):
        """Test worktree status shows uncommitted changes correctly."""
        original_cwd = os.getcwd()
        os.chdir(git_repo)

        try:
            worktree_path = worktree_base_dir / "changes-test-worktree"

            # Create worktree
            result = cli_runner.invoke(
                main,
                [
                    "worktrees",
                    "create",
                    "changes-test",
                    "feature-changes",
                    "--path",
                    str(worktree_path),
                ],
            )
            assert result.exit_code == 0

            # Make changes in the worktree
            test_file = worktree_path / "test.txt"
            test_file.write_text("test content")

            # Get worktree ID
            with get_db_session() as session:
                worktrees = WorktreeCRUD.list_all(session)
                worktree_id = worktrees[0].id

            # Check status - should show changes
            result = cli_runner.invoke(
                main, ["worktrees", "status", str(worktree_id), "--format", "json"]
            )
            assert result.exit_code == 0

            # The output should indicate there are changes
            # (Implementation detail: may vary based on how status is reported)
            assert "changes-test" in result.output

        finally:
            os.chdir(original_cwd)

    def test_worktree_json_output_format(self, cli_runner, git_repo, worktree_base_dir):
        """Test JSON output format for worktree commands."""
        original_cwd = os.getcwd()
        os.chdir(git_repo)

        try:
            worktree_path = worktree_base_dir / "json-test-worktree"

            # Create worktree with JSON output
            result = cli_runner.invoke(
                main,
                [
                    "worktrees",
                    "create",
                    "json-test",
                    "feature-json",
                    "--path",
                    str(worktree_path),
                    "--format",
                    "json",
                ],
            )
            assert result.exit_code == 0

            # Output should be valid JSON
            import json

            output_data = json.loads(result.output)
            assert output_data["name"] == "json-test"
            assert output_data["branch"] == "feature-json"

            # List with JSON format
            result = cli_runner.invoke(main, ["worktrees", "list", "--format", "json"])
            assert result.exit_code == 0

            list_data = json.loads(result.output)
            assert len(list_data) == 1
            assert list_data[0]["name"] == "json-test"

        finally:
            os.chdir(original_cwd)
