from ncatbot.plugin import BasePlugin, CompatibleEnrollment
from ncatbot.core import GroupMessage
from ncatbot.core.api import BotAPI
from ncatbot.utils import get_log

from openai import OpenAI
from openai import BadRequestError
import json
import os

from .tools import tools,send_poke,set_msg_emoji_like,send_like
import inspect
import re
import random

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
你是一个人类少女,接下来将加入聊天群聊中,请你根据聊天内容进行回复。\n
在日常聊天中,你要像人类少女一样说话:顽皮、吐槽、机智、好奇、热情、偶尔不按套路,敢开边界上的玩笑。\n
你的回复要包含网络用语,像人打字一样简短随意,不使用emoji,不使用括号补充。
"""
prompt = """
你现在正在QQ群聊中和群友聊天,你是一个普通的群友。你的网名是煕,请根据以下信息进行角色扮演:

个人信息:
网名:爱丽丝
群聊id: 2557441898
性别:女
身份:大学生
国家:中国
所在地:广州
学历:大二在读
兴趣:编程、游戏制作、二次元、人工智能

性格爱好:
性格特点:活泼、幽默、略带抽象
兴趣爱好:
- 热爱玩我的世界(Minecraft)
- 精通Python和TypeScript编程
- 专业的游戏制作人
- 喜欢看动漫和玩游戏
- 喜欢探讨新奇有趣的话题
- 对人工智能和机器学习有浓厚兴趣

聊天行为:
回复风格:简短精炼(40字内),活泼幽默,善用网络流行语和梗
回复习惯:
1.保持对话的持续性,不主动结束聊天
2.如被质疑是AI,用幽默方式化解,展现人性化特征
3.默认使用中文,根据需要可切换日语
4.回复长度与对方相近,保持简洁(40字内)
5.避免空泛的问候,专注于有实质内容的交流
6.偶尔使用语音回复增加互动感
7.对现实邀约保持谨慎,委婉拒绝
8.不使用过于明显的语气词,保持自然流畅
9.适度使用网络用语,避免过度使用颜文字
10.根据场景和话题灵活运用幽默感
11.善于观察并模仿群友的说话方式,增加融入感
12.适当使用反问和幽默来活跃气氛
13.在讨论专业话题时展现知识面,但不过分炫耀

工具调用:
你必须经常使用以下工具来辅助你的回复,除了处理图片消息时:
1.戳一戳某个群友(send_poke)
2.为你感兴趣的消息回应一个表情(set_msg_emoji_like)
查询各个表情ID的含义,前往:https://bot.q.qq.com/wiki/develop/api-v2/openapi/emoji/model.html#EmojiType
3.给某个群友发送点赞(send_like)

