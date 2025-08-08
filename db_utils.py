from datetime import datetime, timedelta, timezone
import os
from db import get_db
from sqlalchemy import text
from dotenv import load_dotenv
from typing import List, Dict, Any

from collections import defaultdict
import pytz



load_dotenv()  


def get_user_by_id(user_id: str):
    db = get_db("prod")
    try:
        # 1️⃣ user core + phase name -------------------------------------------------------------
        user_row = (
            db.execute(
                text(
                    """
                    SELECT  u.id, u.name, u.username, u.dob,
                            u.gender, u.pronouns, u.device_type,
                            p.name AS current_phase
                    FROM    users   AS u
                    LEFT JOIN phases AS p ON p.id = u.current_phase
                    WHERE   u.id = :uid
                    """
                ),
                {"uid": user_id},
            ).mappings().first()
        )
        if not user_row:
            return None
        user = dict(user_row)

        # 2️⃣ voyages last 30 days --------------------------------------------------------------
        since = datetime.now(timezone.utc) - timedelta(days=30)
        voyages = db.execute(
            text(
                """
                SELECT v.phase_id, v.created_at, p.name AS phase_name
                FROM   voyages v
                JOIN   phases  p ON p.id = v.phase_id
                WHERE  v.user_id = :uid
                  AND  v.deleted_at IS NULL
                  AND  v.created_at >= :since
                ORDER  BY v.created_at DESC
                """
            ),
            {"uid": user_id, "since": since},
        ).mappings().all()
        user["phases"] = [
            {
                "phase_id": str(v["phase_id"]),
                "name": v["phase_name"],
                "timestamp": v["created_at"].isoformat() if v["created_at"] else None,
            }
            for v in voyages
        ]

        # 3️⃣ recent authored posts -------------------------------------------------------------
        posts = db.execute(
            text(
                """
                SELECT id, description, created_at
                FROM   posts
                WHERE  user_id = :uid AND deleted_at IS NULL
                ORDER  BY created_at DESC
                LIMIT  :lim
                """
            ),
            {"uid": user_id, "lim": POSTS_LIMIT},
        ).mappings().all()
        user["recent_posts"] = [
            {
                "post_id": str(p["id"]),
                "description": p["description"],
                "timestamp": p["created_at"].isoformat() if p["created_at"] else None,
            }
            for p in posts
        ]

        # 4️⃣ liked posts (descriptions only) ---------------------------------------------------
        liked = db.execute(
            text(
                """
                SELECT p.description
                FROM   post_likes pl
                JOIN   posts      p ON p.id = pl.post_id
                WHERE  pl.user_id = :uid AND p.deleted_at IS NULL
                ORDER  BY pl.created_at DESC NULLS LAST, p.created_at DESC
                LIMIT  :lim
                """
            ),
            {"uid": user_id, "lim": LIKED_LIMIT},
        ).all()
        user["liked_posts"] = [row[0] for row in liked]

        # 5️⃣ commented posts -------------------------------------------------------------------
        comments = db.execute(
            text(
                """
                SELECT p.description, c.comment
                FROM   comments c
                JOIN   posts    p ON p.id = c.post_id
                WHERE  c.user_id = :uid AND p.deleted_at IS NULL
                ORDER  BY c.created_at DESC
                LIMIT  :lim
                """
            ),
            {"uid": user_id, "lim": COMMENTED_LIMIT},
        ).all()
        user["commented_posts"] = [
            f"{desc} – {comm}" for desc, comm in comments
        ]

        return user
    finally:
        db.close()



def get_all_users(db):
    """
    Fetch all active users with their metadata.
    """
    result = db.execute(
        text("""
            SELECT 
                u.id AS user_id,
                u.push_token,
                us.current_streak,
                MAX(us.streak_date) AS last_streak_date,
                MAX(p.last_watered) AS last_watered_date
            FROM users u
            LEFT JOIN user_streaks us ON u.id = us.user_id
            LEFT JOIN plant_progress p ON u.id = p.user_id
            WHERE u.is_active = true AND u.push_token IS NOT NULL
            GROUP BY u.id, u.push_token, us.current_streak
        """)
    )
    return result.fetchall()



def classify_user(row, check_date: datetime):
    now = check_date
    last_streak = row.last_streak_date
    last_watered = row.last_watered_date
    current_streak = row.current_streak or 0

    days_since_streak = (now - last_streak).days if last_streak else 999
    days_since_watered = (now - last_watered).days if last_watered else 999

    # App streak classification
    if days_since_streak == 0:
        app_type = "consistent"
    elif days_since_streak == 1:
        app_type = "losing_streak"
    elif days_since_streak <= 3:
        app_type = "inconsistent"
    else:
        app_type = "not_started"

    # Plant classification
    if days_since_watered == 0:
        plant_type = "thriving"
    elif days_since_watered == 1:
        plant_type = "hopeful"
    elif days_since_watered <= 3:
        plant_type = "sad"
    else:
        plant_type = "neglected"

    return {
        "user_id": row.user_id,
        "token": row.push_token,
        "current_streak": current_streak,
        "last_watered_date": last_watered,
        "app_type": app_type,
        "plant_type": plant_type
    }



def group_users_by_schedule(users, check_date: datetime):
    """
    Group users by notification time and message type.
    Returns: { "8:00": [users], "12:00": [users], ... }
    """
    # Define schedule logic
    SCHEDULE_RULES = {
        "lost_streak": ("8:00", "Your plant misses you 💔 Tap to water!"),
        "inconsistent": ("12:00", "Keep going — you're so close!"),
        "consistent": ("18:00", "You're on fire! Just one more day!"),
        "not_started": ("14:00", "Your garden is waiting 🌱 Start today!")
    }

    grouped = defaultdict(list)

    for user in users:
        # Use the most urgent type
        urgency_type = user["app_type"] if user["app_type"] != "consistent" else user["plant_type"]

        if urgency_type in ["losing_streak", "neglected"]:
            key = "lost_streak"
        elif urgency_type == "inconsistent" or user["plant_type"] == "sad":
            key = "inconsistent"
        elif urgency_type == "consistent" or user["plant_type"] == "thriving":
            key = "consistent"
        else:
            key = "not_started"

        time_slot, default_body = SCHEDULE_RULES[key]
        grouped[time_slot].append({
            "user_id": user["user_id"],
            "token": user["token"],
            "default_body": default_body
        })

    return grouped