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
2. Update progress in DEVELOPMENT_LOG.md
3. Reference ARCHITECTURE.md for technical decisions
4. Follow PROJECT_PLAN.md phases

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
