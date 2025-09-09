from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="qwen3-agent",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

# 导入子模块以注册事件响应器/匹配器
from . import agent  # noqa: F401

