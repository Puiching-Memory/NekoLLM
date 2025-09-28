import jsonl
from ncatbot.plugin_system import NcatBotPlugin, command_registry, group_filter
from ncatbot.core.event import BaseMessageEvent
from ncatbot.utils import get_log

logger = get_log()

class messageLog(NcatBotPlugin):
    name = "messageLog"
    version = "0.0.1"
    author = "Unknown"
    description = "将所有群聊的消息事件捕获，然后打印到控制台"

    async def on_load(self):
        """插件加载时调用，用于初始化资源"""
        pass
    
    async def on_close(self):
        """插件卸载时调用，用于清理资源"""
        pass

    @group_filter
    async def on_group_message(self, event: BaseMessageEvent):
        # logger.info(f"save message: {event.to_dict()}")

        with open(f"data/msg_{event.group_id}.jsonl", mode="at", encoding="utf-8") as f:
            jsonl.dump([event.to_dict()], f, text_mode=True)