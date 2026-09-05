"""
Sanity check for the AI contract, run before any Gemini integration work.

This does NOT test Django views/models/DB — it only proves that a
realistic, hand-written chapter (transcribed directly from an actual
uploaded PDF, not invented) can be represented by GeneratedChapter
without validation errors. If this fails, the schema itself needs to
change before writing a single line of prompt or API code.

Run with: python manage.py test courses.tests.test_schemas
"""
import json
import os

from django.test import SimpleTestCase
from pydantic import ValidationError

from courses.schemas import GeneratedChapter

FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'fixtures', 'pt_week_4_chapter2_manual.json'
)

class SchemaFixtureTests(SimpleTestCase):
    def setUp(self):
        with open(FIXTURE_PATH, 'r', encoding='utf-8') as f:
            self.chapter_data = json.load(f)

    def test_hand_transcribed_chapter_validates(self):
        """The real 'Service Models' chapter from PT-Week-4.pdf must be
        representable by GeneratedChapter with zero modification.
        A failure here means the schema is missing something the
        source material actually needs (as happened with the first
        draft schema, which had no room for the IaaS/PaaS/SaaS table).
        """
        try:
            chapter = GeneratedChapter(**self.chapter_data)
        except ValidationError as e:
            self.fail(f'Fixture failed schema validation:\n{e}')

        self.assertEqual(chapter.order, 2)
        self.assertEqual(len(chapter.key_terms), 3)
        self.assertIsNotNone(chapter.analogy)
        self.assertEqual(len(chapter.comparisons), 1)
        self.assertEqual(chapter.comparisons[0].title, 'Comparing IaaS, PaaS, and SaaS')
        self.assertEqual(len(chapter.comparisons[0].rows), 4)
        self.assertEqual(len(chapter.common_confusions), 2)
        self.assertEqual(len(chapter.quiz.questions), 3)

    def test_quiz_questions_have_exactly_one_correct_choice(self):
        chapter = GeneratedChapter(**self.chapter_data)
        for question in chapter.quiz.questions:
            correct = [c for c in question.choices if c.is_correct]
            self.assertEqual(
                len(correct), 1,
                f"Question '{question.text[:40]}...' should have exactly one correct choice."
            )

    def test_tampered_question_with_two_correct_choices_is_rejected(self):
        """Proves the model_validator actually fires — not just that
        well-formed data passes, but that malformed data is caught.
        """
        bad_data = json.loads(json.dumps(self.chapter_data))  # deep copy
        bad_data['quiz']['questions'][0]['choices'][1]['is_correct'] = True

        with self.assertRaises(ValidationError):
            GeneratedChapter(**bad_data)

    def test_tampered_duplicate_choice_text_is_rejected(self):
        bad_data = json.loads(json.dumps(self.chapter_data))
        bad_data['quiz']['questions'][0]['choices'][1]['text'] = \
            bad_data['quiz']['questions'][0]['choices'][0]['text']

        with self.assertRaises(ValidationError):
            GeneratedChapter(**bad_data)
