from ncatbot.plugin import BasePlugin, CompatibleEnrollment
from ncatbot.core import GroupMessage
from ncatbot.utils import get_log

from pathlib import Path
from datetime import datetime
import asyncio
import json
import os
import re
from typing import Any, Dict, Iterable, List, Tuple, Optional, Union
import shutil

import aiohttp

logger = get_log()
bot = CompatibleEnrollment


# ---------- 工具函数 ----------
def _base_logs_dir() -> Path:
    # 当前文件: dev_napcatBot/plugins/messageLog/main.py
    # 目标日志根目录: dev_napcatBot/logs
    return Path(__file__).resolve().parents[2] / "logs"


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _safe_default(o: Any) -> Any:
    # 将不可序列化对象降级为字符串
    try:
        return getattr(o, "__dict__", str(o))
    except Exception:
        return str(o)


def _append_jsonl(path: Path, data: Dict[str, Any]) -> None:
    _ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, default=_safe_default) + "\n")


def _clean_filename(name: str) -> str:
    # 清理不安全的文件名字符
    return re.sub(r"[^\w\-\.]+", "_", name)


def _guess_ext_from_content_type(ct: str | None) -> str:
    if not ct:
        return ""
    ct = ct.lower()
    # 常见图片类型映射
    mapping = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/tiff": ".tiff",
        "image/x-icon": ".ico",
    }
    return mapping.get(ct, "")


def _extract_image_urls_from_segments(message: Any) -> List[str]:
    urls: List[str] = []
    if message is None:
        return urls
    # 尝试将 message 作为可迭代对象处理
    try:
        iterator: Iterable[Any] = message  # type: ignore
    except Exception:
        return urls

    for seg in iterator:
        seg_type = None
        seg_data = None
        # 兼容对象或字典
        if hasattr(seg, "type"):
            seg_type = getattr(seg, "type", None)
        elif isinstance(seg, dict):
            seg_type = seg.get("type")

        if hasattr(seg, "data"):
            seg_data = getattr(seg, "data", None)
        elif isinstance(seg, dict):
            seg_data = seg.get("data")
        if not isinstance(seg_data, dict):
            seg_data = {}

        if str(seg_type).lower() in {"image", "flash", "image_url"}:
            for key in ("url", "file", "image_url", "path"):
                val = seg_data.get(key)
                if isinstance(val, str) and (val.startswith("http://") or val.startswith("https://")):
                    urls.append(val)
    return list(dict.fromkeys(urls))  # 去重保持顺序


def _extract_image_urls_from_raw(raw: str | None) -> List[str]:
    if not raw:
        return []
    urls: List[str] = []
    # 匹配CQ码中的 image 段: [CQ:image,file=...,url=...]
    for key in ("url", "file"):
        pattern = rf"\[CQ:image,[^\]]*{key}=([^,\]]+)"
        urls.extend(re.findall(pattern, raw))
    # 只保留 http(s) 链接
    urls = [u for u in urls if u.startswith("http://") or u.startswith("https://")]
    return list(dict.fromkeys(urls))


def _extract_local_image_paths_from_segments(message: Any) -> List[str]:
    paths: List[str] = []
    if message is None:
        return paths
    try:
        iterator: Iterable[Any] = message  # type: ignore
    except Exception:
        return paths

    for seg in iterator:
        seg_data = None
        if hasattr(seg, "data"):
            seg_data = getattr(seg, "data", None)
        elif isinstance(seg, dict):
            seg_data = seg.get("data")
        if not isinstance(seg_data, dict):
            continue
        for key in ("path", "file"):
            val = seg_data.get(key)
            if isinstance(val, str) and os.path.exists(val):
                paths.append(val)
    # 去重
    return list(dict.fromkeys(paths))


async def _download_one_aiohttp(url: str, dest: Path) -> Tuple[str, bool, Optional[str]]:
    """返回 (路径, 成功, 错误)
    若无法从URL推断后缀，将保持原文件名后缀或不带后缀保存。
    """
    assert aiohttp is not None
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return (str(dest), False, f"HTTP {resp.status}")
                # 若无后缀，根据content-type猜测
                if dest.suffix == "":
                    ext = _guess_ext_from_content_type(resp.headers.get("Content-Type"))
                    if ext:
                        dest = dest.with_suffix(ext)
                _ensure_dir(dest.parent)
                with dest.open("wb") as f:
                    async for chunk in resp.content.iter_chunked(64 * 1024):
                        f.write(chunk)
        return (str(dest), True, None)
    except Exception as e:
        return (str(dest), False, str(e))


