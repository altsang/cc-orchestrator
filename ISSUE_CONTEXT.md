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

# Issue #59: Fix Instance Persistence - Complete Integration Implementation (REOPENED)
See: https://github.com/altsang/cc-orchestrator/issues/59

Focus: 🚨 CRITICAL REGRESSION - Database persistence is completely broken despite previous "completion". Instance management fails with database sync errors.

## Current Status
- **Issue**: #59 - Fix Instance Persistence - Complete Integration Implementation
- **Status**: 🚨 **REOPENED** (Critical regression - database persistence still broken)
- **Branch**: feature/issue-59-database-persistence-fix
- **Worktree**: ~/workspace/cc-orchestrator-issue-59-fix
- **Priority**: CRITICAL (Phase 2 completely blocked)
- **Labels**: feature, phase-2, priority-critical, integration-debt, regression

## 🚨 CRITICAL PROBLEM DISCOVERED IN TESTING

### **Actual Error Output**
```bash
cc-orchestrator instances start 100
# Output:
Failed to sync instance state to database
ERROR: Instance started but will NOT survive system restart!
This is a critical issue - contact system administrator
Successfully started Claude instance for issue 100
Failed to register instance with health monitor
Process no longer exists for database instance, marking as stopped
```

### **Persistence Test Failure**
```bash
cc-orchestrator instances list
# Output: No active instances found.
```

### **Root Cause Analysis**
Despite Issue #59 being marked "completed" and PR #61 being merged, the database integration was never properly implemented. The Orchestrator class is still failing to:
1. Sync instance state to database
2. Register instances with health monitor
3. Persist instances across CLI command invocations

## Technical Requirements (Issue #59 - CRITICAL FIX)

### **CRITICAL FIXES REQUIRED**
1. **Database Connection Implementation** (CRITICAL)
   - Fix Orchestrator.initialize() to properly connect to database
   - Implement proper database session management
   - Replace memory-only storage with database persistence

2. **Instance State Synchronization** (CRITICAL)
   - Fix "Failed to sync instance state to database" error
   - Implement proper InstanceCRUD integration in Orchestrator
   - Ensure instances are saved to database on creation

3. **Health Monitor Integration** (HIGH PRIORITY)
   - Fix "Failed to register instance with health monitor" error
   - Implement proper process tracking in database
   - Ensure health status is properly maintained

4. **Cross-Session Persistence** (CRITICAL)
   - Ensure instances persist across separate CLI command invocations
   - Load existing instances from database on Orchestrator initialization
   - Test complete lifecycle: start → list → stop → list

## Acceptance Criteria (Issue #59) - CRITICAL TESTS
- [ ] `cc-orchestrator instances start 999` succeeds without database errors
- [ ] `cc-orchestrator instances list` shows created instances (NOT "No active instances found")
- [ ] Instances persist across separate CLI command invocations
- [ ] Health monitor registration works without errors
- [ ] Instance stop/start lifecycle works correctly

## MANDATORY Testing Requirements
```bash
# CRITICAL TEST - Must work after fix:
cc-orchestrator instances start 999
cc-orchestrator instances list    # Must show instance 999
cc-orchestrator instances stop 999
cc-orchestrator instances list    # Must show no instances

# Cross-session persistence test:
cc-orchestrator instances start 888
cc-orchestrator instances start 777
cc-orchestrator instances list    # Must show both instances
# Exit and restart CLI
cc-orchestrator instances list    # Must still show both instances
```

## Current State (Issue #59)
🚨 **CRITICAL REGRESSION** - Ready for immediate remediation:
- Git worktree created at ~/workspace/cc-orchestrator-issue-59-fix
- Tmux session ready: cc-orchestrator-issue-59-fix
- Critical database persistence failure confirmed during testing
- Previous "completion" was invalid - core functionality is broken

## Key Files Requiring Implementation
- `src/cc_orchestrator/core/orchestrator.py` - Database integration missing
- `src/cc_orchestrator/cli/instances.py` - Instance persistence broken
- Database connection and session management code
- Health monitoring integration

## Worker 1 Assignment
**Priority**: CRITICAL - This blocks all Phase 2 functionality
**Task**: Implement the database persistence that was supposed to be completed previously
**Environment**: Ready for immediate development work

This issue represents a **critical regression** where supposedly completed functionality is completely broken and unusable.
