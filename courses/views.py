import json

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Chapter, Choice, Course, Question, Quiz, QuizAttempt, UserProfile, XPTransaction, ChapterCompletion
from django.db import transaction
from .services import generate_course_journey, extract_text_from_file

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
    """The central dashboard displaying stats, progress, and daily goals."""
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
        uploaded_file = request.FILES.get('content_file')
        
        if not uploaded_file:
            return render(request, 'courses/course_form.html', {
                'error': 'Please select a study material to upload.'
            })

        raw_name = uploaded_file.name.rsplit('.', 1)[0]
        title = raw_name.replace('_', ' ').replace('-', ' ').strip().title()

        try:
            with transaction.atomic():
                extracted_text = extract_text_from_file(uploaded_file)
                course = Course.objects.create(
                    user=request.user,
                    title=title or "Untitled Course",
                    syllabus_text=extracted_text,
                    description="AI-generated learning path based on your uploaded materials."
                )
                _build_journey(course, uploaded_file=uploaded_file)
                
            return redirect('courses:course_detail', pk=course.pk)

        except Exception as e:
            print(f"[Course Generation Failed]: {repr(e)}")
            return render(request, 'courses/course_form.html', {
                'generation_failed': True,
                'previous_filename': uploaded_file.name,
            })
        
    return render(request, 'courses/course_form.html')


@transaction.atomic
def _build_journey(course, uploaded_file=None, journey_override=None):
    journey = journey_override if journey_override is not None else generate_course_journey(
        course, uploaded_file=uploaded_file
    )

    # Safe extraction with fallback to uploaded filename/defaults
    course_meta = journey.get('course', {})
    course.title = course_meta.get('title') or journey.get('title') or course.title
    course.description = course_meta.get('description') or journey.get('description') or course.description
    course.structured_content = journey
    course.save(update_fields=['title', 'description', 'structured_content'])

    chapters_data = journey.get('chapters', [])
    if not chapters_data:
        raise ValueError("AI response did not contain any valid chapters.")

    for idx, chapter_data in enumerate(chapters_data, start=1):
        chapter = Chapter.objects.create(
            course=course,
            order=chapter_data.get('order', idx),
            title=chapter_data.get('title', f"Chapter {idx}"),
            review_content=chapter_data.get('review_content') or chapter_data.get('overview', ''),
            source_data=chapter_data,
        )

        quiz_data = chapter_data.get('quiz')
        if not quiz_data:
            continue

        quiz = Quiz.objects.create(
            chapter=chapter, 
            title=quiz_data.get('title', f"{chapter.title} Quiz")
        )

        for q_idx, question_data in enumerate(quiz_data.get('questions', []), start=1):
            question = Question.objects.create(
                quiz=quiz,
                order=question_data.get('order', q_idx),
                text=question_data.get('text', ''),
                explanation=question_data.get('explanation', ''),
            )
            for choice_data in question_data.get('choices', []):
                Choice.objects.create(
                    question=question,
                    text=choice_data.get('text', ''),
                    is_correct=choice_data.get('is_correct', False),
                )


@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    chapters = list(course.chapters.all())
    completed_quiz_ids = set(
        QuizAttempt.objects.filter(
            user=request.user,
            quiz__chapter__course=course,
        ).values_list('quiz_id', flat=True)
    )
    first_incomplete_found = False
    for chapter in chapters:
        quiz_id = chapter.quiz.id if hasattr(chapter, 'quiz') and chapter.quiz else None
        if quiz_id and quiz_id in completed_quiz_ids:
            chapter.progress_status = 'completed'
        elif not first_incomplete_found:
            chapter.progress_status = 'active'
            first_incomplete_found = True
        else:
            chapter.progress_status = 'upcoming'
    return render(request, 'courses/course_detail.html', {'course': course, 'chapters': chapters})


@login_required
def chapter_review(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk, course__user=request.user)
    has_quiz = hasattr(chapter, 'quiz')
    question_count = chapter.quiz.questions.count() if has_quiz else 0
    is_completed = ChapterCompletion.objects.filter(user=request.user, chapter=chapter).exists()

    return render(request, 'courses/chapter_review.html', {
        'chapter': chapter,
        'has_quiz': has_quiz,
        'question_count': question_count,
        'is_completed': is_completed,
    })


