from types import SimpleNamespace
from typing import Any, cast
from unittest import TestCase
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.services.question_location_analysis_service import QuestionLocationAnalysisService


class QuestionLocationAnalysisServiceTest(TestCase):
    def _build_service(self) -> Any:
        service = cast(Any, QuestionLocationAnalysisService.__new__(QuestionLocationAnalysisService))
        service.db = MagicMock()
        service.question_repository = MagicMock()
        service.task_repository = MagicMock()
        service.client = MagicMock()
        service._nominatim_next_allowed_at = 0.0
        return service

    def _build_task(self, status: str = "pending") -> SimpleNamespace:
        return SimpleNamespace(id=uuid4(), status=status, result={})

    def test_run_job_fails_early_when_area_backfill_needs_llm_config(self) -> None:
        service = self._build_service()
        task = self._build_task()

        service.task_repository.get_by_idempotency_key.return_value = None
        service.task_repository.create_pending.return_value = task
        service.task_repository.mark_running.return_value = task
        service.task_repository.mark_failed.side_effect = (
            lambda task_id, error_message, max_attempts: SimpleNamespace(
                id=task_id, status="failed", result={}, error_message=error_message, max_attempts=max_attempts
            )
        )
        service.question_repository.count_without_coordinates.return_value = 1
        service.question_repository.count_needing_area_backfill.return_value = 1
        service.question_repository.list_needing_area_backfill.return_value = [
            {"id": uuid4(), "area": "", "content": "北京朝阳区有一场活动"}
        ]

        with patch("app.services.question_location_analysis_service.settings") as mock_settings:
            mock_settings.question_location_analysis_osm_base_url = "https://nominatim.openstreetmap.org"
            mock_settings.auto_review_model = ""
            mock_settings.auto_review_base_url = ""
            mock_settings.auto_review_api_key = ""
            mock_settings.auto_review_batch_size = 10
            mock_settings.question_location_analysis_scope = "week"

            response = service.run_location_analysis_job()

        self.assertEqual(response.status, "failed")
        self.assertEqual(service.task_repository.mark_failed.call_count, 1)
        self.assertIn("AUTO_REVIEW_MODEL is required", service.task_repository.mark_failed.call_args.kwargs["error_message"])

    def test_run_job_backfills_area_then_queries_coordinates(self) -> None:
        service = self._build_service()
        task = self._build_task()
        completed = self._build_task(status="completed")

        service.task_repository.get_by_idempotency_key.return_value = None
        service.task_repository.create_pending.return_value = task
        service.task_repository.mark_running.return_value = task
        service.task_repository.mark_completed.return_value = completed
        service.question_repository.count_without_coordinates.return_value = 1
        service.question_repository.count_needing_area_backfill.return_value = 1
        service.question_repository.list_needing_area_backfill.return_value = [
            {"id": uuid4(), "area": "", "content": "北京朝阳区有一场活动"}
        ]
        service.question_repository.update_area_if_empty.return_value = True
        service.question_repository.count_needing_coordinate_backfill.return_value = 1
        service.question_repository.list_needing_coordinate_backfill.return_value = [
            {"id": uuid4(), "area": "北京市", "content": "北京朝阳区有一场活动"}
        ]
        service.question_repository.update_coordinates.return_value = True
        service._extract_location_name_from_content = MagicMock(return_value="北京市")
        service._extract_coordinates_osm_from_name = MagicMock(return_value=(39.9042, 116.4074))

        with patch("app.services.question_location_analysis_service.settings") as mock_settings:
            mock_settings.question_location_analysis_osm_base_url = "https://nominatim.openstreetmap.org"
            mock_settings.auto_review_model = "glm-4.5"
            mock_settings.auto_review_base_url = "https://llm.example.com"
            mock_settings.auto_review_api_key = "test-key"
            mock_settings.auto_review_batch_size = 10
            mock_settings.question_location_analysis_scope = "week"

            response = service.run_location_analysis_job()

        self.assertEqual(response.status, "completed")
        service.question_repository.update_area_if_empty.assert_called_once()
        service.question_repository.update_coordinates.assert_called_once()
        service._extract_location_name_from_content.assert_called_once_with("北京朝阳区有一场活动")
        service._extract_coordinates_osm_from_name.assert_called_once_with("北京市")
        self.assertEqual(service.task_repository.mark_failed.call_count, 0)

    def test_run_job_allows_osm_only_when_second_phase_has_area(self) -> None:
        service = self._build_service()
        task = self._build_task()
        completed = self._build_task(status="completed")

        service.task_repository.get_by_idempotency_key.return_value = None
        service.task_repository.create_pending.return_value = task
        service.task_repository.mark_running.return_value = task
        service.task_repository.mark_completed.return_value = completed
        service.question_repository.count_without_coordinates.return_value = 1
        service.question_repository.count_needing_area_backfill.return_value = 0
        service.question_repository.list_needing_area_backfill.return_value = []
        service.question_repository.count_needing_coordinate_backfill.return_value = 1
        service.question_repository.list_needing_coordinate_backfill.return_value = [
            {"id": uuid4(), "area": "北京市", "content": "北京朝阳区有一场活动"}
        ]
        service.question_repository.update_coordinates.return_value = True
        service._extract_coordinates_osm_from_name = MagicMock(return_value=(39.9042, 116.4074))

        with patch("app.services.question_location_analysis_service.settings") as mock_settings:
            mock_settings.question_location_analysis_osm_base_url = "https://nominatim.openstreetmap.org"
            mock_settings.auto_review_model = ""
            mock_settings.auto_review_base_url = ""
            mock_settings.auto_review_api_key = ""
            mock_settings.auto_review_batch_size = 10
            mock_settings.question_location_analysis_scope = "week"

            response = service.run_location_analysis_job()

        self.assertEqual(response.status, "completed")
        service._extract_coordinates_osm_from_name.assert_called_once_with("北京市")
        service.question_repository.update_coordinates.assert_called_once()
        self.assertEqual(service.task_repository.mark_failed.call_count, 0)

    def test_wait_for_nominatim_slot_paces_requests(self) -> None:
        service = self._build_service()

        with patch("app.services.question_location_analysis_service.time.monotonic", side_effect=[10.0, 10.0, 10.5, 10.5]), patch(
            "app.services.question_location_analysis_service.time.sleep"
        ) as sleep_mock:
            service._wait_for_nominatim_slot()
            service._wait_for_nominatim_slot()

        sleep_mock.assert_called_once()
        self.assertAlmostEqual(sleep_mock.call_args.args[0], 0.6, places=6)

    def test_extract_coordinates_osm_retries_once_on_429_with_ascii_user_agent(self) -> None:
        service = self._build_service()

        first_response = MagicMock()
        first_response.status_code = 429
        first_response.headers = {"Retry-After": "2"}

        second_response = MagicMock()
        second_response.status_code = 200
        second_response.headers = {}
        second_response.json.return_value = [{"lat": "39.9042", "lon": "116.4074", "display_name": "Beijing"}]

        with patch.object(service, "_wait_for_nominatim_slot") as wait_mock, patch(
            "app.services.question_location_analysis_service.requests.get",
            side_effect=[first_response, second_response],
        ) as get_mock, patch("app.services.question_location_analysis_service.time.sleep") as sleep_mock, patch(
            "app.services.question_location_analysis_service.settings"
        ) as mock_settings:
            mock_settings.question_location_analysis_osm_base_url = "https://nominatim.openstreetmap.org"
            mock_settings.question_location_analysis_osm_timeout_seconds = 10

            coordinates = service._extract_coordinates_osm_from_name("Beijing")

        self.assertEqual(coordinates, (39.9042, 116.4074))
        self.assertEqual(get_mock.call_count, 2)
        self.assertEqual(wait_mock.call_count, 2)
        sleep_mock.assert_called_once_with(2.0)
        self.assertEqual(get_mock.call_args.kwargs["headers"]["User-Agent"], "MOPPA-LocationAnalysis/1.0 (backend-service)")
