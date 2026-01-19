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


def require_env(name: str, value: str | None) -> str:
    if value:
        return value
    raise RuntimeError(f"Missing required env var: {name}")

