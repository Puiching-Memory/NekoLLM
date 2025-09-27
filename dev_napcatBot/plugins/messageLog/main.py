import jsonl
from ncatbot.plugin_system import NcatBotPlugin
from ncatbot.plugin_system import command_registry
from ncatbot.core.event import BaseMessageEvent

class messageLog(NcatBotPlugin):
    name = "messageLog"
    version = "0.0.1"

    async def on_load(self):
        pass
    @command_registry.group("messageLog_group")
    async def on_group_message(self, event: BaseMessageEvent):
        print(event)

        # with open(f"logs/msg_{event.group_id}.jsonl", mode="at", encoding="utf-8") as f:
        #     jsonl.dump(record, f, text_mode=True)