from ncatbot.plugin import BasePlugin, CompatibleEnrollment
from ncatbot.core import GroupMessage
from ncatbot.utils import config
from ncatbot.utils import get_log
import os
import sys

# Ensure project root is on sys.path for absolute imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dev_napcatBot.plugins._bot_api import api

logger = get_log()
bot = CompatibleEnrollment()

class poke(BasePlugin):
    name = "poke" # 插件名
    version = "0.0.1" # 插件版本

    @bot.notice_event
    async def on_notice_event(msg: dict):
        if msg.get("sub_type") == "poke" and msg.get("target_id") == msg.get("self_id"): # 被戳 而且 戳的是自己
            await api.send_poke(user_id=msg.get("user_id"), group_id=msg.get("group_id")) # 戳回去
