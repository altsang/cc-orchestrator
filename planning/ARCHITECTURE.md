# Technical Architecture

## Technology Stack

### Backend Core
- **Python 3.11+**: Core orchestration logic
- **Click**: CLI framework with excellent UX
- **SQLite**: Lightweight persistent storage
- **GitPython**: Git operations and worktree management
- **asyncio**: Concurrent process management

### Web Interface
- **FastAPI**: Modern Python web framework with OpenAPI
- **WebSockets**: Real-time bidirectional communication
- **React + TypeScript**: Frontend with type safety
- **Tailwind CSS**: Utility-first styling
- **Chart.js**: Real-time monitoring visualizations

### Process & Session Management
- **tmux**: Session persistence and terminal management
- **libtmux**: Python library for tmux automation and control
- **subprocess**: Claude Code process spawning
- **watchdog**: File system monitoring
- **psutil**: System resource monitoring

## Project Structure
```
cc-orchestrator/
├── src/cc_orchestrator/
│   ├── __init__.py
│   ├── cli/                 # Click-based CLI commands
│   │   ├── __init__.py
│   │   ├── main.py         # Main CLI entry point
│   │   ├── tasks.py        # Task management commands
│   │   ├── instances.py    # Instance management commands
│   │   ├── worktrees.py    # Worktree management commands
│   │   ├── tmux.py         # Tmux session management commands
│   │   └── config.py       # Configuration commands
│   ├── core/                # Core orchestration logic
│   │   ├── __init__.py
│   │   ├── orchestrator.py # Main orchestrator class
│   │   ├── worktree_manager.py
│   │   ├── instance_manager.py
│   │   ├── task_coordinator.py
│   │   └── database.py     # SQLite models and operations
│   ├── web/                 # FastAPI backend
│   │   ├── __init__.py
│   │   ├── api.py          # REST API routes
│   │   ├── websockets.py   # WebSocket handlers
│   │   ├── models.py       # Pydantic models
│   │   └── dependencies.py # FastAPI dependencies
│   ├── tmux/                # Tmux session management
│   │   ├── __init__.py
│   │   ├── service.py       # Core tmux service implementation
│   │   └── logging_utils.py # Tmux-specific logging utilities
│   ├── integrations/        # External APIs
│   │   ├── __init__.py
│   │   ├── github.py       # GitHub API client
│   │   ├── jira.py         # Jira API client
│   │   └── slack.py        # Slack notifications
│   ├── config/              # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py     # Configuration models
│   │   └── defaults.py     # Default configurations
│   └── utils/               # Shared utilities
│       ├── __init__.py
│       ├── git.py          # Git operations
│       ├── process.py      # Process management
│       └── logging.py      # Logging configuration
├── web-ui/                  # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── InstanceGrid.tsx
│   │   │   ├── TaskBoard.tsx
│   │   │   ├── WorktreeMap.tsx
│   │   │   └── LogViewer.tsx
│   │   ├── services/
│   │   │   ├── api.ts      # REST API client
│   │   │   └── websocket.ts # WebSocket client
│   │   ├── types/
│   │   │   └── index.ts    # TypeScript type definitions
│   │   ├── utils/
│   │   │   └── helpers.ts  # Utility functions
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── tests/                   # Test suites
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/                    # Documentation
├── examples/                # Example workflows
├── pyproject.toml
├── README.md
└── .gitignore
```

## Key Design Decisions

### 1. SQLite for State Management
**Rationale**: Lightweight, no external dependencies, ACID compliance
- **Schema**: instances, tasks, worktrees, configurations
- **Backup**: File-based, easy to version control
- **Migration**: Simple schema evolution with alembic-like migrations

### 2. Tmux for Session Persistence
**Rationale**: Battle-tested, survives disconnections, team collaboration
- **Layout**: Main session + per-instance sessions
- **Integration**: Python libtmux library for programmatic control
- **Naming**: Consistent session naming with cc-orchestrator prefix

#### Tmux Session Management Architecture
The tmux integration provides comprehensive session lifecycle management:

**Core Components:**
- **TmuxService**: Main service class for session operations
- **SessionConfig**: Configuration object for session creation
- **LayoutTemplate**: Configurable window and pane layouts
- **Session Discovery**: Automatic detection of orphaned sessions

**Session Naming Convention:**
- Format: `cc-orchestrator-{instance-id}`
- Example: `cc-orchestrator-issue-15-worker`
- Prefix ensures easy identification and filtering

**Layout Templates:**
- **default**: Single window with shell
- **development**: Multi-window setup (editor, terminal, monitoring)
- **claude**: Optimized for Claude Code usage
- **custom**: User-defined layouts via CLI

**Lifecycle Management:**
1. **Creation**: Session with configured layout and environment
2. **Attachment**: Connect clients to persistent sessions
3. **Detachment**: Preserve sessions across disconnections
4. **Discovery**: Find and reconnect to existing sessions
5. **Cleanup**: Graceful termination and resource cleanup

**Multi-User Support:**
- Shared sessions for team collaboration
- Client tracking and management
- Concurrent access handling

**Integration Points:**
- **Process Manager**: Spawns Claude instances in tmux sessions
- **CLI Commands**: Full session management via command line
- **Web Interface**: Session status and control (future)
- **Database**: Session metadata persistence

