from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response, Security, status
from fastapi.security import APIKeyHeader
from loguru import logger

__all__ = ["create_proxy_app", "app"]


def create_proxy_app() -> FastAPI:
    """Build the FastAPI application that proxies traffic to the upstream service."""
    api_key_header = APIKeyHeader(name="Authorization", auto_error=False)
    http_client: httpx.AsyncClient | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal http_client
        logger.remove()
        logger.add(sys.stderr, level=os.getenv("LOG_LEVEL", "INFO"))
        logger.info("NekoLLM proxy starting up")
        http_client = httpx.AsyncClient()
        try:
            yield
        finally:
            if http_client is not None:
                await http_client.aclose()
            logger.info("NekoLLM proxy shutting down")

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
        title="NekoLLM Proxy API",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
    async def reverse_proxy(
        request: Request,
        path: str,
        api_key: str = Depends(get_api_key),
    ) -> Response:
        if http_client is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Client not ready")

        forward_url = f"http://127.0.0.1:5141/{path}"
        filtered_headers = [(k, v) for k, v in request.headers.raw if k.lower() != b"host"]
        content = await request.body()
        forward_request = http_client.build_request(
            method=request.method,
            url=forward_url,
            headers=filtered_headers,
            content=content,
        )
        response = await http_client.send(forward_request)
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )

    return app


app = create_proxy_app()
