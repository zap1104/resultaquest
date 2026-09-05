from django.contrib import admin
from .models import Chapter, Choice, Course, Question, Quiz, UserProfile, XPTransaction, QuizAttempt

class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')
    inlines = [ChapterInline]

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 0

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'quiz')
    inlines = [ChoiceInline]

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'current_level', 'total_xp', 'streak_days', 'last_study_date')

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'score', 'total_questions', 'xp_earned', 'completed_at')
    list_filter = ('completed_at',)

@admin.register(XPTransaction)
class XPTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'reason', 'created_at')
    list_filter = ('created_at',)

admin.site.register(Chapter)
admin.site.register(Quiz)