from ncatbot.plugin import BasePlugin, CompatibleEnrollment
from ncatbot.core import GroupMessage
from ncatbot.core.api import BotAPI
from ncatbot.utils import get_log
from dashscope import Application
import os
import re
import markdown

logger = get_log()
bot = CompatibleEnrollment
api = BotAPI()

context = dict()

class qwen3(BasePlugin):
    name = "qwen3" # 插件名
    version = "0.0.1" # 插件版本

    @bot.group_event()
    async def on_group_message(msg: GroupMessage):
        if msg.self_id == msg.user_id: return # 忽略自己发的消息
        if str(msg.self_id) not in msg.raw_message: return # 仅回应at自己的消息
        
        logger.info(f"输入消息: {msg.raw_message}")

        response = Application.call(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            app_id='30b765b512c245a28b73f0ec72a10042',
            prompt=[
                {"role": "user", "text": msg.raw_message}
            ],)

        # 格式化
        cleaned_text = re.sub(r'<ref>.*?</ref>', '', response.output.text)
        cleaned_text = markdown.markdown(cleaned_text)
        cleaned_text = re.sub('<[^>]+>', '', cleaned_text)

        await msg.reply(text=cleaned_text, at=msg.user_id)


if __name__ == "__main__":
    response = Application.call(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        app_id='30b765b512c245a28b73f0ec72a10042',
        prompt=[
            {"role": "user", "text": "偷外卖的学生被抓到了会有什么惩罚呢？"}
        ],)

    print(response.output.text)
    print("="*50)
    
    cleaned_text = re.sub(r'<ref>.*?</ref>', '', response.output.text)
    print(cleaned_text)
    print("="*50)

    # 将Markdown格式的文本转换为HTML
    converted_text = markdown.markdown(cleaned_text)
    print(converted_text)
    print("="*50)

    # 去除HTML标签
    plain_text = re.sub('<[^>]+>', '', converted_text)
    print(plain_text)