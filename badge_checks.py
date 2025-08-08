from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from constants import BADGES, PLANT_BADGES, get_plant_messages
from db import get_db
from random import choice
import json
from typing import Dict, Any, List


# === Creative Templates ===
STREAK_TEMPLATES = {
    "weekly": {
        "consistent": {
            "titles": [
                "🔥 Streak in Motion!",
                "🎯 Weekly Warrior Rising!",
                "⚡ Momentum Builder",
                "📅 Almost There!",
                "🏆 Badge on the Horizon",
                "💫 Daily Dynamo",
                "🌟 On the Brink of Glory"
            ],
            "descriptions": [
                "Just {days} more {day_s} to lock in your 7-day streak! Keep showing up.",
                "You're {days} day{day_s} away from a shiny new badge. Don’t break now!",
                "Consistency is power — {days} more {day_s} and you’ll own it!",
                "The Weekly Warrior badge is calling your name. Answer in {days} {day_s}.",
                "One check-in at a time. {days} to go until victory!",
                "Your rhythm is strong. Keep it alive for {days} more {day_s}!"
            ]
        },
        "losing_streak": {
            "titles": [
                    "⚠️ Streak at Risk!",
                    "💔 One Day Away from Reset",
                    "🚨 Don’t Let It Slip!",
                    "⏳ Last Chance to Save It",
                    "🔥 Re-ignite Your Fire",
                    "🛑 One Missed, But Not Lost!"
                ],
            "descriptions": [
                "You missed yesterday — check in today to revive your {count}-day streak!",
                "Your streak is hanging by a thread. Tap in now to save it!",
                "Don’t let all that progress vanish. Return today to keep it alive.",
                "One day off doesn’t define you. Come back now and reclaim your flow.",
                "Almost had it! One more tap to keep your streak burning."
            ]
        },
        "inconsistent": {
            "titles": [
                "🔄 Getting Into the Groove",
                "📈 Building Momentum",
                "🌱 Progress, Not Perfection",
                "🌀 On Again, Off Again",
                "💡 Starting to Stick"
            ],
            "descriptions": [
                "You've checked in {count} times this week — aim for 7 with {days} left!",
                "Some days count, some don’t. Let’s make the rest count!",
                "You're building rhythm. Try to hit {days} more {day_s} this week.",
                "Inconsistency is normal. What matters is showing up again and again."
            ]
        }
    },
    "monthly": {
        "consistent": {
            "titles": [
                "🌕 Monthly Master in the Making",
                "📅 Calendar Crusher",
                "🗓️ Month-Long Mission",
                "📆 Daily Dominator"
            ],
            "descriptions": [
                "You’ve been active {count} days this month — only {days} left to complete it!",
                "Total domination awaits. {days} more {day_s} to become a Monthly Master.",
                "Track your progress — {count}/30 days done. Keep the calendar green!"
            ]
        },
        "inconsistent": {
            "titles": [
                "📉 Patchy Progress",
                "🧩 Missing Pieces",
                "📅 Not Every Day, But Some"
            ],
            "descriptions": [
                "You've shown up {count} times this month. Can you reach 30?",
                "Spotty but present. Let’s fill in the gaps with {days} more {day_s}.",
                "It’s not too late to turn this month around. Try daily check-ins!"
            ]
        }
    },
    "night_owl": {
        "consistent": {
            "titles": [
                "🦉 Night Owl Soaring",
                "🌙 Midnight Marauder",
                "🌃 After-Hours Ace"
            ],
            "descriptions": [
                "You’ve checked in {count} times after 10 PM! Only {days} more to earn your badge.",
                "The world sleeps — but you’re conquering the night. {days} more {day_s} to go!",
                "Your late-night hustle is paying off. Keep glowing after dark!"
            ]
        },
        "inconsistent": {
            "titles": [
                "🌑 Part-Time Nocturne",
                "🌌 Occasional Night Walker"
            ],
            "descriptions": [
                "You’ve made {count} late-night visits. Can you hit 30?",
                "Sometimes you rise at night. Let’s make it a habit — {days} more {day_s} needed."
            ]
        }
    },
    "early_bird": {
        "consistent": {
            "titles": [
                "🌅 Early Bird Soaring",
                "🌤️ Sunrise Superstar",
                "⏰ Morning Maverick"
            ],
            "descriptions": [
                "You’ve crushed {count} early check-ins! Only {days} more to earn your badge.",
                "While others sleep, you rise. {days} more mornings to mastery!",
                "Your mornings are golden. Keep showing up before 9 AM!"
            ]
        },
        "inconsistent": {
            "titles": [
                "⛅ Part-Time Sunrise",
                "🌤️ Sporadic Starter"
            ],
            "descriptions": [
                "You’ve started strong {count} times before 9 AM. Can you hit 30?",
                "Some days you rise early — let’s make it most days. {days} more to go!"
            ]
        }
    }
}

