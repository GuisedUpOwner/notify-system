# example background_check.py
import json
from datetime import datetime, timezone
from badge_checks import check_plant_badges_upcoming, get_single_app_streak_message, get_upcoming_achievements
from notifier import send_push_notification
# from db import get_users_to_notify  # hypothetically

# users = get_users_to_notify()
tokens = ["dDP3xJ0tTK-21L1aQYH8Ic:APA91bFZBDECRjVW-mzGytvdfHCR5Srvzjs1P9o6Gb3UT_0-ugtWJU8CUcPT0Y_HoD3ey-asL_4c5-GLMS_Ijok9DCjgBzYMEnuaeh-Enx839HhzudsLQzQ", "frMgjKkYcEcevbYPulSQms:APA91bHCBGu5Z005euBShEnW2SM-jrEeNru22fwxte3SgFEw3NwiQUdpaKM17D_bmZZEdX_D6-4oyTOGwhHsE9GpAtzcZclhv6Ep8Ni62_oZ-FMvNE2dgEg"]

# send_push_notification(
#     tokens=tokens,
#     title="You're inactive 😴",
#     body="Time to return to the app and check your messages!"
# )


def background_checks(user_id: str, current_streak: int, last_watered_date: datetime, check_date: datetime = None):
    """
    Call both plant and app streak checks.
    Returns upcoming nudges (for notifications).
    """
    # Get plant-based upcoming badges
    plant_upcoming = check_plant_badges_upcoming(user_id, last_watered_date, current_streak)

    # Get app usage-based upcoming achievements
    app_single_upcoming = get_single_app_streak_message(user_id, check_date)
    # app_upcoming = get_upcoming_achievements(user_id, check_date)

    return {
        'plant': plant_upcoming,
        # 'app': app_upcoming,
        'app_single': app_single_upcoming
    }



# === 🔧 Sample Data ===
if __name__ == "__main__":
    sample_user_id = "9f20c134-8bb8-4369-8efd-bfcfa7a5eaa0"
    sample_current_streak = 6  # Close to 7-day Bloom Boss
    last_watered_date_str = "2025-08-07"
    sample_date = datetime.now(timezone.utc)  # Proper UTC-aware datetime

    try:
        last_watered_date = datetime.fromisoformat(last_watered_date_str).replace(tzinfo=timezone.utc)
    except ValueError:
        print("⚠️ Invalid date format. Using fallback: today.")
        last_watered_date = sample_date


    print("🔍 Running background checks for user...\n")
    result = background_checks(
        user_id=sample_user_id,
        current_streak=sample_current_streak,
        last_watered_date=last_watered_date,
        check_date=sample_date
    )

    # Pretty-print result
    print(json.dumps(result, indent=2, default=str, ensure_ascii=False))