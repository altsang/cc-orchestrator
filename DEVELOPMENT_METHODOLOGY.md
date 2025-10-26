# CC-Orchestrator Development Methodology

## Production-Ready Development Standards

This document establishes the mandatory development methodology to ensure all components are production-ready before merge.

---

## 🎯 **Core Principles**

### 1. **Zero Integration Debt Policy**
- **No features exist in isolation** - every feature must be integrated end-to-end before merge
- **No technical debt** - components must meet production standards before PR approval
- **No placeholder implementations** - all TODOs in critical paths must be completed
- Technical debt is addressed immediately, not deferred

### 2. **Integration-First Development**
- **User journey drives development** - start with complete user workflow, not individual components
- **End-to-end testing mandatory** - features must work across all system boundaries
- **State persistence verified** - data must survive process restarts and separate invocations
- **Cross-component integration proven** - CLI/Web/Database layers must be connected

### 3. **Quality Gates**
Every component must pass ALL quality gates:
- ✅ **Type Safety**: mypy passes with zero errors
- ✅ **Code Quality**: ruff/black formatting and linting clean
- ✅ **Test Coverage**: Minimum 90% coverage for new code
- ✅ **Integration Testing**: Full user workflows tested end-to-end
- ✅ **State Persistence**: Data survives across separate process invocations
- ✅ **Functionality**: All tests pass, manual verification complete
- ✅ **Documentation**: Code is self-documenting with proper docstrings

### 4. **Defense in Depth**
Multiple layers of quality assurance:
- Pre-commit hooks (automated)
- Integration testing (mandatory)
- End-to-end workflow validation
- Cross-process state verification
- Manual code review
- CI/CD pipeline validation

---

## 📋 **Development Workflow**

### Phase 0: Repository Sync (MANDATORY)

**CRITICAL**: Always sync with actual repository state before providing status or making decisions. Other worker threads may have completed work that changes the current context.

#### Status Check Sequence (MANDATORY for all status requests)

```bash
# 1. Sync with remote repository
git fetch origin
git status

# 2. Check PROJECT PHASE from PROJECT_PLAN.md to understand current work context
grep -A 5 "Phase.*COMPLETE\|Phase.*IN PROGRESS" planning/PROJECT_PLAN.md

# 3. Check actual completed issues (not documentation)
gh issue list --state closed --limit 20
gh pr list --state merged --limit 10

# 4. Get CURRENT PHASE issues only (critical for accurate status)
gh issue list --label "phase-2" --state open  # Replace phase-2 with current phase

# 5. Run current test suite to verify system state
python -m pytest --tb=short

# 6. Check current git log for recent completions
git log --oneline -10

# 7. Verify project board reflects actual status
gh project item-list 1 --owner altsang --format json | jq '.items[] | select(.content.state == "CLOSED") | {number: .content.number, title: .content.title}'
```

#### When to Use This Protocol
- **ALWAYS** when user asks "what's the status?"
- **ALWAYS** before planning next work
- **ALWAYS** before setting up new worker environments
- **ALWAYS** when resuming work after time gap
- **ALWAYS** when multiple workers are active

#### Why This Protocol is Critical
- **Parallel Development**: Multiple workers complete issues simultaneously
- **Context Accuracy**: Documentation may lag behind actual progress
- **Decision Making**: Work assignments depend on actual completion status
- **Resource Efficiency**: Avoid duplicate work on completed issues
- **Phase Awareness**: Must filter issues by current project phase, not just priority

#### Critical Phase Awareness Requirements
- **ALWAYS** check current phase from PROJECT_PLAN.md before listing "next issues"
- **NEVER** list issues from future phases when asked "what's next to work on"
- **FILTER** issue lists by current phase label (e.g., `--label "phase-2"`)
- **UNDERSTAND** that high-priority issues from Phase 5/6 are NOT current work if we're in Phase 2
- **ERROR EXAMPLE**: Listing Phase 5 resource management issues when asked "what's next" during Phase 2

**NEVER** rely solely on documentation for current status - always verify with actual repository state first.

### Phase 1: Integration-First Planning & Design

```markdown
## Before Writing Code - Integration-First Approach:
1. [ ] **Define complete user journey** - map full workflow from user action to final outcome
2. [ ] **Identify all integration points** - list every component, layer, and boundary the feature touches
3. [ ] **Plan integration skeleton** - design minimal end-to-end flow that connects all components
4. [ ] **Define acceptance criteria clearly** - focus on user outcomes, not individual component behavior
5. [ ] **Plan cross-process state verification** - how will data persist across separate CLI invocations?
6. [ ] **Design integration testing strategy** - plan tests that verify complete user workflows
7. [ ] **Plan type-safe interfaces and data structures** - ensure data flows correctly across boundaries
8. [ ] **Design error handling and edge cases** - consider failures across the entire integrated system
9. [ ] **Consider backwards compatibility and migration needs** - impact on existing integrations
```

**Example: Issue #14 Integration-First Planning**
```markdown
User Journey: "Create instance → List instances → Stop instance → Verify stopped"
Integration Points: CLI → Orchestrator → Database → Process Manager
Integration Skeleton:
  1. CLI commands connect to Orchestrator with database session
  2. Orchestrator persists instances to database (not memory)
  3. Process operations update database state
  4. Separate CLI invocations read from same database
Integration Test: Full workflow script that verifies state persistence
```

