"""
Legacy health router (deprecated).

This router is kept for backward compatibility but will be removed in future versions.
Use /api/v1/health instead.
"""

from .v1.health import router as v1_router

# Re-export the v1 router for backward compatibility
router = v1_router
