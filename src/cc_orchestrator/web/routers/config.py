"""
Legacy config router (deprecated).

This router is kept for backward compatibility but will be removed in future versions.
Use /api/v1/config instead.
"""

from .v1.config import router as v1_router

# Re-export the v1 router for backward compatibility
router = v1_router
