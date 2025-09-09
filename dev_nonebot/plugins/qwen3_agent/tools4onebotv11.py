"""
将 OneBot v11 的 Bot API 映射为 OpenAI 工具（function calling）

- send_group_text：发送群文本
- send_group_image：发送图片
- send_group_face：发送表情包（QQ 系统表情）
- send_group_poke：对某人“戳一戳”
- send_group_at：@某人并发送文本
- send_group_reply：回复某条消息（消息 ID）
- send_group_msg：原始消息发送（接收 CQ 码/字符串），作为兜底

实现说明：
- 以上高阶工具均在分发器里装配为对 send_group_msg 的调用；消息体使用 OneBot v11 的消息段（CQ 码）
- 所有工具都仅面向群聊，必须提供 group_id；可选 bot_self_id 指定使用的 Bot
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from nonebot import get_bots
from nonebot.adapters.onebot.v11 import Bot


## =============== 工具定义构建 ===============

def _base_params_with_self_id(properties: Dict[str, Any], required: List[str] | None = None) -> Dict[str, Any]:
	"""为每个工具统一加入可选的 bot_self_id 选择器。"""
	schema = {
		"type": "object",
		"properties": {
			"bot_self_id": {
				"type": ["string", "integer"],
				"description": "可选，指定要调用的 Bot self_id；不填则取第一个已连接 Bot",
			},
			**properties,
		},
		"additionalProperties": False,
	}
	if required:
		schema["required"] = required
	return schema


def get_openai_tools() -> List[Dict[str, Any]]:
	"""返回 OpenAI Chat Completions 可用的工具，仅群聊、仅“像真人”的行为。"""
	f = lambda name, desc, params: {
		"type": "function",
		"function": {"name": name, "description": desc, "parameters": params},
	}

	tools: List[Dict[str, Any]] = []

	# 兜底：原始群消息发送（允许直接传入 CQ 码）
	tools.append(
		f(
			"send_group_msg",
			"向指定群发送消息（可为文本或 CQ 码）",
			_base_params_with_self_id(
				{
					"group_id": {"type": "integer", "description": "群号"},
					"message": {"type": "string", "description": "消息内容（文本或 CQ 码）"},
					"auto_escape": {
						"type": "boolean",
						"description": "是否将消息内容作为纯文本发送，忽略 CQ 码",
						"default": False,
					},
				},
				["group_id", "message"],
			),
		)
	)

	# 高阶封装：文本
	tools.append(
		f(
			"send_group_text",
			"发送群文本消息",
			_base_params_with_self_id(
				{
					"group_id": {"type": "integer", "description": "群号"},
					"text": {"type": "string", "description": "文本内容"},
				},
				["group_id", "text"],
			),
		)
	)

	# 高阶封装：图片（file 支持 URL、本地路径、base64 等由实现决定）
	tools.append(
		f(
			"send_group_image",
			"发送群图片",
			_base_params_with_self_id(
				{
					"group_id": {"type": "integer", "description": "群号"},
					"file": {"type": "string", "description": "图片资源（URL/路径/缓存键等）"},
				},
				["group_id", "file"],
			),
		)
	)

	# 高阶封装：表情（QQ 系统表情 id）
	tools.append(
		f(
			"send_group_face",
			"发送群表情包（QQ 系统表情）",
			_base_params_with_self_id(
				{
					"group_id": {"type": "integer", "description": "群号"},
					"id": {"type": "integer", "description": "QQ 系统表情 id"},
				},
				["group_id", "id"],
			),
		)
	)

	# 高阶封装：戳一戳（poke）
	tools.append(
		f(
			"send_group_poke",
			"对某位群成员戳一戳",
			_base_params_with_self_id(
				{
					"group_id": {"type": "integer", "description": "群号"},
					"user_id": {"type": "integer", "description": "被戳对象 QQ 号"},
				},
				["group_id", "user_id"],
			),
		)
	)

	# 高阶封装：@某人
	tools.append(
		f(
			"send_group_at",
			"@某人并发送文本",
			_base_params_with_self_id(
				{
					"group_id": {"type": "integer", "description": "群号"},
					"user_id": {"type": "integer", "description": "被 @ 的 QQ 号"},
					"text": {"type": "string", "description": "附带文本，可为空", "default": ""},
				},
				["group_id", "user_id"],
			),
		)
	)

	# 高阶封装：回复某条消息
	tools.append(
		f(
			"send_group_reply",
			"回复群内一条消息（通过 message_id）",
			_base_params_with_self_id(
				{
					"group_id": {"type": "integer", "description": "群号"},
					"message_id": {"type": "integer", "description": "要回复的消息 ID"},
					"text": {"type": "string", "description": "回复文本，可为空", "default": ""},
				},
				["group_id", "message_id"],
			),
		)
	)

	return tools


## =============== 执行分发 ===============

def _pick_bot(bot_self_id: Optional[str | int]) -> Bot:
	bots = get_bots()
	if not bots:
		raise RuntimeError("没有已连接的 OneBot v11 Bot")
	if bot_self_id is None:
		return next(iter(bots.values()))  # type: ignore[return-value]
	target = str(bot_self_id)
	if target in bots:
		return bots[target]  # type: ignore[return-value]
	for b in bots.values():
		if getattr(b, "self_id", None) is not None and str(getattr(b, "self_id")) == target:
			return b  # type: ignore[return-value]
	raise RuntimeError(f"未找到指定 self_id 的 Bot: {bot_self_id}")


def _cq_image(file: str) -> str:
	return f"[CQ:image,file={file}]"


def _cq_face(face_id: int) -> str:
	return f"[CQ:face,id={face_id}]"


def _cq_at(user_id: int) -> str:
	return f"[CQ:at,qq={user_id}]"


def _cq_reply(message_id: int) -> str:
	return f"[CQ:reply,id={message_id}]"


def _cq_poke(user_id: int) -> str:
	# 依照 go-cqhttp/OneBot v11 常见实现的 poke 段
	return f"[CQ:poke,qq={user_id}]"


async def call_onebot_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
	"""执行模型返回的工具调用（仅群聊行为）。"""
	bot_self_id = arguments.pop("bot_self_id", None)
	bot: Bot = _pick_bot(bot_self_id)

	if tool_name == "send_group_text":
		group_id = int(arguments["group_id"])  # required
		text = str(arguments.get("text", ""))
		return await bot.send_group_msg(group_id=group_id, message=text)

	if tool_name == "send_group_image":
		group_id = int(arguments["group_id"])  # required
		file = str(arguments["file"])  # required
		return await bot.send_group_msg(group_id=group_id, message=_cq_image(file))

	if tool_name == "send_group_face":
		group_id = int(arguments["group_id"])  # required
		face_id = int(arguments["id"])  # required
		return await bot.send_group_msg(group_id=group_id, message=_cq_face(face_id))

	if tool_name == "send_group_poke":
		group_id = int(arguments["group_id"])  # required
		user_id = int(arguments["user_id"])  # required
		return await bot.send_group_msg(group_id=group_id, message=_cq_poke(user_id))

	if tool_name == "send_group_at":
		group_id = int(arguments["group_id"])  # required
		user_id = int(arguments["user_id"])  # required
		text = str(arguments.get("text", ""))
		return await bot.send_group_msg(group_id=group_id, message=f"{_cq_at(user_id)} {text}")

	if tool_name == "send_group_reply":
		group_id = int(arguments["group_id"])  # required
		msg_id = int(arguments["message_id"])  # required
		text = str(arguments.get("text", ""))
		return await bot.send_group_msg(group_id=group_id, message=f"{_cq_reply(msg_id)}{text}")

	if tool_name == "send_group_msg":
		# 兜底原始群发
		group_id = int(arguments["group_id"])  # required
		message = str(arguments.get("message", ""))
		auto_escape = bool(arguments.get("auto_escape", False))
		return await bot.send_group_msg(group_id=group_id, message=message, auto_escape=auto_escape)

	# 未知工具：直接尝试 call_api（但仅限群聊相关）
	return await bot.call_api(tool_name, **arguments)