@login_required
@require_POST
def complete_chapter(request, pk):
    """Marks a chapter's review as read and awards a small, one-time XP
    bonus. Safe to trigger client-side — there's no correctness to fake
    here, only "did the button get pressed," and the unique_together
    constraint on ChapterCompletion prevents farming XP by re-submitting.
    """
    chapter = get_object_or_404(Chapter, pk=pk, course__user=request.user)

    completion, created = ChapterCompletion.objects.get_or_create(user=request.user, chapter=chapter)

    if created:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.award_xp(15, reason=f'Completed lesson: {chapter.title}')
        profile.record_study_activity()
        return JsonResponse({'awarded': True, 'xp_earned': 15, 'new_total_xp': profile.total_xp})

    return JsonResponse({'awarded': False, 'xp_earned': 0})

@login_required
def course_edit(request, pk):
    """Updates course title and description."""
    course = get_object_or_404(Course, pk=pk, user=request.user)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        if title:
            course.title = title
            course.description = description
            course.save(update_fields=['title', 'description'])
    return redirect('courses:course_detail', pk=course.pk)


@login_required
def course_delete(request, pk):
    """Deletes a course and all associated chapters/quizzes via CASCADE."""
    course = get_object_or_404(Course, pk=pk, user=request.user)
    if request.method == 'POST':
        course.delete()
        return redirect('courses:course_list')
    return redirect('courses:course_detail', pk=course.pk)


@login_required
def chapter_rename(request, pk):
    """Renames an individual chapter."""
    chapter = get_object_or_404(Chapter, pk=pk, course__user=request.user)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if title:
            chapter.title = title
            chapter.save(update_fields=['title'])
    return redirect('courses:course_detail', pk=chapter.course.pk)

@login_required
def chapter_quiz(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk, course__user=request.user)
    quiz = getattr(chapter, 'quiz', None)
    return render(request, 'courses/chapter_quiz.html', {
        'chapter': chapter,
        'quiz': quiz,
    })


@login_required
@require_POST
def submit_quiz(request, pk):
    """Grades a quiz attempt server-side. Expects a JSON body:
        {"answers": {"<question_id>": <choice_id>, ...}}
    Never trusts anything the client claims about correctness — every
    choice's is_correct flag is re-checked against the database here.
    """
    chapter = get_object_or_404(Chapter, pk=pk, course__user=request.user)
    quiz = getattr(chapter, 'quiz', None)
    if quiz is None:
        return JsonResponse({'error': 'No quiz for this chapter.'}, status=404)

    try:
        payload = json.loads(request.body)
        submitted_answers = payload.get('answers', {})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    questions = list(quiz.questions.prefetch_related('choices').all())
    total_questions = len(questions)
    score = 0
    results = []

    for question in questions:
        chosen_choice_id = submitted_answers.get(str(question.id))
        correct_choice = next((c for c in question.choices.all() if c.is_correct), None)
        is_correct = (
            chosen_choice_id is not None
            and correct_choice is not None
            and int(chosen_choice_id) == correct_choice.id
        )
        if is_correct:
            score += 1

        results.append({
            'question_id': question.id,
            'is_correct': is_correct,
            'correct_choice_id': correct_choice.id if correct_choice else None,
        })

    # XP formula: 10 per correct answer, +20 bonus for a perfect score
    xp_earned = score * 10
    if total_questions > 0 and score == total_questions:
        xp_earned += 20

    QuizAttempt.objects.create(
        user=request.user,
        quiz=quiz,
        score=score,
        total_questions=total_questions,
        xp_earned=xp_earned,
    )

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.award_xp(xp_earned, reason=f'Quiz: {chapter.title}')

    # SPRINT C: a completed quiz counts as a study activity for streak purposes
    profile.record_study_activity()

    return JsonResponse({
        'score': score,
        'total_questions': total_questions,
        'xp_earned': xp_earned,
        'new_total_xp': profile.total_xp,
        'new_level': profile.current_level,
        'new_streak': profile.streak_days,
        'results': results,
    })