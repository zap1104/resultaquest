from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from courses.credits import (
    COURSE_GENERATION_COOLDOWN,
    FREE_ACTIVE_COURSE_LIMIT,
    award_course_completion_bonus,
    calculate_delta_quiz_xp,
    consume_generation_credit,
    get_generation_eligibility,
)
from courses.models import (
    Chapter,
    ChapterCompletion,
    Course,
    CourseCreditTransaction,
    Quiz,
    QuizAttempt,
    UserCourseCompletion,
    UserProfile,
)


class CreditEligibilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="credit-user", password="password123")
        self.profile = UserProfile.objects.get(user=self.user)

    def test_first_generation_is_allowed(self):
        eligibility = get_generation_eligibility(self.profile)
        self.assertTrue(eligibility.allowed)
        self.assertEqual(eligibility.source, "weekly")

    def test_cooldown_blocks_without_bonus(self):
        self.profile.last_course_generated_at = timezone.now() - timedelta(days=2)
        self.profile.save()
        self.assertFalse(get_generation_eligibility(self.profile).allowed)

    def test_bonus_bypasses_cooldown(self):
        self.profile.last_course_generated_at = timezone.now() - timedelta(days=1)
        self.profile.bonus_course_credits = 1
        self.profile.save()
        self.assertEqual(get_generation_eligibility(self.profile).source, "bonus")

    def test_active_limit_excludes_archived(self):
        for index in range(FREE_ACTIVE_COURSE_LIMIT):
            Course.objects.create(user=self.user, title=f"Archived {index}", status="archived")
        self.assertTrue(get_generation_eligibility(self.profile).allowed)

    def test_active_limit_blocks_active_courses(self):
        for index in range(FREE_ACTIVE_COURSE_LIMIT):
            Course.objects.create(user=self.user, title=f"Active {index}", status="active")
        self.assertEqual(get_generation_eligibility(self.profile).reason, "active_course_limit")

    def test_plus_plan_has_three_generations_and_fifteen_slots(self):
        self.profile.plan = "plus"
        self.profile.save(update_fields=["plan"])
        eligibility = get_generation_eligibility(self.profile)
        self.assertEqual(eligibility.active_limit, 15)
        for index in range(3):
            course = Course.objects.create(user=self.user, title=f"Plus {index}")
            consume_generation_credit(self.user, course)
        self.profile.refresh_from_db()
        self.assertFalse(get_generation_eligibility(self.profile).allowed)


class CreditLedgerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ledger-user", password="password123")
        self.profile = UserProfile.objects.get(user=self.user)
        self.course = Course.objects.create(user=self.user, title="Ledger Course")

    def test_weekly_consumption_writes_ledger(self):
        self.assertEqual(consume_generation_credit(self.user, self.course), "weekly")
        transaction = CourseCreditTransaction.objects.get(user=self.user)
        self.assertEqual(transaction.transaction_type, "weekly_spend")
        self.assertEqual(transaction.amount, -1)

    def test_bonus_consumption_writes_ledger(self):
        self.profile.last_course_generated_at = timezone.now() - timedelta(days=1)
        self.profile.bonus_course_credits = 1
        self.profile.save()
        self.assertEqual(consume_generation_credit(self.user, self.course), "bonus")
        self.assertEqual(CourseCreditTransaction.objects.get(transaction_type="bonus_spend").amount, -1)


class CourseCompletionBonusTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bonus-user", password="password123")
        self.course = Course.objects.create(user=self.user, title="Complete Course")
        self.chapter = Chapter.objects.create(course=self.course, order=1, title="Chapter 1")
        self.quiz = Quiz.objects.create(chapter=self.chapter, title="Quiz")

    def test_bonus_is_awarded_once_after_completion(self):
        ChapterCompletion.objects.create(user=self.user, chapter=self.chapter)
        QuizAttempt.objects.create(user=self.user, quiz=self.quiz, score=3, total_questions=4, xp_earned=35)
        self.assertTrue(award_course_completion_bonus(self.user, self.course)["bonus_awarded"])
        self.assertFalse(award_course_completion_bonus(self.user, self.course)["bonus_awarded"])
        self.assertEqual(UserCourseCompletion.objects.count(), 1)
        self.assertEqual(CourseCreditTransaction.objects.filter(transaction_type="bonus_award").count(), 1)


class DeltaQuizXPTests(TestCase):
    def test_improvement_awards_only_delta(self):
        user = User.objects.create_user(username="xp-user", password="password123")
        course = Course.objects.create(user=user, title="XP Course")
        chapter = Chapter.objects.create(course=course, order=1, title="Chapter")
        quiz = Quiz.objects.create(chapter=chapter, title="Quiz")
        QuizAttempt.objects.create(user=user, quiz=quiz, score=3, total_questions=4, xp_earned=35)
        self.assertEqual(calculate_delta_quiz_xp(user, quiz, 100), 25)


class CourseArchiveTests(TestCase):
    def test_archive_and_restore(self):
        user = User.objects.create_user(username="archive-user", password="password123")
        course = Course.objects.create(user=user, title="Archive Course")
        client = Client()
        client.login(username="archive-user", password="password123")
        response = client.post(reverse("courses:course_archive", kwargs={"pk": course.pk}))
        self.assertEqual(response.status_code, 302)
        course.refresh_from_db()
        self.assertEqual(course.status, "archived")
        response = client.post(reverse("courses:course_restore", kwargs={"pk": course.pk}))
        self.assertEqual(response.status_code, 302)
        course.refresh_from_db()
        self.assertEqual(course.status, "active")
