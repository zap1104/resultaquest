import json
import re
import unicodedata

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import (
    Chapter,
    ChapterCompletion,
    Choice,
    Course,
    Question,
    Quiz,
    QuizAttempt,
    UserProfile,
)
from .schemas import GenerationPreferences
from .services import generate_course_journey

REGULAR_QUIZ_PASS_THRESHOLD = 70
TEST_OUT_THRESHOLD = 85
LESSON_COMPLETION_XP = 15


# --------------------------------------------------
# 1. NORMALIZATION & PROGRESSION HELPERS
# --------------------------------------------------
def normalize_text_answer(value):
    """
    Deterministic normalization for Identification and Enumeration.
    Avoids fuzzy matching to prevent credit on incorrect technical terms.
    """
    value = unicodedata.normalize("NFKC", value or "")
    value = value.casefold()
    value = re.sub(r"[^\w\s.]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip().strip(".")


def calculate_quiz_xp(percentage):
    if percentage >= 100:
        return 60
    if percentage >= 85:
        return 45
    if percentage >= 70:
        return 35
    if percentage >= 50:
        return 20
    return 10


def get_reading_session_key(chapter):
    return f"chapter_read_to_end:{chapter.pk}"


def has_read_to_end(request, chapter):
    return bool(request.session.get(get_reading_session_key(chapter), False))


def get_best_quiz_percentage(user, chapter):
    quiz = getattr(chapter, "quiz", None)
    if quiz is None:
        return None

    attempts = QuizAttempt.objects.filter(
        user=user,
        quiz=quiz,
        total_questions__gt=0,
    ).only("score", "total_questions")

    best_percentage = None
    for attempt in attempts:
        percentage = round(attempt.score / max(attempt.total_questions, 1) * 100)
        if best_percentage is None or percentage > best_percentage:
            best_percentage = percentage

    return best_percentage


def get_chapter_completion_state(user, chapter):
    """
    Guided completion: Lesson marked complete + quiz score >= 70%
    Test-out completion: Quiz score >= 85% (even if reading was skipped)
    """
    lesson_completed = ChapterCompletion.objects.filter(user=user, chapter=chapter).exists()
    best_quiz_percentage = get_best_quiz_percentage(user, chapter)
    quiz = getattr(chapter, "quiz", None)
    has_quiz = quiz is not None

    quiz_passed = (
        best_quiz_percentage is not None
        and best_quiz_percentage >= REGULAR_QUIZ_PASS_THRESHOLD
    )

    tested_out = (
        best_quiz_percentage is not None
        and best_quiz_percentage >= TEST_OUT_THRESHOLD
        and not lesson_completed
    )

    if has_quiz:
        completed = (lesson_completed and quiz_passed) or tested_out
    else:
        completed = lesson_completed

    return {
        "lesson_completed": lesson_completed,
        "has_quiz": has_quiz,
        "best_quiz_percentage": best_quiz_percentage,
        "quiz_passed": quiz_passed,
        "tested_out": tested_out,
        "completed": completed,
    }


def get_previous_chapter(chapter):
    return (
        Chapter.objects.filter(course=chapter.course, order__lt=chapter.order)
        .order_by("-order")
        .first()
    )


def get_next_chapter(chapter):
    return (
        Chapter.objects.filter(course=chapter.course, order__gt=chapter.order)
        .order_by("order")
        .first()
    )


def get_chapter_status(user, chapter):
    """Returns 'completed', 'available', or 'locked'."""
    current_state = get_chapter_completion_state(user, chapter)
    if current_state["completed"]:
        return "completed"

    previous_chapter = get_previous_chapter(chapter)
    if previous_chapter is None:
        return "available"

    previous_state = get_chapter_completion_state(user, previous_chapter)
    if previous_state["completed"]:
        return "available"

    return "locked"


def calculate_course_progress(user, course):
    chapters = list(course.chapters.all())
    total_chapters = len(chapters)
    if total_chapters == 0:
        return {"total_chapters": 0, "completed_count": 0, "percentage": 0}

    completed_count = sum(
        1 for chapter in chapters if get_chapter_completion_state(user, chapter)["completed"]
    )
    percentage = int((completed_count / total_chapters) * 100)
    return {
        "total_chapters": total_chapters,
        "completed_count": completed_count,
        "percentage": percentage,
    }


# --------------------------------------------------
# 2. AUTH & DASHBOARD VIEWS
# --------------------------------------------------
def auth_portal(request):
    if request.user.is_authenticated:
        return redirect("courses:dashboard")

    active_tab = request.GET.get("tab", "login")
    login_form = AuthenticationForm()
    signup_form = UserCreationForm()

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "login":
            login_form = AuthenticationForm(request, data=request.POST)
            if login_form.is_valid():
                login(request, login_form.get_user())
                return redirect("courses:dashboard")
            active_tab = "login"
        elif action == "signup":
            signup_form = UserCreationForm(request.POST)
            if signup_form.is_valid():
                user = signup_form.save()
                login(request, user)
                return redirect("courses:dashboard")
            active_tab = "signup"

    return render(request, "courses/login.html", {
        "login_form": login_form,
        "signup_form": signup_form,
        "active_tab": active_tab,
    })


@login_required
def dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    courses = list(
        Course.objects.filter(user=request.user).prefetch_related(
            "chapters", "chapters__quiz", "chapters__quiz__attempts"
        )
    )

    xp_needed_next = profile.current_level * 100
    xp_percentage = min(int((profile.total_xp / max(xp_needed_next, 1)) * 100), 100)

    for course in courses:
        progress = calculate_course_progress(request.user, course)
        course.progress_pct = progress["percentage"]
        course.completed_chapter_count = progress["completed_count"]
        course.total_chapter_count = progress["total_chapters"]

    recent_course = courses[0] if courses else None

    unlocked_count = 0
    if courses:
        unlocked_count += 1
    if profile.total_xp >= 20:
        unlocked_count += 1
    if profile.streak_days >= 7:
        unlocked_count += 1
    if profile.current_level >= 5:
        unlocked_count += 1

    return render(request, "courses/dashboard.html", {
        "profile": profile,
        "courses": courses,
        "xp_needed_next": xp_needed_next,
        "xp_percentage": xp_percentage,
        "recent_course": recent_course,
        "unlocked_count": unlocked_count,
    })


@login_required
def course_list(request):
    courses = Course.objects.filter(user=request.user)
    return render(request, "courses/course_list.html", {"courses": courses})


# --------------------------------------------------
# 3. COURSE CREATION & BUILDER
# --------------------------------------------------
@login_required
def course_create(request):
    if request.method == "POST":
        content_file = request.FILES.get("content_file")
        custom_title = request.POST.get("custom_title", "").strip()

        preference_data = {
            "study_goal": request.POST.get("study_goal", "balanced_review"),
            "assessment_formats": request.POST.getlist("assessment_focus") or ["multiple_choice"],
        }

        try:
            preferences = GenerationPreferences.model_validate(preference_data)
        except Exception:
            return render(request, "courses/course_form.html", {
                "generation_failed": True,
                "generation_error": "The selected study settings were invalid.",
                "previous_filename": content_file.name if content_file else "uploaded file",
            })

        dummy_course = Course(title=custom_title or "Untitled Course", user=request.user)

        try:
            journey_data = generate_course_journey(
                dummy_course,
                uploaded_file=content_file,
                study_goal=preferences.study_goal,
                assessment_formats=preferences.assessment_formats,
            )
            journey_data["generation_profile"] = preferences.model_dump()

            with transaction.atomic():
                course = _build_journey(
                    request.user,
                    journey_data=journey_data,
                    custom_title=custom_title,
                )

            return redirect("courses:course_detail", pk=course.pk)

        except Exception as error:
            print("[Course Generation Failed]:", repr(error))
            return render(request, "courses/course_form.html", {
                "generation_failed": True,
                "previous_filename": content_file.name if content_file else "uploaded file",
            })

    return render(request, "courses/course_form.html")


@transaction.atomic
def _build_journey(course_or_user, journey_data=None, journey_override=None, custom_title=""):
    data = journey_override if journey_override is not None else journey_data

    if isinstance(course_or_user, Course):
        course = course_or_user
        if journey_override is None:
            from .services import _generate_mock_journey
            data = _generate_mock_journey(course)
        course.structured_content = data
        course.save(update_fields=["structured_content"])
    else:
        if data is None:
            raise ValueError("Journey data is required.")
        user = course_or_user
        course_meta = data["course"]
        final_title = custom_title or course_meta["title"]
        course = Course.objects.create(
            user=user,
            title=final_title,
            description=course_meta["description"],
            structured_content=data,
        )

    for chapter_data in data["chapters"]:
        chapter = Chapter.objects.create(
            course=course,
            order=chapter_data["order"],
            title=chapter_data["title"],
            review_content=chapter_data.get("overview", ""),
            source_data=chapter_data,
        )

        quiz_data = chapter_data["quiz"]
        quiz = Quiz.objects.create(chapter=chapter, title=quiz_data["title"])

        for question_data in quiz_data["questions"]:
            question_type = (
                question_data.get("type")
                or question_data.get("question_type", "multiple_choice")
            )

            answer_data = {}
            if question_type == "identification":
                answer_data = {"accepted_answers": question_data.get("accepted_answers", [])}
            elif question_type == "enumeration":
                answer_data = {
                    "expected_items": question_data.get("expected_items", []),
                    "order_matters": question_data.get("order_matters", False),
                }

            question = Question.objects.create(
                quiz=quiz,
                order=question_data["order"],
                question_type=question_type,
                text=question_data["text"],
                explanation=question_data.get("explanation", ""),
                answer_data=answer_data,
            )

            if question_type in {"multiple_choice", "true_false"}:
                for choice_data in question_data.get("choices", []):
                    Choice.objects.create(
                        question=question,
                        text=choice_data["text"],
                        is_correct=choice_data["is_correct"],
                    )

    return course


# --------------------------------------------------
# 4. COURSE DETAIL & CHAPTER REVIEW (WITH LOCK GATES)
# --------------------------------------------------
@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    chapters = list(course.chapters.select_related("quiz").all())

    for chapter in chapters:
        chapter.progress_status = get_chapter_status(request.user, chapter)
        completion_state = get_chapter_completion_state(request.user, chapter)
        chapter.lesson_completed = completion_state["lesson_completed"]
        chapter.quiz_passed = completion_state["quiz_passed"]
        chapter.tested_out = completion_state["tested_out"]
        chapter.best_quiz_percentage = completion_state["best_quiz_percentage"]
        chapter.previous_chapter = get_previous_chapter(chapter)

    progress = calculate_course_progress(request.user, course)

    return render(request, "courses/course_detail.html", {
        "course": course,
        "chapters": chapters,
        "course_progress_pct": progress["percentage"],
        "completed_count": progress["completed_count"],
        "total_chapters": progress["total_chapters"],
    })


@login_required
def chapter_review(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk, course__user=request.user)
    course = chapter.course

    chapter_status = get_chapter_status(request.user, chapter)
    if chapter_status == "locked":
        previous_chapter = get_previous_chapter(chapter)
        previous_state = (
            get_chapter_completion_state(request.user, previous_chapter)
            if previous_chapter
            else None
        )
        return render(request, "courses/chapter_locked.html", {
            "chapter": chapter,
            "previous_chapter": previous_chapter,
            "prev_chapter": previous_chapter,
            "previous_state": previous_state,
            "course": course,
            "regular_pass_threshold": REGULAR_QUIZ_PASS_THRESHOLD,
            "test_out_threshold": TEST_OUT_THRESHOLD,
        }, status=403)

    progress = calculate_course_progress(request.user, course)
    quiz = getattr(chapter, "quiz", None)
    question_count = quiz.questions.count() if quiz else 0
    completion_state = get_chapter_completion_state(request.user, chapter)

    return render(request, "courses/chapter_review.html", {
        "chapter": chapter,
        "chapter_data": chapter.source_data or {},
        "has_quiz": quiz is not None,
        "question_count": question_count,
        "is_completed": completion_state["lesson_completed"],
        "chapter_fully_completed": completion_state["completed"],
        "quiz_passed": completion_state["quiz_passed"],
        "tested_out": completion_state["tested_out"],
        "best_quiz_percentage": completion_state["best_quiz_percentage"],
        "has_read_to_end": has_read_to_end(request, chapter),
        "total_chapters": progress["total_chapters"],
        "completed_count": progress["completed_count"],
        "course_progress_pct": progress["percentage"],
        "regular_pass_threshold": REGULAR_QUIZ_PASS_THRESHOLD,
        "test_out_threshold": TEST_OUT_THRESHOLD,
    })


@login_required
@require_POST
def record_chapter_reading(request, pk):
    """Records that the user reached the end of the lesson reader."""
    chapter = get_object_or_404(Chapter, pk=pk, course__user=request.user)
    if get_chapter_status(request.user, chapter) == "locked":
        return JsonResponse({"error": "This chapter is locked."}, status=403)

    request.session[get_reading_session_key(chapter)] = True
    request.session.modified = True
    return JsonResponse({"recorded": True, "chapter_id": chapter.pk})


@login_required
@require_POST
def complete_chapter(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk, course__user=request.user)

    if get_chapter_status(request.user, chapter) == "locked":
        return JsonResponse({"error": "This chapter is locked."}, status=403)

    if not has_read_to_end(request, chapter):
        return JsonResponse({
            "error": "Finish reviewing the lesson before marking it complete."
        }, status=403)

    completion, created = ChapterCompletion.objects.get_or_create(
        user=request.user, chapter=chapter
    )

    if created:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.award_xp(LESSON_COMPLETION_XP, reason=f"Completed lesson: {chapter.title}")
        profile.record_study_activity()

        completion_state = get_chapter_completion_state(request.user, chapter)
        next_chapter = get_next_chapter(chapter)

        return JsonResponse({
            "awarded": True,
            "xp_earned": LESSON_COMPLETION_XP,
            "new_total_xp": profile.total_xp,
            "chapter_completed": completion_state["completed"],
            "quiz_required": (completion_state["has_quiz"] and not completion_state["quiz_passed"]),
            "next_chapter_unlocked": (completion_state["completed"] and next_chapter is not None),
        })

    return JsonResponse({"awarded": False, "xp_earned": 0})


@login_required
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        if title:
            course.title = title
            course.description = description
            course.save(update_fields=["title", "description"])
    return redirect("courses:course_detail", pk=course.pk)


@login_required
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    if request.method == "POST":
        course.delete()
        return redirect("courses:course_list")
    return redirect("courses:course_detail", pk=course.pk)


@login_required
def chapter_rename(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk, course__user=request.user)
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        if title:
            chapter.title = title
            chapter.save(update_fields=["title"])
    return redirect("courses:course_detail", pk=chapter.course.pk)


# --------------------------------------------------
# 5. MIXED-ASSESSMENT GRADING & QUIZ FLOW
# --------------------------------------------------
@login_required
def chapter_quiz(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk, course__user=request.user)
    if get_chapter_status(request.user, chapter) == "locked":
        previous_chapter = get_previous_chapter(chapter)
        return render(request, "courses/chapter_locked.html", {
            "chapter": chapter,
            "previous_chapter": previous_chapter,
            "prev_chapter": previous_chapter,
            "course": chapter.course,
            "regular_pass_threshold": REGULAR_QUIZ_PASS_THRESHOLD,
            "test_out_threshold": TEST_OUT_THRESHOLD,
        }, status=403)

    quiz = getattr(chapter, "quiz", None)
    return render(request, "courses/chapter_quiz.html", {"chapter": chapter, "quiz": quiz})


def _grade_question(question, submitted_answer):
    max_points = question.max_points()
    if not isinstance(submitted_answer, dict):
        submitted_answer = {}

    # Choice-based grading
    if question.question_type in {"multiple_choice", "true_false"}:
        chosen_choice_id = submitted_answer.get("choice_id") if submitted_answer else None
        correct_choice = next((c for c in question.choices.all() if c.is_correct), None)
        try:
            chosen_choice_id = int(chosen_choice_id)
        except (TypeError, ValueError):
            chosen_choice_id = None
        is_correct = chosen_choice_id is not None and correct_choice is not None and chosen_choice_id == correct_choice.id
        return (
            1 if is_correct else 0,
            max_points,
            {
                "is_correct": is_correct,
                "correct_choice_id": correct_choice.id if correct_choice else None,
                "correct_choice_text": correct_choice.text if correct_choice else "",
            },
        )

    # Identification grading
    if question.question_type == "identification":
        submitted_text = (submitted_answer or {}).get("text", "")
        if not isinstance(submitted_text, str):
            submitted_text = ""
        accepted_answers = question.answer_data.get("accepted_answers", [])
        normalized_submitted = normalize_text_answer(submitted_text)
        is_correct = any(
            normalize_text_answer(a) == normalized_submitted for a in accepted_answers
        )
        return (
            1 if is_correct else 0,
            max_points,
            {
                "is_correct": is_correct,
                "accepted_answers": accepted_answers,
                "canonical_answer": accepted_answers[0] if accepted_answers else "",
            },
        )

    # Enumeration grading
    if question.question_type == "enumeration":
        submitted_items = (submitted_answer or {}).get("items", [])
        if not isinstance(submitted_items, list):
            submitted_items = []
        expected_items = list(question.answer_data.get("expected_items", []))
        order_matters = bool(question.answer_data.get("order_matters", False))

        if order_matters:
            matched_items = []
            for index, expected in enumerate(expected_items):
                if index >= len(submitted_items):
                    break
                sub_norm = normalize_text_answer(submitted_items[index])
                candidates = [expected["canonical"]] + expected.get("accepted_variants", [])
                if any(normalize_text_answer(c) == sub_norm for c in candidates):
                    matched_items.append(expected["canonical"])

            missing_items = [
                exp["canonical"] for exp in expected_items if exp["canonical"] not in matched_items
            ]
        else:
            remaining = list(expected_items)
            matched_items = []
            seen_submissions = set()

            for raw_item in submitted_items:
                normalized = normalize_text_answer(raw_item)
                if not normalized or normalized in seen_submissions:
                    continue
                seen_submissions.add(normalized)

                match_index = None
                for index, expected in enumerate(remaining):
                    candidates = [expected["canonical"]] + expected.get("accepted_variants", [])
                    if any(normalize_text_answer(c) == normalized for c in candidates):
                        match_index = index
                        break

                if match_index is not None:
                    matched_items.append(remaining[match_index]["canonical"])
                    remaining.pop(match_index)

            missing_items = [expected["canonical"] for expected in remaining]

        earned_points = len(matched_items)
        return (
            earned_points,
            max_points,
            {
                "is_correct": (earned_points == max_points),
                "matched_items": matched_items,
                "missing_items": missing_items,
                "order_matters": order_matters,
            },
        )

    return (0, max_points, {"is_correct": False})


@login_required
@require_POST
def check_quiz_answer(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk, course__user=request.user)
    if get_chapter_status(request.user, chapter) == "locked":
        return JsonResponse({"error": "This chapter is locked."}, status=403)

    quiz = getattr(chapter, "quiz", None)
    if quiz is None:
        return JsonResponse({"error": "No quiz for this chapter."}, status=404)

    try:
        payload = json.loads(request.body)
        question_id = payload.get("question_id")
        submitted_answer = payload.get("answer", {})
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    question = get_object_or_404(
        Question.objects.prefetch_related("choices"), pk=question_id, quiz=quiz
    )
    earned_points, maximum_points, feedback = _grade_question(question, submitted_answer)

    return JsonResponse({
        "question_id": question.id,
        "question_type": question.question_type,
        "earned_points": earned_points,
        "maximum_points": maximum_points,
        "explanation": question.explanation,
        **feedback,
    })


@login_required
@require_POST
def submit_quiz(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk, course__user=request.user)
    if get_chapter_status(request.user, chapter) == "locked":
        return JsonResponse({"error": "This chapter is locked."}, status=403)

    quiz = getattr(chapter, "quiz", None)
    if quiz is None:
        return JsonResponse({"error": "No quiz for this chapter."}, status=404)

    try:
        payload = json.loads(request.body)
        submitted_answers = payload.get("answers", {})
        if not isinstance(submitted_answers, dict):
            submitted_answers = {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    questions = list(quiz.questions.prefetch_related("choices").all())
    total_earned = 0
    total_maximum = 0
    results = []

    for question in questions:
        submitted_answer = submitted_answers.get(str(question.id))
        earned_points, maximum_points, feedback = _grade_question(question, submitted_answer)
        total_earned += earned_points
        total_maximum += maximum_points
        review_entry = {
            "question_id": question.id,
            "order": question.order,
            "question_type": question.question_type,
            "question_text": question.text,
            "earned_points": earned_points,
            "maximum_points": maximum_points,
            "explanation": question.explanation,
            "submitted_answer": submitted_answer if isinstance(submitted_answer, dict) else {},
            **feedback,
        }

        if question.question_type in {"multiple_choice", "true_false"}:
            chosen_id = (submitted_answer or {}).get("choice_id") if isinstance(submitted_answer, dict) else None
            try:
                chosen_id = int(chosen_id)
            except (TypeError, ValueError):
                chosen_id = None
            chosen_choice = next((choice for choice in question.choices.all() if choice.id == chosen_id), None)
            review_entry["submitted_choice_text"] = chosen_choice.text if chosen_choice else "No answer"

        results.append(review_entry)

    percentage = round(total_earned / max(total_maximum, 1) * 100)
    xp_earned = calculate_quiz_xp(percentage)

    QuizAttempt.objects.create(
        user=request.user,
        quiz=quiz,
        score=total_earned,
        total_questions=total_maximum,
        xp_earned=xp_earned,
    )

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.award_xp(xp_earned, reason=f"Quiz: {chapter.title}")
    profile.record_study_activity()

    completion_state = get_chapter_completion_state(request.user, chapter)
    next_chapter = get_next_chapter(chapter)

    return JsonResponse({
        "score": total_earned,
        "total_questions": total_maximum,
        "percentage": percentage,
        "passed": (percentage >= REGULAR_QUIZ_PASS_THRESHOLD),
        "tested_out": (
            percentage >= TEST_OUT_THRESHOLD and not completion_state["lesson_completed"]
        ),
        "chapter_completed": completion_state["completed"],
        "next_chapter_unlocked": (completion_state["completed"] and next_chapter is not None),
        "next_chapter_id": next_chapter.pk if (completion_state["completed"] and next_chapter) else None,
        "xp_earned": xp_earned,
        "new_total_xp": profile.total_xp,
        "new_level": profile.current_level,
        "new_streak": profile.streak_days,
        "results": results,
    })