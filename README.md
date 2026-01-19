## Geodesist Max

Отдельный сервис для AmoCRM: отправка геодезисту сообщения в MAX через Wappi при переводе сделки на этап «Назначен».

### Endpoint для робота AmoCRM
`POST /webhook/amocrm/geodesist-assigned`

Рекомендуемый JSON:
```json
{
  "lead_id": 12345,
  "geodesist": "Дмитрий, тел +79614723557",
  "work_type": "Межевание",
  "address": "Ставрополь, ...",
  "time_slot": "20.01.2026 13:45",
  "client_name": "Иван",
  "client_phone": "+7963..."
}
```

### Railway Variables (обязательно)
- `AMOCRM_DOMAIN`
- `AMOCRM_ACCESS_TOKEN`
- `WAPPI_API_TOKEN`
- `WAPPI_MAX_PROFILE_ID`

### Healthcheck
`GET /health` → `{"status":"healthy"}`

