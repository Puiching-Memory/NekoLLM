from ncatbot.plugin import BasePlugin, CompatibleEnrollment
from ncatbot.core import GroupMessage

from ncatbot.utils import config
from ncatbot.utils import get_log

logger = get_log()
bot = CompatibleEnrollment

class messageLog(BasePlugin):
    name = "messageLog" # 插件名
    version = "0.0.1" # 插件版本

    @bot.group_event()
    async def on_group_message(msg: GroupMessage):
        logger.info(msg)

    @bot.notice_event()
    async def on_notice_event(msg: dict):
        logger.info(msg)

    @bot.request_event()
    async def on_request_event(msg: GroupMessage):
        logger.info(msg)
