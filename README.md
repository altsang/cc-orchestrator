# CC-Orchestrator

A Claude Code orchestrator that manages multiple Claude instances through git worktrees, providing both CLI and web interfaces for parallel development workflows.

## Overview

CC-Orchestrator acts as a control plane for managing multiple Claude Code instances, enabling:

- **Parallel Development**: Run multiple Claude instances in isolated git worktrees
- **Session Persistence**: Tmux integration for disconnection-proof sessions  
- **Visual Monitoring**: Real-time web dashboard for instance oversight
- **Task Coordination**: Automated task assignment and progress tracking
- **External Integration**: GitHub/Jira synchronization for workflow automation

## Quick Start

```bash
# Initialize orchestrator in your repository
cc-orchestrator init

# Start web dashboard
cc-orchestrator web start

# Create a task and spawn Claude instance
cc-orchestrator task create "Implement feature X" --branch feature/x
cc-orchestrator instance spawn --task TASK-123

# Monitor via CLI or web interface
cc-orchestrator status
# or visit http://localhost:8080
```

## Features

### Multi-Instance Management
- Run up to 10 concurrent Claude Code instances
- Complete isolation via git worktrees
- Resource monitoring and limits
- Automatic cleanup and recovery

### Session Persistence
- Tmux integration for persistent sessions
- Survive SSH disconnections and terminal crashes
- Resume work from anywhere
- Team collaboration support

### Real-Time Dashboard
- Live instance status and resource usage
- Interactive task management board
- Streaming logs with search and filtering
- Mobile-responsive design

### External Integrations
- GitHub Issues ↔ Tasks synchronization
- Jira ticket management
- Slack/Discord notifications
- Webhook support for custom workflows

## Architecture

- **Backend**: Python + FastAPI + SQLite
- **Frontend**: React + TypeScript + WebSockets
- **Session Management**: tmux
- **Git Operations**: GitPython with worktree support

## Installation

```bash
pip install cc-orchestrator
```

Or from source:
```bash
git clone https://github.com/yourusername/cc-orchestrator
cd cc-orchestrator
pip install -e .
```

## Configuration

```yaml
# ~/.config/cc-orchestrator/config.yaml
max_instances: 5
tmux_enabled: true
web:
  enabled: true
  port: 8080
integrations:
  github:
    token: "your-token"
  jira:
    url: "https://company.atlassian.net"
    token: "your-token"
```

## Development Status

🚧 **Currently in development** - See `planning/` directory for detailed implementation plan.

- **Phase 1**: Core Infrastructure (In Progress)
- **Phase 2**: Git & Process Management (Planned)
- **Phase 3**: Web Interface (Planned)
- **Phase 4**: External Integrations (Planned)
- **Phase 5**: Advanced Features (Planned)
- **Phase 6**: Documentation & Release (Planned)

## Contributing

This project is in active development. See `planning/PROJECT_PLAN.md` for the detailed roadmap and `planning/TODO.md` for current tasks.

## License

MIT License - see LICENSE file for details.