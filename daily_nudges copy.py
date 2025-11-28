# daily_nudges.py
import json
from sqlalchemy import create_engine
from datetime import datetime, timezone

from background_check import background_checks
from badge_checks import check_plant_badges_upcoming, get_single_app_streak_message
from notifier import send_push_notification
from db_utils import get_all_users, classify_user, group_users_by_schedule

from dotenv import load_dotenv
load_dotenv()
import os

MAIN_DATABASE_URL = os.getenv("MAIN_DATABASE_URL")


def main():
    engine = create_engine(MAIN_DATABASE_URL)
    with engine.connect() as conn:
        # Set db session
        db = conn.execution_options(autocommit=False)

        # 1. Get all users
        raw_users = get_all_users(db)
        check_date = datetime.now(timezone.utc)

        # 2. Classify each user
        classified_users = [
            classify_user(row, check_date) for row in raw_users
        ]

        # 3. Group by schedule
        scheduled_groups = group_users_by_schedule(classified_users, check_date)

        # 4. Process each time slot
        for time_slot, users in scheduled_groups.items():
            print(f"\n⏰ Processing time slot: {time_slot}")

            # Split into chunks of 100
            chunk_size = 100
            for i in range(0, len(users), chunk_size):
                chunk = users[i:i + chunk_size]

                # Run background check for first user to get dynamic message
                sample = chunk[0]
                result = background_checks(
                    user_id=sample["user_id"],
                    current_streak=sample["current_streak"],
                    last_watered_date=sample["last_watered_date"],
                    check_date=check_date
                )

                # Pick best message
                if result.get("plant"):
                    title = result["plant"]["title"]
                    body = result["plant"]["description"]
                elif result.get("app_single"):
                    title = result["app_single"]["title"]
                    body = result["app_single"]["description"]
                else:
                    title = "Keep Growing"
                    body = "Your garden is listening 🌿"

                # Send chunk
                send_chunked_notifications(chunk, title, body)


def send_chunked_notifications(users_chunk, title: str, body: str):
    """
    Send push notifications in chunks of 100 (or your provider’s limit).
    """
    tokens = [u["token"] for u in users_chunk]
    if not tokens:
        return

    try:
        send_push_notification(
            tokens=tokens,
            title=title,
            body=body
        )
        print(f"✅ Sent to {len(tokens)} users")
    except Exception as e:
        print(f"❌ Failed to send batch: {e}")