### Phase 2: Integration-First Implementation

#### **Integration Skeleton First**
**MANDATORY**: Build minimal end-to-end integration before implementing functionality.

```python
# ✅ REQUIRED: Integration skeleton connects all components
class Orchestrator:
    def __init__(self, db_session: Session | None = None):
        """Always integrate with database from day one."""
        self.db_session = db_session or get_db_session()
        self.db = InstanceCRUD(self.db_session)
        self.instances: dict[str, ClaudeInstance] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Real initialization - no TODOs in critical paths."""
        # ✅ IMPLEMENTED: Database connection established
        self.db.initialize_schema()
        # ✅ IMPLEMENTED: Load existing instances from database
        stored_instances = self.db.list_all()
        for instance_data in stored_instances:
            instance = ClaudeInstance.from_db_data(instance_data)
            self.instances[instance.issue_id] = instance
        self._initialized = True

    async def create_instance(self, issue_id: str, **kwargs) -> ClaudeInstance:
        """Integration-first: immediately persist to database."""
        instance = ClaudeInstance(issue_id=issue_id, **kwargs)
        await instance.initialize()

        # ✅ CRITICAL: Persist to database immediately
        db_instance = self.db.create(issue_id=issue_id, **kwargs)
        instance.db_id = db_instance.id

        self.instances[issue_id] = instance
        return instance
```

#### **Type Safety With Integration**
```python
# ✅ REQUIRED: Proper type annotations
def load_config(
    config_path: str | None = None,
    profile: str | None = None,
    cli_overrides: dict[str, Any] | None = None
) -> OrchestratorConfig:
    """Load configuration with proper type safety."""

# ✅ REQUIRED: Handle Union types safely
if hasattr(field_type, "__origin__") and getattr(field_type, "__origin__", None) is Union:
    # Safe Union type handling
```

#### **Error Handling Standards**
```python
# ✅ REQUIRED: Comprehensive error handling
try:
    result = risky_operation()
    return result
except SpecificError as e:
    logger.error(f"Operation failed: {e}", extra={"context": context})
    raise ConfigurationError(f"Failed to process: {e}") from e
except Exception as e:
    logger.critical(f"Unexpected error: {e}")
    raise
```

#### **Logging Standards**
```python
# ✅ REQUIRED: Structured logging with context
logger.info(
    "Configuration loaded successfully",
    config_path=config_path,
    profile=profile,
    has_overrides=bool(cli_overrides)
)
```

### Phase 3: Integration-First Testing Requirements

#### **Mandatory Integration Testing**
**CRITICAL**: Every feature must include integration tests that verify complete user workflows.

```python
class TestInstanceManagementIntegration:
    """✅ REQUIRED: Integration tests verify end-to-end workflows."""

    @pytest.fixture
    def orchestrator_with_db(self):
        """Real database session for integration testing."""
        db_session = create_test_db_session()
        orchestrator = Orchestrator(db_session)
        yield orchestrator
        db_session.close()

    async def test_complete_instance_lifecycle_integration(self, orchestrator_with_db):
        """✅ CRITICAL: Test full user workflow - create → list → stop → verify"""
        orchestrator = orchestrator_with_db
        await orchestrator.initialize()

        # Step 1: Create instance (like CLI: cc-orchestrator instances start issue-123)
        instance = await orchestrator.create_instance("issue-123")
        assert instance.issue_id == "issue-123"

        # Step 2: Verify persistence - simulate separate CLI invocation
        fresh_orchestrator = Orchestrator(orchestrator.db_session)
        await fresh_orchestrator.initialize()
        instances = fresh_orchestrator.list_instances()
        assert len(instances) == 1
        assert instances[0].issue_id == "issue-123"

        # Step 3: Stop instance (like CLI: cc-orchestrator instances stop issue-123)
        success = await fresh_orchestrator.destroy_instance("issue-123")
        assert success is True

        # Step 4: Verify stopped - simulate another separate CLI invocation
        final_orchestrator = Orchestrator(orchestrator.db_session)
        await final_orchestrator.initialize()
        final_instances = final_orchestrator.list_instances()
        assert len(final_instances) == 0

    async def test_cross_process_state_persistence(self, orchestrator_with_db):
        """✅ CRITICAL: Verify state survives process boundaries"""
        # Simulate first CLI command creating instance
        orchestrator1 = orchestrator_with_db
        await orchestrator1.initialize()
        await orchestrator1.create_instance("test-persistence")

        # Simulate second CLI command (different process) reading instances
        orchestrator2 = Orchestrator(orchestrator1.db_session)
        await orchestrator2.initialize()
        instances = orchestrator2.list_instances()

        assert len(instances) == 1
        assert instances[0].issue_id == "test-persistence"

    async def test_cli_to_web_api_integration(self, orchestrator_with_db):
        """✅ REQUIRED: Test CLI creates instance, Web API can access it"""
        # Create via CLI layer
        orchestrator = orchestrator_with_db
        await orchestrator.initialize()
        cli_instance = await orchestrator.create_instance("cli-web-test")

        # Access via Web API layer
        from cc_orchestrator.database.crud import InstanceCRUD
        db_instances = InstanceCRUD.list_all(orchestrator.db_session)
        assert len(db_instances) == 1
        assert db_instances[0].issue_id == "cli-web-test"
```

