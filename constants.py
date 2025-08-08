BADGES = {
    "WEEKLY": "Weekly Warrior",
    "MONTHLY": "Monthly Master",
    "NIGHT_OWL": "Night Owl",
    "EARLY_BIRD": "Early Bird",
}

PLANT_BADGES = {
    1: "The Daily Drip",
    3: "Hydration Hero",
    5: "Sprout Keeper",
    7: "Bloom Boss",
    10: "The Plant Whisperer",
    15: "Water Warrior",
    30: "Root Ruler",
    50: "The Garden Guardian",
    70: "Captain Chlorophyll",
    100: "Queen of Green / King of Green",
    120: "Thirst Trap King/Queen 😎",
    150: "H2OG",
    170: "Drip Dealer",
    200: "Moist Master",
    220: "The Soak Legend",
    250: "Drip God/Goddess",
    270: "Aqua Baddie",
    300: "Wet Work MVP",
    320: "Zen Botanist",
    365: "Serotonin Sprinkler",
    400: "Vibe Cultivator",
    450: "Mindful Grower",
    500: "Flow Gardener",
    600: "Peace Planter",
    730: "Aura Farmer"  # 2 years = 730 days (non-leap)
}


def get_plant_messages(badge_name: str, days_remaining: int) -> list:
    """
    Returns a list of fun, motivational messages for upcoming plant badges.
    Works for any badge (e.g., Bloom Boss, Root Ruler) and any days remaining.
    """
    day_word = "day" if days_remaining == 1 else "days"
    s = "s" if days_remaining > 1 else ""

    templates = [
        "🌱 Just {days} more splashy {day}s 'til you're a full-on {badge}!",
        "💧 {days} more watering {day}s and you’ll level up to {badge} status!",
        "🥤 Keep it up—only {days} more {day}s 'til your inner {badge} shines!",
        "🌊 Just a couple more sips and you're officially a {badge}!",
        "💦 Almost there! Water for {days} more {day}s to earn your sparkly {badge} badge!",
        "🐣 You're just {days} waterings away from blossoming into a {badge}!",
        "💙 {days} more {day}s of watering and you'll be the cutest {badge} on the block!",
        "⏳ Only {days} more water drops away from {badge} status!",
        "🚰 You're on a roll—just {days} more {day}s to hydrate your way to {badge}hood!",
        "✨ {days} more {day}s of watery goodness and {badge} is all yours!",
        "💧 Just {days} more hydration hugs and you’ll be our official {badge}!",
        "🌟 Almost time to sparkle—{days} more {day}s ‘til you’re crowned {badge}!"
    ]

    return [
        template.format(days=days_remaining, day=day_word, badge=badge_name, s=s)
        for template in templates
    ]