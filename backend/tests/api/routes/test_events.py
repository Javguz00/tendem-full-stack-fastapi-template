import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.event import create_random_event


def test_create_event(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    data = {
        "title": "Test Event",
        "description": "Test event description",
        "event_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "participant_ids": []
    }
    response = client.post(
        f"{settings.API_V1_STR}/events/", headers=superuser_token_headers, json=data
    )
    assert response.status_code == 200
    content = response.json()
    assert content["title"] == data["title"]
    assert content["description"] == data["description"]
    assert "id" in content
    assert "owner_id" in content
    assert "created_at" in content


def test_read_event(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    event = create_random_event(db)
    response = client.get(
        f"{settings.API_V1_STR}/events/{event.id}", headers=superuser_token_headers
    )
    assert response.status_code == 200
    content = response.json()
    assert content["id"] == str(event.id)
    assert content["title"] == event.title


def test_read_event_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/events/{uuid.uuid4()}", headers=superuser_token_headers
    )
    assert response.status_code == 404
    content = response.json()
    assert content["detail"] == "Event not found"


def test_read_event_not_enough_permissions(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    event = create_random_event(db)
    response = client.get(
        f"{settings.API_V1_STR}/events/{event.id}", headers=normal_user_token_headers
    )
    assert response.status_code == 400
    content = response.json()
    assert content["detail"] == "Not enough permissions"


def test_read_event_as_participant(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    from tests.utils.user import create_random_user
    from tests.utils.utils import user_authentication_headers
    from app.crud import add_participants_to_event_sync
    
    # Create a participant user and get their token
    participant_user = create_random_user(db)
    participant_token_headers = user_authentication_headers(
        client=client, email=participant_user.email, db=db
    )
    
    # Create event with different owner
    event = create_random_event(db)
    
    # Add the participant user to the event
    add_participants_to_event_sync(session=db, db_event=event, participant_ids=[participant_user.id])
    
    # Now the participant should be able to read the event
    response = client.get(
        f"{settings.API_V1_STR}/events/{event.id}", headers=participant_token_headers
    )
    assert response.status_code == 200
    content = response.json()
    assert content["id"] == str(event.id)


def test_read_events(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # Create exactly 5 events
    events = [create_random_event(db) for _ in range(5)]
    
    # Test default pagination
    response = client.get(
        f"{settings.API_V1_STR}/events/", headers=superuser_token_headers
    )
    assert response.status_code == 200
    content = response.json()
    assert "data" in content
    assert "count" in content
    assert content["count"] == 5
    assert len(content["data"]) == 5
    
    # Test pagination with limit
    response = client.get(
        f"{settings.API_V1_STR}/events/?skip=0&limit=3", headers=superuser_token_headers
    )
    assert response.status_code == 200
    content = response.json()
    assert content["count"] == 5
    assert len(content["data"]) == 3
    
    # Test pagination with skip
    response = client.get(
        f"{settings.API_V1_STR}/events/?skip=3&limit=3", headers=superuser_token_headers
    )
    assert response.status_code == 200
    content = response.json()
    assert content["count"] == 5
    assert len(content["data"]) == 2


def test_read_events_normal_user(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    from tests.utils.user import create_random_user
    from tests.utils.utils import user_authentication_headers
    from app.crud import add_participants_to_event_sync
    
    # Get the normal user
    normal_user = create_random_user(db)
    normal_user_headers = user_authentication_headers(
        client=client, email=normal_user.email, db=db
    )
    
    # Create events for different scenarios
    # 1. Event owned by normal user
    owned_event = create_random_event(db, owner_id=normal_user.id)
    
    # 2. Event where normal user is participant
    other_user = create_random_user(db)
    participant_event = create_random_event(db, owner_id=other_user.id)
    add_participants_to_event_sync(session=db, db_event=participant_event, participant_ids=[normal_user.id])
    
    # 3. Event not related to normal user (should not be visible)
    create_random_event(db, owner_id=other_user.id)
    
    response = client.get(
        f"{settings.API_V1_STR}/events/", headers=normal_user_headers
    )
    assert response.status_code == 200
    content = response.json()
    assert "data" in content
    assert "count" in content
    assert content["count"] == 2  # Only owned and participant events
    
    # Verify the visible events are the correct ones
    visible_event_ids = {event["id"] for event in content["data"]}
    expected_event_ids = {str(owned_event.id), str(participant_event.id)}
    assert visible_event_ids == expected_event_ids


def test_update_event(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    from tests.utils.user import create_random_user
    from tests.utils.utils import user_authentication_headers
    
    # Create owner user and get their token
    owner_user = create_random_user(db)
    owner_token_headers = user_authentication_headers(
        client=client, email=owner_user.email, db=db
    )
    
    # Create event as owner
    event = create_random_event(db, owner_id=owner_user.id)
    
    data = {"title": "Updated Event Title"}
    response = client.put(
        f"{settings.API_V1_STR}/events/{event.id}",
        headers=owner_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["title"] == data["title"]
    assert content["id"] == str(event.id)


def test_update_event_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {"title": "Updated Event Title"}
    response = client.put(
        f"{settings.API_V1_STR}/events/{uuid.uuid4()}",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 404
    content = response.json()
    assert content["detail"] == "Event not found"


def test_update_event_not_enough_permissions(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    event = create_random_event(db)
    data = {"title": "Updated Event Title"}
    response = client.put(
        f"{settings.API_V1_STR}/events/{event.id}",
        headers=normal_user_token_headers,
        json=data,
    )
    assert response.status_code == 400
    content = response.json()
    assert content["detail"] == "Not enough permissions"


def test_update_event_participants(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    from tests.utils.user import create_random_user
    from tests.utils.utils import user_authentication_headers
    from app.models import Event
    
    # Create owner user and get their token
    owner_user = create_random_user(db)
    owner_token_headers = user_authentication_headers(
        client=client, email=owner_user.email, db=db
    )
    
    # Create event as owner
    event = create_random_event(db, owner_id=owner_user.id)
    user1 = create_random_user(db)
    user2 = create_random_user(db)
    
    # Add participants via PUT
    data = {"participant_ids": [str(user1.id), str(user2.id)]}
    response = client.put(
        f"{settings.API_V1_STR}/events/{event.id}",
        headers=owner_token_headers,
        json=data,
    )
    assert response.status_code == 200
    
    # Verify participants were added by checking database
    db_event = db.get(Event, event.id)
    participant_ids = {p.id for p in db_event.participants}
    assert participant_ids == {user1.id, user2.id}
    
    # Remove one participant via PUT
    data = {"participant_ids": [str(user1.id)]}
    response = client.put(
        f"{settings.API_V1_STR}/events/{event.id}",
        headers=owner_token_headers,
        json=data,
    )
    assert response.status_code == 200
    
    # Verify participant was removed by checking database
    db.refresh(db_event)
    participant_ids = {p.id for p in db_event.participants}
    assert participant_ids == {user1.id}


def test_delete_event(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    from tests.utils.user import create_random_user
    from tests.utils.utils import user_authentication_headers
    
    # Create owner user and get their token
    owner_user = create_random_user(db)
    owner_token_headers = user_authentication_headers(
        client=client, email=owner_user.email, db=db
    )
    
    # Create event as owner
    event = create_random_event(db, owner_id=owner_user.id)
    
    response = client.delete(
        f"{settings.API_V1_STR}/events/{event.id}", headers=owner_token_headers
    )
    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Event deleted"


def test_delete_event_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.delete(
        f"{settings.API_V1_STR}/events/{uuid.uuid4()}", headers=superuser_token_headers
    )
    assert response.status_code == 404
    content = response.json()
    assert content["detail"] == "Event not found"


def test_delete_event_not_enough_permissions(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    event = create_random_event(db)
    response = client.delete(
        f"{settings.API_V1_STR}/events/{event.id}", headers=normal_user_token_headers
    )
    assert response.status_code == 400
    content = response.json()
    assert content["detail"] == "Not enough permissions"


def test_add_participants(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    from tests.utils.user import create_random_user
    
    event = create_random_event(db)
    user1 = create_random_user(db)
    user2 = create_random_user(db)
    
    data = {"participant_ids": [str(user1.id), str(user2.id)]}
    response = client.post(
        f"{settings.API_V1_STR}/events/{event.id}/participants",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["id"] == str(event.id)


def test_remove_participant(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    from tests.utils.user import create_random_user
    from app.crud import add_participants_to_event_sync
    
    event = create_random_event(db)
    user = create_random_user(db)
    
    # Add participant first
    add_participants_to_event_sync(session=db, db_event=event, participant_ids=[user.id])
    
    # Remove participant
    response = client.delete(
        f"{settings.API_V1_STR}/events/{event.id}/participants/{user.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["id"] == str(event.id)