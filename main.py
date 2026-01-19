import logging
import re
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import JSONResponse

from config import (
    AMOCRM_ACCESS_TOKEN,
    AMOCRM_DOMAIN,
    AMO_ASSIGNED_STATUS_NAME,
    AMO_FIELD_NAME_ADDRESS,
    AMO_FIELD_NAME_GEODESIST,
    AMO_FIELD_NAME_TIME,
    AMO_FIELD_NAME_CAD_1,
    AMO_FIELD_NAME_CAD_2,
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

# cache: pipeline_id -> { status_name_lower: status_id }
_PIPELINES_CACHE: dict[int, dict[str, int]] = {}


def _dedup(key: str) -> bool:
    if key in _DEDUP:
        return True
    if len(_DEDUP) > 5000:
        _DEDUP.clear()
    _DEDUP.add(key)
    return False


def _extract_first_lead_event(form: dict) -> tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
    """
    AmoCRM webhooks (настройки -> Webhooks) присылают form-urlencoded вида:
      leads[status][0][id]=...
      leads[status][0][pipeline_id]=...
      leads[status][0][status_id]=...
      leads[status][0][updated_at]=...

    Возвращаем: (lead_id, pipeline_id, status_id, updated_at)
    """
    lead_id = None
    pipeline_id = None
    status_id = None
    updated_at = None

    for k, v in form.items():
        if not isinstance(v, str):
            continue
        if lead_id is None and re.search(r"leads\[(?:status|update)\]\[\d+\]\[id\]$", k):
            if v.isdigit():
                lead_id = int(v)
        if pipeline_id is None and re.search(r"leads\[(?:status|update)\]\[\d+\]\[pipeline_id\]$", k):
            if v.isdigit():
                pipeline_id = int(v)
        if status_id is None and re.search(r"leads\[(?:status|update)\]\[\d+\]\[status_id\]$", k):
            if v.isdigit():
                status_id = int(v)
        if updated_at is None and re.search(r"leads\[(?:status|update)\]\[\d+\]\[updated_at\]$", k):
            if v.isdigit():
                updated_at = int(v)

    # fallback: иногда ключи могут быть другими — берём первое подходящее leads..[id]
    if lead_id is None:
        for k, v in form.items():
            if isinstance(v, str) and v.isdigit() and k.endswith("[id]") and "leads" in k:
                lead_id = int(v)
                break

    return lead_id, pipeline_id, status_id, updated_at


def _cf_value_by_name(lead: dict, field_name: str) -> str:
    target = (field_name or "").strip().lower()
    if not target:
        return ""
    for cf in lead.get("custom_fields_values") or []:
        name = str(cf.get("field_name") or "").strip().lower()
        if name != target:
            continue
        values = cf.get("values") or []
        if not values:
            return ""
        v0 = values[0] or {}
        if isinstance(v0, dict):
            if v0.get("value") is not None:
                return str(v0["value"]).strip()
            if v0.get("enum") is not None:
                return str(v0["enum"]).strip()
            if v0.get("enum_id") is not None:
                return str(v0["enum_id"]).strip()
        return ""
    return ""


def _cf_values_by_names(lead: dict, field_names: list[str]) -> list[str]:
    """
    Берёт значения нескольких полей по точному названию. Пустые отбрасывает.
    """
    out: list[str] = []
    for n in field_names:
        v = _cf_value_by_name(lead, n)
        if v:
            out.append(v)
    return out


def _contact_phone(contact: dict) -> str:
    for cf in contact.get("custom_fields_values") or []:
        if cf.get("field_code") != "PHONE":
            continue
        values = cf.get("values") or []
        for v in values:
            if isinstance(v, dict) and v.get("value"):
                return str(v["value"]).strip()
    return ""


def _primary_contact_id(lead: dict) -> Optional[int]:
    embedded = lead.get("_embedded") or {}
    contacts = embedded.get("contacts") or []
    if not contacts:
        return None
    cid = (contacts[0] or {}).get("id")
    return int(cid) if cid else None


async def _get_assigned_status_id(amo: AmoCRMClient, pipeline_id: int) -> Optional[int]:
    if pipeline_id in _PIPELINES_CACHE:
        return _PIPELINES_CACHE[pipeline_id].get(AMO_ASSIGNED_STATUS_NAME.strip().lower())

    data = await amo.get_pipelines()
    pipelines = data.get("_embedded", {}).get("pipelines", [])
    for p in pipelines:
        pid = p.get("id")
        if not pid:
            continue
        statuses = p.get("_embedded", {}).get("statuses", []) or []
        mapping: dict[str, int] = {}
        for st in statuses:
            sid = st.get("id")
            nm = str(st.get("name") or "").strip().lower()
            if sid and nm:
                mapping[nm] = int(sid)
        _PIPELINES_CACHE[int(pid)] = mapping

    return _PIPELINES_CACHE.get(pipeline_id, {}).get(AMO_ASSIGNED_STATUS_NAME.strip().lower())


def _format_time_msk(raw: str) -> str:
    """
    Поле времени может быть строкой даты/времени или unix timestamp (сек/мс).
    Форматируем в МСК.
    """
    s = (raw or "").strip()
    if not s:
        return "Не указано"
    if re.fullmatch(r"\d{10,13}", s):
        try:
            ts = int(s)
            if len(s) == 13:
                ts = ts // 1000
            from datetime import datetime
            from zoneinfo import ZoneInfo

            dt = datetime.fromtimestamp(ts, tz=ZoneInfo("Europe/Moscow"))
            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return s
    return s


def _geodesist_name(geodesist_raw: str) -> str:
    s = (geodesist_raw or "").strip()
    if not s:
        return ""
    return s.split(",")[0].strip()


async def _process_geodesist_webhook(lead_id: int, pipeline_id: Optional[int], status_id: Optional[int]) -> None:
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

    # 1) читаем сделку
    lead = await amo.get_lead(lead_id)
    lead_status_id = int(lead.get("status_id") or 0)
    lead_pipeline_id = int(lead.get("pipeline_id") or 0)

    # 2) фильтр: только "Назначен"
    effective_pipeline_id = pipeline_id or lead_pipeline_id
    assigned_status_id = await _get_assigned_status_id(amo, effective_pipeline_id) if effective_pipeline_id else None
    if assigned_status_id is None:
        await amo.add_note_to_lead(
            lead_id,
            f"⚠️ Geodesist Max: не найден статус '{AMO_ASSIGNED_STATUS_NAME}'. Отправка не выполнена.",
        )
        return
    if lead_status_id != assigned_status_id:
        return

    # 3) данные из полей сделки
    geodesist_raw = _cf_value_by_name(lead, AMO_FIELD_NAME_GEODESIST)
    phone = extract_phone(geodesist_raw) or normalize_phone(geodesist_raw)
    if not phone:
        raise ValueError("Не удалось определить телефон геодезиста из поля сделки")

    addr = _cf_value_by_name(lead, AMO_FIELD_NAME_ADDRESS) or "Не указано"
    ts = _format_time_msk(_cf_value_by_name(lead, AMO_FIELD_NAME_TIME))
    cadastral_numbers = _cf_values_by_names(lead, [AMO_FIELD_NAME_CAD_1, AMO_FIELD_NAME_CAD_2])

    # 4) клиент из контакта сделки
    cn = "Не указано"
    cp = "Не указано"
    cid = _primary_contact_id(lead)
    if cid:
        contact = await amo.get_contact(cid)
        cn = (contact.get("name") or "").strip() or cn
        cp = _contact_phone(contact) or cp

    geo_name = _geodesist_name(geodesist_raw) or "Не указано"
    cad = [x.strip() for x in (cadastral_numbers or []) if str(x).strip()]
    cad_line = ", ".join(cad)

    # Сообщение геодезисту в MAX (без служебной информации)
    text = (
        "Добрый день!\n"
        "Вам назначен выезд на объект.\n\n"
        f"Геодезист: {geo_name}\n"
        f"Клиент: {cn}\n"
        f"Телефон клиента: {cp}\n"
        f"Адрес: {addr}\n"
        f"Когда (МСК): {ts}"
        + (f"\nКадастровые номера: {cad_line}" if cad_line else "")
    )

    # 5) отправляем в MAX
    await wappi.send_text(recipient=phone, body=text)

    # Примечание в AmoCRM — без служебной информации Wappi
    note = (
        "✅ Геодезисту отправлено в MAX\n\n"
        f"Геодезист: {geo_name} ({phone})\n"
        f"Клиент: {cn}\n"
        f"Телефон клиента: {cp}\n"
        f"Адрес: {addr}\n"
        f"Когда (МСК): {ts}"
        + (f"\nКадастровые номера: {cad_line}" if cad_line else "")
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
    Webhook от AmoCRM на смену статуса сделки.

    В интерфейсе AmoCRM можно указать только URL — поэтому берём lead_id из стандартного payload
    и дальше всё делаем сами через API.
    """
    try:
        content_type = (request.headers.get("content-type") or "").lower()
        if "application/json" in content_type:
            body = await request.json()
            lead_id_raw = body.get("lead_id") or body.get("leadId") or body.get("id")
            if lead_id_raw is None:
                return JSONResponse({"status": "error", "reason": "lead_id_required"}, status_code=200)
            lead_id = int(str(lead_id_raw).strip())
            pipeline_id_i = int(body.get("pipeline_id")) if str(body.get("pipeline_id", "")).isdigit() else None
            status_id_i = int(body.get("status_id")) if str(body.get("status_id", "")).isdigit() else None
            dedup_key = f"json:{lead_id}:{pipeline_id_i}:{status_id_i}"
        else:
            form = await request.form()
            body = dict(form)
            lead_id, pipeline_id_i, status_id_i, updated_at = _extract_first_lead_event(body)
            if not lead_id:
                return JSONResponse({"status": "ignored", "reason": "no_lead_id"}, status_code=200)
            dedup_key = f"amo:{lead_id}:{pipeline_id_i}:{status_id_i}:{updated_at or ''}"

        if _dedup(dedup_key):
            return JSONResponse({"status": "ignored", "reason": "duplicate"}, status_code=200)

        background_tasks.add_task(_process_geodesist_webhook, lead_id, pipeline_id_i, status_id_i)
        return JSONResponse({"status": "processing", "lead_id": lead_id}, status_code=200)
    except Exception as e:
        logger.error("Webhook error: %s", e)
        return JSONResponse({"status": "error"}, status_code=200)

