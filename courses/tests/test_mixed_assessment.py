import json

from django.contrib.auth.models import User
from django.test import TestCase

from courses.models import Chapter, Choice, Course, Question, Quiz
from courses.views import calculate_quiz_xp


class MixedAssessmentFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="mixed-flow-user",
            password="temporary-test-password",
        )
        self.course = Course.objects.create(
            user=self.user,
            title="Mixed Assessment Course",
            description="Test course",
        )
        self.chapter = Chapter.objects.create(
            course=self.course,
            order=1,
            title="Assessment Fundamentals",
            review_content="Read this lesson before testing.",
        )
        self.quiz = Quiz.objects.create(chapter=self.chapter, title="Mixed Quiz")
        self.identification = Question.objects.create(
            quiz=self.quiz,
            order=1,
            question_type="identification",
            text="Identify the framework.",
            explanation="Zachman is the accepted framework.",
            answer_data={"accepted_answers": ["Zachman Framework", "Zachman"]},
        )
        self.enumeration = Question.objects.create(
            quiz=self.quiz,
            order=2,
            question_type="enumeration",
            text="List the domains.",
            explanation="These are the three domains.",
            answer_data={
                "expected_items": [
                    {"canonical": "Business", "accepted_variants": []},
                    {"canonical": "Data", "accepted_variants": ["Information"]},
                    {"canonical": "Technology", "accepted_variants": []},
                ],
                "order_matters": False,
            },
        )
        self.client.login(username="mixed-flow-user", password="temporary-test-password")

    def post_json(self, url, payload):
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def test_initial_quiz_payload_does_not_expose_answer_keys(self):
        response = self.client.get(f"/chapters/{self.chapter.pk}/quiz/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"isCorrect", response.content)
        self.assertNotIn(b"Zachman Framework", response.content)
        self.assertNotIn(b"Business", response.content)

    def test_identification_and_enumeration_are_graded_server_side(self):
        identification_response = self.post_json(
            f"/chapters/{self.chapter.pk}/quiz/check/",
            {
                "question_id": self.identification.pk,
                "answer": {"text": " zachman "},
            },
        )
        enumeration_response = self.post_json(
            f"/chapters/{self.chapter.pk}/quiz/check/",
            {
                "question_id": self.enumeration.pk,
                "answer": {"items": ["Business", "Information"]},
            },
        )

        self.assertEqual(identification_response.json()["earned_points"], 1)
        self.assertEqual(enumeration_response.json()["earned_points"], 2)
        self.assertEqual(enumeration_response.json()["maximum_points"], 3)

    def test_malformed_answers_fail_as_incorrect_instead_of_server_errors(self):
        response = self.post_json(
            f"/chapters/{self.chapter.pk}/quiz/check/",
            {
                "question_id": self.identification.pk,
                "answer": {"text": {"unexpected": "object"}},
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["earned_points"], 0)

    def test_final_submission_uses_point_percentage(self):
        response = self.post_json(
            f"/chapters/{self.chapter.pk}/quiz/submit/",
            {
                "answers": {
                    str(self.identification.pk): {"text": "Zachman"},
                    str(self.enumeration.pk): {"items": ["Business", "Data", "Technology"]},
                },
            },
        )

        result = response.json()
        self.assertEqual(result["score"], 4)
        self.assertEqual(result["total_questions"], 4)
        self.assertEqual(result["percentage"], 100)
        self.assertEqual(len(result["results"]), 2)

    def test_quiz_xp_is_based_on_percentage_bands(self):
        self.assertEqual(calculate_quiz_xp(49), 10)
        self.assertEqual(calculate_quiz_xp(50), 20)
        self.assertEqual(calculate_quiz_xp(70), 35)
        self.assertEqual(calculate_quiz_xp(85), 45)
        self.assertEqual(calculate_quiz_xp(100), 60)
