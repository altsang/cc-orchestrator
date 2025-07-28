# GitHub Project Board Management

## Current Status

The CC-Orchestrator project uses GitHub Projects for tracking all development work across 6 phases.

**Project Board**: [CC-Orchestrator Development](https://github.com/altsang/cc-orchestrator/projects/1)

## Active Development - Phase 1

### Issues Currently Being Worked On (3 Parallel Instances)

1. **Issue #7: Project setup with pyproject.toml and dependencies**
   - **Status**: In Progress (manually update on GitHub)
   - **Priority**: CRITICAL PATH - blocks other development
   - **Instance**: claude-issue-7
   - **Branch**: feature/project-setup
   - **URL**: https://github.com/altsang/cc-orchestrator/issues/7

2. **Issue #11: Basic logging and error handling setup**
   - **Status**: In Progress (manually update on GitHub)  
   - **Priority**: High - needed by all components
   - **Instance**: claude-issue-11
   - **Branch**: feature/logging-system
   - **URL**: https://github.com/altsang/cc-orchestrator/issues/11

3. **Issue #12: Unit test framework setup**
   - **Status**: In Progress (manually update on GitHub)
   - **Priority**: High - enables quality assurance
   - **Instance**: claude-issue-12
   - **Branch**: feature/test-framework
   - **URL**: https://github.com/altsang/cc-orchestrator/issues/12

## 🚨 MANDATORY GitHub Project Board Workflow Protocol

**⚠️ CRITICAL**: All work MUST follow this exact workflow to maintain project visibility and proper status tracking.

### GitHub Project Board Status Workflow

The project board has three status columns that MUST be updated at specific points:

1. **Todo** → 2. **In Progress** → 3. **Done**

### 📋 Mandatory Status Update Points

#### 🟡 START OF WORK: Move to "In Progress"
**WHEN**: Before starting any implementation work
**HOW**: 
```bash
# Via GitHub CLI (preferred):
gh project item-edit --id <ITEM_ID> --project-id PVT_kwHOACKAcc4A-64R --field-id PVTSSF_lAHOACKAcc4A-64RzgyLaOg --single-select-option-id 47fc9ee4

# Via Web UI (alternative):
# 1. Go to https://github.com/users/altsang/projects/1
# 2. Find the issue and drag to "In Progress" column
```

#### 🔄 DURING WORK: Keep as "In Progress"  
**WHEN**: Throughout implementation, testing, debugging
**STATUS**: Remains "In Progress" even when code is complete locally
**IMPORTANT**: Do NOT move to "Done" when implementation is finished

#### ✅ END OF WORK: Move to "Done"
**WHEN**: ONLY after Pull Request is created, reviewed, and merged
**HOW**:
```bash
# Via GitHub CLI:
gh project item-edit --id <ITEM_ID> --project-id PVT_kwHOACKAcc4A-64R --field-id PVTSSF_lAHOACKAcc4A-64RzgyLaOg --single-select-option-id 98236657
```

### 🚫 Common Workflow Violations (DO NOT DO)

❌ **Never move to "Done" when code is complete locally**
❌ **Never skip the "In Progress" status when starting work**  
❌ **Never leave issues in "Todo" while actively working**
❌ **Never move to "Done" before PR is merged**

### 📖 Project Board Field IDs (For CLI Usage)

- **Project ID**: `PVT_kwHOACKAcc4A-64R`
- **Status Field ID**: `PVTSSF_lAHOACKAcc4A-64RzgyLaOg`
- **Status Options**:
  - Todo: `f75ad846`
  - In Progress: `47fc9ee4`  
  - Done: `98236657`

### 🔧 Finding Item IDs

```bash
# Find item ID for an issue:
gh project item-list 1 --owner altsang --format json | jq '.items[] | select(.content.number == <ISSUE_NUMBER>) | .id'
```

### Manual Project Board Access (Alternative)
1. Go to: https://github.com/users/altsang/projects/1
2. Find the issue card
3. Drag to appropriate status column

## Next Phase Planning

After current 3 issues complete, next parallel batch:
- **Issue #8**: CLI framework implementation (depends on #7)
- **Issue #9**: SQLite database schema (depends on #7) 
- **Issue #10**: Configuration management (depends on #8)

## Automation Future

Once CC-Orchestrator is built, it will automate:
- ✅ GitHub issue status synchronization
- ✅ Project board updates
- ✅ Automatic assignment of issues to instances
- ✅ Progress tracking and reporting

For now, manual updates ensure proper project visibility and coordination.