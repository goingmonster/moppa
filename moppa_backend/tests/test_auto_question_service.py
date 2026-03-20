from typing import Any, cast
from unittest import TestCase
from unittest.mock import MagicMock

from app.services.auto_question_service import AutoQuestionService


class AutoQuestionServiceTest(TestCase):
    def _build_service(self) -> Any:
        service = cast(Any, AutoQuestionService.__new__(AutoQuestionService))
        service.db = MagicMock()
        service.event_repository = MagicMock()
        service.question_repository = MagicMock()
        service.template_repository = MagicMock()
        service.task_repository = MagicMock()
        return service

    def test_build_generated_question_log_entries_returns_question_and_answer_space(self) -> None:
        service = self._build_service()

        result = service._build_generated_question_log_entries(
            [
                {
                    "question": "  Will it rain tomorrow?  ",
                    "candidate_answers": [" Yes ", "No", "  "],
                }
            ]
        )

        self.assertEqual(
            result,
            [
                {
                    "index": 1,
                    "question": "Will it rain tomorrow?",
                    "answer_space": '[" Yes ", "No", "  "]',
                }
            ],
        )

    def test_build_generated_question_log_entries_handles_string_answer_space(self) -> None:
        service = self._build_service()

        result = service._build_generated_question_log_entries(
            [
                {
                    "question": "What will the score be?",
                    "candidate_answers": "0-1, 2-3, 4+",
                }
            ]
        )

        self.assertEqual(result[0]["answer_space"], "0-1, 2-3, 4+")
        self.assertEqual(result[0]["question"], "What will the score be?")

    def test_build_generated_question_log_entries_handles_invalid_items(self) -> None:
        service = self._build_service()

        result = service._build_generated_question_log_entries(["bad item", {"candidate_answers": None}])

        self.assertEqual(
            result,
            [
                {"index": 1, "question": None, "answer_space": None},
                {"index": 2, "question": None, "answer_space": None},
            ],
        )

    def test_build_answer_space_serializes_dict_as_json_string(self) -> None:
        service = self._build_service()

        result = service._build_answer_space({"A": "是", "B": "否"})

        self.assertEqual(result, '{"A": "是", "B": "否"}')

    def test_build_answer_space_serializes_number_as_string(self) -> None:
        service = self._build_service()

        result = service._build_answer_space(42)

        self.assertEqual(result, "42")

    def test_build_answer_space_serializes_list_as_json_string(self) -> None:
        service = self._build_service()

        result = service._build_answer_space(["是", "否"])

        self.assertEqual(result, '["是", "否"]')
