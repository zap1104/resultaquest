from django.db import models


class Course(models.Model):
    """A subject/course the learner wants a personalized review journey for.

    Raw materials are pasted in by the user; `structured_content` is where the
    AI-generated JSON breakdown (modules -> chapters -> quests) will eventually
    live once the AI integration is wired up.
    """

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
    """One quest/step in a course's learning path (a NetAcad-style review unit)."""

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
    """The Duolingo/Kahoot-style check at the end of a chapter."""

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