# Fallback
FALLBACK = {
    "title": "You're Doing Amazing!",
    "description": "Keep up the great work — every tap counts! 🌿✨",
    "type": "consistent"
}

def get_single_app_streak_message(user_id: str, date: datetime = None) -> Dict[str, Any]:
    """
    Returns a rich motivational nudge for the most urgent upcoming app streak.
    Returns: { "title": "...", "description": "...", "type": "consistent|inconsistent|losing_streak" }
    """
    if date is None:
        date = datetime.now(timezone.utc)
    db = get_db()  # Use prod DB
    candidates = []  # List of (urgency_score, result_dict)

    def random_choice(templates, **kwargs):
        return choice(templates).format(**kwargs)

    def add_candidate(priority: int, template_key: str, badge_type: str, **kwargs):
        templates = STREAK_TEMPLATES.get(badge_type, {}).get(template_key, {})
        if not templates:
            return
        title = random_choice(templates["titles"])
        description = random_choice(templates["descriptions"], **kwargs)
        candidates.append((
            priority,
            {
                "title": title,
                "description": description,
                "type": template_key
            }
        ))

    # ================= Weekly Warrior =================
    week_ago = date - timedelta(days=6)
    result = db.execute(
        text("""
            SELECT DATE(streak_date) AS streak_date
            FROM user_streaks
            WHERE user_id = :user_id
              AND streak_date >= :start_date
            ORDER BY streak_date DESC
        """),
        {"user_id": user_id, "start_date": week_ago.date()}
    )
    streak_dates = [row.streak_date.isoformat() for row in result]

    consecutive_count = 0
    total_weekly_active = 0
    current = date

    for _ in range(7):
        d = current.date().isoformat()
        if d in streak_dates:
            total_weekly_active += 1
            if consecutive_count == 0 or (current + timedelta(days=1)).date().isoformat() in streak_dates:
                consecutive_count += 1
            else:
                break
        else:
            break
        current -= timedelta(days=1)

    if consecutive_count < 7:
        days_remaining = 7 - consecutive_count
        yesterday = (date - timedelta(days=1)).date().isoformat()
        day_before = (date - timedelta(days=2)).date().isoformat()

        # Losing streak: had 2+ day streak, missed yesterday
        if consecutive_count == 1 and yesterday not in streak_dates and day_before in streak_dates:
            add_candidate(
                1, "losing_streak", "weekly",
                count=consecutive_count - 1,
                days=days_remaining,
                day_s="s" if days_remaining > 1 else ""
            )
        elif consecutive_count >= 1:
            add_candidate(
                days_remaining, "consistent", "weekly",
                days=days_remaining,
                day_s="s" if days_remaining > 1 else ""
            )
        else:
            add_candidate(
                days_remaining, "inconsistent", "weekly",
                count=total_weekly_active,
                days=days_remaining,
                day_s="s" if days_remaining > 1 else ""
            )

    # ================= Monthly Master =================
    start_of_month = date.replace(day=1)
    next_month = (date.replace(day=28) + timedelta(days=4)).replace(day=1)
    end_of_month = next_month - timedelta(days=1)
    total_days_in_month = end_of_month.day

    result = db.execute(
        text("""
            SELECT COUNT(DISTINCT DATE(streak_date)) AS count
            FROM user_streaks
            WHERE user_id = :user_id
              AND streak_date >= :start_date
              AND streak_date <= :end_date
        """),
        {"user_id": user_id, "start_date": start_of_month, "end_date": end_of_month}
    )
    row = result.fetchone()
    days_active = row.count if row.count else 0

    if days_active < total_days_in_month:
        days_remaining = total_days_in_month - days_active
        if days_active > total_days_in_month * 0.5:
            add_candidate(
                days_remaining, "consistent", "monthly",
                count=days_active,
                days=days_remaining,
                day_s="s" if days_remaining > 1 else ""
            )
        else:
            add_candidate(
                days_remaining, "inconsistent", "monthly",
                count=days_active,
                days=days_remaining,
                day_s="s" if days_remaining > 1 else ""
            )

    # ================= Night Owl =================
    result = db.execute(
        text("""
            SELECT COUNT(*) AS count
            FROM user_streaks
            WHERE user_id = :user_id
              AND streak_date::time >= '22:00:00'
        """),
        {"user_id": user_id}
    )
    night_count = result.fetchone().count

    if night_count < 30:
        days_remaining = 30 - night_count
        if night_count > 10:
            add_candidate(
                days_remaining, "consistent", "night_owl",
                count=night_count,
                days=days_remaining,
                day_s="s" if days_remaining > 1 else ""
            )
        else:
            add_candidate(
                days_remaining, "inconsistent", "night_owl",
                count=night_count,
                days=days_remaining,
                day_s="s" if days_remaining > 1 else ""
            )

    # ================= Early Bird =================
    result = db.execute(
        text("""
            SELECT COUNT(*) AS count
            FROM user_streaks
            WHERE user_id = :user_id
              AND streak_date::time < '09:00:00'
        """),
        {"user_id": user_id}
    )
    early_count = result.fetchone().count

    if early_count < 30:
        days_remaining = 30 - early_count
        if early_count > 10:
            add_candidate(
                days_remaining, "consistent", "early_bird",
                count=early_count,
                days=days_remaining,
                day_s="s" if days_remaining > 1 else ""
            )
        else:
            add_candidate(
                days_remaining, "inconsistent", "early_bird",
                count=early_count,
                days=days_remaining,
                day_s="s" if days_remaining > 1 else ""
            )

    # === Pick the Most Urgent (Lowest Priority Score) ===
    if not candidates:
        return FALLBACK

    best = min(candidates, key=lambda x: x[0])
    return best[1]









