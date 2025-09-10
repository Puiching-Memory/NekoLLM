from ncatbot.core import BotClient, GroupMessage, PrivateMessage
from ncatbot.utils import config
from ncatbot.utils import get_log

_log = get_log()

config.set_bot_uin("2557441898")  # 设置 bot qq 号 (必填)
config.set_root("1138663075")  # 设置 bot 超级管理员账号 (建议填写)

bot = BotClient()
@bot.group_event()
async def on_group_message(msg: GroupMessage):
    _log.info(msg)
    if msg.raw_message == "测试":
        await msg.reply(text="NcatBot 测试成功喵~")

@bot.private_event()
async def on_private_message(msg: PrivateMessage):
    _log.info(msg)
    if msg.raw_message == "测试":
        await bot.api.post_private_msg(msg.user_id, text="NcatBot 测试成功喵~")

if __name__ == "__main__":
    bot.run()