PLAN_LIMITS = {
    "free": {
        "name": "StudyQuest Free",
        "weekly_generations": 1,
        "active_courses": 5,
        "bonus_credit_cap": 1,
        "shows_sponsors": True,
        "upload_size_mb": 10,
    },
    "plus": {
        "name": "StudyQuest Plus",
        "weekly_generations": 3,
        "active_courses": 15,
        "bonus_credit_cap": 2,
        "shows_sponsors": False,
        "upload_size_mb": 25,
    },
}


def get_plan_limits(plan):
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
