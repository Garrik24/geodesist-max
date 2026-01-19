import logging
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import JSONResponse

from config import (
    AMOCRM_ACCESS_TOKEN,
    AMOCRM_DOMAIN,
    DEBUG,
    WAPPI_API_TOKEN,
    WAPPI_MAX_PROFILE_ID,
    require_env,
)
from services.amocrm import AmoCRMClient, AmoConfig
from services.wappi_max import WappiMaxClient, WappiMaxConfig, extract_phone, normalize_phone

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("geodesist-max")

app = FastAPI(title="Geodesist Max", version="1.0.0")

# in-memory dedup
_DEDUP: set[str] = set()


def _dedup(key: str) -> bool:
    if key in _DEDUP:
        return True
    if len(_DEDUP) > 5000:
        _DEDUP.clear()
    _DEDUP.add(key)
    return False


def _format_message(
    lead_id: int,
    client_name: str,
    client_phone: str,
    work_type: str,
    address: str,
    time_slot: str,
) -> str:
    return (
        "🧭 ВЫЕЗД ГЕОДЕЗИСТА\n\n"
        f"👤 Клиент: {client_name}\n"
        f"☎️ Телефон: {client_phone}\n"
        f"🧩 Тип работ: {work_type}\n"
        f"📍 Адрес: {address}\n"
        f"🕒 Когда: {time_slot}\n\n"
        f"ID сделки: {lead_id}\n"
    )


async def _process_geodesist_webhook(
    lead_id: int,
    geodesist: Optional[str],
    geodesist_phone: Optional[str],
    work_type: Optional[str],
    address: Optional[str],
    time_slot: Optional[str],
    client_name: Optional[str],
    client_phone: Optional[str],
) -> None:
    # resolve geodesist phone
    phone = normalize_phone(geodesist_phone or "") or extract_phone(geodesist or "")
    if not phone:
        raise ValueError("Не удалось определить телефон геодезиста")

    # message data
    cn = (client_name or "").strip() or "Не указано"
    cp = (client_phone or "").strip() or "Не указано"
    wt = (work_type or "").strip() or "Не указано"
    addr = (address or "").strip() or "Не указано"
    ts = (time_slot or "").strip() or "Не указано"

    text = _format_message(lead_id, cn, cp, wt, addr, ts)

    # clients
    wappi = WappiMaxClient(
        WappiMaxConfig(
            api_token=require_env("WAPPI_API_TOKEN", WAPPI_API_TOKEN),
            profile_id=require_env("WAPPI_MAX_PROFILE_ID", WAPPI_MAX_PROFILE_ID),
        )
    )
    amo = AmoCRMClient(
        AmoConfig(
            domain=require_env("AMOCRM_DOMAIN", AMOCRM_DOMAIN),
            access_token=require_env("AMOCRM_ACCESS_TOKEN", AMOCRM_ACCESS_TOKEN),
        )
    )

    wappi_result = await wappi.send_text(recipient=phone, body=text)

    note = (
        "✅ Геодезисту отправлено в MAX\n\n"
        f"Геодезист: {phone}\n"
        f"Клиент: {cn}\n"
        f"Телефон: {cp}\n"
        f"Тип работ: {wt}\n"
        f"Адрес: {addr}\n"
        f"Когда: {ts}\n\n"
        f"Wappi: {wappi_result}"
    )
    await amo.add_note_to_lead(lead_id, note)


@app.get("/")
async def root():
    return {"status": "ok", "service": "geodesist-max"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/webhook/amocrm/geodesist-assigned")
async def geodesist_assigned(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook от робота AmoCRM.
    Поддерживает JSON и form-urlencoded.
    """
    try:
        content_type = (request.headers.get("content-type") or "").lower()
        body = {}
        if "application/json" in content_type:
            body = await request.json()
        else:
            form = await request.form()
            body = dict(form)

        lead_id_raw = body.get("lead_id") or body.get("leadId") or body.get("id")
        if lead_id_raw is None:
            return JSONResponse({"status": "error", "reason": "lead_id_required"}, status_code=200)
        try:
            lead_id = int(str(lead_id_raw).strip())
        except Exception:
            return JSONResponse({"status": "error", "reason": "lead_id_invalid"}, status_code=200)

        geodesist = body.get("geodesist")
        geodesist_phone = body.get("geodesist_phone") or body.get("geodesistPhone")
        work_type = body.get("work_type") or body.get("workType")
        address = body.get("address")
        time_slot = body.get("time_slot") or body.get("timeSlot")
        client_name = body.get("client_name") or body.get("clientName")
        client_phone = body.get("client_phone") or body.get("clientPhone")

        dedup_key = f"{lead_id}:{geodesist_phone or geodesist or ''}:{work_type or ''}:{address or ''}:{time_slot or ''}"
        if _dedup(dedup_key):
            return JSONResponse({"status": "ignored", "reason": "duplicate"}, status_code=200)

        background_tasks.add_task(
            _process_geodesist_webhook,
            lead_id,
            str(geodesist).strip() if geodesist is not None else None,
            str(geodesist_phone).strip() if geodesist_phone is not None else None,
            str(work_type).strip() if work_type is not None else None,
            str(address).strip() if address is not None else None,
            str(time_slot).strip() if time_slot is not None else None,
            str(client_name).strip() if client_name is not None else None,
            str(client_phone).strip() if client_phone is not None else None,
        )

        return JSONResponse({"status": "processing", "lead_id": lead_id}, status_code=200)
    except Exception as e:
        logger.error("Webhook error: %s", e)
        return JSONResponse({"status": "error"}, status_code=200)

