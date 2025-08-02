# CC-Orchestrator Development Methodology

## Production-Ready Development Standards

This document establishes the mandatory development methodology to ensure all components are production-ready before merge.

---

## 🎯 **Core Principles**

### 1. **Zero Technical Debt Policy**
- No code merges with known type errors, linting issues, or test failures
- All components must meet production standards before PR approval
- Technical debt is addressed immediately, not deferred

### 2. **Quality Gates**
Every component must pass ALL quality gates:
- ✅ **Type Safety**: mypy passes with zero errors
- ✅ **Code Quality**: ruff/black formatting and linting clean
- ✅ **Test Coverage**: Minimum 90% coverage for new code
- ✅ **Functionality**: All tests pass, manual verification complete
- ✅ **Documentation**: Code is self-documenting with proper docstrings

### 3. **Defense in Depth**
Multiple layers of quality assurance:
- Pre-commit hooks (automated)
- CI/CD pipeline validation
- Manual code review
- Integration testing

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

### Phase 1: Planning & Design
```markdown
## Before Writing Code:
1. [ ] Define acceptance criteria clearly
2. [ ] Plan type-safe interfaces and data structures
3. [ ] Design error handling and edge cases
4. [ ] Plan test scenarios (unit, integration, edge cases)
5. [ ] Consider backwards compatibility and migration needs
```

### Phase 2: Implementation Standards

#### **Type Safety First**
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

### Phase 3: Testing Requirements

#### **Mandatory Test Coverage**
```python
class TestConfigurationSystem:
    """✅ REQUIRED: Comprehensive test coverage."""

    def test_happy_path(self):
        """Test normal operation."""
        pass

    def test_edge_cases(self):
        """Test boundary conditions."""
        pass

    def test_error_conditions(self):
        """Test error handling."""
        pass

    def test_integration(self):
        """Test component integration."""
        pass
```

#### **Test Quality Standards**
- **Unit Tests**: 95%+ coverage for new code
- **Integration Tests**: Cover all component interactions
- **Error Path Testing**: Test all error conditions and recovery
- **Edge Case Testing**: Boundary values, null inputs, malformed data
- **Performance Testing**: Verify acceptable response times

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

### **Before Every PR:**
```markdown
- [ ] All quality gates passed
- [ ] Integration tests with existing components
- [ ] Backwards compatibility maintained
- [ ] Migration path documented (if breaking changes)
- [ ] Security implications reviewed
- [ ] Performance impact assessed
- [ ] Monitoring/logging instrumentation added
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
tmux new-session -d -s "cc-orchestrator-issue-<NUMBER>" -c "~/workspace/cc-orchestrator-issue-<NUMBER>"

# 3. Update GitHub project board status
gh project item-edit --id <ITEM_ID> --field-id <STATUS_FIELD> --single-select-option-id <IN_PROGRESS_ID>

# 4. Assign GitHub issue
gh issue edit <NUMBER> --assignee @me
```

**Worker Activation Commands:**
```bash
# From existing tmux session (Worker 1, Worker 2)
tmux switch-client -t "cc-orchestrator-issue-<NUMBER>"
claude --dangerously-skip-permissions --conversation-id "issue-<NUMBER>-<description>"

# From fresh terminal
tmux attach-session -t "cc-orchestrator-issue-<NUMBER>"
claude --dangerously-skip-permissions --conversation-id "issue-<NUMBER>-<description>"
```

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

#### **Solution**: Unique Conversation IDs
Use `--conversation-id` flags to maintain separate conversation threads for each role:

```bash
# Control Tower (coordination and setup)
claude --conversation-id "control-tower-coordination"

# Worker 1 (Issue #15 example)  
claude --dangerously-skip-permissions --conversation-id "issue-15-tmux-integration"

# Worker 2 (Issue #16 example)
claude --dangerously-skip-permissions --conversation-id "issue-16-health-monitoring"

# Reviewer (code review and quality checks)
claude --conversation-id "code-review-session"
```

#### **Benefits**
- **Thread Isolation**: Each instance maintains separate conversation history
- **Resume Capability**: Stop and restart any instance without mixing threads
- **Directory Access**: All instances can navigate between sibling worktrees from ~/workspace
- **Role Clarity**: Conversation IDs clearly identify which instance serves which role

#### **Conversation ID Patterns**
- **Control Tower**: `control-tower-coordination`
- **Issue Work**: `issue-<NUMBER>-<description>` (e.g., `issue-15-tmux-integration`)
- **Code Review**: `code-review-session`
- **Hotfix/Emergency**: `hotfix-<description>` (e.g., `hotfix-critical-bug`)

### **Performance Optimization**
- **Tmux Configuration**: Optimize for responsiveness and session management
- **Claude Code Settings**: Use skip permissions for routine development
- **Git Worktree Benefits**: Complete isolation without repository duplication
- **Resource Management**: Each session has dedicated working directory
- **Conversation Management**: Unique conversation IDs prevent thread mixing

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

### **Reviewer Checklist**
```markdown
## Functionality Review
- [ ] Feature works as designed
- [ ] Error handling comprehensive
- [ ] Edge cases covered
- [ ] Performance acceptable
- [ ] Security implications considered

## Code Quality Review
- [ ] Type annotations complete and correct
- [ ] Error handling follows standards
- [ ] Logging appropriate and structured
- [ ] Code is readable and maintainable
- [ ] No code duplication or technical debt

## Testing Review
- [ ] Test coverage ≥90% for new code
- [ ] Tests cover happy path, errors, edge cases
- [ ] Integration tests adequate
- [ ] Tests are maintainable and clear

## Documentation Review
- [ ] Docstrings complete and accurate
- [ ] README/docs updated if needed
- [ ] Breaking changes documented
- [ ] Migration path clear (if applicable)
```

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

A component is **production-ready** when:

```markdown
✅ **Quality Gates**
- [ ] Zero mypy errors
- [ ] Zero linting issues
- [ ] 100% test pass rate
- [ ] ≥90% test coverage
- [ ] Performance benchmarks met

✅ **Functionality**
- [ ] All acceptance criteria met
- [ ] Error scenarios handled gracefully
- [ ] Integration with existing components verified
- [ ] Manual testing completed

✅ **Documentation**
- [ ] Code self-documenting with docstrings
- [ ] User-facing documentation updated
- [ ] Deployment/operation procedures documented

✅ **Security & Operations**
- [ ] Security review completed
- [ ] Monitoring instrumentation added
- [ ] Health checks implemented
- [ ] Graceful degradation designed

✅ **Team Readiness**
- [ ] Code review completed and approved
- [ ] Knowledge transferred to team
- [ ] Support procedures documented
```

**Remember**: If any criterion is not met, the component is **not production-ready** and should not be merged.

---

*This methodology ensures that every component delivered meets production standards from day one, eliminating technical debt and ensuring system reliability.*
