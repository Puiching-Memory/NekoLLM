import os
import json
import time
import asyncio
from typing import Any, Dict, List, Tuple, Optional

from nonebot import on_message, get_plugin_config, get_driver
from nonebot.rule import is_type
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageEvent

from openai import AsyncOpenAI
import tiktoken

from .config import Config


# 异步 OpenAI 客户端（DashScope 兼容模式）
client = AsyncOpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

cfg: Config = get_plugin_config(Config)
SYSTEM_PROMPT = cfg.system_prompt
# 事件响应器：仅处理群消息，设置较低优先级且不阻塞，避免影响其他插件
matcher = on_message(rule=is_type(GroupMessageEvent))



# =============== 小工具函数 ===============


def _parse_event_content(event: MessageEvent) -> Tuple[str, List[str]]:
    """提取事件中的纯文本与图片 URL 列表。"""
    msg = event.get_message()
    user_text = msg.extract_plain_text().strip()
    image_urls: List[str] = []
    for seg in msg:
        if seg.type == "image":
            url = seg.data.get("url") or seg.data.get("file")
            if url:
                image_urls.append(str(url))
    return user_text, image_urls

 


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


# 全局 tokenizer（编码名不合法将抛错，便于尽早发现配置问题）
TOKENIZER = tiktoken.get_encoding(cfg.token_encoding or "cl100k_base")


# =============== 复用：LLM 与 VL 处理（无工具） ===============

async def _run_llm_simple(
    gid: str,
    messages: List[Dict[str, Any]],
    model: str,
    idle: bool = False,
) -> str:
    """简单的 ChatCompletions 调用（不使用工具）。

    返回：模型文本；失败时返回空串。
    """
    try:
        logger.debug(
            f"[group {gid}] {'IDLE ' if idle else ''}LLM messages={len(messages)}"
        )
        rsp = await client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
        )
        return rsp.choices[0].message.content or ""
    except Exception:
        logger.exception("LLM request failed")
        return ""


def _build_vl_messages(sys_text: str, urls: List[str]) -> List[Dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": [{"type": "text", "text": sys_text}],
        },
        {
            "role": "user",
            "content": [
                *[{"type": "image_url", "image_url": {"url": u}} for u in urls]
            ],
        },
    ]


async def _generate_vl_text(sys_text: str, urls: List[str], model: str) -> str:
    """调用多模态模型，返回生成文本；失败时返回错误提示。"""
    msgs = _build_vl_messages(sys_text, urls)
    try:
        rsp = await client.chat.completions.create(model=model, messages=msgs)  # type: ignore[arg-type]
        return rsp.choices[0].message.content or "(已收到图片)"
    except Exception as e:
        logger.exception("VL request failed")
        return f"图片解析失败：{e}"


@matcher.handle()  # type: ignore[misc]
async def _(bot: Bot, event: GroupMessageEvent):
    gid = str(event.group_id)

    state = GROUP_STATES.setdefault(gid, GroupState())

    # 机器人自身消息：记录到历史，但不触发逻辑
    if str(event.user_id) == str(getattr(bot, "self_id", "")):
        self_text, self_images = _parse_event_content(event)
        if self_text:
            state.add_message("assistant", self_text, cfg.max_history_tokens)
        elif self_images:
            state.add_message("assistant", f"[图片x{len(self_images)}]", cfg.max_history_tokens)
        state.last_activity = time.time()
        return

    # 解析消息：提取纯文本与图片段
    user_text, image_urls = _parse_event_content(event)
    # 记录最近图片（若无图片则清空）
    state.last_images = list(image_urls) if image_urls else []

    # 检查是否 @ 到机器人（适配器会自动去除前缀方便命令匹配）
    is_tome = bool(getattr(event, "is_tome", lambda: False)())

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
    preview = user_text if user_text else (f"[图片x{len(image_urls)}]" if image_urls else "")
    logger.debug(
        f"[group {gid}] <- user={event.user_id} text_len={len(user_text)} preview=\"{_truncate(preview)}\" state={_snapshot_group_state(state)}"
    )
    # 基础冷却 + @机器人加成：仅依据 is_tome（适配器已自动去除前缀/@）
    bonus = cfg.cooldown_bonus_at_bot if is_tome else 0

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
    # 统一的 LLM 调用（无工具）
    messages: List[Dict[str, Any]] = _build_messages(state.history)
    model = os.getenv("QWEN_MODEL") or cfg.qwen_model

    logger.debug(
        f"[group {gid}] LLM start model={model} history_len={len(state.history)} tokens={state._token_count}"
    )

    final_text = await _run_llm_simple(gid, messages, model)

    if final_text:
        logger.debug(f"[group {gid}] assistant final len={len(final_text)} preview=\"{_truncate(final_text)}\"")
        await bot.send(event, final_text)
        state.add_message("assistant", final_text, cfg.max_history_tokens)
    else:
        await bot.send(event, "收到。等待更多上下文以给出更完整的回复。")

    # 视为一次活动，刷新 last_activity，避免立刻进入 idle 增长
    state.last_activity = time.time()


