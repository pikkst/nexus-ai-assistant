"""Google Calendar typed models and provider protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol, Any


_VALID_EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
_VALID_TIMEZONE = r"^[A-Za-z_]+(/[A-Za-z_]+)*$"


def _validate_email(value: str, field_name: str) -> None:
    import re
    if not re.match(_VALID_EMAIL, value):
        raise ValueError(f"{field_name} must be a valid email address")


def _validate_emails(values: tuple[str, ...], field_name: str) -> None:
    for item in values:
        _validate_email(item, field_name)


def _validate_timezone(value: str, field_name: str) -> None:
    import re
    if not re.match(_VALID_TIMEZONE, value):
        raise ValueError(f"{field_name} must be a valid IANA timezone identifier")


@dataclass(frozen=True, slots=True)
class Timezone:
    id: str
    display_name: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("timezone id is required")
        _validate_timezone(self.id, "timezone id")
        if not self.display_name:
            object.__setattr__(self, "display_name", self.id)


@dataclass(frozen=True, slots=True)
class Attendee:
    email: str
    display_name: str = ""
    optional: bool = False
    response_status: str = "needsAction"

    def __post_init__(self) -> None:
        if not self.email:
            raise ValueError("attendee email is required")
        _validate_email(self.email, "attendee email")
        if self.response_status not in {"needsAction", "declined", "tentative", "accepted"}:
            raise ValueError("response_status must be a valid attendee response state")


class RecurrenceFrequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass(frozen=True, slots=True)
class RecurrenceRule:
    frequency: RecurrenceFrequency
    count: int | None = None
    interval: int = 1
    until: datetime | None = None

    def __post_init__(self) -> None:
        if self.count is not None and self.count <= 0:
            raise ValueError("recurrence count must be a positive integer")
        if self.interval <= 0:
            raise ValueError("recurrence interval must be a positive integer")
        if self.until is not None and self.until.tzinfo is None:
            raise ValueError("recurrence until must be timezone-aware")


@dataclass(frozen=True, slots=True)
class Reminder:
    method: str
    minutes: int

    def __post_init__(self) -> None:
        if self.method not in {"email", "popup"}:
            raise ValueError("reminder method must be email or popup")
        if not isinstance(self.minutes, int) or self.minutes < 0:
            raise ValueError("reminder minutes must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class FreeBusySlot:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("free/busy slots must be timezone-aware")
        if self.end <= self.start:
            raise ValueError("free/busy end must be after start")


class FreeBusyStatus(Enum):
    FREE = "free"
    BUSY = "busy"
    TENTATIVE = "tentative"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class Event:
    id: str
    summary: str
    description: str = ""
    location: str = ""
    start: datetime = field(default_factory=lambda: datetime(1970, 1, 1, tzinfo=timezone.utc))
    end: datetime = field(default_factory=lambda: datetime(1970, 1, 2, tzinfo=timezone.utc))
    timezone: Timezone = field(default_factory=lambda: Timezone(id="UTC"))
    attendees: tuple[Attendee, ...] = ()
    recurrence: tuple[RecurrenceRule, ...] = ()
    reminders: tuple[Reminder, ...] = ()
    status: str = "confirmed"
    visibility: str = "default"
    color_id: str = "0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    etag: str = ""
    calendar_id: str = "primary"

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("event id is required")
        if not self.summary:
            raise ValueError("event summary is required")
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("event start and end must be timezone-aware")
        if self.end <= self.start:
            raise ValueError("event end must be after start")
        if self.status not in {"confirmed", "tentative", "cancelled"}:
            raise ValueError("event status must be confirmed, tentative, or cancelled")


@dataclass(frozen=True, slots=True)
class Calendar:
    id: str
    summary: str
    description: str = ""
    timezone: Timezone = field(default_factory=lambda: Timezone(id="UTC"))
    primary: bool = False
    access_role: str = "owner"

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("calendar id is required")
        if not self.summary:
            raise ValueError("calendar summary is required")


@dataclass(frozen=True, slots=True)
class EventDraft:
    id: str
    summary: str
    description: str = ""
    location: str = ""
    start: datetime = field(default_factory=lambda: datetime(1970, 1, 1, tzinfo=timezone.utc))
    end: datetime = field(default_factory=lambda: datetime(1970, 1, 2, tzinfo=timezone.utc))
    timezone: Timezone = field(default_factory=lambda: Timezone(id="UTC"))
    attendees: tuple[Attendee, ...] = ()
    recurrence: tuple[RecurrenceRule, ...] = ()
    reminders: tuple[Reminder, ...] = ()
    calendar_id: str = "primary"
    conflicts: tuple[Event, ...] = ()
    idempotency_key: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("draft id is required")
        if not self.summary:
            raise ValueError("draft summary is required")
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("draft start and end must be timezone-aware")
        if self.end <= self.start:
            raise ValueError("draft end must be after start")


@dataclass(frozen=True, slots=True)
class FreeBusyRequest:
    time_min: datetime
    time_max: datetime
    items: tuple[str, ...]
    timezone: Timezone = field(default_factory=lambda: Timezone(id="UTC"))

    def __post_init__(self) -> None:
        if not self.items:
            raise ValueError("free/busy request must include at least one calendar item")
        if self.time_min.tzinfo is None or self.time_max.tzinfo is None:
            raise ValueError("free/busy bounds must be timezone-aware")
        if self.time_max <= self.time_min:
            raise ValueError("free/busy time_max must be after time_min")


class CalendarProvider(Protocol):
    async def list_calendars(self) -> tuple[list[Calendar], str | None]: ...
    async def list_events(self, calendar_id: str, *, time_min: datetime, time_max: datetime, page_token: str | None = None) -> tuple[list[Event], str | None]: ...
    async def get_event(self, calendar_id: str, event_id: str) -> Event: ...
    async def create_event_draft(self, draft: EventDraft) -> EventDraft: ...
    async def create_event(self, draft: EventDraft, *, confirmed: bool = False) -> Event: ...
    async def update_event(self, calendar_id: str, event_id: str, *, summary: str | None = None, description: str | None = None, start: datetime | None = None, end: datetime | None = None, attendees: tuple[Attendee, ...] | None = None) -> Event: ...
    async def delete_event(self, calendar_id: str, event_id: str) -> None: ...
    async def free_busy(self, request: FreeBusyRequest) -> tuple[list[FreeBusySlot], str | None]: ...
    async def find_conflicts(self, calendar_id: str, event: Event) -> tuple[list[Event], str | None]: ...
