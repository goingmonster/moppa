from http.client import RemoteDisconnected
from types import SimpleNamespace
from typing import Any, cast
from unittest import TestCase
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.services.auto_question_service import AutoQuestionService


class AutoQuestionServiceTest(TestCase):
    def _build_service(self) -> Any:
        service = cast(Any, AutoQuestionService.__new__(AutoQuestionService))
        service.db = MagicMock()
        service.event_repository = MagicMock()
        service.question_repository = MagicMock()
        service.template_repository = MagicMock()
        service.task_repository = MagicMock()
        service._session_factory = MagicMock()
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

    def test_call_generate_api_wraps_remote_disconnected_as_runtime_error(self) -> None:
        service = self._build_service()

        with (
            patch(
                "app.services.auto_question_service.urlopen",
                side_effect=RemoteDisconnected("Remote end closed connection without response"),
            ),
            patch("app.services.auto_question_service.settings") as mock_settings,
        ):
            mock_settings.auto_question_generate_url = "http://example.invalid"
            mock_settings.auto_question_timeout_seconds = 1

            with self.assertRaises(RuntimeError) as context:
                service._call_generate_api({})

        self.assertIn("remote disconnected", str(context.exception).lower())

    def test_run_auto_question_job_falls_back_to_fresh_session_when_mark_failed_session_is_dead(self) -> None:
        service = self._build_service()
        task = SimpleNamespace(id=uuid4(), status="running", result={})
        fallback_task = SimpleNamespace(id=task.id, status="failed", result={})
        fresh_db = MagicMock()
        fresh_context = MagicMock()
        fresh_context.__enter__.return_value = fresh_db
        fresh_context.__exit__.return_value = None

        service.task_repository.get_by_idempotency_key.return_value = None
        service.task_repository.create_pending.return_value = task
        service.task_repository.mark_running.return_value = task
        service.template_repository.list_all.side_effect = Exception("boom")
        service.db.rollback.side_effect = Exception("rollback failed")
        service.task_repository.mark_failed.side_effect = Exception("dead session")
        service._session_factory.return_value = fresh_context

        with (
            patch("app.services.auto_question_service.settings") as mock_settings,
            patch("app.services.auto_question_service.TaskExecutionRepository") as repository_class,
        ):
            mock_settings.auto_question_generate_url = "http://example.invalid"
            repository_class.return_value.mark_failed.return_value = fallback_task

            result = service.run_auto_question_job()

        repository_class.assert_called_once_with(fresh_db)
        repository_class.return_value.mark_failed.assert_called_once_with(
            task.id,
            error_message="boom",
            max_attempts=3,
        )
        self.assertEqual(result.status, "failed")
