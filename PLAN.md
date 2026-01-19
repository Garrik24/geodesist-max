## Цель
Отдельный сервис **Geodesist Max**: при переводе сделки в AmoCRM на этап «Назначен» робот отправляет webhook в сервис, а сервис:
- отправляет сообщение геодезисту в **MAX** через **Wappi MAX API**
- пишет примечание в сделку о факте отправки

## Ограничения
- Без AssemblyAI/OpenAI/транскрибации — это отдельный проект.
- Геодезист не имеет доступа к AmoCRM.
- В сообщении **нет ссылки** на сделку и финансов.

## Контракт webhook (от робота AmoCRM)
Endpoint: `POST /webhook/amocrm/geodesist-assigned`

Поддерживаем JSON и form-urlencoded.

Поля (минимум):
- `lead_id` (обязательно)
- `geodesist` (строка из поля сделки, например: `Дмитрий, тел +7961...`) **или** `geodesist_phone`

Рекомендуемые поля (передавать из полей сделки, чтобы не искать field_id):
- `work_type` (Тип сделки)
- `address` (Адрес выезда)
- `time_slot` (Время/половина дня)
- `client_name` (имя клиента — если есть в плейсхолдерах)
- `client_phone` (телефон клиента — если есть в плейсхолдерах)

## Конфигурация (Railway Variables)
- `AMOCRM_DOMAIN`
- `AMOCRM_ACCESS_TOKEN`
- `WAPPI_API_TOKEN`
- `WAPPI_MAX_PROFILE_ID`
- `PORT` (Railway задаёт сам, но можно явно)
- `DEBUG` (опционально)

## Тест-план (ручной)
1) `GET /health` отдаёт `200 {"status":"healthy"}`
2) В AmoCRM робот вызывает webhook с `lead_id` и `geodesist` → сообщение приходит в MAX
3) В сделке появляется примечание “✅ Геодезисту отправлено в MAX …”