async def _download_images(urls: List[str], dest_dir: Path, filename_prefix: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    if not urls:
        return results
    _ensure_dir(dest_dir)

    tasks = []
    for idx, url in enumerate(urls, start=1):
        # 根据URL末尾尝试带上扩展名
        url_path = Path(re.sub(r"[?#].*$", "", url))  # 去掉query/fragment
        ext = url_path.suffix
        filename = _clean_filename(f"{filename_prefix}_{idx}{ext}") if ext else _clean_filename(f"{filename_prefix}_{idx}")
        dest = dest_dir / filename
        tasks.append(_download_one_aiohttp(url, dest))

    for res in await asyncio.gather(*tasks, return_exceptions=True):
        if isinstance(res, Exception):
            results.append({"path": None, "ok": False, "error": str(res)})
        else:
            path, ok, err = res
            results.append({"path": path if ok else None, "ok": ok, "error": err})
    return results


async def _copy_local_images(paths: List[str], dest_dir: Path, filename_prefix: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    if not paths:
        return results
    _ensure_dir(dest_dir)

    for idx, src in enumerate(paths, start=1):
        try:
            ext = Path(src).suffix
            filename = _clean_filename(f"{filename_prefix}_local_{idx}{ext}") if ext else _clean_filename(f"{filename_prefix}_local_{idx}")
            dest = dest_dir / filename
            # 使用线程以避免阻塞
            await asyncio.to_thread(shutil.copyfile, src, dest)
            results.append({"path": str(dest), "ok": True, "error": None})
        except Exception as e:
            results.append({"path": None, "ok": False, "error": str(e)})
    return results


def _serialize_message_segments(message: Any) -> Any:
    # 尝试将 Message 段序列化为基础dict
    try:
        iterator: Iterable[Any] = message  # type: ignore
    except Exception:
        return _safe_default(message)

    out = []
    for seg in iterator:
        if isinstance(seg, dict):
            out.append(seg)
            continue
        item: Dict[str, Any] = {}
        for key in ("type", "data", "text"):
            val = getattr(seg, key, None)
            if val is not None:
                item[key] = val
        if not item:
            item = {"repr": str(seg)}
        out.append(item)
    return out


class messageLog(BasePlugin):
    name = "messageLog"  # 插件名
    version = "0.1.0"  # 插件版本

    @bot.group_event()
    async def on_group_message(msg: GroupMessage):
        """保存群消息文本与图片到本地。"""
        try:
            # 基本字段
            group_id = getattr(msg, "group_id", "unknown")
            user_id = getattr(msg, "user_id", None)
            self_id = getattr(msg, "self_id", None)
            msg_id = getattr(msg, "message_id", None)
            raw_message = getattr(msg, "raw_message", None)
            message_obj = getattr(msg, "message", None)
            ts = getattr(msg, "time", None)

            # 提取图片URL与本地路径
            urls = []
            urls.extend(_extract_image_urls_from_segments(message_obj))
            urls.extend(_extract_image_urls_from_raw(raw_message if isinstance(raw_message, str) else None))
            urls = list(dict.fromkeys(urls))
            local_paths = _extract_local_image_paths_from_segments(message_obj)

            # 保存图片（下载+复制）
            base = _base_logs_dir()
            images_dir = base / "images" / f"group_{group_id}"
            filename_prefix = _clean_filename(f"{int(ts) if ts else int(datetime.now().timestamp())}_{msg_id or 'msg'}")
            download_results = await _download_images(urls, images_dir, filename_prefix)
            copy_results = await _copy_local_images(local_paths, images_dir, filename_prefix)

            # 记录文本
            messages_dir = base / "messages"
            messages_file = messages_dir / f"group_{group_id}.jsonl"
            record: Dict[str, Any] = {
                "time": ts,
                "datetime": datetime.fromtimestamp(ts).isoformat() if ts else datetime.now().isoformat(),
                "group_id": group_id,
                "user_id": user_id,
                "self_id": self_id,
                "message_id": msg_id,
                "raw_message": raw_message,
                "message": _serialize_message_segments(message_obj),
                "image_urls": urls,
                "local_image_paths": local_paths,
                "images_saved": [
                    {**r, "method": "download"} for r in download_results
                ] + [
                    {**r, "method": "copy"} for r in copy_results
                ],
            }
            _append_jsonl(messages_file, record)

            logger.info(f"messageLog 保存完成: group={group_id} msg_id={msg_id} 文本+图片")
        except Exception as e:
            logger.exception(f"messageLog 处理群消息失败: {e}")

    @bot.notice_event()
    async def on_notice_event(msg: dict):
        try:
            ts = (msg or {}).get("time") if isinstance(msg, dict) else None
            base = _base_logs_dir()
            notice_dir = base / "notice"
            notice_file = notice_dir / "notice.jsonl"

            record = {
                "datetime": datetime.fromtimestamp(ts).isoformat() if isinstance(ts, (int, float)) else datetime.now().isoformat(),
                "payload": msg,
            }
            _append_jsonl(notice_file, record)
            logger.info("notice 事件已保存")
        except Exception as e:
            logger.exception(f"保存 notice 事件失败: {e}")

    @bot.request_event()
    async def on_request_event(msg: Union[GroupMessage, dict]):
        try:
            ts = getattr(msg, "time", None) if not isinstance(msg, dict) else msg.get("time")
            base = _base_logs_dir()
            req_dir = base / "requests"
            req_file = req_dir / "request.jsonl"

            payload: Any
            if isinstance(msg, dict):
                payload = msg
            else:
                # 尝试序列化 GroupMessage
                payload = {
                    "time": getattr(msg, "time", None),
                    "group_id": getattr(msg, "group_id", None),
                    "user_id": getattr(msg, "user_id", None),
                    "message_id": getattr(msg, "message_id", None),
                    "raw_message": getattr(msg, "raw_message", None),
                    "message": _serialize_message_segments(getattr(msg, "message", None)),
                }

            record = {
                "datetime": datetime.fromtimestamp(ts).isoformat() if isinstance(ts, (int, float)) else datetime.now().isoformat(),
                "payload": payload,
            }
            _append_jsonl(req_file, record)
            logger.info("request 事件已保存")
        except Exception as e:
            logger.exception(f"保存 request 事件失败: {e}")
