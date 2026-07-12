"""Permissioned Google Calendar tools for listing, drafts, creation, update, and delete."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .audit import ToolAuditLog, redact
from .calendar_models import (
    Attendee,
    Calendar,
    Event,
    EventDraft,
    FreeBusyRequest,
    FreeBusySlot,
    RecurrenceFrequency,
    RecurrenceRule,
    Reminder,
    Timezone,
    _validate_email,
    _validate_emails,
    _validate_timezone,
    CalendarProvider,
)
from .models import RiskLevel, Tool, ToolDescriptor, ToolValidationError
from .permissions import PermissionPolicy
from .registry import ToolRegistry


def _validate_id(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _validate_optional_email(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    _validate_email(value.strip(), field_name)
    return value.strip()


def _calendar_to_dict(calendar: Calendar) -> dict[str, Any]:
    return {
        "id": calendar.id, "summary": calendar.summary, "description": calendar.description,
        "timezone": calendar.timezone.id, "display_name": calendar.timezone.display_name,
        "primary": calendar.primary, "access_role": calendar.access_role,
    }


def _event_to_dict(event: Event) -> dict[str, Any]:
    return {
        "id": event.id, "summary": event.summary, "description": event.description,
        "location": event.location, "start": event.start.isoformat(), "end": event.end.isoformat(),
        "timezone": event.timezone.id, "attendees": [_attendee_to_dict(a) for a in event.attendees],
        "recurrence": [_recurrence_to_dict(r) for r in event.recurrence],
        "reminders": [_reminder_to_dict(r) for r in event.reminders],
        "status": event.status, "visibility": event.visibility, "color_id": event.color_id,
        "calendar_id": event.calendar_id, "created_at": event.created_at.isoformat(),
        "updated_at": event.updated_at.isoformat(), "etag": event.etag,
    }


def _draft_to_dict(draft: EventDraft) -> dict[str, Any]:
    return {
        "id": draft.id, "summary": draft.summary, "description": draft.description,
        "location": draft.location, "start": draft.start.isoformat(), "end": draft.end.isoformat(),
        "timezone": draft.timezone.id, "attendees": [_attendee_to_dict(a) for a in draft.attendees],
        "recurrence": [_recurrence_to_dict(r) for r in draft.recurrence],
        "reminders": [_reminder_to_dict(r) for r in draft.reminders],
        "calendar_id": draft.calendar_id, "conflicts": [_event_to_dict(c) for c in draft.conflicts],
        "idempotency_key": draft.idempotency_key, "created_at": draft.created_at.isoformat(),
    }


def _attendee_to_dict(attendee: Attendee) -> dict[str, Any]:
    return {
        "email": attendee.email, "display_name": attendee.display_name,
        "optional": attendee.optional, "response_status": attendee.response_status,
    }


def _recurrence_to_dict(rule: RecurrenceRule) -> dict[str, Any]:
    return {
        "frequency": rule.frequency.value, "count": rule.count, "interval": rule.interval,
        "until": rule.until.isoformat() if rule.until else None,
    }


def _reminder_to_dict(reminder: Reminder) -> dict[str, Any]:
    return {"method": reminder.method, "minutes": reminder.minutes}


class ListCalendarsTool:
    name, description, risk = "calendar.list_calendars", "List all available Google Calendars.", RiskLevel.READ_ONLY
    parameters = {"type": "object", "properties": {}, "additionalProperties": False}

    def __init__(self, provider: CalendarProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        if arguments:
            raise ToolValidationError("no arguments are accepted")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        calendars, _ = await self.provider.list_calendars()
        return {"calendars": [_calendar_to_dict(cal) for cal in calendars]}


class ListEventsTool:
    name, description, risk = "calendar.list_events", "List events in a calendar within a time range.", RiskLevel.READ_ONLY
    parameters = {"type": "object", "properties": {"calendar_id": {"type": "string"}, "time_min": {"type": "string", "format": "date-time"}, "time_max": {"type": "string", "format": "date-time"}, "page_token": {"type": "string"}}, "required": ["calendar_id", "time_min", "time_max"], "additionalProperties": False}

    def __init__(self, provider: CalendarProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_id(arguments.get("calendar_id"), "calendar_id")
        time_min = arguments.get("time_min")
        time_max = arguments.get("time_max")
        if not isinstance(time_min, str) or not time_min.strip():
            raise ToolValidationError("time_min must be a non-empty ISO-8601 datetime string")
        if not isinstance(time_max, str) or not time_max.strip():
            raise ToolValidationError("time_max must be a non-empty ISO-8601 datetime string")
        try:
            t_min = datetime.fromisoformat(time_min)
            t_max = datetime.fromisoformat(time_max)
            if t_min.tzinfo is None or t_max.tzinfo is None:
                raise ValueError("datetimes must be timezone-aware")
            if t_max <= t_min:
                raise ValueError("time_max must be after time_min")
        except (TypeError, ValueError) as exc:
            raise ToolValidationError(str(exc)) from exc

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        time_min = datetime.fromisoformat(arguments["time_min"])
        time_max = datetime.fromisoformat(arguments["time_max"])
        events, next_token = await self.provider.list_events(
            arguments["calendar_id"], time_min=time_min, time_max=time_max,
            page_token=arguments.get("page_token"),
        )
        return {"events": [_event_to_dict(event) for event in events], "next_page_token": next_token}


class GetEventTool:
    name, description, risk = "calendar.get_event", "Get a single calendar event by id.", RiskLevel.READ_ONLY
    parameters = {"type": "object", "properties": {"calendar_id": {"type": "string"}, "event_id": {"type": "string"}}, "required": ["calendar_id", "event_id"], "additionalProperties": False}

    def __init__(self, provider: CalendarProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_id(arguments.get("calendar_id"), "calendar_id")
        _validate_id(arguments.get("event_id"), "event_id")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        event = await self.provider.get_event(arguments["calendar_id"], arguments["event_id"])
        return _event_to_dict(event)


class FindFreeTimeTool:
    name, description, risk = "calendar.find_free_time", "Find free time slots across calendars.", RiskLevel.READ_ONLY
    parameters = {"type": "object", "properties": {"time_min": {"type": "string", "format": "date-time"}, "time_max": {"type": "string", "format": "date-time"}, "items": {"type": "array", "items": {"type": "string"}}, "timezone_id": {"type": "string"}}, "required": ["time_min", "time_max", "items"], "additionalProperties": False}

    def __init__(self, provider: CalendarProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        time_min = arguments.get("time_min")
        time_max = arguments.get("time_max")
        items = arguments.get("items")
        if not isinstance(time_min, str) or not time_min.strip():
            raise ToolValidationError("time_min must be a non-empty ISO-8601 datetime string")
        if not isinstance(time_max, str) or not time_max.strip():
            raise ToolValidationError("time_max must be a non-empty ISO-8601 datetime string")
        if not isinstance(items, list) or not items:
            raise ToolValidationError("items must be a non-empty array of calendar ids")
        try:
            t_min = datetime.fromisoformat(time_min)
            t_max = datetime.fromisoformat(time_max)
            if t_min.tzinfo is None or t_max.tzinfo is None:
                raise ValueError("datetimes must be timezone-aware")
            if t_max <= t_min:
                raise ValueError("time_max must be after time_min")
        except (TypeError, ValueError) as exc:
            raise ToolValidationError(str(exc)) from exc

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        time_min = datetime.fromisoformat(arguments["time_min"])
        time_max = datetime.fromisoformat(arguments["time_max"])
        tz_id = arguments.get("timezone_id", "UTC")
        _validate_timezone(tz_id, "timezone_id")
        request = FreeBusyRequest(
            time_min=time_min, time_max=time_max,
            items=tuple(arguments["items"]),
            timezone=Timezone(id=tz_id),
        )
        slots, _ = await self.provider.free_busy(request)
        return {"slots": [{"start": slot.start.isoformat(), "end": slot.end.isoformat()} for slot in slots]}


class FindConflictsTool:
    name, description, risk = "calendar.find_conflicts", "Find conflicting events for a proposed event window.", RiskLevel.READ_ONLY
    parameters = {"type": "object", "properties": {"calendar_id": {"type": "string"}, "summary": {"type": "string"}, "start": {"type": "string", "format": "date-time"}, "end": {"type": "string", "format": "date-time"}, "timezone_id": {"type": "string"}}, "required": ["calendar_id", "summary", "start", "end"], "additionalProperties": False}

    def __init__(self, provider: CalendarProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_id(arguments.get("calendar_id"), "calendar_id")
        summary = arguments.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise ToolValidationError("summary must be a non-empty string")
        start = arguments.get("start")
        end = arguments.get("end")
        if not isinstance(start, str) or not start.strip():
            raise ToolValidationError("start must be a non-empty ISO-8601 datetime string")
        if not isinstance(end, str) or not end.strip():
            raise ToolValidationError("end must be a non-empty ISO-8601 datetime string")
        try:
            t_start = datetime.fromisoformat(start)
            t_end = datetime.fromisoformat(end)
            if t_start.tzinfo is None or t_end.tzinfo is None:
                raise ValueError("datetimes must be timezone-aware")
            if t_end <= t_start:
                raise ValueError("end must be after start")
        except (TypeError, ValueError) as exc:
            raise ToolValidationError(str(exc)) from exc

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        tz_id = arguments.get("timezone_id", "UTC")
        _validate_timezone(tz_id, "timezone_id")
        event = Event(
            id="proposed", summary=arguments["summary"],
            start=datetime.fromisoformat(arguments["start"]),
            end=datetime.fromisoformat(arguments["end"]),
            timezone=Timezone(id=tz_id), calendar_id=arguments["calendar_id"],
        )
        conflicts, _ = await self.provider.find_conflicts(arguments["calendar_id"], event)
        return {"conflicts": [_event_to_dict(c) for c in conflicts]}


class CreateEventDraftTool:
    name, description, risk = "calendar.create_event_draft", "Create a calendar event draft without sending invites.", RiskLevel.LOCAL_WRITE
    parameters = {"type": "object", "properties": {"summary": {"type": "string"}, "description": {"type": "string"}, "location": {"type": "string"}, "start": {"type": "string", "format": "date-time"}, "end": {"type": "string", "format": "date-time"}, "timezone_id": {"type": "string"}, "attendees": {"type": "array", "items": {"type": "string"}}, "recurrence": {"type": "array", "items": {"type": "object"}}, "reminders": {"type": "array", "items": {"type": "object"}}, "calendar_id": {"type": "string"}, "idempotency_key": {"type": "string"}}, "required": ["summary", "start", "end"], "additionalProperties": False}

    def __init__(self, provider: CalendarProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        if not isinstance(arguments.get("summary"), str) or not arguments["summary"].strip():
            raise ToolValidationError("summary must be a non-empty string")
        if len(arguments.get("summary", "")) > 1024:
            raise ToolValidationError("summary must be 1024 characters or fewer")
        start = arguments.get("start")
        end = arguments.get("end")
        if not isinstance(start, str) or not start.strip():
            raise ToolValidationError("start must be a non-empty ISO-8601 datetime string")
        if not isinstance(end, str) or not end.strip():
            raise ToolValidationError("end must be a non-empty ISO-8601 datetime string")
        try:
            t_start = datetime.fromisoformat(start)
            t_end = datetime.fromisoformat(end)
            if t_start.tzinfo is None or t_end.tzinfo is None:
                raise ValueError("datetimes must be timezone-aware")
            if t_end <= t_start:
                raise ValueError("end must be after start")
        except (TypeError, ValueError) as exc:
            raise ToolValidationError(str(exc)) from exc
        tz_id = arguments.get("timezone_id", "UTC")
        _validate_timezone(tz_id, "timezone_id")
        attendees = arguments.get("attendees", ())
        if attendees:
            try:
                _validate_emails(tuple(attendees), "attendees")
            except ValueError as exc:
                raise ToolValidationError(str(exc)) from exc
        recurrence = arguments.get("recurrence", ())
        if recurrence:
            if not isinstance(recurrence, list):
                raise ToolValidationError("recurrence must be an array of recurrence rules")
            for idx, rule in enumerate(recurrence):
                freq = rule.get("frequency") if isinstance(rule, dict) else None
                if freq is None:
                    raise ToolValidationError(f"recurrence[{idx}] must have a frequency")
                try:
                    RecurrenceFrequency(freq)
                except ValueError as exc:
                    raise ToolValidationError(f"recurrence[{idx}] frequency must be a valid frequency") from exc
        reminders = arguments.get("reminders", ())
        if reminders:
            if not isinstance(reminders, list):
                raise ToolValidationError("reminders must be an array of reminder objects")
            for idx, reminder in enumerate(reminders):
                if not isinstance(reminder, dict):
                    raise ToolValidationError(f"reminders[{idx}] must be an object")
                method = reminder.get("method")
                minutes = reminder.get("minutes")
                if method not in {"email", "popup"}:
                    raise ToolValidationError(f"reminders[{idx}] method must be email or popup")
                if not isinstance(minutes, int) or minutes < 0:
                    raise ToolValidationError(f"reminders[{idx}] minutes must be a non-negative integer")
        idempotency_key = arguments.get("idempotency_key")
        if idempotency_key is not None and not isinstance(idempotency_key, str):
            raise ToolValidationError("idempotency_key must be a string")
        calendar_id = arguments.get("calendar_id", "primary")
        if not isinstance(calendar_id, str) or not calendar_id.strip():
            raise ToolValidationError("calendar_id must be a non-empty string")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        tz_id = arguments.get("timezone_id", "UTC")
        timezone = Timezone(id=tz_id)
        t_start = datetime.fromisoformat(arguments["start"])
        t_end = datetime.fromisoformat(arguments["end"])
        attendees = tuple(Attendee(email=email) for email in arguments.get("attendees", ()))
        recurrence = tuple(
            RecurrenceRule(
                frequency=RecurrenceFrequency(rule["frequency"]),
                count=rule.get("count"), interval=rule.get("interval", 1),
                until=datetime.fromisoformat(rule["until"]) if rule.get("until") else None,
            )
            for rule in arguments.get("recurrence", ())
        )
        reminders = tuple(
            Reminder(method=reminder["method"], minutes=reminder["minutes"])
            for reminder in arguments.get("reminders", ())
        )
        draft = EventDraft(
            id=f"draft_{uuid.uuid4().hex[:8]}",
            summary=arguments["summary"], description=arguments.get("description", ""),
            location=arguments.get("location", ""), start=t_start, end=t_end,
            timezone=timezone, attendees=attendees, recurrence=recurrence, reminders=reminders,
            calendar_id=arguments.get("calendar_id", "primary"),
            idempotency_key=arguments.get("idempotency_key", ""),
        )
        created = await self.provider.create_event_draft(draft)
        return _draft_to_dict(created)


class CreateEventTool:
    name, description, risk = "calendar.create_event", "Create a confirmed calendar event from a draft.", RiskLevel.EXTERNAL
    parameters = {"type": "object", "properties": {"draft_id": {"type": "string"}, "send_updates": {"type": "string"}}, "required": ["draft_id"], "additionalProperties": False}

    def __init__(self, provider: CalendarProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_id(arguments.get("draft_id"), "draft_id")
        updates = arguments.get("send_updates")
        if updates is not None and updates not in {"all", "externalOnly", "none"}:
            raise ToolValidationError("send_updates must be all, externalOnly, or none")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            draft = self.provider._drafts[arguments["draft_id"]]
        except (AttributeError, KeyError) as exc:
            raise ValueError(f"draft not found: {arguments['draft_id']}") from exc
        event = await self.provider.create_event(draft, confirmed=True)
        return _event_to_dict(event)


class UpdateEventTool:
    name, description, risk = "calendar.update_event", "Update an existing calendar event.", RiskLevel.EXTERNAL
    parameters = {"type": "object", "properties": {"calendar_id": {"type": "string"}, "event_id": {"type": "string"}, "summary": {"type": "string"}, "description": {"type": "string"}, "start": {"type": "string", "format": "date-time"}, "end": {"type": "string", "format": "date-time"}, "attendees": {"type": "array", "items": {"type": "string"}}}, "required": ["calendar_id", "event_id"], "additionalProperties": False}

    def __init__(self, provider: CalendarProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_id(arguments.get("calendar_id"), "calendar_id")
        _validate_id(arguments.get("event_id"), "event_id")
        if not any(key in arguments for key in ("summary", "description", "start", "end", "attendees")):
            raise ToolValidationError("at least one updatable field must be provided")
        start = arguments.get("start")
        end = arguments.get("end")
        if start is not None:
            if not isinstance(start, str) or not start.strip():
                raise ToolValidationError("start must be a non-empty ISO-8601 datetime string")
            try:
                t_start = datetime.fromisoformat(start)
                if t_start.tzinfo is None:
                    raise ValueError("start must be timezone-aware")
            except (TypeError, ValueError) as exc:
                raise ToolValidationError(str(exc)) from exc
        if end is not None:
            if not isinstance(end, str) or not end.strip():
                raise ToolValidationError("end must be a non-empty ISO-8601 datetime string")
            try:
                t_end = datetime.fromisoformat(end)
                if t_end.tzinfo is None:
                    raise ValueError("end must be timezone-aware")
            except (TypeError, ValueError) as exc:
                raise ToolValidationError(str(exc)) from exc
        attendees = arguments.get("attendees")
        if attendees is not None:
            if not isinstance(attendees, list):
                raise ToolValidationError("attendees must be an array of email addresses")
            try:
                _validate_emails(tuple(attendees), "attendees")
            except ValueError as exc:
                raise ToolValidationError(str(exc)) from exc

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        attendees = None
        if "attendees" in arguments:
            attendees = tuple(Attendee(email=email) for email in arguments["attendees"])
        start = datetime.fromisoformat(arguments["start"]) if "start" in arguments else None
        end = datetime.fromisoformat(arguments["end"]) if "end" in arguments else None
        event = await self.provider.update_event(
            arguments["calendar_id"], arguments["event_id"],
            summary=arguments.get("summary"), description=arguments.get("description"),
            start=start, end=end, attendees=attendees,
        )
        return _event_to_dict(event)


class DeleteEventTool:
    name, description, risk = "calendar.delete_event", "Permanently cancel a calendar event.", RiskLevel.DESTRUCTIVE
    parameters = {"type": "object", "properties": {"calendar_id": {"type": "string"}, "event_id": {"type": "string"}}, "required": ["calendar_id", "event_id"], "additionalProperties": False}

    def __init__(self, provider: CalendarProvider) -> None:
        self.provider = provider

    def validate(self, arguments: dict[str, Any]) -> None:
        _validate_id(arguments.get("calendar_id"), "calendar_id")
        _validate_id(arguments.get("event_id"), "event_id")

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        await self.provider.delete_event(arguments["calendar_id"], arguments["event_id"])
        return {"deleted": True, "calendar_id": arguments["calendar_id"], "event_id": arguments["event_id"]}
