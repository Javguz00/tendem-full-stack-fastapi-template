import uuid
from datetime import datetime, timezone

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel, Column
from sqlalchemy import ForeignKey
from sqlalchemy.types import DateTime as SADateTime


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# EventParticipant junction table (defined before User to avoid forward reference issues)
class EventParticipant(SQLModel, table=True):
    __tablename__ = "event_participant"

    event_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("event.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        )
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        )
    )


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)
    events_owned: list["Event"] = Relationship(back_populates="owner", cascade_delete=True)
    events_participating: list["Event"] = Relationship(
        back_populates="participants",
        link_model=EventParticipant
    )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


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


# Database model, database table inferred from class name
class Event(SQLModel, table=True):
    __tablename__ = "event"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
    )
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)
    event_time: datetime = Field(
        sa_column=Column(SADateTime(timezone=True), nullable=False)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            SADateTime(timezone=True),
            nullable=False,
        ),
    )

    owner_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    # Relationships
    owner: User | None = Relationship(back_populates="events_owned")
    participants: list[User] = Relationship(
        back_populates="events_participating",
        link_model=EventParticipant,
    )


# Properties to return via API, id is always required
class EventPublic(EventBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime


class EventsPublic(SQLModel):
    data: list[EventPublic]
    count: int
