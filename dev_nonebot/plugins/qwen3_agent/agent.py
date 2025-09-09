import os
import json
import time
import asyncio
from typing import Any, Dict, List, Tuple, Optional

from nonebot import on_message, get_plugin_config, get_driver
from nonebot.rule import is_type
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot, Event, GroupMessageEvent, MessageEvent

from openai import AsyncOpenAI
import tiktoken

from .config import Config
from .tools4onebotv11 import get_openai_tools, call_onebot_tool


# 异步 OpenAI 客户端（DashScope 兼容模式）
client = AsyncOpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

cfg: Config = get_plugin_config(Config)

# 事件响应器：仅处理群消息，设置较低优先级且不阻塞，避免影响其他插件
matcher = on_message(rule=is_type(GroupMessageEvent), priority=99, block=False)


SYSTEM_PROMPT = cfg.system_prompt


def _build_messages(history: List[Tuple[str, str]], system_prompt: Optional[str] = None) -> List[Dict[str, str]]:
    sp = system_prompt or SYSTEM_PROMPT
    msgs: List[Dict[str, str]] = [{"role": "system", "content": sp}]
    for role, content in history:
        msgs.append({"role": role, "content": content})
    return msgs


def _truncate(text: str, max_len: int = 120) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _snapshot_group_state(state: "GroupState") -> Dict[str, Any]:
    return {
        "cooldown": state.cooldown,
        "token_count": state._token_count,
        "history_len": len(state.history),
        "last_activity_ago": round(time.time() - state.last_activity, 1),
    }


# =============== 群上下文与冷却 ===============

class GroupState:
    def __init__(self) -> None:
        self.history: List[Tuple[str, str]] = []  # (role, content) 仅保留文本
        self.cooldown: int = 0
        self.last_activity: float = time.time()
        self._token_count: int = 0  # token 统计
        # 防止在长时间无人说话时重复发送“活跃气氛”的提示
        self.idle_prompt_sent = False
        # 最近一条用户图片的 URL 列表（用于空闲新话题时基于图片联想）
        self.last_images = []

    def _count_tokens(self, text: str) -> int:
        return len(TOKENIZER.encode(text))

    def add_message(self, role: str, content: str, max_tokens: int) -> None:
        self.history.append((role, content))
        self._token_count += self._count_tokens(content)
        # 裁剪：超过窗口则从最早的一条非 system 开始弹出
        while self._token_count > max_tokens and len(self.history) > 1:
            r, c = self.history[1]
            self._token_count -= self._count_tokens(c)
            self.history.pop(1)
        logger.debug(
            f"[dialog] add_message role={role} len={len(content)} tokens={self._count_tokens(content)} "
            f"window={max_tokens} -> history_len={len(self.history)} token_count={self._token_count}"
        )

    def bump_cooldown_by_message(self, delta: int) -> None:
        self.cooldown += delta
        self.last_activity = time.time()

    def bump_cooldown_by_idle(self, delta: int) -> None:
        self.cooldown += delta

    def should_trigger(self, threshold: int) -> bool:
        return self.cooldown >= threshold and any(role == "user" for role, _ in self.history)

    def reset_cooldown(self) -> None:
        self.cooldown = 0


# group_id -> GroupState
GROUP_STATES: Dict[str, GroupState] = {}


def _gid_of_event(event: MessageEvent) -> Optional[str]:
    if isinstance(event, GroupMessageEvent):
        return str(event.group_id)
    return None


# 全局 tokenizer（编码名不合法将抛错，便于尽早发现配置问题）
TOKENIZER = tiktoken.get_encoding(cfg.token_encoding or "cl100k_base")