async def _handle_images_with_vl(bot: Bot, event: GroupMessageEvent, gid: str, state: GroupState, image_urls: List[str]) -> None:
    # 仅传图给 VL，避免高额 token 成本；取前 vl_max_images 张
    urls = image_urls[: max(1, int(getattr(cfg, 'vl_max_images', 1)))]
    sys_text = f"{cfg.system_prompt}\n{cfg.vl_system_prompt}"
    model = os.getenv("QWEN_VL_MODEL") or getattr(cfg, 'vl_model', 'qwen-vl-max-latest')
    logger.debug(f"[group {gid}] VL start model={model} images={len(urls)}")

    text = await _generate_vl_text(sys_text, urls, model)
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
                    # 若本轮“空闲活跃提示”已发送，则等待新的用户发言再触发
                    if state.should_trigger(cfg.cooldown_trigger_threshold) and not state.idle_prompt_sent:
                        try:
                            logger.debug(f"[group {gid}] idle trigger with state={_snapshot_group_state(state)}")
                            await _trigger_group_llm_reply_idle(gid, state)
                            state.reset_cooldown()
                            logger.debug(f"[group {gid}] cooldown reset to 0 after idle reply")
                        except Exception:
                            logger.exception(f"idle trigger failed: gid={gid}")
                    # 已发送过一次提示，则等待新的用户发言再触发
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
    messages: List[Dict[str, Any]] = _build_messages(state.history, system_prompt=cfg.idle_system_prompt)
    model = os.getenv("QWEN_MODEL") or cfg.qwen_model

    logger.debug(
        f"[group {gid}] IDLE LLM start model={model} history_len={len(state.history)} tokens={state._token_count}"
    )

    final_text = await _run_llm_simple(gid, messages, model, idle=True)

    if final_text:
        logger.debug(f"[group {gid}] (idle) assistant final len={len(final_text)} preview=\"{_truncate(final_text)}\"")
        await _send_group_text(gid, final_text)
        state.add_message("assistant", final_text, cfg.max_history_tokens)
        state.idle_prompt_sent = True
        state.last_activity = time.time()
    else:
        # 超过轮次仍未给出最终答复
        fallback = "（自动播报）收到上下文，将在有更多线索时继续总结。"
        await _send_group_text(gid, fallback)
        state.add_message("assistant", fallback, cfg.max_history_tokens)
        state.idle_prompt_sent = True
        state.last_activity = time.time()


async def _idle_new_topic_from_images(gid: str, state: GroupState) -> bool:
    """基于最近图片，用 VL 模型抛出一个新话题；成功返回 True。"""
    urls = state.last_images[: max(1, int(getattr(cfg, 'vl_max_images', 1)))]
    if not urls:
        return False

    sys_text = f"{cfg.system_prompt}\n{cfg.vl_idle_system_prompt}"
    model = os.getenv("QWEN_VL_MODEL") or getattr(cfg, 'vl_model', 'qwen-vl-max-latest')
    logger.debug(f"[group {gid}] IDLE-VL start model={model} images={len(urls)}")

    text = await _generate_vl_text(sys_text, urls, model)
    if not text.strip():
        return False

    await _send_group_text(gid, text)
    state.add_message("assistant", text, cfg.max_history_tokens)
    state.idle_prompt_sent = True
    state.last_activity = time.time()
    return True

def _build_vl_messages(sys_text: str, urls: List[str]) -> List[Dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": [{"type": "text", "text": sys_text}],
        },
        {
            "role": "user",
            "content": [
                *[{"type": "image_url", "image_url": {"url": u}} for u in urls]
            ],
        },
    ]


async def _generate_vl_text(sys_text: str, urls: List[str], model: str) -> str:
    """调用多模态模型，返回生成文本；失败时返回错误提示。"""
    msgs = _build_vl_messages(sys_text, urls)
    try:
        rsp = await client.chat.completions.create(model=model, messages=msgs)  # type: ignore[arg-type]
        return rsp.choices[0].message.content or "(已收到图片)"
    except Exception as e:
        logger.exception("VL request failed")
        return f"图片解析失败：{e}"


async def _send_group_text(gid: str, text: str) -> None:
    """通过可用的 Bot 主动向群发送文本（替代工具调用）。"""
    try:
        bots = get_driver().bots
        if not bots:
            logger.warning("no connected bot to send group message")
            return
        bot = next(iter(bots.values()))
        await bot.call_api("send_group_msg", group_id=int(gid), message=text)
    except Exception:
        logger.exception("failed to send group message")
