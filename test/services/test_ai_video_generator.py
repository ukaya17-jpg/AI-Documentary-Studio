import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.departments.production import ai_video_generator
from app.models.asset import AssetCandidate, AssetPlan
from app.utils import utils


def _plan(prompts: dict[int, str]) -> AssetPlan:
    return AssetPlan(
        candidates=[
            AssetCandidate(scene_index=i, provider="ai_generated", prompt=p)
            for i, p in prompts.items()
        ]
    )


class TestGenerateAiClips(unittest.TestCase):
    def setUp(self):
        self.task_id = "ai-video-test-task"
        self.addCleanup(lambda: shutil.rmtree(utils.task_dir(self.task_id), ignore_errors=True))

    def test_returns_plan_unchanged_when_no_candidates_have_a_prompt(self):
        plan = AssetPlan(candidates=[AssetCandidate(scene_index=0, search_term="ruins")])

        with patch(
            "app.departments.production.ai_video_generator.fal_video_service"
        ) as mock_service:
            result = ai_video_generator.generate_ai_clips(plan, self.task_id)

        self.assertIs(result, plan)
        mock_service.submit_video_job.assert_not_called()

    @patch("app.departments.production.ai_video_generator.time.sleep")
    @patch("app.departments.production.ai_video_generator.fal_video_service")
    def test_all_clips_succeed_on_first_poll(self, mock_service, mock_sleep):
        plan = _plan({0: "wide shot of ancient ruins", 1: "close-up of stone carvings"})
        mock_service.submit_video_job.side_effect = [
            {"success": True, "request_id": "req-0"},
            {"success": True, "request_id": "req-1"},
        ]
        mock_service.poll_job_status.return_value = {"success": True, "status": "COMPLETED"}
        mock_service.get_job_result.return_value = {
            "success": True,
            "video_url": "https://v2.fal.media/clip.mp4",
        }
        mock_service.download_video.return_value = True
        progress_calls = []

        result = ai_video_generator.generate_ai_clips(
            plan, self.task_id, on_substage_progress=lambda done, total: progress_calls.append((done, total))
        )

        self.assertEqual(len(result.downloaded_paths), 2)
        self.assertTrue(result.downloaded_paths[0].endswith("ai_clip_scene_0.mp4"))
        self.assertTrue(result.downloaded_paths[1].endswith("ai_clip_scene_1.mp4"))
        self.assertEqual(progress_calls, [(1, 2), (2, 2)])
        mock_sleep.assert_not_called()

    @patch("app.departments.production.ai_video_generator.time.sleep")
    @patch("app.departments.production.ai_video_generator.fal_video_service")
    def test_polls_across_multiple_iterations_until_completed(self, mock_service, mock_sleep):
        plan = _plan({0: "wide shot of ancient ruins"})
        mock_service.submit_video_job.return_value = {"success": True, "request_id": "req-0"}
        mock_service.poll_job_status.side_effect = [
            {"success": True, "status": "IN_QUEUE"},
            {"success": True, "status": "IN_PROGRESS"},
            {"success": True, "status": "COMPLETED"},
        ]
        mock_service.get_job_result.return_value = {
            "success": True,
            "video_url": "https://v2.fal.media/clip.mp4",
        }
        mock_service.download_video.return_value = True

        result = ai_video_generator.generate_ai_clips(plan, self.task_id)

        self.assertEqual(len(result.downloaded_paths), 1)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("app.departments.production.ai_video_generator.time.sleep")
    @patch("app.departments.production.ai_video_generator.fal_video_service")
    def test_raises_with_scene_detail_when_submit_fails(self, mock_service, mock_sleep):
        plan = _plan({0: "wide shot of ancient ruins", 1: "close-up of stone carvings"})
        mock_service.submit_video_job.side_effect = [
            {"success": True, "request_id": "req-0"},
            {"success": False, "error": "content policy violation"},
        ]
        mock_service.poll_job_status.return_value = {"success": True, "status": "COMPLETED"}
        mock_service.get_job_result.return_value = {
            "success": True,
            "video_url": "https://v2.fal.media/clip.mp4",
        }
        mock_service.download_video.return_value = True

        with self.assertRaises(ai_video_generator.AIVideoGenerationError) as ctx:
            ai_video_generator.generate_ai_clips(plan, self.task_id)

        self.assertEqual(ctx.exception.failures, [(1, "content policy violation")])
        # Scene 0 already submitted successfully (real money spent) -- its
        # clip is still generated and downloaded rather than discarded.
        self.assertIn(0, ctx.exception.completed_paths)

    @patch("app.departments.production.ai_video_generator._MAX_POLL_ITERATIONS", 2)
    @patch("app.departments.production.ai_video_generator.time.sleep")
    @patch("app.departments.production.ai_video_generator.fal_video_service")
    def test_raises_timeout_error_when_job_never_completes(self, mock_service, mock_sleep):
        plan = _plan({0: "wide shot of ancient ruins"})
        mock_service.submit_video_job.return_value = {"success": True, "request_id": "req-0"}
        mock_service.poll_job_status.return_value = {"success": True, "status": "IN_PROGRESS"}

        with self.assertRaises(ai_video_generator.AIVideoGenerationError) as ctx:
            ai_video_generator.generate_ai_clips(plan, self.task_id)

        self.assertEqual(len(ctx.exception.failures), 1)
        self.assertIn("timed out", ctx.exception.failures[0][1])

    @patch("app.departments.production.ai_video_generator.time.sleep")
    @patch("app.departments.production.ai_video_generator.fal_video_service")
    def test_raises_when_fal_job_status_is_a_failure_state(self, mock_service, mock_sleep):
        plan = _plan({0: "wide shot of ancient ruins"})
        mock_service.submit_video_job.return_value = {"success": True, "request_id": "req-0"}
        mock_service.poll_job_status.return_value = {"success": True, "status": "ERROR"}

        with self.assertRaises(ai_video_generator.AIVideoGenerationError) as ctx:
            ai_video_generator.generate_ai_clips(plan, self.task_id)

        self.assertIn("fal.ai job failed", ctx.exception.failures[0][1])

    @patch("app.departments.production.ai_video_generator.time.sleep")
    @patch("app.departments.production.ai_video_generator.fal_video_service")
    def test_raises_when_download_fails(self, mock_service, mock_sleep):
        plan = _plan({0: "wide shot of ancient ruins"})
        mock_service.submit_video_job.return_value = {"success": True, "request_id": "req-0"}
        mock_service.poll_job_status.return_value = {"success": True, "status": "COMPLETED"}
        mock_service.get_job_result.return_value = {
            "success": True,
            "video_url": "https://v2.fal.media/clip.mp4",
        }
        mock_service.download_video.return_value = False

        with self.assertRaises(ai_video_generator.AIVideoGenerationError) as ctx:
            ai_video_generator.generate_ai_clips(plan, self.task_id)

        self.assertIn("failed to download", ctx.exception.failures[0][1])

    @patch("app.departments.production.ai_video_generator.time.sleep")
    @patch("app.departments.production.ai_video_generator.fal_video_service")
    def test_passes_aspect_ratio_and_each_candidates_own_ai_duration_to_submit(
        self, mock_service, mock_sleep
    ):
        # Yüzyıl/binyıl... hayır, bu "tekrar eden kare" düzeltmesi: her
        # candidate'in KENDİ ai_duration'ı kullanılmalı, tek bir global
        # değer değil -- sadece gerçekten ihtiyacı olan sahne "10" ödesin.
        plan = AssetPlan(
            candidates=[
                AssetCandidate(
                    scene_index=0,
                    provider="ai_generated",
                    prompt="wide shot of ancient ruins",
                    ai_duration="5",
                ),
                AssetCandidate(
                    scene_index=1,
                    provider="ai_generated",
                    prompt="close-up of stone carvings",
                    ai_duration="10",
                ),
            ]
        )
        mock_service.submit_video_job.return_value = {"success": True, "request_id": "req-x"}
        mock_service.poll_job_status.return_value = {"success": True, "status": "COMPLETED"}
        mock_service.get_job_result.return_value = {
            "success": True,
            "video_url": "https://v2.fal.media/clip.mp4",
        }
        mock_service.download_video.return_value = True

        ai_video_generator.generate_ai_clips(plan, self.task_id, aspect_ratio="9:16")

        mock_service.submit_video_job.assert_any_call(
            "wide shot of ancient ruins",
            duration="5",
            aspect_ratio="9:16",
            character_elements=None,
        )
        mock_service.submit_video_job.assert_any_call(
            "close-up of stone carvings",
            duration="10",
            aspect_ratio="9:16",
            character_elements=None,
        )

    @patch("app.departments.production.ai_video_generator.time.sleep")
    @patch("app.departments.production.ai_video_generator.fal_video_service")
    def test_character_reference_is_passed_as_character_elements(self, mock_service, mock_sleep):
        """"Bao" planı: character_reference verildiğinde her submit_video_job
        çağrısı, model_dump()'ı character_elements listesi içinde alır --
        Kling O1'in elements[] şeması (bkz. docs/character-consistency-research.md).
        """
        from app.models.character import CharacterReference

        plan = _plan({0: "wide shot of ancient ruins"})
        character_reference = CharacterReference(
            name="Bao", frontal_image_url="data:image/jpeg;base64,front"
        )
        mock_service.submit_video_job.return_value = {
            "success": True,
            "request_id": "req-0",
            "app_id": "fal-ai/kling-video",
        }
        mock_service.poll_job_status.return_value = {"success": True, "status": "COMPLETED"}
        mock_service.get_job_result.return_value = {
            "success": True,
            "video_url": "https://v2.fal.media/clip.mp4",
        }
        mock_service.download_video.return_value = True

        ai_video_generator.generate_ai_clips(
            plan, self.task_id, character_reference=character_reference
        )

        mock_service.submit_video_job.assert_any_call(
            "wide shot of ancient ruins",
            duration="5",
            aspect_ratio="9:16",
            character_elements=[character_reference.model_dump()],
        )

    @patch("app.departments.production.ai_video_generator.time.sleep")
    @patch("app.departments.production.ai_video_generator.fal_video_service")
    def test_app_id_from_submit_is_passed_to_poll_and_result(self, mock_service, mock_sleep):
        """poll_job_status/get_job_result must be called with the SAME app_id
        submit_video_job returned -- not silently re-derived from whatever
        the live provider config says at poll time (see fal_video.py's
        app_id override docstrings; this matters when a character job is
        submitted while a different provider is globally selected).
        """
        plan = _plan({0: "wide shot of ancient ruins"})
        mock_service.submit_video_job.return_value = {
            "success": True,
            "request_id": "req-0",
            "app_id": "fal-ai/kling-video",
        }
        mock_service.poll_job_status.return_value = {"success": True, "status": "COMPLETED"}
        mock_service.get_job_result.return_value = {
            "success": True,
            "video_url": "https://v2.fal.media/clip.mp4",
        }
        mock_service.download_video.return_value = True

        ai_video_generator.generate_ai_clips(plan, self.task_id)

        mock_service.poll_job_status.assert_any_call("req-0", app_id="fal-ai/kling-video")
        mock_service.get_job_result.assert_any_call("req-0", app_id="fal-ai/kling-video")


if __name__ == "__main__":
    unittest.main()
