# Issue #8: CLI framework implementation with Click
See: https://github.com/altsang/cc-orchestrator/issues/8

Focus: Implement the main CLI framework using Click with command groups for different orchestrator functions.

## Current Status
- **Issue**: #8 - CLI framework implementation with Click
- **Status**: ✅ COMPLETED (GitHub issue closed)
- **Branch**: feature/issue-8-cli-framework
- **Worktree**: ~/workspace/cc-orchestrator-issue-8

# Issue #9: SQLite database schema and models
See: https://github.com/altsang/cc-orchestrator/issues/9

Focus: Design and implement SQLite database schema for storing instances, tasks, worktrees, and configuration state.

## Current Status
- **Issue**: #9 - SQLite database schema and models
- **Status**: ✅ COMPLETED (GitHub issue closed)
- **Branch**: feature/issue-9-database-schema
- **Worktree**: ~/workspace/cc-orchestrator-issue-9
- **Priority**: High (Phase 1)
- **Dependencies**: Project setup (#7) ✅ COMPLETED

## Technical Requirements (Issue #8)
- Click framework for CLI commands
- Command groups: instances, tasks, worktrees, config, web
- Help system with comprehensive documentation
- Configuration file and environment variable support
- Output formatting (human-readable and JSON)

## Acceptance Criteria (Issue #8)
- [x] Main CLI entry point cc-orchestrator works
- [x] Command groups implemented: instances, tasks, worktrees, config, web
- [x] Help text comprehensive for all commands
- [x] Supports both config files and environment variables
- [x] Error handling with clear user messages
- [x] Output can be formatted as JSON for automation

## Current State (Issue #8)
✅ **COMPLETED** - Full CLI framework implementation:
- Main CLI entry point with comprehensive help and options
- Complete command group structure: instances, tasks, worktrees, config, web
- Configuration loading from files and environment variables
- JSON and human-readable output formatting
- Comprehensive test suite with unit and integration tests
- Error handling with clear user messages

## Technical Requirements (Issue #9)
- SQLite database with proper schema design
- Tables: instances, tasks, worktrees, configurations
- Database migrations support
- CRUD operations for all entities
- Transaction support for data consistency

## Acceptance Criteria (Issue #9)
- [x] Database schema created with all required tables
- [x] Database models/classes for each entity
- [x] Migration system for schema updates
- [x] Basic CRUD operations implemented
- [x] Database connection pooling and error handling
- [x] Data validation and constraints enforced

## Current State (Issue #9)
✅ **COMPLETED** - Full database implementation:
- Complete SQLAlchemy models for instances, tasks, worktrees, and configurations
- Database connection management with pooling and transaction handling
- Migration system with versioning and initial schema migration
- Comprehensive CRUD operations with validation and error handling
- Performance optimizations with strategic indexes
- 60 comprehensive tests (46 unit + 14 integration) all passing
- Hierarchical configuration system with scope precedence
- Data integrity with foreign key constraints and cascade deletes

# Issue #10: Configuration management system
See: https://github.com/altsang/cc-orchestrator/issues/10

Focus: Implement hierarchical configuration management with validation, file generation, and enhanced environment variable support.

## Current Status
- **Issue**: #10 - Configuration management system
- **Status**: 🚧 IN PROGRESS (GitHub project board updated)
- **Branch**: feature/issue-10-configuration-management
- **Worktree**: ~/workspace/cc-orchestrator-issue-10
- **Priority**: High (Phase 1)
- **Dependencies**: Project setup (#7) ✅ COMPLETED, CLI framework (#8) ✅ COMPLETED, Database schema (#9) ✅ COMPLETED

## Technical Requirements (Issue #10)
- Hierarchical configuration loading (Global → User → Project → Instance)
- Enhanced validation with detailed error messages
- Configuration file generation and initialization via CLI
- Improved environment variable handling and documentation
- Configuration schema validation with Pydantic
- Support for configuration inheritance and overrides

## Acceptance Criteria (Issue #10)
- [ ] Hierarchical config loading with proper precedence
- [ ] CLI commands for config init, validate, show, and get
- [ ] Enhanced error messages for configuration issues
- [ ] Environment variable documentation and validation
- [ ] Configuration file templates and generation
- [ ] Comprehensive test suite for config management

## Current State (Issue #10)
🚧 **IN PROGRESS** - Setting up development environment:
- Git worktree created at ~/workspace/cc-orchestrator-issue-10
- GitHub project board updated to "In Progress" status
- Basic configuration loading exists in config/loader.py
- Ready to enhance and expand configuration management system

## Related Issues
- Part of epic: Phase 1 Epic (#1)
- Depends on: Project setup (#7) ✅ COMPLETED
- Depends on: CLI framework (#8) ✅ COMPLETED
- Depends on: Database schema (#9) ✅ COMPLETED
- Issue #8 blocks: Configuration management system (#10) 🚧 IN PROGRESS
- Issue #9 blocks: Instance and task management features

## Development Plan (Issue #8)
1. ✅ Expand CLI command structure with proper groups
2. ✅ Implement comprehensive help and error handling
3. ✅ Add configuration file support
4. ✅ Add JSON output formatting
5. ✅ Create comprehensive test suite
6. ✅ Update documentation

## Development Plan (Issue #9)
1. ✅ Design database schema for core entities
2. ✅ Implement SQLAlchemy models and relationships
3. ✅ Create database connection and session management
4. ✅ Implement migration system for schema versioning
5. ✅ Add CRUD operations and data validation
6. ✅ Create comprehensive test suite
7. ✅ Update documentation

## Testing Requirements (Issue #8)
- ✅ Unit tests for all CLI commands
- ✅ Integration tests for command workflows
- ✅ Test help text and error messages
- ✅ Test configuration file loading
- ✅ Test output formatting options

## Testing Requirements (Issue #9)
- ✅ Unit tests for all database models (14 tests)
- ✅ Integration tests for CRUD operations (32 tests)
- ✅ Test database migrations and versioning (5 tests)
- ✅ Test data validation and constraints (9 tests)
- ✅ Test connection handling and error cases (included)

**Total: 60 comprehensive tests, all passing**

## Key Files (Issue #8)
- `src/cc_orchestrator/cli/main.py` - Main CLI entry point
- `src/cc_orchestrator/cli/` - Command group modules
- `tests/unit/test_cli.py` - CLI unit tests
- `tests/integration/` - CLI integration tests

## Key Files (Issue #9)
- `src/cc_orchestrator/database/models.py` - SQLAlchemy models
- `src/cc_orchestrator/database/schema.py` - Database schema definition
- `src/cc_orchestrator/database/connection.py` - Database connection management
- `src/cc_orchestrator/database/migrations/` - Migration scripts
- `tests/unit/test_database.py` - Database unit tests
- `tests/integration/test_database_integration.py` - Database integration tests

## Schema Design Considerations
### Core Entities
- **Instances**: Claude Code instances with status, configuration, git info
- **Tasks**: Work items with status, priority, assignment to instances
- **Worktrees**: Git worktree management with paths, branches, status
- **Configurations**: System and user configuration settings

### Relationships
- Instances can have multiple tasks assigned
- Tasks are associated with specific worktrees
- Worktrees track git branch and workspace information
- Configurations support hierarchical overrides

### Performance Requirements
- Fast queries for instance status and task assignment
- Efficient filtering and sorting for dashboard views
- Proper indexing for commonly accessed data

# Issue #62: Fix tmux session layout template variable substitution
See: https://github.com/altsang/cc-orchestrator/issues/62

Focus: CRITICAL tmux integration bug - Template variable substitution failure prevents tmux session creation, blocking Phase 2 tmux functionality.

## Current Status
- **Issue**: #62 - Fix tmux session layout template variable substitution
- **Status**: 🚧 IN PROGRESS (tmux integration bug fix)
- **Branch**: feature/issue-62-fix-tmux-template-variables
- **Worktree**: ~/workspace/cc-orchestrator-issue-62
- **Priority**: High (Phase 2 functionality blocker)
- **Labels**: bug, phase-2, priority-high, tmux

## 🐛 TMUX INTEGRATION BUG DISCOVERED

### Root Cause Analysis
**Primary Issue**: Template variable substitution in tmux session creation
```
Error: Failed to apply layout template - cc-orchestrator-test-session (template: default): ["can't find session: $18"]
```

**Problem**: Variables like `$18` are not being properly replaced with actual session references before being sent to tmux commands.

**Discovery Context**: Found during comprehensive integration audit post-Issue #59 resolution

**Command that fails**:
```bash
cc-orchestrator tmux create --instance-id 999 test-session /path/to/workspace
```

### Technical Requirements (Issue #62)

### CRITICAL FIXES REQUIRED
1. **Template Variable Substitution Engine** (CRITICAL)
   - Fix variable replacement in tmux layout templates
   - Ensure session ID variables are properly substituted
   - Verify template processing before sending to tmux

2. **Session Reference Validation** (HIGH PRIORITY)
   - Validate session references exist before applying templates
   - Improve error handling for template variable issues
   - Add debugging for template processing

3. **Integration Testing** (HIGH PRIORITY)
   - Add specific tests for tmux session creation with templates
   - Test template variable substitution mechanisms
   - Verify end-to-end tmux integration workflows

## Acceptance Criteria (Issue #62)
- [ ] `cc-orchestrator tmux create --instance-id 999 test-session /path/to/workspace` succeeds
- [ ] Template variables are properly substituted before tmux execution
- [ ] Session creation works with different layout templates
- [ ] Error handling provides clear feedback for template issues
- [ ] Integration tests cover tmux session creation workflows

## MANDATORY Testing Requirements
```bash
# Test 1: Basic session creation
cc-orchestrator tmux create --instance-id 123 test-session-1 /workspace/path

# Test 2: Session with different templates
cc-orchestrator tmux create --instance-id 124 test-session-2 /workspace/path --template custom

# Test 3: Session integration with instances
cc-orchestrator instances start 125
# Should properly create and integrate tmux session

# Test 4: Template variable verification
# Verify that session variables are substituted correctly in template processing
```

## Current State (Issue #62)
🚧 **IN PROGRESS** - Ready for manual development:
- Git worktree created at ~/workspace/cc-orchestrator-issue-62
- Tmux session ready: cc-orchestrator-issue-62
- Template variable substitution bug documented and prioritized
- Claude Code instance terminated - ready for manual work
- All context and requirements documented

## Key Files Requiring Investigation
- `src/cc_orchestrator/cli/tmux.py` - Main tmux CLI commands
- Template processing logic (layout template application)
- Session creation and variable substitution code
- Template configuration files

## Development Approach
1. **Analysis Phase**: Investigate template variable processing in tmux commands
2. **Root Cause**: Identify why `$18` and similar variables aren't being substituted
3. **Implementation**: Fix the template processing engine
4. **Testing**: Verify all mandatory test cases pass
5. **Integration**: Ensure end-to-end tmux workflows function

## Impact Assessment
- **BLOCKS**: Complete tmux integration functionality
- **AFFECTS**: Instance-to-tmux session workflow
- **FINAL COMPONENT**: Needed for complete Phase 2 integration

## Manual Development Instructions
To begin manual work on this issue:
```bash
# Navigate to the worktree
cd ~/workspace/cc-orchestrator-issue-62

# Attach to tmux session (optional)
tmux attach-session -t "cc-orchestrator-issue-62"

# Start manual development
# Focus on src/cc_orchestrator/cli/tmux.py and template processing
```

This issue represents the **final functional gap** in Phase 2 integration. Once resolved, Phase 2 will be truly complete with all components fully integrated.
