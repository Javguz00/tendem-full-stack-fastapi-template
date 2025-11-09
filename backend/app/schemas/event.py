import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


# Shared properties
class EventBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    event_time: datetime


# Properties to receive on event creation
class EventCreate(EventBase):
    participant_ids: list[uuid.UUID] = Field(default_factory=list)


# Properties to receive on event update
class EventUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    event_time: datetime | None = None
    participant_ids: list[uuid.UUID] | None = None


# Properties to return via API, id is always required
class EventPublic(EventBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime


class EventsPublic(SQLModel):
    data: list[EventPublic]
    count: int
