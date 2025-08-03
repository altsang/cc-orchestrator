# CC-Orchestrator Project

## Project Overview
Claude Code orchestrator managing multiple instances through git worktrees with CLI + Web dashboard + Tmux integration.

## Current Status
- Phase: Phase 1 ✅ COMPLETE, Phase 2 ✅ NEARLY COMPLETE, Phase 3 🚧 STARTED
- Current: Phase 2 (4/5 tasks done) + Phase 3 development started
- Active Issues: #17 (worktree isolation - Worker 1), #18 (FastAPI backend - Worker 2)

## Key Context
- Dual interface: CLI (tmux) + Web control tower
- Git worktree isolation for parallel development
- GitHub/Jira integration for task management
- Real-time monitoring and coordination

## Important Files
- PROJECT_PLAN.md: Complete implementation roadmap
- ARCHITECTURE.md: Technical design decisions
- TODO.md: Current task tracking
- REQUIREMENTS.md: Feature specifications

## Development Workflow
1. **MANDATORY**: Sync repository and project status first (see Repository Sync Protocol below)
2. Read current TODO.md for active tasks
3. **MANDATORY**: Complete full worker terminal setup (see Worker Terminal Setup Protocol below)
4. **MANDATORY**: Update GitHub project board status to "In Progress" AND assign issue to yourself before starting work
5. Update progress in DEVELOPMENT_LOG.md
6. Reference ARCHITECTURE.md for technical decisions
7. Follow PROJECT_PLAN.md phases
8. **MANDATORY**: Create PR following standardized format (see PR Protocol below)
9. **MANDATORY**: Only move project board to "Done" after PR is merged

## 📡 Repository Sync Protocol (MANDATORY)

**CRITICAL**: Always sync with actual repository state before providing status or making decisions. Other worker threads may have completed work that changes the current context.

### Status Check Sequence (MANDATORY for all status requests)

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

### When to Use This Protocol
- **ALWAYS** when user asks "what's the status?"
- **ALWAYS** before planning next work
- **ALWAYS** before setting up new worker environments
- **ALWAYS** when resuming work after time gap
- **ALWAYS** when multiple workers are active

### Why This Protocol is Critical
- **Parallel Development**: Multiple workers complete issues simultaneously
- **Context Accuracy**: Documentation may lag behind actual progress
- **Decision Making**: Work assignments depend on actual completion status
- **Resource Efficiency**: Avoid duplicate work on completed issues
- **Phase Awareness**: Must filter issues by current project phase, not just priority

### Critical Phase Awareness Requirements
- **ALWAYS** check current phase from PROJECT_PLAN.md before listing "next issues"
- **NEVER** list issues from future phases when asked "what's next to work on"
- **FILTER** issue lists by current phase label (e.g., `--label "phase-2"`)
- **UNDERSTAND** that high-priority issues from Phase 5/6 are NOT current work if we're in Phase 2

**NEVER** rely solely on documentation for current status - always verify with actual repository state first.

## 🔧 Worker Terminal Setup Protocol (MANDATORY)

**Purpose**: Create isolated development environment for each GitHub issue to enable parallel development streams.

### Complete Setup Sequence (Run as Control Tower)

For each new issue, the control tower MUST execute all of these steps:

```bash
# 1. Create git worktree with feature branch
git worktree add -b feature/issue-<NUMBER>-<description> ../cc-orchestrator-issue-<NUMBER>

# 2. Create dedicated tmux session in the worktree directory
tmux new-session -d -s "cc-orchestrator-issue-<NUMBER>" -c "~/workspace/cc-orchestrator-issue-<NUMBER>"

# 3. Update GitHub project board to "In Progress" AND assign work
gh project item-list 1 --owner altsang --format json | jq '.items[] | select(.content.number == <NUMBER>) | .id'
gh project item-edit --id <ITEM_ID> --project-id PVT_kwHOACKAcc4A-64R --field-id PVTSSF_lAHOACKAcc4A-64RzgyLaOg --single-select-option-id 47fc9ee4
gh issue edit <NUMBER> --assignee @me

# 4. Update ISSUE_CONTEXT.md with issue details
# (Manual edit to add issue section)
```

### User Action After Setup
```bash
# User attaches to prepared session and invokes Claude Code
tmux attach-session -t "cc-orchestrator-issue-<NUMBER>"
claude  # or claude-code depending on installation
```

### Benefits of This Protocol
- **Isolation**: Each issue has dedicated worktree + tmux session
- **Persistence**: Sessions survive disconnections and terminal crashes
- **Parallelization**: Multiple issues can be developed simultaneously
- **Consistency**: Standardized environment for all development work
- **Tracking**: GitHub project board accurately reflects active work

## 🧹 Cleanup Protocol (MANDATORY)

**CRITICAL**: All development work MUST follow strict cleanup practices to prevent repository pollution.

### During Development
- **Never commit temporary files**: test scripts, debug outputs, manual testing artifacts
- **Use .gitignore**: Ensure temporary files are ignored automatically
- **Clean as you go**: Remove debugging code and temporary scripts immediately after use

### Before PR Creation (MANDATORY Checklist)
```bash
# 1. Rebase on latest main to prevent conflicts
git fetch origin
git rebase origin/main
# Resolve any conflicts if they arise
# git add <resolved-files>
# git rebase --continue

# 2. Check for stray files
git status
git ls-files --others --exclude-standard

# 3. Remove any temporary artifacts
rm -f test_*.py debug_*.py manual_*.py temp_*.* *.tmp

# 4. Verify clean state
git status  # Should show only intended changes

# 5. Run final tests to ensure nothing broke
python -m pytest

# 6. Only then create PR
```

