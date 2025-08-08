from checks import check_user_badge_progress, check_user_plant_progress
from db import get_db
from notifier import send_push_notification
from sqlalchemy import text


def run_background_checks():
    db = get_db("prod")
    user_ids = db.execute(text("SELECT id FROM users")).scalars().all()

    for user_id in user_ids:
        badge_msgs = check_user_badge_progress(user_id)
        plant_msgs = check_user_plant_progress(user_id)

        all_msgs = badge_msgs + plant_msgs
        if all_msgs:
            send_push_notification(user_id=user_id, messages=all_msgs)