#### **Mandatory Unit Test Coverage**
```python
class TestConfigurationSystem:
    """✅ REQUIRED: Comprehensive test coverage."""

    def test_happy_path(self):
        """Test normal operation."""
        # ✅ REQUIRED: Full implementation, no placeholder passes
        config = ConfigLoader.load_default()
        assert config.max_instances == 5
        assert config.tmux_enabled is True
        assert config.web_port == 8080

    def test_edge_cases(self):
        """Test boundary conditions."""
        # ✅ REQUIRED: Full implementation, no placeholder passes
        config = ConfigLoader.load_with_overrides({"max_instances": 0})
        with pytest.raises(ValidationError):
            config.validate()

    def test_error_conditions(self):
        """Test error handling."""
        # ✅ REQUIRED: Full implementation, no placeholder passes
        with pytest.raises(FileNotFoundError):
            ConfigLoader.load_from_file("/nonexistent/path")

    def test_integration(self):
        """Test component integration."""
        # ✅ REQUIRED: Full implementation, no placeholder passes
        config = ConfigLoader.load_default()
        orchestrator = Orchestrator(config)
        assert orchestrator.max_instances == config.max_instances
```

#### **Test Quality Standards**
- **Unit Tests**: 95%+ coverage for new code
- **Integration Tests**: Cover all component interactions
- **Error Path Testing**: Test all error conditions and recovery
- **Edge Case Testing**: Boundary values, null inputs, malformed data
- **Performance Testing**: Verify acceptable response times

#### **❌ FORBIDDEN: Placeholder Tests**
```python
# ❌ NEVER ACCEPTABLE: Empty placeholder tests
def test_feature_works(self):
    pass

def test_error_handling(self):
    # TODO: implement later
    pass

# ❌ NEVER ACCEPTABLE: Minimal placeholders
def test_configuration_loading(self):
    assert True  # placeholder

# ✅ REQUIRED: Full implementation with real assertions
def test_configuration_loading(self):
    config = load_config("test_config.yaml")
    assert config.database_url == "sqlite:///test.db"
    assert config.max_connections == 10
    assert len(config.endpoints) == 3
```

#### **Test Implementation Requirements**
- **No Empty Tests**: Every test method must contain real implementation
- **Real Assertions**: Tests must verify actual behavior, not just existence
- **Complete Coverage**: All code paths must be tested with meaningful scenarios
- **Error Testing**: Exception paths must be tested with specific exception types
- **Data Validation**: Test with realistic data, edge cases, and invalid inputs

#### **Issue Work Testing Policy**
**MANDATORY for all GitHub issue implementations:**

✅ **REQUIRED**: All tests must be fully implemented with real assertions
✅ **REQUIRED**: Tests must cover happy path, edge cases, and error conditions
✅ **REQUIRED**: No placeholder tests (`pass`, `assert True`, `# TODO`)
✅ **REQUIRED**: All acceptance criteria must have corresponding tests
✅ **REQUIRED**: Test coverage must meet 90% minimum before PR creation

❌ **REJECTED**: PRs with placeholder or unimplemented tests
❌ **REJECTED**: Tests that only verify code exists without testing behavior
❌ **REJECTED**: Missing tests for any acceptance criteria

### Phase 4: Pre-Commit Validation

#### **Automated Quality Checks**
```yaml
# .pre-commit-config.yaml - MANDATORY
repos:
  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: mypy
        language: system
        types: [python]
        require_serial: true
        fail_fast: true

      - id: ruff
        name: ruff
        entry: ruff check --fix
        language: system
        types: [python]

      - id: black
        name: black
        entry: black
        language: system
        types: [python]

      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

---

## 🔧 **Quality Gates Checklist**

### **Before Every Commit:**
```markdown
- [ ] `mypy src/` passes with zero errors
- [ ] `ruff check .` passes with zero issues
- [ ] `black .` formatting applied
- [ ] `pytest` all tests pass with ≥90% coverage
- [ ] Manual functionality verification complete
- [ ] Error handling tested for failure scenarios
- [ ] Performance acceptable (if applicable)
- [ ] Documentation updated (docstrings, README)
```

### **Before Every PR - Integration-First Requirements:**
```markdown
## Integration Verification (MANDATORY)
- [ ] **Complete user workflow tested** - full end-to-end journey from user action to outcome
- [ ] **Cross-process state persistence verified** - data survives separate CLI/API invocations
- [ ] **Integration tests included** - tests verify component connections, not just individual units
- [ ] **No TODOs in critical integration paths** - database connections, state management fully implemented
- [ ] **All layers connected** - CLI → Core → Database → Process management working together

## Quality Gates
- [ ] All automated quality gates passed
- [ ] Integration tests with existing components pass
- [ ] Unit test coverage ≥90% for new code
- [ ] Manual end-to-end workflow verification completed
- [ ] Cross-component data flow tested

