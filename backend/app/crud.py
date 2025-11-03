import uuid
from typing import Any

from sqlmodel import Session, select, func, or_

from app.core.security import get_password_hash, verify_password
from app.models import (
    Item, ItemCreate, User, UserCreate, UserUpdate,
    Event, EventCreate, EventUpdate, EventParticipant
)


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


# Event CRUD operations
def create_event(*, session: Session, event_in: EventCreate, owner_id: uuid.UUID) -> Event:
    db_event = Event.model_validate(
        event_in,
        update={"owner_id": owner_id},
        exclude={"participant_ids"}
    )
    # Add participants if provided
    if event_in.participant_ids:
        participants = session.exec(
            select(User).where(User.id.in_(event_in.participant_ids))
        ).all()
        db_event.participants = list(participants)
    
    session.add(db_event)
    session.commit()
    session.refresh(db_event)
    return db_event


def get_event(*, session: Session, event_id: uuid.UUID) -> Event | None:
    return session.get(Event, event_id)


def get_events(*, session: Session, skip: int = 0, limit: int = 100) -> tuple[list[Event], int]:
    count_statement = select(func.count()).select_from(Event)
    count = session.exec(count_statement).one()
    
    statement = select(Event).offset(skip).limit(limit)
    events = session.exec(statement).all()
    
    return list(events), count


def get_events_for_user(
    *,
    session: Session,
    user_id: uuid.UUID,
    is_superuser: bool,
    skip: int = 0,
    limit: int = 100
) -> tuple[list[Event], int]:
    if is_superuser:
        return get_events(session=session, skip=skip, limit=limit)
    
    # Events where user is owner or participant
    participant_subq = select(EventParticipant.event_id).where(
        EventParticipant.user_id == user_id
    )
    
    count_statement = select(func.count()).select_from(Event).where(
        or_(
            Event.owner_id == user_id,
            Event.id.in_(participant_subq)
        )
    )
    count = session.exec(count_statement).one()
    
    statement = select(Event).where(
        or_(
            Event.owner_id == user_id,
            Event.id.in_(participant_subq)
        )
    ).offset(skip).limit(limit)
    
    events = session.exec(statement).all()
    return list(events), count


def update_event(*, session: Session, db_event: Event, event_in: EventUpdate) -> Event:
    event_data = event_in.model_dump(exclude_unset=True, exclude={"participant_ids"})
    db_event.sqlmodel_update(event_data)
    
    # Update participants if provided
    if event_in.participant_ids is not None:
        participants = session.exec(
            select(User).where(User.id.in_(event_in.participant_ids))
        ).all()
        db_event.participants = list(participants)
    
    session.add(db_event)
    session.commit()
    session.refresh(db_event)
    return db_event


def delete_event(*, session: Session, db_event: Event) -> None:
    session.delete(db_event)
    session.commit()
