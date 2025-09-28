from ncatbot.core import BotClient
from ncatbot.utils import get_log, config

logger = get_log()
bot = BotClient()

if __name__ == "__main__":
    bot.run_frontend(bt_uin=2557441898, enable_webui_interaction=True)