def get_upcoming_achievements(user_id: str, date: datetime = None):
    """
    Returns list of upcoming achievement nudges based on app usage streaks.
    Does NOT award badges.
    """
    if date is None:
        date = datetime.now(timezone.utc)
        
    db = get_db()
    upcoming = []

    # Helper to randomize message
    def random_message(templates, days_remaining):
        template = choice(templates)
        day_s = "days" if days_remaining > 1 else "day"
        return template.format(days=days_remaining, day_s=day_s)

    # ================= Weekly Warrior =================
    week_ago = date - timedelta(days=6)  # last 7 days including today
    result = db.execute(
        text("""
            SELECT DATE(streak_date) AS streak_date
            FROM user_streaks
            WHERE user_id = :user_id
              AND streak_date >= :start_date
            ORDER BY streak_date DESC
        """),
        {"user_id": user_id, "start_date": week_ago.date()}
    )
    streak_dates = [row.streak_date.isoformat() for row in result]

    # Count consecutive days from today backward
    consecutive_count = 0
    check_date = date
    for _ in range(7):
        if check_date.date().isoformat() in streak_dates:
            consecutive_count += 1
        else:
            break
        check_date -= timedelta(days=1)

    if consecutive_count < 7:
        days_remaining = 7 - consecutive_count
        badge = db.execute(
            text("SELECT id, name FROM badges WHERE name = :name"),
            {"name": BADGES['WEEKLY']}
        ).fetchone()

        if badge:
            weekly_messages = [
                "Keep it up! Just {days} more {day_s} and your 7-day streak badge is yours! 🌟",
                "Day 1 done! Come back tomorrow — you're on your way to that shiny streak badge! ✨",
                "You're starting strong! Keep coming back for {days} more {day_s} to grab your 7-day badge! 🏅",
                "Streak started! Return each day for {days} more {day_s} to earn your 7-day superstar badge! 💫",
                "One down, {days} to go! Your 7-day streak badge is waiting! 🎉",
                "The countdown is on! {days} more {day_s} 'til your 7-day streak badge! ⏳⭐",
                "You’ve started something awesome! Come back daily for {days} more {day_s} to unlock your badge! 🎖️",
            ]
            upcoming.append({
                'badge': {'id': badge.id, 'name': badge.name},
                'days_remaining': days_remaining,
                'message': random_message(weekly_messages, days_remaining)
            })

    # ================= Monthly Master =================
    start_of_month = date.replace(day=1)
    if date.month == 12:
        next_month = date.replace(year=date.year + 1, month=1, day=1)
    else:
        next_month = date.replace(month=date.month + 1, day=1)
    end_of_month = next_month - timedelta(days=1)
    total_days_in_month = end_of_month.day

    result = db.execute(
        text("""
            SELECT COUNT(DISTINCT DATE(streak_date)) AS count
            FROM user_streaks
            WHERE user_id = :user_id
              AND streak_date >= :start_date
              AND streak_date <= :end_date
        """),
        {
            "user_id": user_id,
            "start_date": start_of_month,
            "end_date": end_of_month
        }
    )
    row = result.fetchone()
    days_active = row.count if row.count else 0

    if days_active < total_days_in_month:
        days_remaining = total_days_in_month - days_active
        badge = db.execute(
            text("SELECT id, name FROM badges WHERE name = :name"),
            {"name": BADGES['MONTHLY']}
        ).fetchone()

        if badge:
            message = f"You're {days_remaining} day{'s' if days_remaining > 1 else ''} away from the Monthly Master badge!"
            upcoming.append({
                'badge': {'id': badge.id, 'name': badge.name},
                'days_remaining': days_remaining,
                'message': message
            })

    # ================= Night Owl =================
    result = db.execute(
        text("""
            SELECT COUNT(*) AS count
            FROM user_streaks
            WHERE user_id = :user_id
            AND streak_date::time >= '22:00:00'
        """),
        {"user_id": user_id}
    )
    night_count = result.fetchone().count

    if night_count < 30:
        days_remaining = 30 - night_count
        badge = db.execute(
            text("SELECT id, name FROM badges WHERE name = :name"),
            {"name": BADGES['NIGHT_OWL']}
        ).fetchone()

        if badge:
            night_messages = [
                "Stay up and check in after 10 PM for the next {days} {day_s} to earn your Night Owl badge! 🌙🦉",
                "Night owls unite! Drop by after 10 PM for {days} {day_s} to unlock your badge! ✨🌌",
                "Your Night Owl badge is just {days} late-night check-ins away! See you after 10 PM! 🌜💫",
                "Glow up at night! Check in post-10 PM for {days} {day_s} to earn your Night Owl badge! 🌟🌙",
                "Only {days} cozy late-night check-ins (after 10 PM) to become a true Night Owl! 🛌🦉",
                "Ready for the night shift? Check in after 10 PM for the next {days} {day_s} to claim your Night Owl badge! 🌃🏅",
                "Keep it up, night adventurer! {days} more check-ins after 10 PM = your Night Owl badge! 🌌🎖️",
            ]
            upcoming.append({
                'badge': {'id': badge.id, 'name': badge.name},
                'days_remaining': days_remaining,
                'message': random_message(night_messages, days_remaining)
            })

    # ================= Early Bird =================
    result = db.execute(
        text("""
            SELECT COUNT(*) AS count
            FROM user_streaks
            WHERE user_id = :user_id
            AND streak_date::time < '09:00:00'
        """),
        {"user_id": user_id}
    )
    early_count = result.fetchone().count

    if early_count < 30:
        days_remaining = 30 - early_count
        badge = db.execute(
            text("SELECT id, name FROM badges WHERE name = :name"),
            {"name": BADGES['EARLY_BIRD']}
        ).fetchone()

        if badge:
            early_messages = [
                "Check in before 9 AM for {days} {day_s} to earn your Early Bird badge! 🐥✨",
                "{days} early check-ins = one shiny Early Bird badge! 🌅🏅",
                "Rise early, earn big! {days} mornings before 9 AM! 🌞🎖️",
                "Be an early bird! {days} check-ins before 9 AM! 🐦💛",
                "Catch the badge! {days} days of early check-ins! 🐣🌄",
                "Wake, tap, repeat! {days}x before 9 AM = badge! ⏰🌟",
                "Mornings matter! Check in early for {days} {day_s} to win! 🌞🏆",
            ]
            upcoming.append({
                'badge': {'id': badge.id, 'name': badge.name},
                'days_remaining': days_remaining,
                'message': random_message(early_messages, days_remaining)
            })

    return upcoming





