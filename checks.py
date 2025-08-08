from db import get_db
from sqlalchemy import text


def check_user_badge_progress(user_id: str):
    db = get_db("prod")
    
    # Fetch badge progress along with badge metadata
    badge_progress_list = db.execute(text("""
        SELECT 
            bp.badge_id,
            bp.progress,
            b.name AS badge_name,
            b.required_progress,
            b.rarity
        FROM badge_progress bp
        JOIN badges b ON b.id = bp.badge_id
        WHERE bp.user_id = :uid
    """), {"uid": user_id}).mappings().all()

    earned_badges = db.execute(text("""
        SELECT badge_id FROM user_badges WHERE user_id = :uid
    """), {"uid": user_id}).scalars().all()

    notifications = []

    for bp in badge_progress_list:
        badge_id = bp["badge_id"]
        progress = bp["progress"]
        badge_name = bp["badge_name"]
        required_progress = bp["required_progress"]
        rarity = bp["rarity"]

        # Notification emoji by rarity
        rarity_emoji = {
            "common": "🎉",
            "rare": "🌟",
            "epic": "🔥",
            "legendary": "🏆"
        }.get(rarity.lower(), "🎉")

        if progress >= required_progress and badge_id not in earned_badges:
            notifications.append(f"{rarity_emoji} Congrats! You earned the '{badge_name}' badge.")
            db.execute(text("""
                INSERT INTO user_badges (user_id, badge_id, awarded_at)
                VALUES (:uid, :bid, NOW())
            """), {"uid": user_id, "bid": badge_id})
        elif progress >= (required_progress * 0.9) and badge_id not in earned_badges:
            left = int(required_progress - progress)
            notifications.append(f"⚡ You're just {left}% away from the '{badge_name}' badge!")

    db.commit()
    return notifications




def check_user_plant_progress(user_id: str):
    db = get_db("prod")

    plants = db.execute(text("""
        SELECT id, name, current_stage, water_streak, last_watered_date
        FROM user_plants
        WHERE user_id = :uid AND is_active = true
    """), {"uid": user_id}).mappings().all()

    notifications = []

    for plant in plants:
        name = plant["name"]
        stage = plant["current_stage"]
        streak = plant["water_streak"]

        if streak == 6:
            notifications.append(f"💧 Just one more day of watering and '{name}' will grow!")
        elif stage == "medium":
            notifications.append(f"🌿 '{name}' is now at the medium stage!")

    return notifications
