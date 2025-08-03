#!/usr/bin/env python3
"""
Example usage of the tmux session management functionality.

This example demonstrates how to use the tmux service programmatically
for managing Claude Code instances in persistent sessions.
"""

import asyncio
from pathlib import Path

from cc_orchestrator.tmux import (
    LayoutTemplate,
    SessionConfig,
    TmuxError,
    get_tmux_service,
)


async def basic_session_management():
    """Demonstrate basic session creation and management."""
    print("=== Basic Session Management ===")

    tmux_service = get_tmux_service()

    # Create a basic session configuration
    config = SessionConfig(
        session_name="example-basic",
        working_directory=Path.cwd(),
        instance_id="example-instance-1",
        layout_template="default",
        environment={"EXAMPLE_VAR": "demo_value"},
        auto_attach=False,
    )

    try:
        # Create the session
        print(f"Creating session '{config.session_name}'...")
        session_info = await tmux_service.create_session(config)
        print(f"✓ Session created: {session_info.session_name}")
        print(f"  Instance ID: {session_info.instance_id}")
        print(f"  Status: {session_info.status.value}")
        print(f"  Windows: {', '.join(session_info.windows)}")

        # Get session information
        info = await tmux_service.get_session_info("example-basic")
        if info:
            print(f"✓ Session info retrieved: {info.current_window} window active")

        # Simulate attaching and detaching
        print("Simulating attach/detach operations...")
        await tmux_service.attach_session("example-basic")
        await tmux_service.detach_session("example-basic")
        print("✓ Attach/detach operations completed")

        # Clean up
        print("Destroying session...")
        await tmux_service.destroy_session("example-basic")
        print("✓ Session destroyed")

    except TmuxError as e:
        print(f"✗ Error: {e}")


async def custom_layout_example():
    """Demonstrate custom layout template creation and usage."""
    print("\n=== Custom Layout Template ===")

    tmux_service = get_tmux_service()

    # Create a custom layout template
    custom_template = LayoutTemplate(
        name="development-example",
        description="Example development layout with multiple panes",
        windows=[
            {
                "name": "code",
                "command": "bash",
                "panes": [
                    {"command": "echo 'Editor pane ready'"},
                    {"command": "echo 'File browser pane'", "split": "vertical"},
                ],
            },
            {
                "name": "terminal",
                "command": "bash",
                "panes": [{"command": "echo 'Terminal ready for commands'"}],
            },
            {
                "name": "monitoring",
                "command": "bash",
                "panes": [
                    {"command": "echo 'System monitor'"},
                    {"command": "echo 'Log viewer'", "split": "horizontal"},
                ],
            },
        ],
    )

    # Add the custom template
    tmux_service.add_layout_template(custom_template)
    print(f"✓ Added custom template: {custom_template.name}")

    # Create session with custom template
    config = SessionConfig(
        session_name="example-custom",
        working_directory=Path.cwd(),
        instance_id="example-instance-2",
        layout_template="development-example",
    )

    try:
        session_info = await tmux_service.create_session(config)
        print(f"✓ Session created with custom layout: {session_info.session_name}")
        print(f"  Layout: {session_info.layout_template}")
        print(f"  Windows: {', '.join(session_info.windows)}")

        # Clean up
        await tmux_service.destroy_session("example-custom")
        print("✓ Custom layout session destroyed")

    except TmuxError as e:
        print(f"✗ Error: {e}")


async def multiple_sessions_example():
    """Demonstrate managing multiple sessions simultaneously."""
    print("\n=== Multiple Sessions Management ===")

    tmux_service = get_tmux_service()

    # Create multiple session configurations
    configs = [
        SessionConfig(
            session_name=f"multi-example-{i}",
            working_directory=Path.cwd(),
            instance_id=f"multi-instance-{i}",
            layout_template="claude" if i % 2 == 0 else "development",
            environment={"INSTANCE_NUM": str(i)},
        )
        for i in range(3)
    ]

    try:
        # Create all sessions
        print("Creating multiple sessions...")
        session_infos = []
        for config in configs:
            session_info = await tmux_service.create_session(config)
            session_infos.append(session_info)
            print(f"✓ Created: {session_info.session_name}")

        # List all sessions
        print("\nListing all sessions:")
        all_sessions = await tmux_service.list_sessions()
        multi_sessions = [s for s in all_sessions if "multi-example" in s.session_name]

        for session in multi_sessions:
            print(f"  • {session.session_name}")
            print(f"    Instance: {session.instance_id}")
            print(f"    Status: {session.status.value}")
            print(f"    Layout: {session.layout_template}")

        # Cleanup sessions by instance
        print("\nCleaning up sessions...")
        for i in range(3):
            cleaned = await tmux_service.cleanup_sessions(
                instance_id=f"multi-instance-{i}", force=True
            )
            print(f"✓ Cleaned up {cleaned} session(s) for instance {i}")

    except TmuxError as e:
        print(f"✗ Error: {e}")