## System Integration
- [ ] Backwards compatibility maintained across all interfaces
- [ ] Migration path documented (if breaking changes to integrations)
- [ ] Security implications reviewed for all integration points
- [ ] Performance impact assessed across integrated system
- [ ] Monitoring/logging instrumentation added to integration boundaries

## Review Requirements
- [ ] **Integration demo required** - PR author demonstrates complete user workflow to reviewer
- [ ] **State persistence demo** - show data surviving separate process invocations
- [ ] **Component boundary review** - verify all integration points are properly connected
```

---

## 📊 **Code Quality Standards**

### **Type Safety Requirements**
```python
# ✅ MANDATORY: Explicit return types
def process_data(input_data: dict[str, Any]) -> ProcessResult:
    """Always specify return types."""

# ✅ MANDATORY: Handle Optional/Union types properly
def safe_get_value(data: dict[str, Any], key: str) -> str | None:
    """Use Union types for nullable returns."""
    return data.get(key)

# ✅ MANDATORY: Generic type parameters
def create_handler[T](handler_type: type[T]) -> T:
    """Use proper generic typing."""
```

### **Error Handling Requirements**
```python
# ✅ MANDATORY: Custom exception types
class ConfigurationError(Exception):
    """Specific error types for different failure modes."""
    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context or {}

# ✅ MANDATORY: Graceful degradation
def load_optional_config() -> Config:
    """Always provide fallback behavior."""
    try:
        return load_user_config()
    except ConfigNotFoundError:
        logger.info("User config not found, using defaults")
        return get_default_config()
```

### **Performance Standards**
- **Response Times**: API calls <100ms, CLI commands <500ms
- **Memory Usage**: Efficient data structures, avoid memory leaks
- **Resource Cleanup**: Proper context managers and cleanup
- **Scalability**: Design for growth, avoid O(n²) algorithms

---

## 🚀 **CI/CD Pipeline Standards**

### **Automated Pipeline Requirements**
```yaml
# Required CI checks
stages:
  - lint_and_type_check:
      - mypy --strict src/
      - ruff check . --no-fix
      - black --check .

  - test:
      - pytest --cov=src --cov-min=90
      - pytest --integration
      - pytest --performance

  - security:
      - bandit -r src/
      - safety check
      - semgrep --config=auto

  - build_and_deploy:
      - docker build --no-cache
      - integration tests against built image
      - staging deployment validation
```

### **Deployment Readiness**
- **Health Checks**: Proper readiness/liveness endpoints
- **Graceful Shutdown**: Handle SIGTERM properly
- **Configuration Validation**: Validate config on startup
- **Monitoring Integration**: Metrics, logging, tracing
- **Security Hardening**: No secrets in code, proper auth

---

## 🖥️ **Manual Development Methodology (Tmux Multi-Session)**

### **Tmux Session Management for Parallel Development**

The manual development methodology uses tmux sessions to enable parallel development across multiple issues with complete isolation.

#### **Session Architecture**
- **Control Tower**: Main coordination session (typically where you start)
- **Worker Sessions**: Issue-specific development sessions (Worker 1, Worker 2, etc.)
- **Issue Sessions**: Auto-created sessions for each GitHub issue

#### **Session Switching Protocol**

**When already in a tmux session** (Worker 1, Worker 2):
```bash
# ✅ CORRECT: Switch client to target session (no nesting)
tmux switch-client -t "cc-orchestrator-issue-15"

# ❌ INCORRECT: Cannot nest tmux sessions
tmux attach-session -t "cc-orchestrator-issue-15"  # Will fail with nesting error
```

**When outside tmux** (fresh terminal):
```bash
# ✅ CORRECT: Attach to target session
tmux attach-session -t "cc-orchestrator-issue-15"
```

#### **Alternative Session Management**
```bash
# Option 1: Detach and reattach
tmux detach-client
tmux attach-session -t "cc-orchestrator-issue-15"

# Option 2: List and switch
tmux list-sessions  # See available sessions
tmux switch-client -t "target-session"
```

### **Claude Code Launch Options for Maximum Velocity**

#### **Available Launch Modes**
```bash
# 1. Plan Mode (default) - Asks permission for each action
claude

# 2. No Plan Mode - Executes immediately with full visibility
claude --no-plan-mode

# 3. Maximum Speed Mode - Executes with minimal prompting
claude --dangerously-skip-permissions
```

#### **Mode Selection Guidelines**
- **Plan Mode**: Complex architectural changes, unfamiliar codebases
- **No Plan Mode**: Regular development with oversight
- **Skip Permissions**: Routine tasks, maximum development velocity

### **Worker Environment Setup Protocol**

**Control Tower Preparation Steps:**
```bash
# 1. Create isolated git worktree
git worktree add -b feature/issue-<NUMBER>-<description> ../cc-orchestrator-issue-<NUMBER>

# 2. Create dedicated tmux session
tmux new-session -d -s "cc-orchestrator-issue-<NUMBER>" -c "/Users/altsang/workspace/cc-orchestrator-issue-<NUMBER>"

