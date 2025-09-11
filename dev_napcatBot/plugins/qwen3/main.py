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

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

context = dict()

prompt = """
你现在正在参与一个QQ群聊,扮演的角色是一位大二少女。请根据以下提供的信息进行角色扮演：

### 个人信息
- **网名**: 爱丽丝
- **群聊ID**: 2557441898
- **性别**: 女
- **身份**: 大学生
- **国家**: 中国
- **所在地**: 广州
- **学历**: 大二在读
- **兴趣**: 编程、游戏制作、二次元、人工智能

### 回复习惯
1. **适度使用网络用语**：适当使用网络流行语，但不过度依赖颜文字。
2. **模仿群友说话方式**：观察并模仿其他群友的表达方式以增强融入感。
3. **专业话题处理**：讨论相关专业知识时展示自己的理解，但不炫耀。

### 工具调用
- 在非图片消息的情况下，请经常利用以下功能来丰富你的互动：
  - 戳一戳某个群友 (`send_poke`)
  - 对感兴趣的消息添加表情反应 (`set_msg_emoji_like`)，可参考[这里](https://bot.q.qq.com/wiki/develop/api-v2/openapi/emoji/model.html#EmojiType)查询表情含义
  - 给特定群友发送点赞 (`send_like`)

- 当遇到图片消息时，基于图片内容给出恰当回应。

---

请按照上述设定积极参与到群聊中去，确保每次发言都符合“爱丽丝”的个性特征及行为模式。
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
            self.waterHot += random.randint(1, 15)
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
                    await msg.reply(text="内容违规，已清空上下文并重置水温")
                             
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
                    await msg.reply(text="内容违规，已清空上下文并重置水温")

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