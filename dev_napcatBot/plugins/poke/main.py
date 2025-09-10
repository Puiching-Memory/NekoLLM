from ncatbot.plugin import BasePlugin, CompatibleEnrollment
from ncatbot.core import GroupMessage
from ncatbot.core.api import BotAPI

from ncatbot.utils import config
from ncatbot.utils import get_log

logger = get_log()
bot = CompatibleEnrollment
api = BotAPI()

class poke(BasePlugin):
    name = "poke" # 插件名
    version = "0.0.1" # 插件版本

    @bot.notice_event(types="poke")
    async def on_notice_event(msg: dict):
        if msg.get("sub_type") == "poke" and msg.get("target_id") == msg.get("self_id"): # 被戳 而且 戳的是自己
            await api.send_poke(user_id=msg.get("user_id"), group_id=msg.get("group_id")) # 戳回去
