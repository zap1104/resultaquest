"""AI processing hook.

Not wired up yet. Once a key is available, `generate_course_journey` should
call an AI API (e.g. Gemini) with the course's raw syllabus/modules/
activities/assignments text and return a structured dict shaped like the
sample below, which `views.create_course` then uses to create Chapter rows.

Expected shape (this is the "JSON journey" mentioned in the brief):
{
    "chapters": [
        {
            "title": "Chapter 1: Intro to ...",
            "review_content": "...",
            "quiz": {
                "questions": [
                    {
                        "text": "...",
                        "choices": [{"text": "...", "is_correct": true}, ...]
                    }
                ]
            }
        },
        ...
    ]
}
"""


def generate_course_journey(course):
    """Stub. Returns a single placeholder chapter so the review/quiz flow
    has something to open, instead of calling a real AI model.
    """
    return {
        'chapters': [
            {
                'title': 'Chapter 1: Overview',
                'review_content': (
                    'This is a placeholder review generated without AI.\n\n'
                    'Once the AI integration is added, this section will summarize '
                    f'the syllabus and materials you submitted for "{course.title}" '
                    'into a short, personalized review — similar to a NetAcad '
                    'chapter recap — before the quiz unlocks.'
                ),
                'quiz': {
                    'questions': [
                        {
                            'text': f'What course are you currently reviewing?',
                            'choices': [
                                {'text': course.title, 'is_correct': True},
                                {'text': 'Undeclared', 'is_correct': False},
                                {'text': 'None of the above', 'is_correct': False},
                            ],
                        },
                        {
                            'text': 'This quiz is a placeholder until AI-generated questions are wired up. True or false?',
                            'choices': [
                                {'text': 'True', 'is_correct': True},
                                {'text': 'False', 'is_correct': False},
                            ],
                        },
                    ]
                },
            }
        ]
    }