# 3. Update GitHub project board status
gh project item-edit --id <ITEM_ID> --field-id <STATUS_FIELD> --single-select-option-id <IN_PROGRESS_ID>

# 4. Assign GitHub issue
gh issue edit <NUMBER> --assignee @me
```

**Worker Activation Commands:**
```bash
# From existing tmux session (Worker 1, Worker 2)
tmux switch-client -t "cc-orchestrator-issue-<NUMBER>"
claude --dangerously-skip-permissions

# From fresh terminal
tmux attach-session -t "cc-orchestrator-issue-<NUMBER>"
claude --dangerously-skip-permissions
```

### **Issue Completion Cleanup Protocol**

**MANDATORY**: Clean up all development artifacts and scaffolding when issue work is complete. ALL 5 cleanup actions must be performed.

#### **Environment Cleanup Steps (ALL REQUIRED):**
```bash
# 1. CLOSE GITHUB ISSUE (if not already closed)
# Verify issue and PR status first
gh issue view <NUMBER>
gh pr view <PR_NUMBER>

# Close issue if not automatically closed by PR merge
gh issue close <NUMBER> --comment "Resolved by PR #<PR_NUMBER>. [Brief description of what was implemented]"

# 2. UPDATE PROJECT BOARD STATUS TO "DONE"
# Get project item ID
gh project item-list 1 --owner <OWNER> --format json | jq -r '.items[] | select(.content.number == <NUMBER>) | .id'

# Update status to Done
gh project item-edit --id <ITEM_ID> --project-id <PROJECT_ID> --field-id <STATUS_FIELD_ID> --single-select-option-id <DONE_OPTION_ID>

# Verify project board status
gh project item-list 1 --owner <OWNER> --format json | jq -r '.items[] | select(.content.number == <NUMBER>) | "Status: \(.status)"'

# 3. REMOVE GIT WORKTREE
# List worktrees to verify target exists
git worktree list

# Remove the issue worktree
git worktree remove /Users/altsang/workspace/cc-orchestrator-issue-<NUMBER>

# Clean up local feature branch (after merge)
git branch -D feature/issue-<NUMBER>-<description>

# 4. CLEAN UP ORPHANED DIRECTORIES
# Check for any orphaned test or temporary directories
ls -la ~/workspace/ | grep -E "cc-orchestrator-issue|test|temp"

# Remove any orphaned directories not tracked by git worktree
find ~/workspace -maxdepth 1 -type d -name "cc-orchestrator-issue-test-*" -exec rm -rf {} \;
find ~/workspace -maxdepth 1 -type d -name "cc-orchestrator-temp-*" -exec rm -rf {} \;

# 5. KILL TMUX SESSIONS
# List active tmux sessions
tmux list-sessions | grep cc-orchestrator

# Kill the dedicated issue session
tmux kill-session -t "cc-orchestrator-issue-<NUMBER>"

# Kill any orphaned test sessions
for session in $(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep "cc-orchestrator-test-"); do
  tmux kill-session -t "$session"
