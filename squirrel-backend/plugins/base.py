from __future__ import annotations

from typing import Any, Dict, Optional, Protocol


class Plugin(Protocol):
    """Plugin interface.

    A plugin may implement any of the lifecycle hooks below.
    All hooks are optional.
    """

    name: str
    version: str
    description: Optional[str]

    def on_load(self) -> None:  # noqa: D401
        """Called when the plugin is loaded (before app starts)."""
        ...

    def on_app_start(self) -> None:  # noqa: D401
        """Called after FastAPI app is created and before serving."""
        ...

    def on_app_stop(self) -> None:  # noqa: D401
        """Called during application shutdown."""
        ...

    def health_check(self) -> Dict[str, Any]:  # noqa: D401
        """Optional health check method.

        Returns:
            Dict with keys:
                - healthy (bool): Whether the plugin is healthy
                - message (str): Optional status message
                - details (dict): Optional additional details
        """
        ...


