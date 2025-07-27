#!/bin/bash
# File: manage-3-claude-instances.sh
# Manage 3 parallel Claude Code instances for Phase 1 development

case $1 in
  "setup")
    echo "Setting up 3-instance parallel development environment..."
    
    # Create worktrees
    echo "Creating git worktrees..."
    git worktree add ../cc-orchestrator-issue-7 -b feature/project-setup
    git worktree add ../cc-orchestrator-issue-11 -b feature/logging-system
    git worktree add ../cc-orchestrator-issue-12 -b feature/test-framework
    
    # Create tmux sessions
    echo "Creating tmux sessions..."
    tmux new-session -d -s claude-issue-7 -c ~/workspace/cc-orchestrator-issue-7
    tmux new-session -d -s claude-issue-11 -c ~/workspace/cc-orchestrator-issue-11
    tmux new-session -d -s claude-issue-12 -c ~/workspace/cc-orchestrator-issue-12
    
    # Copy issue context to each worktree
    echo "Setting up issue context..."
    echo "# Issue #7: Project setup with pyproject.toml and dependencies
See: https://github.com/altsang/cc-orchestrator/issues/7

Focus: Set up Python project structure with modern tooling including pyproject.toml, 
dependency management, and development tools." > ../cc-orchestrator-issue-7/ISSUE_CONTEXT.md
    
    echo "# Issue #11: Basic logging and error handling setup  
See: https://github.com/altsang/cc-orchestrator/issues/11

Focus: Set up comprehensive logging system and error handling framework 
for the orchestrator." > ../cc-orchestrator-issue-11/ISSUE_CONTEXT.md
    
    echo "# Issue #12: Unit test framework setup
See: https://github.com/altsang/cc-orchestrator/issues/12

Focus: Configure comprehensive testing framework with pytest, coverage 
reporting, and test utilities." > ../cc-orchestrator-issue-12/ISSUE_CONTEXT.md
    
    echo "Setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Run: $0 launch"
    echo "2. Use: $0 attach [7|11|12] to connect to specific instances"
    echo "3. Update GitHub issues manually to 'In Progress' status"
    ;;
    
  "status")
    echo "=== Active Claude Instances ==="
    echo "Issue #7 (Project Setup):   $(tmux list-sessions 2>/dev/null | grep claude-issue-7 || echo 'Not running')"
    echo "Issue #11 (Logging):        $(tmux list-sessions 2>/dev/null | grep claude-issue-11 || echo 'Not running')" 
    echo "Issue #12 (Test Framework): $(tmux list-sessions 2>/dev/null | grep claude-issue-12 || echo 'Not running')"
    echo ""
    echo "=== Git Worktrees ==="
    git worktree list
    echo ""
    echo "=== GitHub Issues Status ==="
    echo "Update these manually on GitHub:"
    echo "- Issue #7: https://github.com/altsang/cc-orchestrator/issues/7"
    echo "- Issue #11: https://github.com/altsang/cc-orchestrator/issues/11"
    echo "- Issue #12: https://github.com/altsang/cc-orchestrator/issues/12"
    ;;
    
  "attach")
    case $2 in
      "7"|"project") 
        echo "Attaching to Issue #7 (Project Setup)..."
        tmux attach -t claude-issue-7 ;;
      "11"|"logging") 
        echo "Attaching to Issue #11 (Logging System)..."
        tmux attach -t claude-issue-11 ;;
      "12"|"test") 
        echo "Attaching to Issue #12 (Test Framework)..."
        tmux attach -t claude-issue-12 ;;
      *) 
        echo "Usage: $0 attach [7|11|12]"
        echo "  7  - Project Setup (Critical Path)"
        echo "  11 - Logging System" 
        echo "  12 - Test Framework"
        ;;
    esac
    ;;
    
  "launch")
    echo "Launching all 3 Claude instances..."
    if tmux has-session -t claude-issue-7 2>/dev/null; then
      tmux send-keys -t claude-issue-7 'claude --continue' Enter
      echo "✓ Launched Claude in Issue #7 session"
    else
      echo "✗ Issue #7 tmux session not found"
    fi
    
    if tmux has-session -t claude-issue-11 2>/dev/null; then
      tmux send-keys -t claude-issue-11 'claude --continue' Enter
      echo "✓ Launched Claude in Issue #11 session"
    else
      echo "✗ Issue #11 tmux session not found"
    fi
    
    if tmux has-session -t claude-issue-12 2>/dev/null; then
      tmux send-keys -t claude-issue-12 'claude --continue' Enter
      echo "✓ Launched Claude in Issue #12 session"
    else
      echo "✗ Issue #12 tmux session not found"
    fi
    echo "All instances launched!"
    ;;
    
  "cleanup")
    echo "Cleaning up parallel development environment..."
    
    # Kill tmux sessions
    tmux kill-session -t claude-issue-7 2>/dev/null && echo "✓ Killed claude-issue-7 session"
    tmux kill-session -t claude-issue-11 2>/dev/null && echo "✓ Killed claude-issue-11 session"
    tmux kill-session -t claude-issue-12 2>/dev/null && echo "✓ Killed claude-issue-12 session"
    
    # Note: Don't auto-remove worktrees as they may have uncommitted work
    echo ""
    echo "Tmux sessions cleaned up."
    echo "Git worktrees preserved (may contain uncommitted work):"
    git worktree list
    echo ""
    echo "To remove worktrees after merging branches:"
    echo "  git worktree remove ../cc-orchestrator-issue-7"
    echo "  git worktree remove ../cc-orchestrator-issue-11" 
    echo "  git worktree remove ../cc-orchestrator-issue-12"
    ;;
    
  "github-update")
    echo "GitHub Project Board Update Instructions:"
    echo ""
    echo "Manually update these issues to 'In Progress' status:"
    echo "1. Go to: https://github.com/altsang/cc-orchestrator/projects"
    echo "2. Open 'CC-Orchestrator Development' project"
    echo "3. Move these issues to 'In Progress' column:"
    echo "   - Issue #7: Project setup with pyproject.toml and dependencies"
    echo "   - Issue #11: Basic logging and error handling setup"
    echo "   - Issue #12: Unit test framework setup"
    echo ""
    echo "Or update via issue pages:"
    echo "- https://github.com/altsang/cc-orchestrator/issues/7"
    echo "- https://github.com/altsang/cc-orchestrator/issues/11"
    echo "- https://github.com/altsang/cc-orchestrator/issues/12"
    ;;
    
  *)
    echo "Usage: $0 {setup|status|attach|launch|cleanup|github-update}"
    echo ""
    echo "Commands:"
    echo "  setup         - Create worktrees and tmux sessions for 3 instances"
    echo "  status        - Show status of instances and worktrees"
    echo "  attach [7|11|12] - Attach to specific Claude instance"
    echo "  launch        - Launch Claude Code in all 3 sessions"
    echo "  cleanup       - Clean up tmux sessions (preserve worktrees)"
    echo "  github-update - Show instructions for updating GitHub project board"
    echo ""
    echo "Workflow:"
    echo "1. $0 setup     # Set up parallel environment"
    echo "2. $0 launch    # Start all Claude instances"
    echo "3. $0 github-update # Update GitHub project board"
    echo "4. $0 attach 7  # Work with specific instance"
    ;;
esac