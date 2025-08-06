"""WebSocket module for real-time communication."""

from .manager import connection_manager
from .router import router

__all__ = ["connection_manager", "router"]
