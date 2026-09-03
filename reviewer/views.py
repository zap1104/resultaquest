from django.shortcuts import get_object_or_404, redirect, render

from .forms import CourseForm
from .models import Chapter, Choice, Course, Question, Quiz
from .services import generate_course_journey


def course_list(request):
    courses = Course.objects.all()
    return render(request, 'reviewer/course_list.html', {'courses': courses})


def course_create(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            _build_journey(course)
            return redirect('reviewer:course_detail', pk=course.pk)
    else:
        form = CourseForm()
    return render(request, 'reviewer/course_form.html', {'form': form})


def _build_journey(course):
    """Runs the (currently stubbed) AI step and saves it as Chapters/Quizzes."""
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


def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    return render(request, 'reviewer/course_detail.html', {'course': course})


def chapter_review(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk)
    has_quiz = hasattr(chapter, 'quiz')
    return render(request, 'reviewer/chapter_review.html', {
        'chapter': chapter,
        'has_quiz': has_quiz,
    })


def chapter_quiz(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk)
    quiz = getattr(chapter, 'quiz', None)
    return render(request, 'reviewer/chapter_quiz.html', {
        'chapter': chapter,
        'quiz': quiz,
    })
