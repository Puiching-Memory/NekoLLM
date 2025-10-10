# NekoLLM

基于 FastAPI 的 Napcat 代理与工具 API。项目已经按照 [uv](https://github.com/astral-sh/uv) 推荐的 `src/` 布局和 `pyproject.toml` 依赖管理方式重构。

## 快速开始

```pwsh
# 克隆仓库
git clone https://github.com/Puiching-Memory/NekoLLM.git
cd NekoLLM

# 创建/激活虚拟环境并同步依赖
uv venv
uv sync

# 启动代理服务（默认端口 6077）
uv run nekollm-proxy

# 启动工具服务（默认端口 6078）
uv run nekollm-tools

# 生成测试 Token
uv run nekollm-token
```

`uv run nekollm` 会读取 `NEKOLLM_APP` 环境变量（默认 `proxy`），在同一个入口下切换目标应用：

```pwsh
$env:NEKOLLM_APP = "tools"
uv run nekollm
```

## 环境变量

- `API_TOKEN`：用于接口鉴权的 Bearer Token，缺省时关闭鉴权。
- `HOST` / `PORT`：可分别覆盖服务监听地址与端口。
- `RELOAD`：设置为 `1` 以启用热重载（默认关闭）。
- `NEKOLLM_APP`：`proxy` 或 `tools`，决定 `uv run nekollm` 启动的实例。

## 兼容性说明

历史脚本 `koishiOnLine.py`、`tools_host.py`、`token_generator.py` 仍保留为兼容入口，但推荐通过 `uv run` 使用新的脚本命令。