from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# --- SPRINT A & B: GAMIFICATION PROFILE & LEDGER ---

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_xp = models.IntegerField(default=0)
    current_level = models.IntegerField(default=1)
    streak_days = models.IntegerField(default=0)
    last_study_date = models.DateField(null=True, blank=True)

    def award_xp(self, amount, reason):
        """The only sanctioned way to add XP. Writes an XPTransaction,
        bumps the cached total, and handles level-ups (100 XP per level).
        """
        XPTransaction.objects.create(user=self.user, amount=amount, reason=reason)
        self.total_xp += amount
        xp_for_next_level = self.current_level * 100
        while self.total_xp >= xp_for_next_level:
            self.current_level += 1
            xp_for_next_level = self.current_level * 100
        self.save(update_fields=['total_xp', 'current_level'])

    def __str__(self):
        return f"{self.user.username} - Lv. {self.current_level} ({self.total_xp} XP)"

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

class XPTransaction(models.Model):
    """An audit-trail entry for every XP award."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='xp_transactions')
    amount = models.IntegerField()
    reason = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username}: {self.amount:+d} XP ({self.reason})'

class QuizAttempt(models.Model):
    """One completed run of a Quiz by a User. Scored server-side."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey('Quiz', on_delete=models.CASCADE, related_name='attempts')
    score = models.PositiveIntegerField()
    total_questions = models.PositiveIntegerField()
    xp_earned = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at']

    def __str__(self):
        return f'{self.user.username} — {self.quiz} ({self.score}/{self.total_questions})'


# --- EXISTING MODELS ---

class Course(models.Model):
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
    course = models.ForeignKey(Course, related_name='chapters', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200)
    review_content = models.TextField(blank=True)
    source_data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.course.title} — {self.title}'

class Quiz(models.Model):
    chapter = models.OneToOneField(Chapter, related_name='quiz', on_delete=models.CASCADE)
    title = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.title or f'Quiz for {self.chapter.title}'

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, related_name='questions', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=1)
    text = models.CharField(max_length=500)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text

class Choice(models.Model):
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text