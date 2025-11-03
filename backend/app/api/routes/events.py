from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import SessionDep, CurrentUser
from app.crud import (
    create_event,
    get_event,
    get_events_visible_for_user,
    update_event,
    delete_event,
    add_participants_to_event,
    remove_participant_from_event,
    is_event_owner,
    is_event_participant,
)
from app.models import (
    Event,
    EventCreate,
    EventUpdate,
    EventPublic,
    EventsPublic,
    Message,
)

router = APIRouter(prefix="/events", tags=["events"])


class ParticipantsBody(BaseModel):
    participant_ids: List[uuid.UUID]


@router.get("/", response_model=EventsPublic)
async def list_events(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> EventsPublic:
    is_super = getattr(current_user, "is_superuser", False)
    events, count = await get_events_visible_for_user(
        session=session,
        user=current_user,
        skip=skip,
        limit=limit,
        is_superuser=is_super,
    )
    return EventsPublic(data=[EventPublic.model_validate(e) for e in events], count=count)


@router.get("/{id}", response_model=EventPublic)
async def read_event(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
) -> EventPublic:
    db_event = await get_event(session=session, event_id=id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    is_super = getattr(current_user, "is_superuser", False)
    if not (
        is_super or is_event_owner(db_event, current_user.id) or is_event_participant(db_event, current_user.id)
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    return EventPublic.model_validate(db_event)


@router.post("/", response_model=EventPublic)
async def create_event_endpoint(
    session: SessionDep,
    current_user: CurrentUser,
    event_in: EventCreate,
) -> EventPublic:
    event = await create_event(session=session, event_in=event_in, owner_id=current_user.id)
    return EventPublic.model_validate(event)


@router.put("/{id}", response_model=EventPublic)
async def update_event_endpoint(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    event_in: EventUpdate,
) -> EventPublic:
    db_event = await get_event(session=session, event_id=id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    is_super = getattr(current_user, "is_superuser", False)
    if not (is_super or is_event_owner(db_event, current_user.id)):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    updated = await update_event(session=session, db_event=db_event, event_in=event_in)
    return EventPublic.model_validate(updated)


@router.delete("/{id}", response_model=Message)
async def delete_event_endpoint(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
) -> Message:
    db_event = await get_event(session=session, event_id=id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    is_super = getattr(current_user, "is_superuser", False)
    if not (is_super or is_event_owner(db_event, current_user.id)):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    await delete_event(session=session, db_event=db_event)
    return Message(message="Event deleted")


@router.post("/{id}/participants", response_model=EventPublic)
async def add_participants_endpoint(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    body: ParticipantsBody,
) -> EventPublic:
    db_event = await get_event(session=session, event_id=id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    is_super = getattr(current_user, "is_superuser", False)
    if not (is_super or is_event_owner(db_event, current_user.id)):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    updated = await add_participants_to_event(
        session=session, db_event=db_event, participant_ids=body.participant_ids
    )
    return EventPublic.model_validate(updated)


@router.delete("/{id}/participants/{user_id}", response_model=EventPublic)
async def remove_participant_endpoint(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    user_id: uuid.UUID,
) -> EventPublic:
    db_event = await get_event(session=session, event_id=id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    is_super = getattr(current_user, "is_superuser", False)
    if not (is_super or is_event_owner(db_event, current_user.id)):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    updated = await remove_participant_from_event(session=session, db_event=db_event, user_id=user_id)
    return EventPublic.model_validate(updated)