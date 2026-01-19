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

# Wappi MAX
WAPPI_API_TOKEN = os.getenv("WAPPI_API_TOKEN")
WAPPI_MAX_PROFILE_ID = os.getenv("WAPPI_MAX_PROFILE_ID")

# AmoCRM: имя статуса, на котором шлём геодезисту
AMO_ASSIGNED_STATUS_NAME = os.getenv("AMO_ASSIGNED_STATUS_NAME", "Назначен")

# AmoCRM: имена полей сделки (custom fields) — можно переопределить через env
AMO_FIELD_NAME_GEODESIST = os.getenv("AMO_FIELD_NAME_GEODESIST", "Геодезист")
AMO_FIELD_NAME_WORK_TYPE = os.getenv("AMO_FIELD_NAME_WORK_TYPE", "Тип сделки")
AMO_FIELD_NAME_ADDRESS = os.getenv("AMO_FIELD_NAME_ADDRESS", "Адрес выезда")
AMO_FIELD_NAME_TIME = os.getenv("AMO_FIELD_NAME_TIME", "Время выезда")


def require_env(name: str, value: str | None) -> str:
    if value:
        return value
    raise RuntimeError(f"Missing required env var: {name}")