@matcher.handle()  # type: ignore[misc]
async def _(bot: Bot, event: GroupMessageEvent):
    gid = _gid_of_event(event)
    if gid is None:
        return

    state = GROUP_STATES.setdefault(gid, GroupState())

    # 忽略机器人自身的消息，仅记录“别人”的发言
    try:
        if event.user_id == int(bot.self_id):  # type: ignore[attr-defined]
            return
    except Exception:
        pass

    # 解析消息：提取纯文本与图片段
    msg = event.get_message()
    user_text = msg.extract_plain_text().strip()
    image_urls: List[str] = []
    try:
        for seg in msg:
            if seg.type == "image":
                url = seg.data.get("url") or seg.data.get("file")
                if url:
                    image_urls.append(str(url))
    except Exception:
        pass
    # 记录最近图片（若无图片则清空）
    state.last_images = list(image_urls) if image_urls else []

    # 检查是否 @ 到机器人（或以昵称开头），适配器会自动去除前缀方便命令匹配
    try:
        is_tome_method = getattr(event, "is_tome", None)
        is_tome = bool(is_tome_method()) if callable(is_tome_method) else False
    except Exception:
        is_tome = False

    # 若存在图片且是 @ 机器人：触发 VL（仅输入图片，降低成本）；否则将图片计作一次普通聊天但不立刻回复
    if image_urls and is_tome:
        placeholder = f"[图片x{len(image_urls)}]"
        state.add_message("user", placeholder, cfg.max_history_tokens)
        state.idle_prompt_sent = False
        logger.debug(
            f"[group {gid}] <- user={event.user_id} images={len(image_urls)} preview=\"{_truncate(placeholder)}\" state={_snapshot_group_state(state)}"
        )
        await _handle_images_with_vl(bot, event, gid, state, image_urls)
        return

    if not user_text:
        if image_urls:
            # 非 @ 的图片：仅计入一次普通聊天
            placeholder = f"[图片x{len(image_urls)}]"
            state.add_message("user", placeholder, cfg.max_history_tokens)
            # 有新的用户发言，解除 idle 抑制标记
            state.idle_prompt_sent = False
            logger.debug(
                f"[group {gid}] <- user={event.user_id} images={len(image_urls)} preview=\"{_truncate(placeholder)}\" state={_snapshot_group_state(state)}"
            )
        else:
            return

    if user_text:
        state.add_message("user", user_text, cfg.max_history_tokens)
    # 有新的用户发言，解除 idle 抑制标记
    state.idle_prompt_sent = False
    logger.debug(
        f"[group {gid}] <- user={event.user_id} text_len={len(user_text)} "
        f"preview=\"{_truncate(user_text or placeholder)}\" state={_snapshot_group_state(state)}"
    )
    # 基础冷却 + @机器人加成：仅依据 is_tome（适配器已自动去除前缀/@）
    bonus = 0
    if is_tome:
        bonus += cfg.cooldown_bonus_at_bot
    logger.debug(
        f"[group {gid}] at_check detected_by={'is_tome' if is_tome else 'none'} is_tome={is_tome} bonus={bonus}"
    )

    state.bump_cooldown_by_message(cfg.cooldown_per_message + bonus)
    logger.debug(
        f"[group {gid}] cooldown += {cfg.cooldown_per_message + bonus} (base={cfg.cooldown_per_message}, @bot={bonus}) "
        f"=> {state.cooldown} / threshold={cfg.cooldown_trigger_threshold}"
    )

    # 若达到阈值，触发一次集中 LLM 回复
    if state.should_trigger(cfg.cooldown_trigger_threshold):
        logger.debug(f"[group {gid}] trigger LLM reply with state={_snapshot_group_state(state)}")
        await _trigger_group_llm_reply(bot, event, gid, state)
        state.reset_cooldown()
        logger.debug(f"[group {gid}] cooldown reset to 0 after reply")


async def _trigger_group_llm_reply(bot: Bot, event: GroupMessageEvent, gid: str, state: GroupState) -> None:
    tools = get_openai_tools()
    messages: List[Dict[str, Any]] = _build_messages(state.history)
    model = os.getenv("QWEN_MODEL", cfg.qwen_model)

    logger.debug(
        f"[group {gid}] LLM start model={model} history_len={len(state.history)} tokens={state._token_count} tools={len(tools)}"
    )

    for _round in range(cfg.max_tool_rounds):
        logger.debug(f"[group {gid}] LLM round={_round + 1} messages={len(messages)}")
        rsp = await client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            tools=tools,
            extra_body={"enable_search": bool(getattr(cfg, "enable_search", False))},
        )

        choice = rsp.choices[0]
        msg = choice.message

        if getattr(msg, "tool_calls", None):
            # 工具调用
            for tc in msg.tool_calls:  # type: ignore[union-attr]
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except Exception:
                    args = {}
                logger.debug(f"[group {gid}] tool_call name={name} args={args}")
                try:
                    result = await call_onebot_tool(name, args)
                    content = json.dumps(result, ensure_ascii=False)
                    logger.debug(
                        f"[group {gid}] tool_result name={name} size={len(content)} preview=\"{_truncate(content)}\""
                    )
                except Exception as e:
                    logger.exception(f"tool call failed: {name}")
                    content = json.dumps({"error": str(e)}, ensure_ascii=False)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": content,
                })

            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls  # type: ignore[union-attr]
                ],
            })
            continue

        # 最终回应
        final_text = msg.content or ""
        if final_text:
            logger.debug(
                f"[group {gid}] assistant final len={len(final_text)} preview=\"{_truncate(final_text)}\""
            )
            await bot.send(event, final_text)
            # 将 assistant 回复写入历史
            state.add_message("assistant", final_text, cfg.max_history_tokens)
        # 视为一次活动，刷新 last_activity，避免立刻进入 idle 增长
        state.last_activity = time.time()
        return

    # 超过轮次仍未给出最终答复
    await bot.send(event, "收到。等待更多上下文以给出更完整的回复。")


