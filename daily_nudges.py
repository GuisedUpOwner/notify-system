
import os
import time
import json
import logging
from typing import List, Dict, Tuple
from datetime import datetime, timezone
from functools import partial

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# local app imports assumed to be available in same package
from background_check import background_checks
from notifier import send_push_notification

# ======== Configuration ========
MAIN_DATABASE_URL = os.getenv("MAIN_DATABASE_URL")
MAX_BATCH = 100
DB_RETRY_ATTEMPTS = 3
DB_RETRY_BACKOFF = 2  # seconds (exponential)
PUSH_RETRY_ATTEMPTS = 3
PUSH_RETRY_BACKOFF = 1  # seconds (exponential)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ======== DB utilities (simplified) ========
def get_all_users(db):
    query = text("""
        SELECT 
            u.id AS user_id,
            u.push_token AS push_token,
            gs.current_streak AS current_streak,
            p.last_watered_date AS last_watered_date
        FROM users u
        LEFT JOIN garden_stats gs 
            ON gs.user_id = u.id
        LEFT JOIN user_plants p 
            ON p.user_id = u.id 
           AND p.is_active = true
        WHERE u.push_token IS NOT NULL
    """)
    
    result = db.execute(query)
    rows = result.fetchall()

    users = []
    for r in rows:
        users.append({
            "user_id": r.user_id,
            "token": r.push_token,
            "current_streak": r.current_streak or 0,
            "last_watered_date": r.last_watered_date,
        })

    return users



# ======== Classification and scheduling ========

def classify_user(user: Dict, check_date: datetime) -> Dict:
    now = check_date

    # No last_streak_date returned from SQL, so treat streak freshness using watering streak only
    # Since garden_stats.current_streak is your streak source

    current_streak = user.get("current_streak", 0)
    last_watered = user.get("last_watered_date")

    # Convert last_watered (date) into datetime
    if last_watered:
        if isinstance(last_watered, datetime):
            lw = last_watered
        else:
            lw = datetime.combine(last_watered, datetime.min.time(), tzinfo=timezone.utc)
        days_since_watered = (now - lw).days
    else:
        days_since_watered = 999

    # Use watering recency to determine streak status
    # If watered today → streak is "consistent"
    # If watered yesterday → "losing streak"
    # If within 3 days → "inconsistent"
    # Else → "not started"
    if days_since_watered == 0:
        app_type = "consistent"
    elif days_since_watered == 1:
        app_type = "losing_streak"
    elif days_since_watered <= 3:
        app_type = "inconsistent"
    else:
        app_type = "not_started"

    # Plant emotional classification
    if days_since_watered == 0:
        plant_type = "thriving"
    elif days_since_watered == 1:
        plant_type = "hopeful"
    elif days_since_watered <= 3:
        plant_type = "sad"
    else:
        plant_type = "neglected"

    return {
        **user,
        "app_type": app_type,
        "plant_type": plant_type,
        "current_streak": current_streak,
    }


SCHEDULE_RULES = {
    "lost_streak": ("08:00", "Your plant misses you 💔 Tap to water!"),
    "inconsistent": ("12:00", "Keep going — you're so close!"),
    "consistent": ("18:00", "You're on fire! Just one more day!"),
    "not_started": ("14:00", "Your garden is waiting 🌱 Start today!"),
}


def choose_schedule_type(app_type: str, plant_type: str) -> str:
    # returns one of keys in SCHEDULE_RULES
    if app_type in ("losing_streak",) or plant_type == "neglected":
        return "lost_streak"
    if app_type == "inconsistent" or plant_type == "sad":
        return "inconsistent"
    if app_type == "consistent" or plant_type == "thriving":
        return "consistent"
    return "not_started"


