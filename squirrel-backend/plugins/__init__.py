"""
Plugins framework for squirrel-backend.

Provides:
- Base plugin interface
- Registry and decorator for registration
- Loader to discover and initialize plugins
"""

from .base import Plugin
from .registry import register_plugin
from .loader import init_plugins

__all__ = [
    "Plugin",
    "register_plugin",
    "init_plugins",
]


