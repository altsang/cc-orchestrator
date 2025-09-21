# Issue #66: Rewrite Unit Tests to Use Real Implementations Instead of Mocks

See: https://github.com/altsang/cc-orchestrator/issues/66

Focus: Eliminate testing anti-pattern where fully-implemented services are heavily mocked, preventing integration bugs from being caught.

## Current Status
- **Issue**: #66 - Rewrite unit tests to use real implementations instead of mocks
- **Status**: 🚧 IN PROGRESS
- **Branch**: feature/issue-66-testing-refactor
- **Worktree**: ~/workspace/cc-orchestrator-issue-66
- **Tmux Session**: cc-orchestrator-issue-66
- **Priority**: High (Critical testing debt)
- **Labels**: bug, priority-high

## Problem Statement

The current unit test suite extensively uses mocks for **fully-implemented services**, creating a testing gap that allowed Issue #65 (worktree path resolution bug) to slip through.

### Why Issue #65 Wasn't Caught

`WorktreeService.get_worktree_status()` uses `os.path.abspath(path_or_id)` which resolves paths relative to CWD. This bug was not caught because:

1. CLI tests completely mock `WorktreeService`
2. Service tests mock `GitWorktreeManager` and database sessions
3. The real path resolution logic is **never executed** in any test

## Mock Usage Statistics

- `test_cli_instances_coverage.py`: **124 mocks**
- `test_tmux_service_coverage.py`: **86 mocks**
- `test_cli_worktrees.py`: **56 mocks**
- **Total**: ~400+ mocks across 10 test files

## Development Plan

### Phase 1: Infrastructure Setup ✅ COMPLETED
1. ✅ Create `tests/integration/` directory (already exists)
2. ✅ Create shared fixtures (git repo, test db, CLI runner)
3. ⏭️ Set up CI for integration tests (deferred)

### Phase 2: Critical Path Tests 🚧 IN PROGRESS
1. ✅ Worktree CLI integration tests (would catch #65) - **COMPLETED**
   - Created `tests/integration/test_cli_worktrees_integration.py`
   - 6 integration tests using real git operations and database
   - **Key test**: `test_worktree_status_with_real_path_resolution` - Would have caught Issue #65
   - All tests pass without mocks
2. ⏭️ Instance CLI integration tests
3. ⏭️ Tmux CLI integration tests

### Phase 3: Service Layer Tests
1. WorktreeService with real git/db
2. TmuxService with real tmux
3. Orchestrator tests

### Phase 4: End-to-End Tests
1. Complete workflow tests
2. Cross-component integration

### Phase 5: Cleanup
1. Remove redundant mocked tests
2. Document testing strategy

## Key Files Created/Updated

- ✅ `tests/integration/test_cli_worktrees_integration.py` - **NEW**
  - Real git repository fixtures
  - Database cleanup fixtures
  - 6 comprehensive integration tests
  - Tests actual path resolution (Issue #65 scenario)
- ⏭️ `tests/integration/conftest.py` (shared fixtures - to be created)
- ⏭️ `tests/integration/test_cli_instances_integration.py`
- ⏭️ `tests/integration/test_workflows.py`
- ⏭️ `TESTING.md` (strategy documentation)

## Progress Summary

### Completed Work
1. **Analyzed the problem**:
   - Identified that `test_cli_worktrees.py` has 56 mocks
   - Found that Issue #65 (path resolution bug) was not caught because all tests mock WorktreeService
   - The bug: `os.path.abspath(path_or_id)` resolves relative to CWD, not actual worktree path

2. **Created Integration Tests**:
   - `test_cli_worktrees_integration.py` with 6 comprehensive tests
   - Uses real GitWorktreeManager (no mocks)
   - Uses real database sessions
   - Uses real filesystem operations
   - **Critical test added**: `test_worktree_status_with_real_path_resolution`
     - Changes CWD and verifies status works regardless
     - This test would have caught Issue #65

3. **Test Results**:
   - ✅ All 6 integration tests pass
   - ✅ Tests verify real git operations
   - ✅ Tests verify database persistence
   - ✅ Tests verify path resolution across different CWDs

### Next Steps
1. Create similar integration tests for Instance CLI commands
2. Create integration tests for Tmux CLI commands
3. Consider creating shared fixtures in `tests/integration/conftest.py`
4. Document the new testing strategy
5. Gradually reduce reliance on mocked unit tests
