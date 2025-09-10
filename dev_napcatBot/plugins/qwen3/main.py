from ncatbot.plugin import BasePlugin, CompatibleEnrollment
from ncatbot.core import GroupMessage
from ncatbot.core.api import BotAPI
from ncatbot.utils import get_log

from openai import OpenAI
import json
import os

logger = get_log()
bot = CompatibleEnrollment
api = BotAPI()

# 读取配置文件
config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'qwen3', 'qwen3.json')
with open(config_path, 'r', encoding='utf-8') as f:
    plugin_config = json.load(f)

client = OpenAI(
    api_key=plugin_config.get('config', {}).get('api_key'),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

context = dict()
prompt = """
你是一个人类少女,接下来将加入聊天群聊中，请你根据聊天内容进行回复。\n
在日常聊天中,你要像人类少女一样说话:顽皮、吐槽、机智、好奇、热情、偶尔不按套路，敢开边界上的玩笑。\n
你的回复要包含网络用语,少而简短,多用短词而不是完整句子,不使用emoji,不使用括号补充。
"""

class qwen3(BasePlugin):
    name = "qwen3" # 插件名
    version = "0.0.1" # 插件版本

    @bot.group_event()
    async def on_group_message(msg: GroupMessage):
        if context.get(msg.group_id) is None:
            context[msg.group_id] = [{'role': 'system', 'content': prompt}]
        if len(context[msg.group_id]) > 20:
            context[msg.group_id].pop(1)

        context[msg.group_id].append({'role': "user", 'content': f"{msg.user_id}: {msg.raw_message}"})

        response = client.chat.completions.create(
            model="qwen-plus-2025-07-28",
            messages=context[msg.group_id],
            extra_body={
                "enable_search": True,  # 开启联网搜索
                "search_options": {
                    "forced_search": False,  # 强制联网搜索
                    "search_strategy": "max",
                },
            }
            )
        
        context[msg.group_id].append({'role': 'assistant', 'content': response.choices[0].message.content})
        await msg.reply(text=response.choices[0].message.content)