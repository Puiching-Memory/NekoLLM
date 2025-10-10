from __future__ import annotations

# 标准库与类型
import os
import sys
from contextlib import asynccontextmanager

# Web 框架与第三方库
from fastapi import FastAPI, Depends, HTTPException, status, Query, Request, Response
from loguru import logger
from pydantic import BaseModel
from fastapi.security import APIKeyHeader
from fastapi import Security, Depends
import httpx

# --- 日志配置（loguru） ---
# 移除了默认 handler 以便自定义；日志级别从环境变量 LOG_LEVEL 读取，默认 INFO。
logger.remove()
logger.add(sys.stderr, level=os.getenv("LOG_LEVEL", "INFO"))

@asynccontextmanager
async def lifespan(app: FastAPI):
	"""
	应用生命周期管理：替代已弃用的 @app.on_event("startup"/"shutdown")。
	进入时视为启动，退出时视为关闭。
	"""
	global http_client
	logger.info("NekoLLM API starting up")
	http_client = httpx.AsyncClient()
	try:
		yield  # 应用运行期间在此挂起
	finally:
		if http_client:
			await http_client.aclose()
		logger.info("NekoLLM API shutting down")

# 创建HTTP客户端用于反向代理
http_client = None

app = FastAPI(
	title="NekoLLM API",
	version="0.1.0",
	lifespan=lifespan,
)
api_key_header = APIKeyHeader(name="Authorization")
# use centralized `api` from dev_napcatBot.plugins._bot_api

# API 密钥验证
async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key != os.getenv("API_TOKEN"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return api_key

# 反向代理处理器，将5140端口的请求转发到5141端口
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def reverse_proxy(request: Request, path: str):
    # 构造转发到5141端口的URL
    forward_url = f"http://127.0.0.1:5141/{path}"
    
    # 转发请求
    forward_request = http_client.build_request(
        method=request.method,
        url=forward_url,
        headers=[(k, v) for k, v in request.headers.raw if k.lower() != b'host'],
        content=await request.body()
    )
    
    # 发送请求并获取响应
    response = await http_client.send(forward_request)
    
    # 返回响应
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers)
    )


if __name__ == "__main__":
	# 本地开发入口：使用 uvicorn 启动服务
	# 可通过环境变量覆盖默认设置：HOST/PORT/RELOAD
	# 调试url: http://127.0.0.1:6077/docs
	import uvicorn

	host = os.getenv("HOST", "0.0.0.0")
	port = int(os.getenv("PORT", "6077"))
	reload = os.getenv("RELOAD", "1") == "1"

	uvicorn.run("tools_host:app", host=host, port=port, reload=reload)