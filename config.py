"""
Конфигурация Geodesist Max.
"""

import os
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("DEBUG", "false").lower() == "true"
PORT = int(os.getenv("PORT", "8000"))

# AmoCRM
AMOCRM_DOMAIN = os.getenv("AMOCRM_DOMAIN")
AMOCRM_ACCESS_TOKEN = os.getenv("AMOCRM_ACCESS_TOKEN")

# MAX: собственный шлюз max-engine (VPS, маршрут /evo в Caddy)
MAX_ENGINE_URL = os.getenv("MAX_ENGINE_URL")
MAX_ENGINE_API_KEY = os.getenv("MAX_ENGINE_API_KEY")
MAX_ENGINE_INSTANCE = os.getenv("MAX_ENGINE_INSTANCE", "stavgeo-max")

# AmoCRM: имя статуса, на котором шлём геодезисту
AMO_ASSIGNED_STATUS_NAME = os.getenv("AMO_ASSIGNED_STATUS_NAME", "Назначен")

# AmoCRM: имена полей сделки (custom fields) — можно переопределить через env
AMO_FIELD_NAME_GEODESIST = os.getenv("AMO_FIELD_NAME_GEODESIST", "Геодезист")
AMO_FIELD_NAME_ADDRESS = os.getenv("AMO_FIELD_NAME_ADDRESS", "Адрес выезда")
AMO_FIELD_NAME_TIME = os.getenv("AMO_FIELD_NAME_TIME", "Время выезда")

# AmoCRM: поле с типом работ (Межевание / Техплан / Акт обследования …).
# В stavgeo26 это select-поле «Интерес» (id 212083); оно же обязательно
# при переводе в статус «выезд геодезиста».
AMO_FIELD_NAME_WORK_TYPE = os.getenv("AMO_FIELD_NAME_WORK_TYPE", "Интерес")

# Имена полей с кадастровыми номерами.
# Если у вас поля названы иначе — переопределите через Railway Variables.
AMO_FIELD_NAME_CAD_1 = os.getenv("AMO_FIELD_NAME_CAD_1", "Кадастровый номер 1")
AMO_FIELD_NAME_CAD_2 = os.getenv("AMO_FIELD_NAME_CAD_2", "Кадастровый номер 2")


# Уведомление клиента в MAX после отправки геодезисту (по умолчанию включено).
CLIENT_NOTIFY_ENABLED = os.getenv("CLIENT_NOTIFY_ENABLED", "true").lower() not in ("0", "false", "no", "off")
COMPANY_NAME = os.getenv("COMPANY_NAME", "Ставропольгеодезия")


def require_env(name: str, value: str | None) -> str:
    if value:
        return value
    raise RuntimeError(f"Missing required env var: {name}")