### Common Artifacts to Avoid
- ❌ `test_database_manual.py` - Use automated tests instead
- ❌ `debug_*.py` - Remove after debugging
- ❌ `temp_*.py` - Clean up temporary scripts
- ❌ `.DS_Store` - Should be in .gitignore
- ❌ `*.pyc`, `__pycache__/` - Should be in .gitignore
- ❌ Log files, database files - Should be in .gitignore
- ❌ IDE configuration files - Should be in .gitignore

### Critical Rebase Requirement
**MANDATORY**: When working on a new issue after other issues have been merged to main:
- **Always rebase** your feature branch on the latest main before creating PR
- **Never merge** without rebasing first - this prevents conflicts and maintains clean history
- **Resolve conflicts** during rebase, not during merge
- **Test after rebase** to ensure integration works correctly

### Enforcement
- **Control tower responsibility**: Verify clean state and proper rebase before approving PRs
- **Worker responsibility**: Rebase on main, clean up artifacts, and test before requesting review
- **Automated checks**: Pre-commit hooks should catch common artifacts and ensure linear history

### Session Naming Convention
- **Tmux session**: `cc-orchestrator-issue-<NUMBER>`
- **Worktree path**: `~/workspace/cc-orchestrator-issue-<NUMBER>`
- **Branch name**: `feature/issue-<NUMBER>-<description>`

**Example for Issue #10:**
- Session: `cc-orchestrator-issue-10`
- Path: `~/workspace/cc-orchestrator-issue-10`
- Branch: `feature/issue-10-configuration-management`

## 🔗 Pull Request Protocol (MANDATORY)

**CRITICAL**: All Pull Requests MUST follow this exact format for consistency:

### PR Title Format
```
Issue #<NUMBER>: <Brief description of implementation>
```

**Examples:**
- ✅ `Issue #9: Implement SQLite database schema and models`
- ✅ `Issue #8: Implement CLI framework with Click command groups`
- ✅ `Issue #12: Fix unit test framework issues`
- ❌ `Implement CLI framework with Click command groups (Issue #8)`
- ❌ `Fix unit test framework issues - Issue #12`

### PR Body Format
```markdown
## Summary
<Brief overview linking to the issue>

Resolves: #<ISSUE_NUMBER>

<Implementation details>

## Test Plan
- [x] All acceptance criteria met
- [x] Tests passing with adequate coverage
- [x] Code quality checks pass

🤖 Generated with [Claude Code](https://claude.ai/code)
```

### PR Creation Commands
```bash
gh pr create --title "Issue #<NUMBER>: <Brief description>" --body "$(cat <<'EOF'
## Summary
<Implementation summary>

Resolves: #<ISSUE_NUMBER>

<Details>

## Test Plan
- [x] All acceptance criteria met
- [x] Tests passing
- [x] Code quality checks pass

🤖 Generated with [Claude Code](https://claude.ai/code)
EOF
)"
```

## Quick Start for New Sessions
1. Check TODO.md for current task status
2. Review DEVELOPMENT_LOG.md for recent progress
3. Continue with Phase 1 implementation if not yet complete
4. Update documentation as you work

## GitHub Issue Progress Tracking Protocol

When working on issues in git worktrees:

### Progress Updates
- Post structured progress comments on GitHub issues at major milestones
- Include: ✅ Completed, 🔧 Implementation Approach, 🧪 Testing, 🚀 Next Steps
- Document key architectural decisions with rationale
- Update when acceptance criteria are met
- Provide final summary comment when closing issues

### Comment Structure Template
```markdown
## Progress Update - [Date]

### ✅ Completed
- [Specific features/tasks completed]

### 🔧 Implementation Approach
- [Key technical decisions and patterns used]

### 🧪 Testing
- [Testing approach and coverage]

### 🚀 Next Steps
- [Immediate next actions]
```

### Guidelines
- Keep GitHub issues as system of record for high-level planning and progress
- Focus on decisions and context that will help future development
- Update at completion of major milestones, not every small change
- Include links to relevant commits when posting final summaries

## Session Continuity Notes
- This project builds a control plane for managing multiple Claude Code instances
- Each instance runs in isolated git worktrees for parallel development
- Web dashboard provides real-time monitoring and control
- Tmux integration ensures session persistence across disconnections
- External integrations pull tasks from GitHub/Jira automatically
- Note: Claude executable is `claude` not `claude-code`

## 🚨 GitHub Project Board Protocol (MANDATORY)

**CRITICAL**: All GitHub issues MUST follow this exact workflow:

### Status Transitions
1. **Todo** → 2. **In Progress** → 3. **Done**

### When to Update Status
- **"In Progress"**: Move BEFORE starting any work (never work on "Todo" items)
- **"In Progress"**: Keep throughout implementation, even when code is complete locally
- **"Done"**: Move ONLY after Pull Request is created, reviewed, and merged

### Quick CLI Commands
```bash
# Move to "In Progress" (before starting work):
gh project item-edit --id <ITEM_ID> --project-id PVT_kwHOACKAcc4A-64R --field-id PVTSSF_lAHOACKAcc4A-64RzgyLaOg --single-select-option-id 47fc9ee4

# Find item ID:
gh project item-list 1 --owner altsang --format json | jq '.items[] | select(.content.number == <ISSUE_NUMBER>) | .id'

# Move to "Done" (only after PR merged):
gh project item-edit --id <ITEM_ID> --project-id PVT_kwHOACKAcc4A-64R --field-id PVTSSF_lAHOACKAcc4A-64RzgyLaOg --single-select-option-id 98236657
```

**See GITHUB_PROJECT_MANAGEMENT.md for complete protocol details.**