async def _handle_images_with_vl(bot: Bot, event: GroupMessageEvent, gid: str, state: GroupState, image_urls: List[str]) -> None:
    # 仅传图给 VL，避免高额 token 成本；取前 vl_max_images 张
    urls = image_urls[: max(1, int(getattr(cfg, 'vl_max_images', 1)))]
    model = os.getenv("QWEN_VL_MODEL", getattr(cfg, 'vl_model', 'qwen-vl-max-latest'))
    logger.debug(f"[group {gid}] VL start model={model} images={len(urls)}")

    # 构造符合 dashscope 兼容模式的多模态消息体
    persona = cfg.system_prompt
    sys_text = f"{persona}\n{cfg.vl_system_prompt}"
    msgs: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": sys_text},
            ],
        },
        {
            "role": "user",
            "content": [
                *[
                    {"type": "image_url", "image_url": {"url": u}}
                    for u in urls
                ]
            ],
        },
    ]

    try:
        rsp = await client.chat.completions.create(
            model=model,
            messages=msgs,  # type: ignore[arg-type]
        )
        text = rsp.choices[0].message.content or "(已收到图片)"
    except Exception as e:
        logger.exception("VL request failed")
        text = f"图片解析失败：{e}"

    # 发送到群，并写入历史
    await bot.send(event, text)
    state.add_message("assistant", text, cfg.max_history_tokens)
    state.last_activity = time.time()
    # 视为一次完整回复，重置冷却，避免紧接着再次触发文本 LLM 回复
    before_cd = state.cooldown
    state.reset_cooldown()
    logger.debug(f"[group {gid}] cooldown reset {before_cd}->0 after VL reply")


# =============== 后台闲置冷却累计 ===============

async def _idle_cooldown_task():
    while True:
        try:
            await asyncio.sleep(cfg.idle_interval_seconds)
            now = time.time()
            for gid, state in GROUP_STATES.items():
                # 若在一个周期内没有新消息，则给群叠加闲置冷却
                if now - state.last_activity >= cfg.idle_interval_seconds:
                    before = state.cooldown
                    state.bump_cooldown_by_idle(cfg.cooldown_per_idle_interval)
                    logger.debug(
                        f"[group {gid}] idle +{cfg.cooldown_per_idle_interval} cooldown {before}->{state.cooldown}"
                    )
                    # 冷却达阈值则主动触发一次（无事件场景下），避免长时间沉默；
                    # 但若本轮“空闲活跃提示”已发送，则不再重复发送，直到有新的用户发言
                    if state.should_trigger(cfg.cooldown_trigger_threshold) and not state.idle_prompt_sent:
                        try:
                            logger.debug(f"[group {gid}] idle trigger with state={_snapshot_group_state(state)}")
                            await _trigger_group_llm_reply_idle(gid, state)
                            state.reset_cooldown()
                            logger.debug(f"[group {gid}] cooldown reset to 0 after idle reply")
                        except Exception:
                            logger.exception(f"idle trigger failed: gid={gid}")
                    elif state.idle_prompt_sent:
                        logger.debug(f"[group {gid}] idle trigger skipped (idle_prompt_sent=True)")
        except Exception:
            logger.exception("idle cooldown task error")


driver = get_driver()

@driver.on_startup
async def _start_bg_tasks() -> None:
    # 启动后台闲置冷却任务
    asyncio.create_task(_idle_cooldown_task())
    # 启动时输出关键配置，便于调试
    logger.debug(
        f"[startup] model={os.getenv('QWEN_MODEL', cfg.qwen_model)} "
        f"token_encoding={cfg.token_encoding or 'cl100k_base'} "
        f"window={cfg.max_history_tokens} threshold={cfg.cooldown_trigger_threshold} "
        f"per_msg={cfg.cooldown_per_message} bonus_at_bot={cfg.cooldown_bonus_at_bot} "
        f"idle=({cfg.idle_interval_seconds}s,+{cfg.cooldown_per_idle_interval}) "
        f"max_tool_rounds={cfg.max_tool_rounds}"
    )


