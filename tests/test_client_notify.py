import asyncio
import os

os.environ.setdefault("AMOCRM_DOMAIN", "example.amocrm.ru")
os.environ.setdefault("AMOCRM_ACCESS_TOKEN", "x")
os.environ.setdefault("MAX_ENGINE_URL", "http://max.local/evo")
os.environ.setdefault("MAX_ENGINE_API_KEY", "x")
os.environ.setdefault("AMO_ASSIGNED_STATUS_NAME", "выезд геодезиста")

import main  # noqa: E402

LEAD = {
    "id": 1, "status_id": 20899693, "pipeline_id": 1271023,
    "custom_fields_values": [
        {"field_name": "Геодезист", "values": [{"value": "Дмитрий, тел +79614723557"}]},
        {"field_name": "Адрес выезда", "values": [{"value": "ГСК Подгорный 77"}]},
        {"field_name": "Интерес", "values": [{"value": "Межевание"}]},
        {"field_name": "Кадастровый номер 1", "values": [{"value": "26:12:020714:175"}]},
    ],
    "_embedded": {"contacts": [{"id": 5}]},
}
PIPES = {"_embedded": {"pipelines": [{"id": 1271023, "_embedded": {"statuses": [{"id": 20899693, "name": "выезд геодезиста"}]}}]}}


class FakeAmo:
    def __init__(self, lead, contact, notes=None):
        self.lead, self.contact, self.notes, self.added = lead, contact, notes or [], []
    async def get_lead(self, lead_id): return self.lead
    async def get_pipelines(self): return PIPES
    async def get_contact(self, cid): return self.contact
    async def get_lead_notes(self, lead_id): return self.notes
    async def add_note_to_lead(self, lead_id, text):
        self.added.append(text)
        self.notes.insert(0, {"params": {"text": text}})


class FakeMax:
    def __init__(self, fail_for=None):
        self.sent, self.fail_for = [], fail_for
    async def send_text(self, recipient, body):
        if self.fail_for and main.normalize_phone(recipient) == self.fail_for:
            raise RuntimeError("max-engine HTTP 400: number not on MAX")
        self.sent.append((main.normalize_phone(recipient), body))


def run(amo, mx, monkeypatch):
    main._PIPELINES_CACHE.clear()
    monkeypatch.setattr(main, "AmoCRMClient", lambda cfg: amo)
    monkeypatch.setattr(main, "MaxEngineClient", lambda cfg: mx)
    asyncio.run(main._process_geodesist_webhook(1, 1271023, 20899693))


CONTACT = {"name": "Николай Валентинович", "custom_fields_values": [{"field_code": "PHONE", "values": [{"value": "+79054424024"}]}]}


def test_geodesist_and_client(monkeypatch):
    amo, mx = FakeAmo(LEAD, CONTACT), FakeMax()
    run(amo, mx, monkeypatch)
    assert [p for p, _ in mx.sent] == ["79614723557", "79054424024"]
    txt = mx.sent[1][1]
    assert txt.startswith("Здравствуйте, Николай Валентинович! Это «Ставропольгеодезия».")
    assert "ГСК Подгорный 77" in txt and "(Межевание)" in txt
    assert "Дмитрий, контактный номер +7 961 472-35-57" in txt
    assert "Дату и время выезда геодезист согласует с вами." in txt
    assert amo.added[0].startswith("✅ Геодезисту отправлено в MAX")
    assert amo.added[1].startswith("✅ Клиенту отправлено в MAX")
    print("\n---\n" + txt)


def test_no_duplicate(monkeypatch):
    amo, mx = FakeAmo(LEAD, CONTACT, notes=[{"params": {"text": "✅ Клиенту отправлено в MAX\n..."}}]), FakeMax()
    run(amo, mx, monkeypatch)
    assert [p for p, _ in mx.sent] == ["79614723557"]
    # второй прогон по той же сделке тоже не шлёт клиенту
    amo2, mx2 = FakeAmo(LEAD, CONTACT), FakeMax()
    run(amo2, mx2, monkeypatch)
    run(amo2, mx2, monkeypatch)
    assert [p for p, _ in mx2.sent].count("79054424024") == 1


def test_with_time(monkeypatch):
    lead = dict(LEAD, custom_fields_values=LEAD["custom_fields_values"] + [{"field_name": "Время выезда", "values": [{"value": 1793095200}]}])
    amo, mx = FakeAmo(lead, CONTACT), FakeMax()
    run(amo, mx, monkeypatch)
    assert "Выезд запланирован на 27.10.2026 13:00 (МСК)." in mx.sent[1][1]


def test_client_send_fail(monkeypatch):
    amo, mx = FakeAmo(LEAD, CONTACT), FakeMax(fail_for="79054424024")
    run(amo, mx, monkeypatch)
    assert amo.added[-1].startswith("⚠️ Клиенту не отправлено: max-engine HTTP 400")


def test_no_client_phone(monkeypatch):
    amo, mx = FakeAmo(LEAD, {"name": "Иван", "custom_fields_values": []}), FakeMax()
    run(amo, mx, monkeypatch)
    assert len(mx.sent) == 1
    assert amo.added[-1] == "⚠️ Клиенту не отправлено: у основного контакта сделки нет телефона"


def test_service_name_not_used_as_greeting():
    t = main.build_client_text("Входящий +79054424024 (Яндекс УК)", "ул. Мира 1", "Техплан", "Александр", "79624100000", "Не указано")
    assert t.startswith("Здравствуйте! Это")
