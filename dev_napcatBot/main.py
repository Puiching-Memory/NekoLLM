from ncatbot.core import BotClient
from ncatbot.utils import config
from ncatbot.utils import get_log

logger = get_log()

config.set_bot_uin("2557441898")  # 设置 bot qq 号 (必填)
config.set_root("1138663075")  # 设置 bot 超级管理员账号 (建议填写)

bot = BotClient()

if __name__ == "__main__":
    bot.run_frontend()