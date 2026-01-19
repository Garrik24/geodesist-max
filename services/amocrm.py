from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, List

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AmoConfig:
    domain: str
    access_token: str


class AmoCRMClient:
    def __init__(self, cfg: AmoConfig):
        self._cfg = cfg
        self._base_url = f"https://{cfg.domain}/api/v4"
        self._headers = {
            "Authorization": f"Bearer {cfg.access_token}",
            "Content-Type": "application/json",
        }

    async def add_note_to_lead(self, lead_id: int, text: str) -> Dict[str, Any]:
        url = f"{self._base_url}/leads/{lead_id}/notes"
        payload = [{"note_type": "common", "params": {"text": text}}]
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            resp = await client.post(url, headers=self._headers, json=payload)
            resp.raise_for_status()
            try:
                return resp.json()
            except Exception:
                return {"status_code": resp.status_code, "text": resp.text}

    async def get_lead(self, lead_id: int) -> Dict[str, Any]:
        url = f"{self._base_url}/leads/{lead_id}"
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            resp = await client.get(url, headers=self._headers, params={"with": "contacts"})
            resp.raise_for_status()
            return resp.json()

    async def get_contact(self, contact_id: int) -> Dict[str, Any]:
        url = f"{self._base_url}/contacts/{contact_id}"
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            resp = await client.get(url, headers=self._headers)
            resp.raise_for_status()
            return resp.json()

    async def get_pipelines(self) -> Dict[str, Any]:
        """
        Возвращает воронки сделок со статусами.
        GET /api/v4/leads/pipelines
        """
        url = f"{self._base_url}/leads/pipelines"
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            resp = await client.get(url, headers=self._headers)
            resp.raise_for_status()
            return resp.json()

