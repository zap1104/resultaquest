from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta


# --- SPRINT A & B & C: GAMIFICATION PROFILE & LEDGER ---

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_xp = models.IntegerField(default=0)
    current_level = models.IntegerField(default=1)
    streak_days = models.IntegerField(default=0)
    last_study_date = models.DateField(null=True, blank=True)

    def award_xp(self, amount, reason):
        XPTransaction.objects.create(user=self.user, amount=amount, reason=reason)
        self.total_xp += amount
        xp_for_next_level = self.current_level * 100
        while self.total_xp >= xp_for_next_level:
            self.current_level += 1
            xp_for_next_level = self.current_level * 100
        self.save(update_fields=['total_xp', 'current_level'])

    def update_streak(self):
        today = timezone.now().date()
        if self.last_study_date == today:
            return
        elif self.last_study_date == today - timedelta(days=1):
            self.streak_days += 1
        else:
            self.streak_days = 1
        self.last_study_date = today
        self.save(update_fields=['streak_days', 'last_study_date'])

    def record_study_activity(self):
        self.update_streak()

    def __str__(self):
        return f"{self.user.username} - Lv. {self.current_level} ({self.total_xp} XP)"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


# --- EXISTING MODELS ---

class Course(models.Model):
    """A subject/course the learner wants a personalized review journey for."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses')

    title = models.CharField(max_length=200)
    description = models.CharField(max_length=300, blank=True)

    syllabus_text = models.TextField(blank=True)
    modules_text = models.TextField(blank=True)
    activities_text = models.TextField(blank=True)
    assignments_text = models.TextField(blank=True)

    structured_content = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Chapter(models.Model):
    """One step in a course's learning path (a NetAcad-style review unit)."""

    course = models.ForeignKey(Course, related_name='chapters', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200)
    review_content = models.TextField(
        blank=True,
        help_text='Personalized review text for this chapter, generated from the raw materials.',
    )
    source_data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.course.title} — {self.title}'


class Quiz(models.Model):
    """The knowledge-check at the end of a chapter."""

    chapter = models.OneToOneField(Chapter, related_name='quiz', on_delete=models.CASCADE)
    title = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.title or f'Quiz for {self.chapter.title}'


# courses/models.py
class Question(models.Model):
    QUESTION_TYPE_CHOICES = [
        ("multiple_choice", "Multiple Choice"),
        ("true_false", "True or False"),
        ("identification", "Identification"),
        ("enumeration", "Enumeration"),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveIntegerField(default=1)
    question_type = models.CharField(
        max_length=30,
        choices=QUESTION_TYPE_CHOICES,
        default="multiple_choice",
    )
    text = models.TextField()
    explanation = models.TextField(blank=True, default="")
    answer_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Q{self.order} ({self.question_type}): {self.text[:40]}"


class Choice(models.Model):
    """Only used for question_type='multiple_choice'. Identification and
    Enumeration questions have no related Choice rows.
    """
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


# --- SPRINT B: QUIZ PERSISTENCE & XP LEDGER ---

class XPTransaction(models.Model):
    """An audit-trail entry for every XP award. UserProfile.total_xp is a
    cached sum of these — never edit total_xp directly, always go through
    UserProfile.award_xp() so the ledger and the cached total can't drift.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='xp_transactions')
    amount = models.IntegerField()
    reason = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username}: {self.amount:+d} XP ({self.reason})'


class QuizAttempt(models.Model):
    """One completed run of a Quiz by a User. Scoring happens server-side
    in views.submit_quiz — this row is the permanent record of that result.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.PositiveIntegerField()
    total_questions = models.PositiveIntegerField()
    xp_earned = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at']

    def __str__(self):
        return f'{self.user.username} — {self.quiz} ({self.score}/{self.total_questions})'


class ChapterCompletion(models.Model):
    """Tracks that a user has marked a chapter's review content as read.
    Existence of this row = "Mark Complete" was pressed; used both to
    show the ✓ state and to prevent awarding the completion XP more
    than once per user per chapter.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chapter_completions')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='completions')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'chapter')

    def __str__(self):
        return f'{self.user.username} — {self.chapter.title} (read)'