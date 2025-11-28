import uuid
from sqlalchemy import text
from user_db_utils import get_user, get_friends
from notifier import send_push_notification
from db import get_db
from datetime import datetime, timezone


def process_phase_change(user_id, previous_phase):
    db = get_db("prod")
    user = get_user(db, user_id)
    print('User: ', user)

    if not user:
        return

    current_phase = user["current_phase_name"]
    name = user["username"] or user["name"]
    db_text = f" changed their phase from '{previous_phase}' to '{current_phase}'."

    friends = get_friends(db, user_id)

    # testing
    # friends = list(filter(lambda f: str(f["id"]) == "9e35fd93-b0c3-4d30-afdd-17a20c0f6a1e", friends))

    print(friends)

    # Build notifications
    notif_rows = [
        {
            "message": db_text,
            "type": "profile",
            "type_id": user_id,
            "to_user_id": friend["id"],
            "from_user_id": user_id,
        }
        for friend in friends
    ]

    # Insert notifications in bulk
    insert_notifications(db, notif_rows)

    # Dispatch push notifications
    for f in friends:
        if f["push_token"]:
            send_push_notification(
                tokens=[f["push_token"]],
                title=f"{name} changed their phase",
                body=f"{name} changed their phase to '{current_phase}'",
                image=None,
                data={"type": "friend", "id": user_id},
            )



def insert_notifications(db, rows):
    if not rows:
        return

    now = datetime.now(timezone.utc)

    # add id + timestamps
    for r in rows:
        r["id"] = str(uuid.uuid4())
        r["created_at"] = now
        r["updated_at"] = now

    db.execute(
        text("""
            INSERT INTO notifications
                (id, message, type, type_id, to_user_id, from_user_id, created_at, updated_at)
            VALUES
                (:id, :message, :type, :type_id, :to_user_id, :from_user_id, :created_at, :updated_at)
        """),
        rows
    )
    db.commit()
