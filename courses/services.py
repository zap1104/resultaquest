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
    """
    PROTOTYPE MODE: Returns a deterministic mock dictionary structured exactly 
    how the future Gemini JSON output will be formatted.
    """
    title = course.title.lower()

    # Adaptive Route 1: Networking / Infrastructure
    if 'network' in title or 'lan' in title or 'cisco' in title:
        return {
            "chapters": [
                {
                    "title": "Campus Network Fundamentals",
                    "review_content": "A campus network architecture requires robust hierarchical design. Core, Distribution, and Access layers must be mapped carefully to ensure high availability and load balancing across university departments.",
                    "quiz": {
                        "questions": [
                            {
                                "text": "Which layer is responsible for routing traffic between different VLANs in a university setting?",
                                "choices": [
                                    {"text": "Access Layer", "is_correct": False},
                                    {"text": "Distribution Layer", "is_correct": True},
                                    {"text": "Core Layer", "is_correct": False},
                                    {"text": "Physical Layer", "is_correct": False}
                                ]
                            }
                        ]
                    }
                },
                {
                    "title": "Subnetting & IP Allocation",
                    "review_content": "Effective subnetting minimizes broadcast traffic. When designing for hundreds of nodes, choosing the correct CIDR notation ensures scalable growth.",
                    "quiz": {
                        "questions": [
                            {
                                "text": "Which subnet mask allows for exactly 254 usable host IP addresses?",
                                "choices": [
                                    {"text": "/23", "is_correct": False},
                                    {"text": "/24", "is_correct": True},
                                    {"text": "/25", "is_correct": False},
                                    {"text": "/26", "is_correct": False}
                                ]
                            }
                        ]
                    }
                }
            ]
        }

    # Adaptive Route 2: Programming / Software Apps
    elif 'ruby' in title or 'program' in title or 'syntax' in title:
        return {
            "chapters": [
                {
                    "title": "Gamified Logic & Syntax",
                    "review_content": "Learning programming syntax can be vastly accelerated through gamification. By visualizing code blocks and utilizing drag-and-drop interfaces, abstract concepts like loops and arrays become tactile puzzles.",
                    "quiz": {
                        "questions": [
                            {
                                "text": "What is the primary benefit of drag-and-drop syntax learning?",
                                "choices": [
                                    {"text": "It compiles code faster.", "is_correct": False},
                                    {"text": "It eliminates syntax errors while teaching logic.", "is_correct": True},
                                    {"text": "It uses less memory.", "is_correct": False},
                                    {"text": "It requires no internet connection.", "is_correct": False}
                                ]
                            }
                        ]
                    }
                }
            ]
        }

    # Adaptive Route 3: Generic Fallback
    else:
        return {
            "chapters": [
                {
                    "title": "Core Concepts Integration",
                    "review_content": "This is a placeholder review node. In production, Gemini 1.5 Pro will have analyzed your document and synthesized this into a readable, concise study guide.",
                    "quiz": {
                        "questions": [
                            {
                                "text": "Is StudyQuest currently operating in Prototype Mode?",
                                "choices": [
                                    {"text": "Yes, using deterministic mock data.", "is_correct": True},
                                    {"text": "No, it is fully live.", "is_correct": False}
                                ]
                            }
                        ]
                    }
                }
            ]
        }