async def session_discovery_example():
    """Demonstrate session discovery and orphan detection."""
    print("\n=== Session Discovery ===")

    tmux_service = get_tmux_service()

    # Create a session
    config = SessionConfig(
        session_name="discovery-example",
        working_directory=Path.cwd(),
        instance_id="discovery-instance",
        layout_template="default",
    )

    try:
        session_info = await tmux_service.create_session(config)
        print(f"✓ Created session: {session_info.session_name}")

        # Check if session exists
        exists = await tmux_service.session_exists("discovery-example")
        print(f"✓ Session exists check: {exists}")

        # List sessions with orphan detection
        print("Checking for orphaned sessions...")
        sessions = await tmux_service.list_sessions(include_orphaned=True)
        discovery_sessions = [s for s in sessions if "discovery" in s.session_name]

        if discovery_sessions:
            print(f"✓ Found {len(discovery_sessions)} discovery session(s)")

        # Clean up
        await tmux_service.destroy_session("discovery-example")
        print("✓ Discovery session destroyed")

    except TmuxError as e:
        print(f"✗ Error: {e}")


async def error_handling_example():
    """Demonstrate error handling scenarios."""
    print("\n=== Error Handling ===")

    tmux_service = get_tmux_service()

    config = SessionConfig(
        session_name="error-example",
        working_directory=Path.cwd(),
        instance_id="error-instance",
    )

    try:
        # Create session
        session_info = await tmux_service.create_session(config)
        print(f"✓ Created session: {session_info.session_name}")

        # Try to create duplicate session
        try:
            await tmux_service.create_session(config)
            print("✗ Unexpected: Should have failed")
        except TmuxError as e:
            print(f"✓ Expected error caught: {e}")

        # Try operations on non-existent session
        attach_result = await tmux_service.attach_session("non-existent")
        print(f"✓ Attach to non-existent session: {attach_result}")

        info = await tmux_service.get_session_info("non-existent")
        print(f"✓ Info for non-existent session: {info}")

        # Clean up
        await tmux_service.destroy_session("error-example")
        print("✓ Error example session destroyed")

    except TmuxError as e:
        print(f"✗ Unexpected error: {e}")


async def template_management_example():
    """Demonstrate layout template management."""
    print("\n=== Template Management ===")

    tmux_service = get_tmux_service()

    # Show available templates
    templates = tmux_service.get_layout_templates()
    print("Available layout templates:")
    for name, template in templates.items():
        print(f"  • {name}: {template.description}")
        print(f"    Windows: {len(template.windows)}")

    # Create and add a new template
    monitoring_template = LayoutTemplate(
        name="monitoring-example",
        description="Monitoring layout for system observation",
        windows=[
            {
                "name": "system",
                "command": "bash",
                "panes": [
                    {"command": "echo 'CPU/Memory monitor'"},
                    {"command": "echo 'Network monitor'", "split": "horizontal"},
                ],
            },
            {
                "name": "logs",
                "command": "bash",
                "panes": [
                    {"command": "echo 'Application logs'"},
                    {"command": "echo 'System logs'", "split": "vertical"},
                ],
            },
        ],
        default_pane_command="bash",
    )

    tmux_service.add_layout_template(monitoring_template)
    print(f"✓ Added new template: {monitoring_template.name}")

    # Use the new template
    config = SessionConfig(
        session_name="monitoring-example",
        working_directory=Path.cwd(),
        instance_id="monitoring-instance",
        layout_template="monitoring-example",
    )

    try:
        session_info = await tmux_service.create_session(config)
        print(
            f"✓ Created session with monitoring template: {session_info.session_name}"
        )

        # Clean up
        await tmux_service.destroy_session("monitoring-example")
        print("✓ Monitoring example session destroyed")

    except TmuxError as e:
        print(f"✗ Error: {e}")


async def main():
    """Run all examples."""
    print("CC-Orchestrator Tmux Session Management Examples")
    print("=" * 50)

    try:
        await basic_session_management()
        await custom_layout_example()
        await multiple_sessions_example()
        await session_discovery_example()
        await error_handling_example()
        await template_management_example()

        print("\n" + "=" * 50)
        print("All examples completed successfully!")

    except Exception as e:
        print(f"\n✗ Unexpected error in examples: {e}")
        raise

    finally:
        # Ensure cleanup of any remaining test sessions
        tmux_service = get_tmux_service()
        await tmux_service.cleanup_sessions(force=True)
        print("✓ Final cleanup completed")


if __name__ == "__main__":
    # Note: This example requires tmux to be installed and available
    # To run: python examples/tmux_usage.py
    asyncio.run(main())