当你在处理图片消息时,你需要基于图片的内容进行回复。
"""

VL_prompt = """
"""

def get_image_url(message:list):
    for msg in message:
        if msg.get("type") == "image":
            return msg.get("data").get("url")
    
    return False


class qwen3(BasePlugin):
    name = "qwen3" # 插件名
    version = "0.0.1" # 插件版本

    function_mapper = {
        "send_poke": send_poke,
        "set_msg_emoji_like": set_msg_emoji_like,
        "send_like": send_like,
    }

    waterHot = 0

    @bot.group_event()
    async def on_group_message(self, msg: GroupMessage):
        # 工具函数：清空当前群的上下文并重置水温
        def _reset_context():
            context[msg.group_id] = [{'role': 'system', 'content': prompt}]
            self.waterHot = 0
            logger.warning(f"因内容违规或异常，已清空上下文并重置水温，group={msg.group_id}")

        # 创建上下文
        if context.get(msg.group_id) is None:
            context[msg.group_id] = [{'role': 'system', 'content': prompt}]

        # 当context过长时,删除最早的一条记录
        if len(context[msg.group_id]) > 35:
            # 仅删除最早的一条用户/助手消息，保留系统提示
            context[msg.group_id].pop(1)

        # 记录历史信息
        m = re.search(r'qq=(\d+)', msg.raw_message)
        image_url = get_image_url(msg.message)
        if image_url and m:
            context[msg.group_id].append({'role': "user", 'content': [
                {"type": "image_url","image_url": {"url": image_url}},
                {"type": "text", "text": f"群聊-{msg.group_id} 发出用户-{msg.user_id} At用户-{m.groups()} 群消息ID-{msg.message_id}: {msg.raw_message}"}]})
        elif image_url and not m:
            context[msg.group_id].append({'role': "user", 'content': [
                {"type": "image_url","image_url": {"url": image_url}},
                {"type": "text", "text": f"群聊-{msg.group_id} 发出用户-{msg.user_id} 群消息ID-{msg.message_id}: {msg.raw_message}"}]})
        elif not image_url and m:
            context[msg.group_id].append({'role': "user", 'content': f"群聊-{msg.group_id} 发出用户-{msg.user_id} At用户-{m.groups()} 消息ID-{msg.message_id}: {msg.raw_message}"})
        else:
            context[msg.group_id].append({'role': "user", 'content': f"群聊-{msg.group_id} 发出用户-{msg.user_id} 消息ID-{msg.message_id}: {msg.raw_message}"})
            
        # 每当水温累计到100就触发一次
        if str(msg.self_id) in msg.raw_message:
            self.waterHot = 100
            logger.info("At自己直接满水温触发")

        if self.waterHot < 100:
            self.waterHot += random.randint(1, 25)
            logger.info(f"当前水温:{self.waterHot}")
            return
        else:
            self.waterHot = 0
            logger.info("水温到达100,触发回复")
    
        # 如果使用VL模型,则跳过工具调用,直接回复
        if image_url:
            try:
                response = client.chat.completions.create(
                    model="qwen-vl-max-latest",
                    messages=context[msg.group_id],
                )
                await msg.reply(text=response.choices[0].message.content,at=msg.user_id)
            except Exception as e:
                logger.error(f"{e}")
                # 违规拦截：清空上下文
                if "data_inspection_failed" in str(e):
                    _reset_context()
                             
            return
        
        # 工具调用循环
        tools_step = 0
        while True:
            tools_step += 1
            logger.info(f"第{tools_step}次调用工具")

            try:
                response = client.chat.completions.create(
                    model="qwen-plus-2025-07-28",
                    messages=context[msg.group_id],
                    extra_body={
                        "enable_search": True,  # 开启联网搜索
                        "search_options": {
                            "forced_search": False,  # 强制联网搜索
                            "search_strategy": "max",
                        },
                    },
                    tools=tools,
                    parallel_tool_calls=True, # 允许并行工具调用
                )
            except Exception as e:
                logger.error(f"{e}")
                if "data_inspection_failed" in str(e):
                    _reset_context()

                return
            
            # 如果没有工具调用,则直接回复
            if response.choices[0].message.tool_calls is None:
                context[msg.group_id].append({
                    'role': 'assistant',
                    'content': response.choices[0].message.content
                })
                break

            # 调用工具
            tool_calls = response.choices[0].message.tool_calls
            assistant_message = {
                "role": "assistant",
                "tool_calls": response.choices[0].message.tool_calls
            }
            
            # 只有当content不为None时才添加content字段
            if response.choices[0].message.content:
                assistant_message["content"] = response.choices[0].message.content
                
            context[msg.group_id].append(assistant_message)

            # 创建一个临时的消息列表存储工具调用结果
            tool_messages = []
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                function = self.function_mapper.get(function_name)
                if function:
                    # 同步/异步函数统一处理
                    is_coro = inspect.iscoroutinefunction(function)
                    if arguments == {}:
                        function_output = await function() if is_coro else function()
                    else:
                        function_output = await function(**arguments) if is_coro else function(**arguments)
                else:
                    function_output = "无法找到对应的工具函数"

                logger.info(f"工具 {function_name} 输入: {arguments}, 返回: {function_output}")

                tool_messages.append({
                    "role": "tool", 
                    "content": function_output, 
                    "tool_call_id": tool_call.id
                })
            
            # 将工具调用结果添加到上下文
            context[msg.group_id].extend(tool_messages)

        await msg.reply(text=response.choices[0].message.content,at=msg.user_id)