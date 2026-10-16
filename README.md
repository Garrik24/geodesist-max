## Geodesist Max

Отдельный сервис для AmoCRM: отправка геодезисту сообщения в MAX через собственный шлюз max-engine при переводе сделки на этап «Назначен».

### Endpoint для AmoCRM Webhooks (смена статуса сделки)
В AmoCRM можно указать только URL — поэтому сервис принимает стандартный form-urlencoded payload и сам вытягивает сделку/контакт по API.

`POST /webhook/amocrm/geodesist-assigned`

### Railway Variables (обязательно)
- `AMOCRM_DOMAIN`
- `AMOCRM_ACCESS_TOKEN`
- `MAX_ENGINE_URL` — адрес шлюза, напр. `https://<домен MAX-стека>/evo`
- `MAX_ENGINE_API_KEY` — ключ `apikey` для маршрута `/evo` (в Caddy на VPS)
- `MAX_ENGINE_INSTANCE` (по умолчанию `stavgeo-max`)

### Настройки (опционально)
- `AMO_ASSIGNED_STATUS_NAME` (по умолчанию `Назначен`)
- `AMO_FIELD_NAME_GEODESIST` (по умолчанию `Геодезист`)
- `AMO_FIELD_NAME_WORK_TYPE` (по умолчанию `Интерес`) — тип работ (Межевание / Техплан / Акт обследования…), попадает в сообщение
- `AMO_FIELD_NAME_ADDRESS` (по умолчанию `Адрес выезда`)
- `AMO_FIELD_NAME_TIME` (по умолчанию `Время выезда`)

### Healthcheck
`GET /health` → `{"status":"healthy"}`

