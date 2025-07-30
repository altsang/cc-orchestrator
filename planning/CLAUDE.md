# CC-Orchestrator Project

## Project Overview
Claude Code orchestrator managing multiple instances through git worktrees with CLI + Web dashboard + Tmux integration.

## Current Status
- Phase: Planning Complete, Ready for Implementation
- Next: Phase 1 - Core Infrastructure

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
1. Read current TODO.md for active tasks
2. **MANDATORY**: Complete full worker terminal setup (see Worker Terminal Setup Protocol below)
3. **MANDATORY**: Update GitHub project board status to "In Progress" AND assign issue to yourself before starting work
4. Update progress in DEVELOPMENT_LOG.md
5. Reference ARCHITECTURE.md for technical decisions
6. Follow PROJECT_PLAN.md phases
7. **MANDATORY**: Create PR following standardized format (see PR Protocol below)
8. **MANDATORY**: Only move project board to "Done" after PR is merged

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
