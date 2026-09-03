# StudyQuest — Project Brief

*Original pitch, written for a Technopreneurship course requirement.*

## Overview

StudyQuest is a mobile learning app that turns studying into a game through
XP, levels, quests, streaks, achievements, and challenges — inspired by the
gamified learning approach of apps like Duolingo. Students can upload their
syllabus, modules, notes, or assignments, which an AI API (e.g. Gemini)
analyzes to generate personalized lessons, flashcards, quizzes, and learning
paths. It breaks large academic requirements into smaller quests, making
studying more organized, interactive, and motivating.

## Alignment with course objectives

- **Innovation:** combines AI-assisted learning with gamification to make
  traditional studying more engaging and personalized.
- **Technology application:** uses an AI API, document processing, and a
  database to transform uploaded academic materials into interactive
  learning activities.
- **Entrepreneurial value:** addresses students' common problems —
  procrastination, disorganized study materials, and difficulty maintaining
  motivation — while offering premium features through a subscription
  model.

## Feasibility

- **Resources:** buildable by a small student team using existing
  technologies and AI APIs, rather than training a model from scratch.
- **Initial scope:** uploading materials, AI-generated quizzes and
  flashcards, an XP/level system, and progress tracking — before adding more
  advanced features.
- **Monetization:** a free tier to attract users, with a ₱50–₱100/month
  premium subscription offering more AI usage, unlimited uploads,
  personalized learning paths, and detailed progress analytics.

## How this repo maps to the pitch

| Pitch concept | Current repo |
|---|---|
| Upload syllabus/modules/notes/assignments | `reviewer.Course` fields + course intake form |
| AI-generated personalized lessons/quizzes | `reviewer/services.py` (stubbed — see README) |
| Quests / learning path | `reviewer.Chapter`, rendered as the "Quest Map" |
| Duolingo-style quizzes | `reviewer.Quiz` / `Question` / `Choice` + `static/reviewer/js/quiz.js` |
| XP, levels, streaks | UI placeholders only in `base.html` — not yet persisted per user |
| Subscription tier | not built yet |
