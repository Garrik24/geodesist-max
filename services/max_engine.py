from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict

import httpx

logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D+", "", phone or "")
    if not digits:
        return ""
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    return digits


def extract_phone(text: str) -> str:
    """
    Вытаскивает телефон из строки вида: "Дмитрий, тел +7961...".
    """
    s = text or ""
    m = re.search(r"(\+?\d[\d\-\s()]{9,}\d)", s)
    return normalize_phone(m.group(1)) if m else ""


@dataclass(frozen=True)
class MaxEngineConfig:
    base_url: str
    api_key: str
    instance: str = "stavgeo-max"


class MaxEngineClient:
    """
    Отправка в MAX через собственный шлюз max-engine (Evolution-совместимый API).
    Сообщение уходит с рабочего аккаунта MAX.
    """

    def __init__(self, cfg: MaxEngineConfig):
        self._cfg = cfg

    async def send_text(self, recipient: str, body: str) -> Dict[str, Any]:
        phone = normalize_phone(recipient)
        if not phone:
            raise ValueError("recipient phone is empty")
        if not body or not body.strip():
            raise ValueError("message body is empty")

        url = f"{self._cfg.base_url.rstrip('/')}/message/sendText/{self._cfg.instance}"
        headers = {"apikey": self._cfg.api_key}
        payload = {"number": phone, "text": body}

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(f"max-engine HTTP {resp.status_code}: {resp.text[:300]}")
            try:
                return resp.json()
            except Exception:
                return {"status_code": resp.status_code, "text": resp.text}
