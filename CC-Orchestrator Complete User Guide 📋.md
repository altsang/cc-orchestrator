CC-Orchestrator Complete User Guide 📋

  🚀 Installation & Setup

  cd ~/workspace/cc-orchestrator
  pip install -e .

  # Optional: Set up web interface
  export JWT_SECRET_KEY="your-secret-key-change-in-production"

  📝 CLI Commands Reference

  Main Command Structure

  cc-orchestrator [OPTIONS] COMMAND [ARGS]...

  # Global Options:
  --version                  # Show version
  --config TEXT             # Custom config file path
  --profile TEXT            # Configuration profile
  --verbose, -v             # Enable verbose output
  --quiet, -q               # Suppress output
  --json                    # JSON output format
  --max-instances INTEGER   # Override max instances
  --web-port INTEGER        # Override web port
  --web-host TEXT           # Override web host
  --log-level TEXT          # Override log level
  --worktree-base-path TEXT # Override worktree path
  --cpu-threshold FLOAT     # Override CPU threshold
  --memory-limit INTEGER    # Override memory limit

  ---
  ⚙️ Configuration Management

  # View current configuration
  cc-orchestrator config show

  # Get specific config value
  cc-orchestrator config get max_instances
  cc-orchestrator config get web_port

  # Set configuration values
  cc-orchestrator config set max_instances 10
  cc-orchestrator config set web_port 9000
  cc-orchestrator config set log_level DEBUG

  # Initialize config file with defaults
  cc-orchestrator config init

  # Show where config files are searched
  cc-orchestrator config locations

  # List available profiles
  cc-orchestrator config profiles

  # Validate current configuration
  cc-orchestrator config validate

  ---
  🖥️ Instance Management

  # List all instances
  cc-orchestrator instances list
  cc-orchestrator instances status
  cc-orchestrator instances status --json

  # Start new Claude instance
  cc-orchestrator instances start PROJECT_NAME
  cc-orchestrator instances start my-project --json
  cc-orchestrator instances start issue-123 --workspace /custom/path
  cc-orchestrator instances start feature-auth --branch feature/authentication
  cc-orchestrator instances start debug-session --tmux-session debug-env

  # Stop instance
  cc-orchestrator instances stop PROJECT_NAME
  cc-orchestrator instances stop my-project

  # Example complete workflow
  cc-orchestrator instances start web-redesign --json
  cc-orchestrator instances status --json
  cc-orchestrator instances stop web-redesign

  ---
  🌳 Git Worktree Management

  # List all worktrees
  cc-orchestrator worktrees list
  cc-orchestrator worktrees list --format json
  cc-orchestrator worktrees list --no-sync  # Skip git sync

  # Create new worktree
  cc-orchestrator worktrees create NAME BRANCH_NAME
  cc-orchestrator worktrees create feature-login feature/user-login
  cc-orchestrator worktrees create bugfix-auth bugfix/auth-issue
  cc-orchestrator worktrees create hotfix-security hotfix/security-patch

  # Create with custom options
  cc-orchestrator worktrees create my-feature feature/new-ui \
    --path /custom/path \
    --from-branch develop \
    --instance-id 123 \
    --force

  # Get worktree status
  cc-orchestrator worktrees status WORKTREE_NAME
  cc-orchestrator worktrees status feature-login

  # Remove worktree
  cc-orchestrator worktrees remove WORKTREE_NAME
  cc-orchestrator worktrees remove feature-login

  # Clean up stale worktree references
  cc-orchestrator worktrees cleanup

  ---
  🖼️ Tmux Session Management

  # List all tmux sessions
  cc-orchestrator tmux list

  # View available layout templates
  cc-orchestrator tmux templates

  # Create tmux session
  cc-orchestrator tmux create SESSION_NAME WORKING_DIR --instance-id ID
  cc-orchestrator tmux create dev-session /path/to/workspace --instance-id 1
  cc-orchestrator tmux create auth-work /tmp/auth-env --instance-id 2 --layout development
  cc-orchestrator tmux create claude-env /workspace/project --instance-id 3 --layout claude

  # Create with environment variables
  cc-orchestrator tmux create api-dev /api/workspace --instance-id 4 \
    --env "DEBUG=true" \
    --env "PORT=3000" \
    --auto-attach

  # Attach to session
  cc-orchestrator tmux attach SESSION_NAME
  cc-orchestrator tmux attach dev-session

  # Detach from session
  cc-orchestrator tmux detach SESSION_NAME

  # Get session info
  cc-orchestrator tmux info SESSION_NAME
  cc-orchestrator tmux info dev-session

  # Destroy session
  cc-orchestrator tmux destroy SESSION_NAME
  cc-orchestrator tmux destroy dev-session

  # Clean up sessions
  cc-orchestrator tmux cleanup
  cc-orchestrator tmux cleanup --instance-id 123
  cc-orchestrator tmux cleanup --force

  # Add custom layout template
  cc-orchestrator tmux add-template TEMPLATE_NAME DESCRIPTION

  Available Layout Templates:

  - default: Single window with default shell
  - development: Multiple windows (editor, terminal, monitoring)
  - claude: Claude Code optimized layout

  ---
  📋 Task Management

  # List tasks
  cc-orchestrator tasks list

  # Show task details
  cc-orchestrator tasks show TASK_ID
  cc-orchestrator tasks show 123

  # Assign task to instance
  cc-orchestrator tasks assign TASK_ID INSTANCE_ID
  cc-orchestrator tasks assign 123 my-project

  ---
  🌐 Web Interface Control

  # Start web interface
  cc-orchestrator web start
  cc-orchestrator web start --port 8080
  cc-orchestrator web start --host 0.0.0.0 --port 9000
  cc-orchestrator web start --port 8080 --reload  # Development mode

  # Check web interface status
  cc-orchestrator web status

  # Stop web interface
  cc-orchestrator web stop

  ---
  🌐 Web Interface & Dashboards

  Once the web server is running, you can access:

  Main Web Dashboard

  http://localhost:8080/

  API Documentation

  # Interactive API docs (Swagger UI)
  http://localhost:8080/docs

  # Alternative API docs (ReDoc)
  http://localhost:8080/redoc

  API Endpoints

  Health & Status

  # API health check
  curl http://localhost:8080/api/v1/health/

  # System health with details
  curl http://localhost:8080/api/v1/health/system

  Instance Management API

  # List all instances
  curl http://localhost:8080/api/v1/instances/

  # Get specific instance
  curl http://localhost:8080/api/v1/instances/my-project

  # Create new instance
  curl -X POST http://localhost:8080/api/v1/instances/ \
    -H "Content-Type: application/json" \
    -d '{"issue_id": "test-api", "workspace_path": "/tmp/test"}'

  # Stop instance
  curl -X DELETE http://localhost:8080/api/v1/instances/my-project

  # Get instance health
  curl http://localhost:8080/api/v1/instances/my-project/health

  Configuration API

  # Get configuration
  curl http://localhost:8080/api/v1/config/

  # Update configuration
  curl -X PUT http://localhost:8080/api/v1/config/ \
    -H "Content-Type: application/json" \
    -d '{"max_instances": 10, "web_port": 9000}'

  # Validate configuration
  curl -X POST http://localhost:8080/api/v1/config/validate

  Worktree Management API

  # List worktrees
  curl http://localhost:8080/api/v1/worktrees/

  # Create worktree
  curl -X POST http://localhost:8080/api/v1/worktrees/ \
    -H "Content-Type: application/json" \
    -d '{"name": "api-test", "branch_name": "feature/api-test"}'

  # Delete worktree
  curl -X DELETE http://localhost:8080/api/v1/worktrees/api-test

  Log Management API

  # Search logs
  curl "http://localhost:8080/api/v1/logs/search?query=error&limit=10"

  # Export logs
  curl -X POST http://localhost:8080/api/v1/logs/export \
    -H "Content-Type: application/json" \
    -d '{"format": "json", "include_metadata": true}'

  # Get log statistics
  curl http://localhost:8080/api/v1/logs/stats

  # Get available log levels
  curl http://localhost:8080/api/v1/logs/levels

  # Get log contexts
  curl http://localhost:8080/api/v1/logs/contexts

  Task Management API

  # List tasks
  curl http://localhost:8080/api/v1/tasks/

  # Create task
  curl -X POST http://localhost:8080/api/v1/tasks/ \
    -H "Content-Type: application/json" \
    -d '{"title": "Test Task", "description": "API test task"}'

  # Update task
  curl -X PUT http://localhost:8080/api/v1/tasks/123 \
    -H "Content-Type: application/json" \
    -d '{"status": "completed"}'

  WebSocket Endpoints

  // Real-time instance updates
  ws://localhost:8080/ws/instances

  // Real-time log streaming
  ws://localhost:8080/ws/logs

  // Real-time system health
  ws://localhost:8080/ws/health

  ---
  📊 Real-World Usage Examples

  Example 1: Complete Development Setup

  # Set up development environment for new feature
  cc-orchestrator config set max_instances 3
  cc-orchestrator worktrees create auth-feature feature/user-authentication
  cc-orchestrator instances start auth-dev --workspace ./cc-orchestrator-auth-feature
  mkdir -p /tmp/auth-workspace
  cc-orchestrator tmux create auth-session /tmp/auth-workspace --instance-id 1 --layout development

  # Check everything is running
  cc-orchestrator instances status
  cc-orchestrator tmux list

  Example 2: Multi-Project Orchestration

  # Start multiple projects
  cc-orchestrator instances start frontend-redesign
  cc-orchestrator instances start backend-api
  cc-orchestrator instances start mobile-app

  # Create worktrees for each
  cc-orchestrator worktrees create frontend feature/new-ui
  cc-orchestrator worktrees create backend feature/api-v2
  cc-orchestrator worktrees create mobile feature/ios-update

  # Monitor all instances
  cc-orchestrator instances status --json

  Example 3: Web Dashboard Usage

  # Start web interface
  export JWT_SECRET_KEY="development-secret-key"
  cc-orchestrator web start --port 8080 --reload

  # Access in browser:
  # http://localhost:8080/          # Main dashboard
  # http://localhost:8080/docs      # API documentation
  # http://localhost:8080/redoc     # Alternative API docs

  Example 4: Debugging & Monitoring

  # Verbose mode for debugging
  cc-orchestrator --verbose instances start debug-session

  # JSON output for scripts
  cc-orchestrator --json instances status > instances.json

  # Monitor specific instance
  cc-orchestrator instances status debug-session

  ---
  🔧 Troubleshooting Commands

  # Validate configuration
  cc-orchestrator config validate

  # Clean up stale references
  cc-orchestrator worktrees cleanup
  cc-orchestrator tmux cleanup

  # Check system status
  cc-orchestrator --version
  cc-orchestrator config show

  # Debug mode
  cc-orchestrator --verbose --log-level DEBUG instances status

  ---
  📈 Available Dashboards & UIs

  1. Main Dashboard: http://localhost:8080/
    - Instance overview
    - Real-time status monitoring
    - Resource usage graphs
  2. API Documentation: http://localhost:8080/docs
    - Interactive Swagger UI
    - Test API endpoints directly
    - Full API reference
  3. Task Board: http://localhost:8080/tasks (when implemented)
    - Drag-and-drop task management
    - Progress visualization
    - Team collaboration
  4. Log Viewer: http://localhost:8080/logs (when implemented)
    - Real-time log streaming
    - Search and filtering
    - Export capabilities

  This guide covers 100% of the available CLI functionality and all accessible web interfaces in CC-Orchestrator!