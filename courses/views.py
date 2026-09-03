from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CourseForm
from .models import Chapter, Choice, Course, Question, Quiz, UserProfile
from .services import generate_course_journey


def auth_portal(request):
    """Game launcher landing page with tabbed Login and Sign Up."""
    if request.user.is_authenticated:
        return redirect('courses:dashboard')

    active_tab = request.GET.get('tab', 'login')
    login_form = AuthenticationForm()
    signup_form = UserCreationForm()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'login':
            login_form = AuthenticationForm(request, data=request.POST)
            if login_form.is_valid():
                login(request, login_form.get_user())
                return redirect('courses:dashboard')
            active_tab = 'login'
        elif action == 'signup':
            signup_form = UserCreationForm(request.POST)
            if signup_form.is_valid():
                user = signup_form.save()
                login(request, user)
                return redirect('courses:dashboard')
            active_tab = 'signup'

    return render(request, 'courses/login.html', {
        'login_form': login_form,
        'signup_form': signup_form,
        'active_tab': active_tab,
    })


@login_required
def dashboard(request):
    """The central Quest Board displaying stats, trajectories, and bounties."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    courses = list(Course.objects.filter(user=request.user).prefetch_related('chapters'))
    
    # XP math: 100 XP per level
    xp_needed_next = profile.current_level * 100
    xp_percentage = min(int((profile.total_xp / max(xp_needed_next, 1)) * 100), 100)
    
    # Calculate progress for each course
    for course in courses:
        total_chapters = course.chapters.count()
        course.progress_pct = 40 if total_chapters > 1 else (15 if total_chapters == 1 else 0)

    recent_course = courses[0] if courses else None

    # Calculate real achievement unlocks
    unlocked_count = 0
    if len(courses) > 0:
        unlocked_count += 1
    if profile.total_xp >= 20:
        unlocked_count += 1
    if profile.streak_days >= 7:
        unlocked_count += 1
    if profile.current_level >= 5:
        unlocked_count += 1

    return render(request, 'courses/dashboard.html', {
        'profile': profile,
        'courses': courses,
        'xp_needed_next': xp_needed_next,
        'xp_percentage': xp_percentage,
        'recent_course': recent_course,
        'unlocked_count': unlocked_count,
    })


@login_required
def course_list(request):
    courses = Course.objects.filter(user=request.user)
    return render(request, 'courses/course_list.html', {'courses': courses})


@login_required
def course_create(request):
    if request.method == 'POST':
        # 1. Grab the uploaded file
        uploaded_file = request.FILES.get('content_file')
        
        if uploaded_file:
            # Extract filename without extension (e.g., "network_design.pdf" -> "network design")
            raw_name = uploaded_file.name.rsplit('.', 1)[0]
            title = raw_name.replace('_', ' ').replace('-', ' ').title()
        else:
            title = "Untitled Quest"

        # 2. Create the course manually (bypassing the old form)
        course = Course.objects.create(
            user=request.user,
            title=title,
            description="AI-forged learning journey based on your uploaded materials."
        )
        
        # 3. Trigger the mock AI builder
        _build_journey(course)
        
        return redirect('courses:course_detail', pk=course.pk)
        
    return render(request, 'courses/course_form.html')


def _build_journey(course):
    """Runs the AI step and persists Chapters and Quizzes."""
    journey = generate_course_journey(course)
    course.structured_content = journey
    course.save(update_fields=['structured_content'])

    for i, chapter_data in enumerate(journey.get('chapters', []), start=1):
        chapter = Chapter.objects.create(
            course=course,
            order=i,
            title=chapter_data.get('title', f'Chapter {i}'),
            review_content=chapter_data.get('review_content', ''),
            source_data=chapter_data,
        )
        quiz_data = chapter_data.get('quiz')
        if quiz_data:
            quiz = Quiz.objects.create(chapter=chapter, title=f'{chapter.title} Quiz')
            for j, q in enumerate(quiz_data.get('questions', []), start=1):
                question = Question.objects.create(quiz=quiz, order=j, text=q.get('text', ''))
                for choice in q.get('choices', []):
                    Choice.objects.create(
                        question=question,
                        text=choice.get('text', ''),
                        is_correct=choice.get('is_correct', False),
                    )


@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    return render(request, 'courses/course_detail.html', {'course': course})


@login_required
def chapter_review(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk, course__user=request.user)
    has_quiz = hasattr(chapter, 'quiz')
    return render(request, 'courses/chapter_review.html', {
        'chapter': chapter,
        'has_quiz': has_quiz,
    })


@login_required
def chapter_quiz(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk, course__user=request.user)
    quiz = getattr(chapter, 'quiz', None)
    return render(request, 'courses/chapter_quiz.html', {
        'chapter': chapter,
        'quiz': quiz,
    })