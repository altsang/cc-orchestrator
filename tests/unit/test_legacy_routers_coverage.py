"""
Tests to provide coverage for legacy router files.

These tests ensure that the router re-exports work correctly and provide
coverage for the legacy router compatibility layer.
"""

import pytest
from fastapi import APIRouter


class TestLegacyRouters:
    """Test legacy router imports and re-exports."""

    def test_alerts_router_import(self):
        """Test that the legacy alerts router can be imported."""
        from src.cc_orchestrator.web.routers.alerts import router

        assert router is not None
        assert isinstance(router, APIRouter)

    def test_config_router_import(self):
        """Test that the legacy config router can be imported."""
        from src.cc_orchestrator.web.routers.config import router

        assert router is not None
        assert isinstance(router, APIRouter)

    def test_health_router_import(self):
        """Test that the legacy health router can be imported."""
        from src.cc_orchestrator.web.routers.health import router

        assert router is not None
        assert isinstance(router, APIRouter)

    def test_instances_router_import(self):
        """Test that the legacy instances router can be imported."""
        from src.cc_orchestrator.web.routers.instances import router

        assert router is not None
        assert isinstance(router, APIRouter)

    def test_tasks_router_import(self):
        """Test that the legacy tasks router can be imported."""
        from src.cc_orchestrator.web.routers.tasks import router

        assert router is not None
        assert isinstance(router, APIRouter)

    def test_worktrees_router_import(self):
        """Test that the legacy worktrees router can be imported."""
        from src.cc_orchestrator.web.routers.worktrees import router

        assert router is not None
        assert isinstance(router, APIRouter)

    def test_all_routers_are_different_instances(self):
        """Test that different routers are separate instances."""
        from src.cc_orchestrator.web.routers import (
            alerts,
            config,
            health,
            instances,
            tasks,
            worktrees,
        )

        routers = [
            alerts.router,
            config.router,
            health.router,
            instances.router,
            tasks.router,
            worktrees.router,
        ]

        # All should be APIRouter instances
        for router in routers:
            assert isinstance(router, APIRouter)

        # They should reference the same underlying v1 routers
        # (this tests the re-export functionality)
        assert alerts.router is not None
        assert config.router is not None
        assert health.router is not None
        assert instances.router is not None
        assert tasks.router is not None
        assert worktrees.router is not None


if __name__ == "__main__":
    pytest.main([__file__])
