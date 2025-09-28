from ncatbot.plugin_system import NcatBotPlugin, command_registry, group_filter
from ncatbot.core.event import BaseMessageEvent
from ncatbot.utils import get_log
from dashscope import Application
import os
import re
import markdown

logger = get_log()
context = dict()

class qwen3(NcatBotPlugin):
    name = "qwen3" # 插件名
    version = "0.0.1" # 插件版本

    @group_filter
    async def on_group_message(self, event: BaseMessageEvent):
        if event.self_id == event.user_id: return # 忽略自己发的消息
        if str(event.self_id) not in event.raw_message: return # 仅回应at自己的消息

        logger.info(f"输入消息: {event.message.filter_text()[0].text}")

        response = Application.call(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            app_id='30b765b512c245a28b73f0ec72a10042',
            prompt=[
                {"role": "user", "text": event.message.filter_text()[0].text}
            ],)

        # 格式化
        cleaned_text = re.sub(r'<ref>.*?</ref>', '', response.output.text)
        cleaned_text = markdown.markdown(cleaned_text)
        cleaned_text = re.sub('<[^>]+>', '', cleaned_text)

        await event.reply(text=cleaned_text, at=event.user_id)


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