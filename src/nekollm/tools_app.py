from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Security, status
from fastapi.security import APIKeyHeader
from loguru import logger

try:
    from dev_napcatBot.plugins._bot_api import api as napcat_api  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover - external optional dependency
    napcat_api = None
    import_failed = exc
else:
    import_failed = None

__all__ = ["create_tools_app", "app"]


def create_tools_app() -> FastAPI:
    """Build the FastAPI application for auxiliary tooling endpoints."""
    api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.remove()
        logger.add(sys.stderr, level=os.getenv("LOG_LEVEL", "INFO"))
        logger.info("NekoLLM tools API starting up")
        try:
            yield
        finally:
            logger.info("NekoLLM tools API shutting down")

    async def get_api_key(api_key: str | None = Security(api_key_header)) -> str:
        expected = os.getenv("API_TOKEN")
        if not expected:
            return ""
        if api_key != expected:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key",
            )
        return api_key

    app = FastAPI(
        title="NekoLLM Tools API",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.post("/send_poke")
    async def send_poke(
        _api_key: str = Depends(get_api_key),
        user_id: str = Query(...),
        group_id: str = Query(...),
    ) -> dict[str, str]:
        if napcat_api is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Napcat API not available: {import_failed}",
            )
        await napcat_api.send_poke(user_id=user_id, group_id=group_id)
        return {"result": f"已戳一戳用户{user_id}"}

    return app


app = create_tools_app()