done
```

#### **Mandatory Cleanup Checklist:**
**ALL 5 actions must be verified complete:**
- [ ] **1. GitHub Issue**: Closed with resolution comment
- [ ] **2. Project Board**: Status updated to "Done"
- [ ] **3. Git Worktree**: Removed and local branch deleted
- [ ] **4. Orphaned Directories**: All test/temp directories cleaned up
- [ ] **5. Tmux Sessions**: Issue session and any test sessions killed

#### **Error Handling Guidance:**
**Common errors and safe resolution steps:**

**Git Worktree Errors:**
```bash
# Error: "worktree is locked"
# Solution: Remove lock file and retry
rm /Users/altsang/workspace/cc-orchestrator-issue-<NUMBER>/.git/worktrees/*/gitdir.lock
git worktree remove /Users/altsang/workspace/cc-orchestrator-issue-<NUMBER>

# Error: "worktree already removed" or "not a working tree"
# Solution: Clean up manually and prune
rm -rf /Users/altsang/workspace/cc-orchestrator-issue-<NUMBER>
git worktree prune
```

**Tmux Session Errors:**
```bash
# Error: "no session found" or "session not found"
# Solution: This is safe - session already cleaned up, continue

# Error: "can't find session" when listing
# Solution: No action needed, session doesn't exist
```

**Directory Cleanup Errors:**
```bash
# Error: "No such file or directory"
# Solution: Directory already cleaned up, continue

# Error: "Permission denied"
# Solution: Check ownership and use sudo if necessary
sudo find ~/workspace -maxdepth 1 -type d -name "cc-orchestrator-issue-test-*" -exec rm -rf {} \;
```

**GitHub API Errors:**
```bash
# Error: "issue already closed"
# Solution: Verify closure reason and continue
gh issue view <NUMBER> --json state,closedAt,stateReason

# Error: "project item not found"
# Solution: Item may already be removed or moved, verify manually
gh project item-list 1 --owner <OWNER> --format json | jq '.items[] | select(.content.number == <NUMBER>)'
```

#### **Final Cleanup Verification:**
```bash
# Run comprehensive verification to ensure all cleanup complete
echo "=== Git Worktrees ===" && \
git worktree list && \
echo -e "\n=== Workspace Directories ===" && \
ls -la ~/workspace/ | grep cc-orchestrator && \
echo -e "\n=== Tmux Sessions ===" && \
tmux list-sessions | grep cc-orchestrator && \
echo -e "\n=== Issue Status ===" && \
gh issue view <NUMBER> --json state,projectItems --jq '{state: .state, project_status: .projectItems[0].status}'
```

**Expected verification output:**
```
=== Git Worktrees ===
/Users/altsang/workspace/cc-orchestrator  (bare)

=== Workspace Directories ===
drwxr-xr-x  41 altsang staff  1312 Oct  6 11:33 cc-orchestrator

=== Tmux Sessions ===
(no output or only unrelated sessions)

=== Issue Status ===
{"state":"CLOSED","project_status":{"name":"Done"}}
```

#### **Test Worktree Policy:**
- **All test worktrees MUST be removed after testing completion**
- **No worktrees should persist beyond their active development phase**
- **Cleanup is mandatory before moving to next issue**
- **Test branches must be deleted after merge**
- **Orphaned directories from failed tests must be cleaned up**
- **All tmux sessions related to completed work must be killed**

### **Phase Epic Completion Protocol (MANDATORY)**

**CRITICAL**: When ALL issues within a phase are complete, the phase epic must also be closed.

#### **Epic Completion Steps:**
```bash
# 1. Verify all phase issues are closed
gh issue list --label "phase-X" --state open
# Should only show the epic itself (or be empty)

# 2. Close phase epic with completion summary
gh issue close <EPIC_NUMBER> --comment "Phase X Epic completed - all sub-issues implemented, tested, and merged.

✅ [List of completed issues with numbers]

Phase X: [Phase Name] is now complete."

# 3. Move epic to Done on project board
gh project item-edit --id <EPIC_ITEM_ID> --project-id PVT_kwHOACKAcc4A-64R --field-id PVTSSF_lAHOACKAcc4A-64RzgyLaOg --single-select-option-id 98236657

# 4. Update all phase documentation
# - Mark phase as COMPLETE in PROJECT_PLAN.md
# - Update status in CLAUDE.md and README.md
# - Commit and push changes
```

#### **Why Epic Closure is Critical:**
- **Project Tracking**: Ensures accurate phase completion status
- **Documentation Sync**: Keeps GitHub project board aligned with actual progress
- **Milestone Management**: Properly closes phase milestones for reporting
- **Workflow Integrity**: Maintains consistent issue lifecycle management

### **Multi-Session Coordination Best Practices**

#### **Session Naming Convention**
- **Issue Sessions**: `cc-orchestrator-issue-<NUMBER>`
- **Worker Sessions**: `worker-1`, `worker-2`, `worker-3`
- **Control Tower**: `control-tower` or default session

#### **Session Management Commands**
```bash
# List all active sessions
tmux list-sessions

# Switch between sessions quickly
tmux switch-client -t <session-name>

# Create new session for emergency work
tmux new-session -d -s "hotfix-session" -c "~/workspace/cc-orchestrator"

# Kill completed issue sessions
tmux kill-session -t "cc-orchestrator-issue-13"  # After PR merged
```

#### **Development Flow**
1. **Control Tower**: Coordinates and prepares environments
2. **Workers**: Execute focused development in isolated environments
3. **Session Persistence**: All work survives disconnections and crashes
4. **Parallel Development**: Multiple issues can progress simultaneously
5. **Clean Isolation**: No cross-contamination between issue work

### **Conversation Thread Management**

#### **Problem**: Multiple Claude instances in ~/workspace mix conversation histories
When all Claude instances start from the same `~/workspace` directory, conversation threads get mixed between instances, making it impossible to stop and resume specific instances without confusion.

#### **Solution**: Fresh Sessions per Issue
Start fresh Claude sessions for each issue to maintain separate conversation threads:

```bash
# Control Tower (coordination and setup)
claude

# Worker 1 (Issue #17 example)
claude --dangerously-skip-permissions

# Worker 2 (Issue #16 example)
claude --dangerously-skip-permissions

# Reviewer (code review and quality checks)
claude
```

**Alternative**: Use `--resume` to choose from previous sessions:
```bash
# If you need to resume a specific previous conversation
claude --resume --dangerously-skip-permissions
```

#### **Benefits**
- **Thread Isolation**: Each instance maintains separate conversation history
- **Resume Capability**: Stop and restart any instance without mixing threads
- **Directory Access**: All instances can navigate between sibling worktrees from ~/workspace
- **Session Management**: Use `/clear` in Claude to reset context when needed

#### **Session Management Best Practices**
- **Fresh Sessions**: Start new Claude session for each issue to avoid context mixing
- **Resume When Needed**: Use `claude --resume` to choose from previous conversations
- **Clear Context**: Use `/clear` command in Claude to reset conversation when switching tasks
- **Directory Isolation**: Each issue's tmux session starts in its own worktree directory

### **Performance Optimization**
- **Tmux Configuration**: Optimize for responsiveness and session management
- **Claude Code Settings**: Use skip permissions for routine development
- **Git Worktree Benefits**: Complete isolation without repository duplication
- **Resource Management**: Each session has dedicated working directory
- **Conversation Management**: Fresh sessions and `/clear` command prevent thread mixing

---

## 📚 **Documentation Standards**

### **Code Documentation**
```python
def complex_operation(
    data: dict[str, Any],
    options: ProcessingOptions
) -> ProcessingResult:
    """
    Process data according to specified options.

    Args:
        data: Input data dictionary with required keys:
              - 'source': Data source identifier
              - 'payload': Data to process
        options: Processing configuration including:
                - validation_level: 'strict' | 'permissive'
                - output_format: 'json' | 'yaml'

    Returns:
        ProcessingResult containing:
        - success: Whether processing succeeded
        - data: Processed data (if successful)
        - errors: List of errors (if any)

    Raises:
        ValidationError: When data fails validation
        ProcessingError: When processing fails

    Example:
        >>> result = complex_operation(
        ...     {'source': 'api', 'payload': {'key': 'value'}},
        ...     ProcessingOptions(validation_level='strict')
        ... )
        >>> assert result.success
    """
```

### **Project Documentation**
- **README.md**: Clear setup, usage, and contribution guidelines
- **API.md**: Complete API documentation with examples
- **ARCHITECTURE.md**: System design and component interactions
- **TROUBLESHOOTING.md**: Common issues and solutions
- **CHANGELOG.md**: Version history and migration notes

---

## 🔄 **Code Review Standards**

### **Integration-First Reviewer Checklist**
**MANDATORY**: Reviewer must personally execute and verify complete user workflows.

```markdown
## Integration Review (CRITICAL - Must be verified first)
- [ ] **End-to-end workflow executed manually** - reviewer runs complete user journey start to finish
- [ ] **Cross-process persistence verified** - reviewer confirms data survives separate CLI invocations
- [ ] **Integration boundaries inspected** - all component connections reviewed for completeness
- [ ] **No TODOs in integration paths** - database connections, state persistence fully implemented
- [ ] **Component isolation tested** - each layer (CLI/Core/DB) properly connected but not coupled
- [ ] **State consistency verified** - same data accessible via CLI and Web API
- [ ] **Integration demo witnessed** - PR author demonstrates complete workflow to reviewer

## Integration Testing Review
- [ ] **Integration tests present** - tests verify component connections, not just units
- [ ] **Cross-process scenarios tested** - separate invocations, state persistence
- [ ] **User workflow coverage** - integration tests match real user journeys
- [ ] **Component boundary testing** - tests verify data flow across all layers
- [ ] **Integration test quality** - meaningful assertions, realistic data, edge cases

## Functionality Review
- [ ] Feature works as designed across all integration points
- [ ] Error handling comprehensive across component boundaries
- [ ] Edge cases covered for integrated system behavior
- [ ] Performance acceptable for complete user workflows
- [ ] Security implications considered for all integration points

## Code Quality Review
- [ ] Type annotations complete and correct across interfaces
- [ ] Error handling follows standards at integration boundaries
- [ ] Logging appropriate and structured for integrated operations
- [ ] Code is readable and maintainable across component boundaries
- [ ] No code duplication or technical debt in integration logic
- [ ] Component interfaces properly defined and documented

## Unit Testing Review (Secondary to Integration)
- [ ] Test coverage ≥90% for new code
- [ ] Tests cover happy path, errors, edge cases for individual components
- [ ] Unit tests support integration scenarios
- [ ] Tests are maintainable and clear

## Documentation Review
- [ ] Integration patterns documented in docstrings
- [ ] README/docs updated with user workflow examples if needed
- [ ] Breaking changes to integrations documented
- [ ] Migration path clear for integrated systems (if applicable)
```

### **Review Failure Criteria - Automatic Rejection**
**PRs MUST be rejected if:**
- [ ] Reviewer cannot successfully execute complete user workflow
- [ ] State does not persist across separate process invocations
- [ ] Integration tests are missing or inadequate
- [ ] TODOs exist in critical integration paths (database connections, state management)
- [ ] Components exist in isolation without proper integration
- [ ] Integration demo was not provided or failed during review

### **Review Response Standards**
- **All feedback must be addressed** before merge
- **Explanations required** for any standards deviations
- **Follow-up issues created** for any deferred improvements
- **Knowledge sharing** encouraged through review comments

---

## 🎭 **Development Environment**

### **Required Tools**
```bash
# Development dependencies
pip install mypy ruff black pytest pytest-cov
pip install pre-commit safety bandit

# Setup pre-commit hooks
pre-commit install

# IDE Configuration (VS Code example)
{
  "python.linting.mypyEnabled": true,
  "python.linting.enabled": true,
  "python.formatting.provider": "black",
  "python.linting.ruffEnabled": true
}
```

### **Development Commands**
```bash
# Quality check (run before every commit)
make quality-check  # mypy + ruff + black + tests

# Full validation (run before PR)
make full-validation  # quality-check + integration + performance

# Performance baseline
make performance-test

# Security scan
make security-scan
```

---

## 📈 **Metrics & Monitoring**

### **Code Quality Metrics**
- **Type Coverage**: 100% for new code
- **Test Coverage**: ≥90% overall, ≥95% for new code
- **Complexity**: Cyclomatic complexity <10 per function
- **Maintainability Index**: >85
- **Technical Debt Ratio**: <5%

### **Production Metrics**
- **Availability**: 99.9% uptime SLA
- **Performance**: P95 response times <100ms
- **Error Rate**: <0.1% for normal operations
- **Security**: No high/critical vulnerabilities

### **Development Metrics**
- **Lead Time**: Idea to production <2 weeks
- **Cycle Time**: Code to merge <2 days
- **MTTR**: Mean time to resolution <4 hours
- **Deployment Frequency**: Multiple times per day

---

## 🚨 **Escalation & Standards Enforcement**

### **Quality Gate Failures**
1. **Automated Rejection**: CI/CD blocks merge if quality gates fail
2. **Manual Override**: Requires senior engineer approval + technical debt issue
3. **Emergency Fixes**: Hotfix process with immediate follow-up remediation

### **Standards Violations**
1. **First Violation**: Educational guidance and re-review
2. **Repeated Violations**: Required training and mentoring
3. **Persistent Issues**: Process improvement and tooling enhancement

### **Continuous Improvement**
- **Monthly**: Review metrics and adjust standards
- **Quarterly**: Major methodology updates
- **Annually**: Complete methodology review and refresh

---

## ✅ **Success Criteria**

A feature is **production-ready** when it demonstrates complete integration across all system boundaries:

```markdown
✅ **Integration Requirements (MANDATORY)**
- [ ] **Complete user workflow executable** - end-to-end journey works from user action to outcome
- [ ] **Cross-process state persistence verified** - data survives separate CLI/API invocations
- [ ] **All components properly connected** - no TODOs in integration paths (database, state management)
- [ ] **Integration tests implemented** - tests verify component connections and user workflows
- [ ] **Manual integration verification completed** - reviewer executed full workflow successfully
- [ ] **Component boundaries well-defined** - clear interfaces between CLI/Core/Database/Process layers
- [ ] **State consistency across interfaces** - same data accessible via CLI and Web API

✅ **Quality Gates**
- [ ] Zero mypy errors across all integration points
- [ ] Zero linting issues
- [ ] 100% integration test pass rate
- [ ] 100% unit test pass rate
- [ ] ≥90% test coverage including integration scenarios
- [ ] Performance benchmarks met for complete user workflows

✅ **Functionality**
- [ ] All acceptance criteria met with integration verification
- [ ] Error scenarios handled gracefully across component boundaries
- [ ] Integration with existing components verified and tested
- [ ] Manual testing of complete user workflows completed
- [ ] Cross-process scenarios tested (separate invocations)

✅ **Testing**
- [ ] Integration tests present and comprehensive
- [ ] Cross-process persistence scenarios tested
- [ ] User workflow tests match real usage patterns
- [ ] Component boundary testing implemented
- [ ] Unit tests support integration scenarios

✅ **Documentation**
- [ ] Integration patterns documented in code
- [ ] User workflow examples provided
- [ ] Component interface documentation complete
- [ ] Deployment/operation procedures include integration setup

✅ **Security & Operations**
- [ ] Security review completed for all integration points
- [ ] Monitoring instrumentation added across component boundaries
- [ ] Health checks implemented for integrated system
- [ ] Graceful degradation designed across all layers

✅ **Team Readiness**
- [ ] Integration-focused code review completed and approved
- [ ] End-to-end workflow demonstrated to reviewer
- [ ] Knowledge transferred including integration patterns
- [ ] Support procedures documented for integrated system
```

**Critical Rule**: If any integration criterion is not met, the feature is **not production-ready** and should not be merged. Features that work in isolation but fail integration are incomplete and create technical debt.

---

---

## 🔗 **Integration-First Development Summary**

### **The Integration Debt Problem**
The Issue #14 failure demonstrated how features can appear complete while missing critical integration:
- ✅ Database layer implemented (complete CRUD operations)
- ✅ CLI commands implemented (functional structure)
- ✅ Core logic implemented (process management)
- ❌ **Integration missing** - components never connected end-to-end
- ❌ **State persistence broken** - each invocation created fresh isolated state
- ❌ **User workflows failed** - create → list → stop → verify was impossible

### **Integration-First Solution**
This methodology prevents integration debt by requiring:

1. **User Journey First**: Start with complete workflow, build components to support it
2. **Integration Skeleton**: Connect all components with minimal functionality before adding features
3. **Persistent State**: Verify data survives across separate process invocations
4. **Cross-Process Testing**: Test that separate CLI commands share state via database
5. **Integration Review**: Reviewer must manually execute complete user workflows
6. **No TODOs in Integration Paths**: Database connections and state persistence fully implemented

### **Quality Assurance Changes**
- **PR Rejection Criteria**: Missing integration tests or failed cross-process workflows = automatic rejection
- **Review Requirements**: Reviewer must personally execute complete user journey
- **Testing Priority**: Integration tests required before unit tests can be considered sufficient
- **Definition of Done**: Feature incomplete until integrated across all system boundaries

---

*This integration-first methodology ensures that every feature delivers complete, working user value from day one, eliminating the possibility of integration debt that creates the illusion of progress while delivering broken functionality.*
