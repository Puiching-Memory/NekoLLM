# dev_nonebot

## How to start

1. 安装依赖（tiktoken 为强制依赖，用于精确 token 统计）
2. 配置环境变量 `DASHSCOPE_API_KEY`（以及可选的 `QWEN_MODEL`）
3. 在 `dev_nonebot/plugins` 目录下开发插件
4. 运行 NoneBot（建议使用 `nb run --reload`）

Quickstart（PowerShell）：

```powershell
# 1) 使用已有的 Conda/venv 环境
# conda create -n nonebot2 python=3.12; conda activate nonebot2

# 2) 安装依赖（tiktoken 为强制依赖）
pip install tiktoken openai nonebot2 nonebot-adapter-onebot

# 3) 配置环境变量
$env:DASHSCOPE_API_KEY = "<your_key>"
# 可选：指定模型
$env:QWEN_MODEL = "qwen-plus-2025-07-14"

# 4) 运行 NoneBot（在 dev_nonebot 目录内）
nb run --reload
```

## Documentation

See [Docs](https://nonebot.dev/)
