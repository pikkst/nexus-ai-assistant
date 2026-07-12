"""Mock Google Calendar provider for testing and offline development."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

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
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MockCalendarProvider:
    """In-memory Google Calendar API simulator with idempotency and conflict detection."""

    def __init__(self) -> None:
        self._calendars: dict[str, Calendar] = {}
        self._events: dict[str, dict[str, Event]] = {}
        self._drafts: dict[str, EventDraft] = {}
        self._sent_idempotency: set[str] = set()
        self._counter = 0

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{uuid.uuid4().hex[:8]}_{self._counter}"

    def _ensure_calendar(self, calendar_id: str) -> Calendar:
        if calendar_id not in self._calendars:
            cal = Calendar(id=calendar_id, summary=f"Calendar {calendar_id}", primary=(calendar_id == "primary"))
            self._calendars[calendar_id] = cal
        return self._calendars[calendar_id]

    def _slot_overlaps(self, a: Event, b: Event) -> bool:
        return a.start < b.end and b.start < a.end

    def _event_conflicts(self, calendar_id: str, event: Event) -> list[Event]:
        conflicts: list[Event] = []
        for existing in self._events.get(calendar_id, {}).values():
            if existing.status == "cancelled":
                continue
            if self._slot_overlaps(existing, event):
                conflicts.append(existing)
        return conflicts

    def add_event(self, event: Event) -> Event:
        cal = event.calendar_id or "primary"
        self._ensure_calendar(cal)
        self._events.setdefault(cal, {})[event.id] = event
        return event

    async def list_calendars(self) -> tuple[list[Calendar], str | None]:
        return list(self._calendars.values()), None

    async def list_events(self, calendar_id: str, *, time_min: datetime, time_max: datetime, page_token: str | None = None) -> tuple[list[Event], str | None]:
        self._ensure_calendar(calendar_id)
        results = []
        for event in self._events.get(calendar_id, {}).values():
            if event.status == "cancelled":
                continue
            if event.end <= time_min or event.start >= time_max:
                continue
            results.append(event)
        results.sort(key=lambda item: item.start)
        limit = 10
        page = 0
        if page_token:
            try:
                page = int(page_token)
            except ValueError:
                page = 0
        start_idx = page * limit
        end_idx = start_idx + limit
        page_results = results[start_idx:end_idx]
        next_token = str(page + 1) if end_idx < len(results) else None
        return page_results, next_token

    async def get_event(self, calendar_id: str, event_id: str) -> Event:
        try:
            return self._events[calendar_id][event_id]
        except KeyError as exc:
            raise ValueError(f"event not found: {event_id}") from exc

    async def create_event_draft(self, draft: EventDraft) -> EventDraft:
        if not draft.idempotency_key:
            draft_id = self._next_id("draft")
            new_draft = EventDraft(
                id=draft_id,
                summary=draft.summary,
                description=draft.description,
                location=draft.location,
                start=draft.start,
                end=draft.end,
                timezone=draft.timezone,
                attendees=draft.attendees,
                recurrence=draft.recurrence,
                reminders=draft.reminders,
                calendar_id=draft.calendar_id,
                conflicts=self._event_conflicts(draft.calendar_id or "primary", Event(
                    id=draft_id, summary=draft.summary, start=draft.start, end=draft.end,
                    timezone=draft.timezone, calendar_id=draft.calendar_id,
                )),
                idempotency_key=draft.idempotency_key,
                created_at=_now(),
            )
        else:
            new_draft = draft
        self._drafts[draft.id] = new_draft
        return new_draft

    async def create_event(self, draft: EventDraft, *, confirmed: bool = False) -> Event:
        if draft.idempotency_key and draft.idempotency_key in self._sent_idempotency:
            raise ValueError(f"event already created with idempotency key: {draft.idempotency_key}")
        event_id = draft.id if draft.idempotency_key else self._next_id("event")
        event = Event(
            id=event_id,
            summary=draft.summary,
            description=draft.description,
            location=draft.location,
            start=draft.start,
            end=draft.end,
            timezone=draft.timezone,
            attendees=draft.attendees,
            recurrence=draft.recurrence,
            reminders=draft.reminders,
            status="tentative" if not confirmed else "confirmed",
            calendar_id=draft.calendar_id,
            etag=str(uuid.uuid4()),
            created_at=_now(),
            updated_at=_now(),
        )
        self.add_event(event)
        if draft.idempotency_key:
            self._sent_idempotency.add(draft.idempotency_key)
        return event

    async def update_event(self, calendar_id: str, event_id: str, *, summary: str | None = None, description: str | None = None, start: datetime | None = None, end: datetime | None = None, attendees: tuple[Attendee, ...] | None = None) -> Event:
        try:
            existing = self._events[calendar_id][event_id]
        except KeyError as exc:
            raise ValueError(f"event not found: {event_id}") from exc
        updated = Event(
            id=existing.id,
            summary=summary if summary is not None else existing.summary,
            description=description if description is not None else existing.description,
            location=existing.location,
            start=start if start is not None else existing.start,
            end=end if end is not None else existing.end,
            timezone=existing.timezone,
            attendees=attendees if attendees is not None else existing.attendees,
            recurrence=existing.recurrence,
            reminders=existing.reminders,
            status=existing.status,
            visibility=existing.visibility,
            color_id=existing.color_id,
            created_at=existing.created_at,
            updated_at=_now(),
            etag=str(uuid.uuid4()),
            calendar_id=existing.calendar_id,
        )
        if updated.end <= updated.start:
            raise ValueError("event end must be after start")
        self._events[calendar_id][event_id] = updated
        return updated

    async def delete_event(self, calendar_id: str, event_id: str) -> None:
        try:
            event = self._events[calendar_id][event_id]
        except KeyError as exc:
            raise ValueError(f"event not found: {event_id}") from exc
        cancelled = Event(
            id=event.id, summary=event.summary, description=event.description, location=event.location,
            start=event.start, end=event.end, timezone=event.timezone, attendees=event.attendees,
            recurrence=event.recurrence, reminders=event.reminders, status="cancelled",
            visibility=event.visibility, color_id=event.color_id, created_at=event.created_at,
            updated_at=_now(), etag=str(uuid.uuid4()), calendar_id=event.calendar_id,
        )
        self._events[calendar_id][event_id] = cancelled

    async def free_busy(self, request: FreeBusyRequest) -> tuple[list[FreeBusySlot], str | None]:
        results: list[FreeBusySlot] = []
        for calendar_id in request.items:
            self._ensure_calendar(calendar_id)
            for event in self._events.get(calendar_id, {}).values():
                if event.status == "cancelled":
                    continue
                if event.end > request.time_min and event.start < request.time_max:
                    slot_start = max(event.start, request.time_min)
                    slot_end = min(event.end, request.time_max)
                    results.append(FreeBusySlot(start=slot_start, end=slot_end))
        results.sort(key=lambda item: item.start)
        return results, None

    async def find_conflicts(self, calendar_id: str, event: Event) -> tuple[list[Event], str | None]:
        self._ensure_calendar(calendar_id)
        return self._event_conflicts(calendar_id, event), None