# === Emotional Templates for Plant Progress ===
PLANT_TEMPLATES = {
    "thriving": {
        "titles": [
            "🌱 Your Plant is Thriving!",
            "💧 Loved and Watered",
            "✨ Vibrant & Alive",
            "🌼 Blooming with Joy"
        ],
        "descriptions": [
            "Your plant feels your care — it’s glowing with health and gratitude.",
            "One more perfect day. Keep this rhythm going — it’s growing because of you.",
            "It stretches toward the sun, knowing you’ll return tomorrow.",
            "The roots hum a quiet song of thanks. You’ve made today count."
        ]
    },
    "hopeful": {
        "titles": [
            "🌿 Waiting Patiently",
            "💧 It Remembers You",
            "🍃 Still Hoping",
            "🌤️ Just One More Tap"
        ],
        "descriptions": [
            "Your plant curls a leaf inward, waiting for your touch tomorrow.",
            "It hasn’t forgotten your last drop. Come back soon — it believes in you.",
            "The breeze whispers your name through its leaves. Will you answer?",
            "One more day and you’re back on track. It’s not too late."
        ]
    },
    "sad": {
        "titles": [
            "💔 Your Plant Misses You",
            "💧 Drooping in Silence",
            "🌧️ It Rained, But Not for Me",
            "🌱 Forgotten?"
        ],
        "descriptions": [
            "Your plant droops slightly… it misses your tap. It hasn’t forgotten you.",
            "The leaves are quieter today — they miss the sound of your presence.",
            "Dust has settled on its petals. No one’s been here to wipe it away.",
            "It grew anyway… but it aches for your return."
        ]
    },
    "neglected": {
        "titles": [
            "🥀 Deeply Missed",
            "🌍 Forgotten in the Soil",
            "🌫️ Lost Without You",
            "💔 Silence Where Song Once Was"
        ],
        "descriptions": [
            "Your plant is quiet now. It hasn’t felt your touch in days…",
            "The roots whisper: 'Have they forgotten us?'",
            "It doesn’t blame you. But it wonders if you’ll come back.",
            "Even the wind has stopped visiting. You were its favorite."
        ]
    },
    "urgent": {
        "titles": [
            "🔥 One More to Bloom!",
            "💫 Final Drop!",
            "🎯 So Close!",
            "🎉 Almost There!"
        ],
        "descriptions": [
            "Just one more watering and you’ll unlock the '{badge}' badge! Your plant can feel it too!",
            "The last step — your plant is stretching toward the light. Help it bloom!",
            "One more tap and you’re officially a {badge}! Don’t break now!",
            "Your plant is dancing in anticipation — today’s the day!"
        ]
    },
    "upcoming": {
        "titles": [
            "🌱 Growing Toward {badge}",
            "💧 Every Drop Counts",
            "🌿 On the Way to {badge}",
            "🌞 Keep Cultivating"
        ],
        "descriptions": [
            "You’re {days} day{day_s} away from becoming a {badge} — your plant is growing because of you.",
            "Every tap matters. {days} more to go until your next milestone.",
            "The roots are spreading — {days} more days and your plant becomes {badge}.",
            "Growth takes time. You’re doing better than you think."
        ]
    }
}

