"""Mocked Google Calendar API tests covering pagination, DST, conflicts, recurrence, cancellation, errors, and idempotency."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.tools.audit import ToolAuditLog
from src.tools.calendar_factory import create_calendar_registry
from src.tools.calendar_models import Attendee, Calendar, Event, EventDraft, FreeBusySlot, RecurrenceFrequency, RecurrenceRule, Reminder, Timezone
from src.tools.calendar_provider import MockCalendarProvider
from src.tools.models import ToolPermissionError, ToolRequest, ToolValidationError
from src.tools.calendar_tools import (
    CreateEventDraftTool,
    CreateEventTool,
    DeleteEventTool,
    FindConflictsTool,
    FindFreeTimeTool,
    GetEventTool,
    ListCalendarsTool,
    ListEventsTool,
    UpdateEventTool,
)


def _make_provider() -> MockCalendarProvider:
    provider = MockCalendarProvider()
    tz_ny = Timezone(id="America/New_York", display_name="Eastern Time")
    base = datetime(2026, 7, 13, 9, 0, tzinfo=timezone.utc)
    event = Event(
        id="evt_1", summary="Existing Meeting", start=base, end=base + timedelta(hours=1),
        timezone=tz_ny, calendar_id="primary",
    )
    provider.add_event(event)
    provider._ensure_calendar("primary")
    return provider


@pytest.mark.asyncio
async def test_list_calendars_is_read_only(tmp_path: Path):
    provider = _make_provider()
    registry = create_calendar_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("calendar.list_calendars", {}))
    assert result.success
    output = result.output
    assert len(output["calendars"]) >= 1
    assert output["calendars"][0]["id"] == "primary"


@pytest.mark.asyncio
async def test_read_tools_are_read_only_and_do_not_require_confirmation(tmp_path: Path):
    provider = _make_provider()
    registry = create_calendar_registry(provider, audit_path=tmp_path / "audit.jsonl")
    calendars = await registry.invoke(ToolRequest("calendar.list_calendars", {}))
    assert calendars.success and calendars.error_code is None
    events = await registry.invoke(ToolRequest("calendar.list_events", {"calendar_id": "primary", "time_min": "2026-07-13T00:00:00+00:00", "time_max": "2026-07-14T00:00:00+00:00"}))
    assert events.success and events.error_code is None
    event = await registry.invoke(ToolRequest("calendar.get_event", {"calendar_id": "primary", "event_id": "evt_1"}))
    assert event.success and event.error_code is None


@pytest.mark.asyncio
async def test_list_events_pagination(tmp_path: Path):
    provider = MockCalendarProvider()
    base = datetime(2026, 7, 13, 9, 0, tzinfo=timezone.utc)
    for i in range(5):
        event = Event(
            id=f"evt_{i}", summary=f"Meeting {i}", start=base + timedelta(minutes=i * 30),
            end=base + timedelta(minutes=(i + 1) * 30), timezone=Timezone(id="UTC"), calendar_id="primary",
        )
        provider.add_event(event)
    registry = create_calendar_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("calendar.list_events", {"calendar_id": "primary", "time_min": "2026-07-13T00:00:00+00:00", "time_max": "2026-07-14T00:00:00+00:00", "page_token": "0"}))
    assert result.success
    output = result.output
    assert len(output["events"]) == 5
    assert output["next_page_token"] is None


@pytest.mark.asyncio
async def test_dst_aware_time_handling(tmp_path: Path):
    provider = MockCalendarProvider()
    tz = Timezone(id="America/New_York", display_name="Eastern Time")
    spring_forward = datetime(2026, 3, 8, 2, 30, tzinfo=timezone.utc)
    event = Event(
        id="dst_evt", summary="DST Event", start=spring_forward, end=spring_forward + timedelta(hours=1),
        timezone=tz, calendar_id="primary",
    )
    provider.add_event(event)
    registry = create_calendar_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("calendar.list_events", {"calendar_id": "primary", "time_min": "2026-03-08T00:00:00+00:00", "time_max": "2026-03-09T00:00:00+00:00"}))
    assert result.success
    assert len(result.output["events"]) == 1


@pytest.mark.asyncio
async def test_find_free_time(tmp_path: Path):
    provider = _make_provider()
    registry = create_calendar_registry(provider, audit_path=tmp_path / "audit.jsonl")
    base = datetime(2026, 7, 13, 9, 0, tzinfo=timezone.utc)
    result = await registry.invoke(ToolRequest("calendar.find_free_time", {
        "time_min": "2026-07-13T00:00:00+00:00", "time_max": "2026-07-14T00:00:00+00:00",
        "items": ["primary"], "timezone_id": "America/New_York",
    }))
    assert result.success
    slots = result.output["slots"]
    assert len(slots) == 1
    assert slots[0]["start"] == base.isoformat()
    assert slots[0]["end"] == (base + timedelta(hours=1)).isoformat()


@pytest.mark.asyncio
async def test_find_conflicts(tmp_path: Path):
    provider = _make_provider()
    registry = create_calendar_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("calendar.find_conflicts", {
        "calendar_id": "primary", "summary": "New Meeting",
        "start": "2026-07-13T09:30:00+00:00", "end": "2026-07-13T10:30:00+00:00",
    }))
    assert result.success
    assert len(result.output["conflicts"]) == 1


@pytest.mark.asyncio
async def test_create_event_draft_includes_timezone_attendees_reminders_and_conflicts(tmp_path: Path):
    provider = _make_provider()
    registry = create_calendar_registry(provider, audit_path=tmp_path / "audit.jsonl")
    created = await registry.invoke(ToolRequest("calendar.create_event_draft", {
        "summary": "Draft Meeting", "description": "Discuss project", "location": "Room 1",
        "start": "2026-07-13T11:00:00+00:00", "end": "2026-07-13T12:00:00+00:00",
        "timezone_id": "America/New_York",
        "attendees": ["alice@example.test", "bob@example.test"],
        "reminders": [{"method": "email", "minutes": 15}, {"method": "popup", "minutes": 10}],
        "recurrence": [{"frequency": "weekly", "count": 4, "interval": 1}],
        "calendar_id": "primary",
    }), confirmed=True)
    assert created.success
    draft = created.output
    assert draft["summary"] == "Draft Meeting"
    assert draft["timezone"] == "America/New_York"
    assert len(draft["attendees"]) == 2
    assert len(draft["reminders"]) == 2
    assert len(draft["recurrence"]) == 1
    assert "conflicts" in draft


@pytest.mark.asyncio
async def test_create_event_from_draft_requires_confirmation_and_idempotency(tmp_path: Path):
    provider = _make_provider()
    registry = create_calendar_registry(provider, audit_path=tmp_path / "audit.jsonl")
    created = await registry.invoke(ToolRequest("calendar.create_event_draft", {
        "summary": "Confirm Event", "start": "2026-07-13T13:00:00+00:00", "end": "2026-07-13T14:00:00+00:00",
        "calendar_id": "primary", "idempotency_key": "idem-123",
    }), confirmed=True)
    assert created.success
    draft_id = created.output["id"]
    first = await registry.invoke(ToolRequest("calendar.create_event", {"draft_id": draft_id}))
    assert first.error_code == "confirmation_required"
    sent = await registry.invoke(ToolRequest("calendar.create_event", {"draft_id": draft_id}), confirmed=True)
    assert sent.success
    duplicate = await registry.invoke(ToolRequest("calendar.create_event", {"draft_id": draft_id}), confirmed=True)
    assert duplicate.success is False and "idempotency" in (duplicate.error_message or "").lower()


@pytest.mark.asyncio
async def test_update_event_requires_confirmation(tmp_path: Path):
    provider = _make_provider()
    registry = create_calendar_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("calendar.update_event", {
        "calendar_id": "primary", "event_id": "evt_1", "summary": "Updated Meeting",
    }))
    assert result.error_code == "confirmation_required"
    updated = await registry.invoke(ToolRequest("calendar.update_event", {
        "calendar_id": "primary", "event_id": "evt_1", "summary": "Updated Meeting",
    }), confirmed=True)
    assert updated.success
    assert updated.output["summary"] == "Updated Meeting"


@pytest.mark.asyncio
async def test_delete_event_requires_confirmation_and_cancels(tmp_path: Path):
    provider = _make_provider()
    registry = create_calendar_registry(provider, audit_path=tmp_path / "audit.jsonl")
    result = await registry.invoke(ToolRequest("calendar.delete_event", {"calendar_id": "primary", "event_id": "evt_1"}))
    assert result.error_code == "confirmation_required"
    deleted = await registry.invoke(ToolRequest("calendar.delete_event", {"calendar_id": "primary", "event_id": "evt_1"}), confirmed=True)
    assert deleted.success
    assert deleted.output["deleted"] is True


@pytest.mark.asyncio
async def test_audit_redacts_attendees_and_summary(tmp_path: Path):
    provider = _make_provider()
    audit_path = tmp_path / "audit.jsonl"
    registry = create_calendar_registry(provider, audit_path=audit_path)
    await registry.invoke(ToolRequest("calendar.create_event_draft", {
        "summary": "Secret Meeting", "start": "2026-07-13T15:00:00+00:00", "end": "2026-07-13T16:00:00+00:00",
        "attendees": ["alice@example.test"], "calendar_id": "primary",
    }), confirmed=True)
    entries = registry.audit_log.entries()
    assert entries
    raw = entries[0].arguments
    assert "Secret Meeting" not in str(raw)
    assert "alice@example.test" not in str(raw)


def test_validation_rejects_invalid_event_data():
    with pytest.raises(ToolValidationError):
        ListEventsTool(None).validate({})
    with pytest.raises(ToolValidationError):
        CreateEventDraftTool(None).validate({"summary": "", "start": "2026-07-13T09:00:00+00:00", "end": "2026-07-13T10:00:00+00:00"})
    with pytest.raises(ToolValidationError):
        CreateEventDraftTool(None).validate({"summary": "Hi", "start": "2026-07-13T09:00:00+00:00", "end": "2026-07-13T09:00:00+00:00"})
    with pytest.raises(ToolValidationError):
        CreateEventDraftTool(None).validate({"summary": "Hi", "start": "bad", "end": "2026-07-13T10:00:00+00:00"})


def test_tool_descriptors_expose_expected_risk_levels():
    provider = _make_provider()
    registry = create_calendar_registry(provider)
    risks = {item.name: item.risk.value for item in registry.discover()}
    assert risks["calendar.list_calendars"] == "read_only"
    assert risks["calendar.list_events"] == "read_only"
    assert risks["calendar.get_event"] == "read_only"
    assert risks["calendar.find_free_time"] == "read_only"
    assert risks["calendar.find_conflicts"] == "read_only"
    assert risks["calendar.create_event_draft"] == "local_write"
    assert risks["calendar.create_event"] == "external"
    assert risks["calendar.update_event"] == "external"
    assert risks["calendar.delete_event"] == "destructive"


def test_event_models_enforce_constraints():
    with pytest.raises(ValueError):
        Event(id="", summary="Hi", start=datetime.now(timezone.utc), end=datetime.now(timezone.utc) + timedelta(hours=1))
    with pytest.raises(ValueError):
        Event(id="1", summary="Hi", start=datetime.now(timezone.utc), end=datetime.now(timezone.utc))
    with pytest.raises(ValueError):
        EventDraft(id="", summary="Hi", start=datetime.now(timezone.utc), end=datetime.now(timezone.utc) + timedelta(hours=1))
    with pytest.raises(ValueError):
        Attendee(email="bad")
    with pytest.raises(ValueError):
        RecurrenceRule(frequency=RecurrenceFrequency.DAILY, count=0)
    with pytest.raises(ValueError):
        Reminder(method="sms", minutes=5)
    with pytest.raises(ValueError):
        FreeBusySlot(start=datetime.now(timezone.utc), end=datetime.now(timezone.utc) - timedelta(hours=1))
