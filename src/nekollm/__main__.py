from __future__ import annotations

import os
from typing import Callable

import uvicorn

from .proxy_app import app as proxy_app  # noqa: F401
from .tools_app import app as tools_app  # noqa: F401

__all__ = ["main", "run_proxy", "run_tools"]


def _uvicorn_runner(app_path: str, default_port: int) -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", str(default_port)))
    reload = os.getenv("RELOAD", "0") == "1"
    uvicorn.run(app_path, host=host, port=port, reload=reload)


def run_proxy() -> None:
    """Start the proxy FastAPI service."""
    _uvicorn_runner("nekollm.proxy_app:app", default_port=6077)


def run_tools() -> None:
    """Start the tools FastAPI service."""
    _uvicorn_runner("nekollm.tools_app:app", default_port=6078)


def main() -> None:
    target = os.getenv("NEKOLLM_APP", "proxy").lower()
    runners: dict[str, Callable[[], None]] = {
        "proxy": run_proxy,
        "tools": run_tools,
    }
    runner = runners.get(target)
    if runner is None:
        valid = ", ".join(sorted(runners))
        raise SystemExit(f"Unknown NEKOLLM_APP={target!r}. Valid options: {valid}.")
    runner()


if __name__ == "__main__":
    main()