# Fallback if no badge is close
PLANT_FALLBACK = {
    "title": "Keep Growing",
    "description": "Every drop counts. Keep watering — your garden is listening. 🌿💧",
    "type": "hopeful"
}

def check_plant_badges_upcoming(user_id: str, last_watered_date: datetime, current_streak: int) -> List[Dict[str, Any]]:
    """
    Returns a list of upcoming plant badge nudges with:
    - title
    - description
    - type: emotional state ('thriving', 'hopeful', 'sad', 'neglected', 'urgent', 'upcoming')
    """
    db = get_db()
    today = datetime.now(timezone.utc).date()

    # === 1. Find next badge milestone ===
    next_milestone = None
    for days in sorted(PLANT_BADGES.keys()):
        if days > current_streak:
            next_milestone = days
            break

    if not next_milestone:
        return []

    badge_name = PLANT_BADGES[next_milestone]
    result = db.execute(
        text("SELECT id, name FROM badges WHERE name = :name"),
        {"name": badge_name}
    ).fetchone()

    if not result:
        return []

    days_remaining = next_milestone - current_streak

    # === 2. Determine emotional state based on last_watered_date ===
    if not last_watered_date:
        emotional_state = "neglected"
    else:
        last_date = last_watered_date.date()
        days_since_watered = (today - last_date).days

        if days_since_watered == 0:
            emotional_state = "thriving"
        elif days_since_watered == 1:
            emotional_state = "hopeful"
        elif days_since_watered <= 3:
            emotional_state = "sad"
        else:
            emotional_state = "neglected"

    # === 3. Choose message based on urgency and emotion ===
    templates = PLANT_TEMPLATES.get(emotional_state, PLANT_TEMPLATES["upcoming"])

    # Override with "urgent" if 1 day from badge
    if days_remaining == 1:
        templates = PLANT_TEMPLATES["urgent"]
        emotional_state = "urgent"  # high urgency, positive push

    # Format title and description
    try:
        title = choice(templates["titles"])
        description = choice(templates["descriptions"])
    except:
        # Fallback if templates missing
        return [PLANT_FALLBACK]

    day_s = "s" if days_remaining > 1 else ""
    # Apply formatting to title and description
    title = title.format(badge=badge_name, days=days_remaining, day_s=day_s)
    description = description.format(badge=badge_name, days=days_remaining, day_s=day_s)

    # === 4. Return structured nudge ===
    return {
        'days_remaining': days_remaining,
        'title': title,
        'description': description,
        'type': emotional_state  # now used as emotional type
    }