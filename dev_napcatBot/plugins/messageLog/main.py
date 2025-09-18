from ncatbot.plugin import CompatibleEnrollment
from ncatbot.core import GroupMessage
from pathlib import Path
from datetime import datetime
import re
import json
import aiohttp

from ncatbot.plugin import BasePlugin, CompatibleEnrollment
from ncatbot.utils import get_log
from ncatbot.core import GroupMessage

from pathlib import Path
from datetime import datetime
import re
import json
import aiohttp

logger = get_log()
bot = CompatibleEnrollment


class messageLog(BasePlugin):
    name = "messageLog"
    version = "0.1.0"

    def _base_logs_dir(self) -> Path:
        return Path(__file__).resolve().parents[2] / "logs"

    def _append_jsonl(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def _extract_image_urls_from_raw(self, raw: str | None):
        if not raw:
            return []
        return re.findall(r"(https?://[^\s\]]+\.(?:jpg|jpeg|png|gif|webp|bmp|tiff|ico)(?:\?[^\s\]]*)?)", raw, flags=re.IGNORECASE)

    async def _download(self, url: str, dest: Path):
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with aiohttp.ClientSession() as s:
            resp = await s.get(url)
            content = await resp.read()
        with dest.open("wb") as f:
            f.write(content)
        return str(dest)

    @bot.group_event()
    async def on_group_message(self, msg: GroupMessage):
        group_id = getattr(msg, "group_id", "unknown")
        raw = getattr(msg, "raw_message", "")
        ts = getattr(msg, "time", None)

        urls = self._extract_image_urls_from_raw(raw)
        base = self._base_logs_dir()
        images_dir = base / "images" / f"group_{group_id}"
        results = []
        for i, url in enumerate(urls, start=1):
            name = f"{int(ts) if ts else int(datetime.now().timestamp())}_{i}{Path(url).suffix}"
            dest = images_dir / name
            path = await self._download(url, dest)
            results.append({"path": path, "ok": True})

        messages_file = base / "messages" / f"group_{group_id}.jsonl"
        record = {
            "time": ts,
            "datetime": datetime.fromtimestamp(ts).isoformat() if ts else datetime.now().isoformat(),
            "raw_message": raw,
            "image_urls": urls,
            "images_saved": results,
        }
        self._append_jsonl(messages_file, record)
