import uuid
from datetime import datetime, timedelta, timezone
from sqlmodel import Session

from app.models import Event, User
from tests.utils.utils import random_email, random_lower_string


def create_random_event(db: Session, *, owner_id: uuid.UUID | None = None) -> Event:
    """Create a random event for testing."""
    if owner_id is None:
        from tests.utils.utils import MOCK_SUPERUSER_ID
        owner_id = MOCK_SUPERUSER_ID
    
    event = Event(
        title="Test Event",
        description="Test event description",
        event_time=datetime.now(timezone.utc) + timedelta(days=1),
        owner_id=owner_id
    )
    
    db.add(event)
    db.commit()
    db.refresh(event)
    return event