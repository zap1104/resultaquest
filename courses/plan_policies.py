from dataclasses import dataclass


@dataclass(frozen=True)
class PlanLimits:
    name: str
    weekly_generations: int
    active_courses: int
    bonus_credit_cap: int
    shows_sponsors: bool
    upload_size_mb: int
    max_source_files: int
    max_file_bytes: int
    max_bundle_bytes: int
    max_extracted_characters: int

    @property
    def max_extracted_chars(self) -> int:
        return self.max_extracted_characters


PLAN_POLICIES = {
    "free": PlanLimits(
        name="StudyQuest Free",
        weekly_generations=1,
        active_courses=5,
        bonus_credit_cap=1,
        shows_sponsors=True,
        upload_size_mb=10,
        max_source_files=3,
        max_file_bytes=10 * 1024 * 1024,
        max_bundle_bytes=20 * 1024 * 1024,
        max_extracted_characters=75000,
    ),
    "plus": PlanLimits(
        name="StudyQuest Plus",
        weekly_generations=3,
        active_courses=15,
        bonus_credit_cap=2,
        shows_sponsors=False,
        upload_size_mb=25,
        max_source_files=3,
        max_file_bytes=25 * 1024 * 1024,
        max_bundle_bytes=50 * 1024 * 1024,
        max_extracted_characters=125000,
    ),
}

PLAN_LIMITS = {
    plan_key: {
        "name": policy.name,
        "weekly_generations": policy.weekly_generations,
        "active_courses": policy.active_courses,
        "bonus_credit_cap": policy.bonus_credit_cap,
        "shows_sponsors": policy.shows_sponsors,
        "upload_size_mb": policy.upload_size_mb,
        "max_source_files": policy.max_source_files,
        "max_file_bytes": policy.max_file_bytes,
        "max_bundle_bytes": policy.max_bundle_bytes,
        "max_extracted_characters": policy.max_extracted_characters,
        "max_extracted_chars": policy.max_extracted_characters,
    }
    for plan_key, policy in PLAN_POLICIES.items()
}


def get_plan_policy(plan):
    return PLAN_POLICIES.get(plan, PLAN_POLICIES["free"])


def get_plan_limits(plan):
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
