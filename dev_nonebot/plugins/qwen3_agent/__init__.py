from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata
from .config import Config
from . import agent

__plugin_meta__ = PluginMetadata(
    name="qwen3-agent",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