### 3. FastAPI + WebSockets for Web Interface
**Rationale**: Modern async framework, automatic OpenAPI docs, WebSocket support
- **Real-time**: Bidirectional updates between backend and frontend
- **Authentication**: Optional OAuth for team environments
- **Performance**: Async/await for concurrent operations

### 4. Process Management Strategy
**Rationale**: Reliable spawning and monitoring of Claude Code instances
- **Claude Spawning**: subprocess with tmux session attachment
- **Health Monitoring**: Periodic health checks with auto-recovery
- **Resource Limits**: CPU/memory constraints per instance

### 5. Git Worktree Isolation
**Rationale**: Complete isolation between concurrent development streams
- **Branch Strategy**: Feature branches from main/develop
- **Cleanup**: Automatic removal of completed/stale worktrees
- **Safety**: Prevent accidental cross-contamination

## Data Models

### Instance
```python
@dataclass
class Instance:
    id: str
    task_id: Optional[str]
    worktree_path: str
    tmux_session: str
    status: InstanceStatus  # STARTING, RUNNING, IDLE, ERROR, STOPPED
    pid: Optional[int]
    created_at: datetime
    last_activity: datetime
    resource_usage: ResourceUsage
```

### Task
```python
@dataclass
class Task:
    id: str
    title: str
    description: str
    source: str  # github, jira, manual
    source_id: str
    status: TaskStatus  # PENDING, ASSIGNED, IN_PROGRESS, REVIEW, DONE
    assigned_instance: Optional[str]
    priority: Priority  # HIGH, MEDIUM, LOW
    created_at: datetime
    updated_at: datetime
    dependencies: List[str]  # Task IDs this depends on
```

### Worktree
```python
@dataclass
class Worktree:
    path: str
    branch: str
    base_branch: str
    instance_id: Optional[str]
    created_at: datetime
    last_commit: str
    status: WorktreeStatus  # ACTIVE, IDLE, STALE, CLEANUP_PENDING
```

### Configuration
```python
@dataclass
class Configuration:
    max_instances: int = 5
    tmux_enabled: bool = True
    web_enabled: bool = True
    web_port: int = 8080
    log_level: str = "INFO"
    github_token: Optional[str] = None
    jira_url: Optional[str] = None
    jira_token: Optional[str] = None
```

## Database Schema

### SQLite Tables
```sql
CREATE TABLE instances (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    worktree_path TEXT NOT NULL,
    tmux_session TEXT NOT NULL,
    status TEXT NOT NULL,
    pid INTEGER,
    created_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks (id)
);

CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    status TEXT NOT NULL,
    assigned_instance TEXT,
    priority TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (assigned_instance) REFERENCES instances (id)
);

CREATE TABLE worktrees (
    path TEXT PRIMARY KEY,
    branch TEXT NOT NULL,
    base_branch TEXT NOT NULL,
    instance_id TEXT,
    created_at TIMESTAMP NOT NULL,
    last_commit TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (instance_id) REFERENCES instances (id)
);

CREATE TABLE configurations (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

## API Design

### REST Endpoints
```
GET /api/instances          # List all instances
POST /api/instances         # Create new instance
GET /api/instances/{id}     # Get instance details
PUT /api/instances/{id}     # Update instance
DELETE /api/instances/{id}  # Stop and remove instance

GET /api/tasks              # List all tasks
POST /api/tasks             # Create new task
GET /api/tasks/{id}         # Get task details
PUT /api/tasks/{id}         # Update task
DELETE /api/tasks/{id}      # Delete task

GET /api/worktrees          # List all worktrees
POST /api/worktrees         # Create new worktree
DELETE /api/worktrees/{path} # Clean up worktree

GET /api/config             # Get configuration
PUT /api/config             # Update configuration
```

### WebSocket Events
```json
// Instance status updates
{
  "type": "instance_status",
  "instance_id": "claude-123",
  "status": "RUNNING",
  "resource_usage": {...}
}

// Task updates
{
  "type": "task_update",
  "task_id": "TASK-456",
  "status": "IN_PROGRESS",
  "assigned_instance": "claude-123"
}

// Log messages
{
  "type": "log_message",
  "instance_id": "claude-123",
  "level": "INFO",
  "message": "Starting task execution",
  "timestamp": "2025-07-27T10:30:00Z"
}
```

## Security Considerations

### API Security
- Optional authentication via OAuth providers (GitHub, Google)
- API keys for programmatic access
- CORS configuration for web interface
- Rate limiting on API endpoints

### Secret Management
- Environment variables for tokens and secrets
- No secrets stored in database or config files
- Secure token storage using system keyring when available

### Process Isolation
- Each Claude instance runs in separate tmux session
- Worktree isolation prevents cross-contamination
- Resource limits prevent runaway processes

## Performance Considerations

### Database Optimization
- Indexes on frequently queried columns
- Connection pooling for concurrent access
- Periodic cleanup of old records
- Database vacuum for maintenance

### Memory Management
- Lazy loading of large datasets
- Pagination for API responses
- Efficient WebSocket message handling
- Resource monitoring and alerting

### Scalability
- Async/await for I/O operations
- Connection limits for external APIs
- Configurable concurrency limits
- Horizontal scaling considerations for future
