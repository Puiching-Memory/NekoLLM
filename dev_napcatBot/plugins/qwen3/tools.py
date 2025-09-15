from datetime import datetime
from .._bot_api import api

tools = [
    {
        "type": "function",
        "function": {
            "name": "send_poke",
            "description": "戳一戳某个群友",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "要戳的用户的QQ号",
                    },
                    "group_id": {
                        "type": "integer",
                        "description": "所在群的群号",
                    }
                },
                "required": ["user_id", "group_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_msg_emoji_like",
            "description": "为消息回应表情",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "integer",
                        "description": "要回应表情的消息ID",
                    },
                    "emoji_id": {
                        "type": "integer",
                        "description": "要回应的表情ID",
                    }
                },
                "required": ["message_id", "emoji_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_like",
            "description": "给某个QQ号发送点赞",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "要点赞的用户的QQ号",
                    },
                    "times": {
                        "type": "integer",
                        "description": "点赞次数",
                    }
                },
                "required": ["user_id"]
            }
        }
    },
]

# use centralized `api` from dev_napcatBot.plugins._bot_api

# 戳一戳某个群友的工具
async def send_poke(user_id: int, group_id: int):
    await api.send_poke(user_id=user_id, group_id=group_id)
    return f"已戳一戳用户 {user_id} 。"

# 为消息回应表情的工具
async def set_msg_emoji_like(message_id: int, emoji_id: int):
    await api.set_msg_emoji_like(message_id=message_id, emoji_id=emoji_id, emoji_set=True)
    return f"已回复表情 {emoji_id} 。"

# 给某个QQ号发送点赞的工具
async def send_like(user_id: int, times: int = 1):
    await api.send_like(user_id=user_id,times=times)
    return f"已为用户{user_id}点了{times}个赞。"