async def _trigger_group_llm_reply_idle(gid: str, state: GroupState) -> None:
    """无事件上下文的触发：调用 LLM 并通过工具直接向群发送。"""
    # 若最近一条用户消息为图片，占位在历史中；则优先基于该图片用 VL 抛出新话题
    if state.history and state.history[-1][0] == "user" and state.last_images:
        logger.debug(f"[group {gid}] IDLE using last images to start topic images={len(state.last_images)}")
        ok = await _idle_new_topic_from_images(gid, state)
        if ok:
            return
        logger.debug(f"[group {gid}] IDLE VL topic failed or empty, fallback to text path")
    tools = get_openai_tools()
    # idle 场景：改用专用系统提示，以引导开启轻话题、活跃气氛
    messages: List[Dict[str, Any]] = _build_messages(state.history, system_prompt=cfg.idle_system_prompt)
    model = os.getenv("QWEN_MODEL", cfg.qwen_model)

    logger.debug(
        f"[group {gid}] IDLE LLM start model={model} history_len={len(state.history)} tokens={state._token_count} tools={len(tools)}"
    )

    for _round in range(cfg.max_tool_rounds):
        rsp = await client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            tools=tools,
            extra_body={"enable_search": bool(getattr(cfg, "enable_search", False))},
        )

        choice = rsp.choices[0]
        msg = choice.message

        if getattr(msg, "tool_calls", None):
            # 工具调用
            for tc in msg.tool_calls:  # type: ignore[union-attr]
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except Exception:
                    args = {}
                logger.debug(f"[group {gid}] (idle) tool_call name={name} args={args}")
                try:
                    result = await call_onebot_tool(name, args)
                    content = json.dumps(result, ensure_ascii=False)
                    logger.debug(
                        f"[group {gid}] (idle) tool_result name={name} size={len(content)} preview=\"{_truncate(content)}\""
                    )
                except Exception as e:
                    logger.exception(f"tool call failed (idle): {name}")
                    content = json.dumps({"error": str(e)}, ensure_ascii=False)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": content,
                })

            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls  # type: ignore[union-attr]
                ],
            })
            continue

        # 最终文本：直接发群
        final_text = msg.content or ""
        if final_text:
            logger.debug(
                f"[group {gid}] (idle) assistant final len={len(final_text)} preview=\"{_truncate(final_text)}\""
            )
            await call_onebot_tool("send_group_msg", {"group_id": int(gid), "message": final_text})
            state.add_message("assistant", final_text, cfg.max_history_tokens)
            # 标记已发送过一次“空闲活跃提示”，并刷新活动时间
            state.idle_prompt_sent = True
            state.last_activity = time.time()
        return

    # 超过轮次仍未给出最终答复
    await call_onebot_tool("send_group_msg", {"group_id": int(gid), "message": "（自动播报）收到上下文，将在有更多线索时继续总结。"})
    # 兜底文本同样计入历史并设置抑制标记
    state.add_message("assistant", "（自动播报）收到上下文，将在有更多线索时继续总结。", cfg.max_history_tokens)
    state.idle_prompt_sent = True
    state.last_activity = time.time()


async def _idle_new_topic_from_images(gid: str, state: GroupState) -> bool:
    """基于最近图片，用 VL 模型抛出一个新话题；成功返回 True。"""
    urls = state.last_images[: max(1, int(getattr(cfg, 'vl_max_images', 1)))]
    if not urls:
        return False
    model = os.getenv("QWEN_VL_MODEL", getattr(cfg, 'vl_model', 'qwen-vl-max-latest'))
    logger.debug(f"[group {gid}] IDLE-VL start model={model} images={len(urls)}")

    persona = cfg.system_prompt
    sys_text = f"{persona}\n{cfg.vl_idle_system_prompt}"
    msgs: List[Dict[str, Any]] = [
        {"role": "system", "content": [{"type": "text", "text": sys_text}]},
        {
            "role": "user",
            "content": [
                *[{"type": "image_url", "image_url": {"url": u}} for u in urls]
            ],
        },
    ]

    try:
        rsp = await client.chat.completions.create(model=model, messages=msgs)  # type: ignore[arg-type]
        text = (rsp.choices[0].message.content or "").strip()
        if not text:
            return False
    except Exception as e:
        logger.exception("IDLE VL topic failed")
        return False

    await call_onebot_tool("send_group_msg", {"group_id": int(gid), "message": text})
    state.add_message("assistant", text, cfg.max_history_tokens)
    state.idle_prompt_sent = True
    state.last_activity = time.time()
    return True
