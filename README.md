## Geodesist Max

Отдельный сервис для AmoCRM: отправка геодезисту сообщения в MAX через Wappi при переводе сделки на этап «Назначен».

### Endpoint для AmoCRM Webhooks (смена статуса сделки)
В AmoCRM можно указать только URL — поэтому сервис принимает стандартный form-urlencoded payload и сам вытягивает сделку/контакт по API.

`POST /webhook/amocrm/geodesist-assigned`

### Railway Variables (обязательно)
- `AMOCRM_DOMAIN`
- `AMOCRM_ACCESS_TOKEN`
- `WAPPI_API_TOKEN`
- `WAPPI_MAX_PROFILE_ID`

### Настройки (опционально)
- `AMO_ASSIGNED_STATUS_NAME` (по умолчанию `Назначен`)
- `AMO_FIELD_NAME_GEODESIST` (по умолчанию `Геодезист`)
- `AMO_FIELD_NAME_WORK_TYPE` (по умолчанию `Тип сделки`)
- `AMO_FIELD_NAME_ADDRESS` (по умолчанию `Адрес выезда`)
- `AMO_FIELD_NAME_TIME` (по умолчанию `Время выезда`)

### Healthcheck
`GET /health` → `{"status":"healthy"}`