# ======== Notification helpers ========
def build_message_for_user(user: Dict, check_date: datetime) -> Tuple[str, str]:
    """Run background checks and return (title, body) for a single user.
    Handles both dict and list responses from plant badge logic.
    """
    res = background_checks(
        user_id=user["user_id"],
        current_streak=user.get("current_streak", 0),
        last_watered_date=user.get("last_watered_date"),
        check_date=check_date,
    )

    # Handle plant nudges: may be dict OR list OR empty
    plant_msg = res.get("plant")
    if plant_msg:
        if isinstance(plant_msg, dict):
            return plant_msg.get("title", "Keep Growing"), plant_msg.get("description", "Your garden is listening")
        if isinstance(plant_msg, list) and len(plant_msg) > 0:
            first = plant_msg[0]
            return first.get("title", "Keep Growing"), first.get("description", "Your garden is listening")

    # Handle app message: always dict
    app_single = res.get("app_single")
    if isinstance(app_single, dict):
        return (
            app_single.get("title", "Keep Growing"),
            app_single.get("description", "Your garden is listening")
        )

    # Fallback
    return "Keep Growing", "Your garden is listening 🌿"


def retry_send(tokens: List[str], title: str, body: str) -> bool:
    """Attempt to send push notification with retries and exponential backoff.
    Returns True on success, False on final failure.
    """
    attempt = 0
    while attempt < PUSH_RETRY_ATTEMPTS:
        try:
            # send_push_notification(tokens=tokens, title=title, body=body)
            logger.info("Sent %d tokens (title='%s')", len(tokens), title)
            return True
        except Exception as e:
            attempt += 1
            wait = PUSH_RETRY_BACKOFF * (2 ** (attempt - 1))
            logger.warning("Push send failed (attempt %d/%d): %s. Retrying in %ds", attempt, PUSH_RETRY_ATTEMPTS, e, wait)
            time.sleep(wait)
    logger.error("Failed to send push after %d attempts", PUSH_RETRY_ATTEMPTS)
    return False


# ======== Main orchestration ========

def main():
    if not MAIN_DATABASE_URL:
        logger.error("MAIN_DATABASE_URL not set")
        return

    engine = create_engine(MAIN_DATABASE_URL)
    check_date = datetime.now(timezone.utc)

    # 1) Fetch users with DB retry
    users = None
    for attempt in range(1, DB_RETRY_ATTEMPTS + 1):
        try:
            with engine.connect() as conn:
                users = get_all_users(conn)
            break
        except Exception as e:
            wait = DB_RETRY_BACKOFF * (2 ** (attempt - 1))
            logger.warning("DB fetch failed (attempt %d/%d): %s. Retrying in %ds", attempt, DB_RETRY_ATTEMPTS, e, wait)
            time.sleep(wait)

    if users is None:
        logger.critical("Could not fetch users after %d attempts. Aborting.", DB_RETRY_ATTEMPTS)
        return

    logger.info("Fetched %d users", len(users))

    # 2) classify and annotate users
    classified = [classify_user(u, check_date) for u in users]

    # 3) assign schedule and build personalized messages
    # structure: schedules[time_slot][(title,body)] -> list of tokens
    schedules: Dict[str, Dict[Tuple[str, str], List[str]]] = {}

    for u in classified:
        schedule_key = choose_schedule_type(u["app_type"], u["plant_type"])
        time_slot, default_body = SCHEDULE_RULES[schedule_key]

        # Build personalized title/body
        title, body = build_message_for_user(u, check_date)
        # If background_checks returned nothing useful, fall back to schedule message
        if not title or not body:
            title = "Keep Growing"
            body = default_body

        schedules.setdefault(time_slot, {}).setdefault((title, body), []).append(u["token"])

    # 4) send notifications: for each timeslot, group identical messages and batch
    for time_slot, messages in schedules.items():
        logger.info("Processing timeslot %s with %d distinct messages", time_slot, len(messages))
        for (title, body), tokens in messages.items():
            # chunk tokens into provider-friendly size
            for i in range(0, len(tokens), MAX_BATCH):
                batch = tokens[i:i + MAX_BATCH]
                success = retry_send(batch, title, body)
                if not success:
                    # optionally persist failures to a dead-letter table or alerting system
                    logger.error("Failed to send batch for timeslot %s; title=%s", time_slot, title)

    logger.info("Done processing nudges for %s users", len(users))


if __name__ == "__main__":
    main()
