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
class WappiMaxConfig:
    api_token: str
    profile_id: str
    base_url: str = "https://wappi.pro"


class WappiMaxClient:
    def __init__(self, cfg: WappiMaxConfig):
        self._cfg = cfg

    async def send_text(self, recipient: str, body: str) -> Dict[str, Any]:
        phone = normalize_phone(recipient)
        if not phone:
            raise ValueError("recipient phone is empty")
        if not body or not body.strip():
            raise ValueError("message body is empty")

        url = f"{self._cfg.base_url}/maxapi/async/message/send"
        headers = {"Authorization": self._cfg.api_token}
        params = {"profile_id": self._cfg.profile_id}
        payload = {"recipient": phone, "body": body}

        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            resp = await client.post(url, headers=headers, params=params, json=payload)
            resp.raise_for_status()
            try:
                return resp.json()
            except Exception:
                return {"status_code": resp.status_code, "text": resp.text}

