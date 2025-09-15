from __future__ import annotations

# 标准库与类型
import os
import sys
from contextlib import asynccontextmanager

# Web 框架与第三方库
from fastapi import FastAPI, Depends, HTTPException, status, Query
from loguru import logger
from pydantic import BaseModel
from fastapi.security import APIKeyHeader
from fastapi import Security, Depends
from ncatbot.core.api import BotAPI

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
	logger.info("NekoLLM API starting up")
	try:
		yield  # 应用运行期间在此挂起
	finally:
		logger.info("NekoLLM API shutting down")


app = FastAPI(
	title="NekoLLM API",
	version="0.1.0",
	lifespan=lifespan,
)
api_key_header = APIKeyHeader(name="Authorization")
api = BotAPI()

# API 密钥验证
async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key != os.getenv("API_TOKEN"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return api_key
# 戳一戳工具
@app.post("/send_poke")
async def send_poke(key: str = Depends(get_api_key), user_id: str = Query(), group_id: str = Query()):
    await api.send_poke(user_id=user_id, group_id=group_id)
    return {"result": f"已戳一戳用户{user_id}"}

if __name__ == "__main__":
	# 本地开发入口：使用 uvicorn 启动服务
	# 可通过环境变量覆盖默认设置：HOST/PORT/RELOAD
	# 调试url: http://127.0.0.1:6077/docs
	import uvicorn

	host = os.getenv("HOST", "0.0.0.0")
	port = int(os.getenv("PORT", "6077"))
	reload = os.getenv("RELOAD", "1") == "1"

	uvicorn.run("tools_host:app", host=host, port=port, reload=reload)

