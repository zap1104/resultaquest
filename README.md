# 🎮 StudyQuest

StudyQuest is a gamified, AI-assisted study companion. It turns a course's raw
materials — syllabus, modules, activities, assignments — into a personalized,
chapter-by-chapter review journey with Duolingo/Kahoot-style quizzes, XP,
levels, and streaks.

> **Status:** early scaffold. The UI and data model are in place; the AI
> generation step is currently a stub (see [Current State](#current-state)).

## Core idea

1. **Create a course** (e.g. *Technopreneurship*) and paste in your syllabus,
   modules, activities, and assignments.
2. An AI step (planned: Gemini API) turns that raw text into a structured
   JSON "journey" — a sequence of chapters, each with review content and a
   quiz.
3. **Review a chapter** — a short, personalized recap of that chapter's
   material, similar to a Cisco NetAcad chapter review.
4. **Take the quiz** — one question at a time, Duolingo/Kahoot style, with
   instant feedback and XP.

## Tech stack

- **Backend:** Django 5.2 (Python)
- **Database:** SQLite (local dev)
- **Frontend:** Django templates + vanilla CSS/JS (no build step, no framework yet)
- **AI:** not wired up yet — `reviewer/services.py` is the integration point

## Project structure

```
studyquest/
├── manage.py
├── requirements.txt
├── studyquest/          # Django project settings, root urls
└── reviewer/             # main app
    ├── models.py         # Course, Chapter, Quiz, Question, Choice
    ├── services.py        # AI generation hook (stubbed for now)
    ├── forms.py           # course intake form
    ├── views.py
    ├── urls.py
    ├── templates/reviewer/
    └── static/reviewer/
```

## Getting started

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

Then open http://127.0.0.1:8000/.

## Current state

What works today:
- Create a course via a simple form (syllabus/modules/activities/assignments as text)
- On submit, a stub "AI" step (`reviewer/services.py`) generates one
  placeholder chapter with a review and a 2-question quiz, so the full flow
  is clickable end to end
- Quest map, chapter review page, and a working client-side quiz (scoring is
  in-browser only, not persisted yet)
- Django admin for inspecting/editing courses, chapters, and quiz content

What's intentionally not built yet:
- Real AI integration (swap the stub in `reviewer/services.py` for a Gemini/
  other LLM call that returns the same JSON shape)
- Accounts/auth, and persisting XP, levels, and streaks per user
- File uploads (PDF/DOCX syllabus parsing) — text paste only for now
- Subscription/premium tier

## Roadmap (rough)

- [ ] Wire up an AI API (Gemini) in `generate_course_journey()`
- [ ] User accounts + per-user XP/level/streak tracking
- [ ] Persist quiz results and progress
- [ ] File upload support for syllabi/modules
- [ ] "New course" as a modal instead of a full page
- [ ] Mobile app shell (this is meant to be a mobile-first product)

## About

StudyQuest started as a Technopreneurship course project. See
[docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md) for the original pitch
(innovation, technology application, feasibility).

Contributing? See [CONTRIBUTING.md](CONTRIBUTING.md) for the Git/GitHub
workflow this repo uses.
