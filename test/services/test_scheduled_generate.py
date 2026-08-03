import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config.profile_dimensions import Format, Pacing
from scripts import scheduled_generate


def _calendar(long_form=None, shorts=None, language="tr") -> dict:
    return {
        "niche": "Test Niche",
        "language": language,
        "long_form": long_form if long_form is not None else [],
        "shorts": shorts if shorts is not None else [],
    }


class TestNextPlannedEntry(unittest.TestCase):
    def test_returns_first_planned_entry_and_skips_others(self):
        calendar = _calendar(
            shorts=[
                {"index": 1, "topic": "A", "status": "generated"},
                {"index": 2, "topic": "B", "status": "placeholder"},
                {"index": 3, "topic": "C", "status": "planned"},
                {"index": 4, "topic": "D", "status": "planned"},
            ]
        )
        entry = scheduled_generate._next_planned_entry(calendar, "short")
        self.assertEqual(entry["topic"], "C")

    def test_returns_none_when_no_planned_entries(self):
        calendar = _calendar(
            shorts=[
                {"index": 1, "topic": "A", "status": "generated"},
                {"index": 2, "topic": "B", "status": "placeholder"},
            ]
        )
        self.assertIsNone(scheduled_generate._next_planned_entry(calendar, "short"))

    def test_returns_none_for_empty_calendar(self):
        self.assertIsNone(scheduled_generate._next_planned_entry(_calendar(), "long"))

    def test_long_and_short_read_from_separate_lists(self):
        calendar = _calendar(
            long_form=[{"week": 1, "topic": "Long topic", "status": "planned"}],
            shorts=[{"index": 1, "topic": "Short topic", "status": "planned"}],
        )
        self.assertEqual(scheduled_generate._next_planned_entry(calendar, "long")["topic"], "Long topic")
        self.assertEqual(scheduled_generate._next_planned_entry(calendar, "short")["topic"], "Short topic")


class TestRun(unittest.TestCase):
    """"Haftalık Otomatik Üretim" planı (kullanıcı onaylı): run()'un GERÇEK
    davranışı -- doğru parametrelerle run_pipeline() çağırması, sadece
    başarıda takvimi güncellemesi, başarısızlıkta HİÇ dokunmaması.
    Hepsi mock'lu -- gerçek para harcamıyor.
    """

    def setUp(self):
        self.tmp_dir = Path(__import__("tempfile").mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(self.tmp_dir, ignore_errors=True))
        self.calendar_path = self.tmp_dir / "calendar.yaml"
        self.log_path = self.tmp_dir / "scheduled_generate.log"

        self.patches = [
            patch.object(scheduled_generate, "CALENDAR_PATH", self.calendar_path),
            patch.object(scheduled_generate, "LOG_PATH", self.log_path),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def _write_calendar(self, calendar: dict) -> None:
        with open(self.calendar_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(calendar, f, allow_unicode=True, sort_keys=False)

    def _read_calendar(self) -> dict:
        with open(self.calendar_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_returns_0_and_logs_skip_when_no_planned_entries(self):
        self._write_calendar(_calendar(shorts=[{"index": 1, "topic": "X", "status": "placeholder"}]))

        with patch.object(scheduled_generate.default_pipeline, "run_pipeline") as mock_run:
            result = scheduled_generate.run("short")

        self.assertEqual(result, 0)
        mock_run.assert_not_called()
        self.assertIn("SKIP", self.log_path.read_text(encoding="utf-8"))

    def test_short_uses_short_pacing_9_16_and_forced_stock_source(self):
        self._write_calendar(
            _calendar(
                shorts=[
                    {
                        "index": 1,
                        "topic": "Why do we procrastinate?",
                        "topic_category": "psychology",
                        "status": "planned",
                    }
                ]
            )
        )

        with patch.object(scheduled_generate.default_pipeline, "run_pipeline") as mock_run:
            result = scheduled_generate.run("short")

        self.assertEqual(result, 0)
        _args, kwargs = mock_run.call_args
        self.assertEqual(kwargs["topic"], "Why do we procrastinate?")
        self.assertEqual(kwargs["topic_category_override"], "psychology")
        self.assertEqual(kwargs["pacing"], Pacing.short)
        self.assertEqual(kwargs["video_source"], "pexels")
        self.assertEqual(kwargs["video_aspect"], "9:16")
        self.assertEqual(kwargs["format"], Format.educational)
        self.assertEqual(kwargs["language"], "tr")

    def test_long_uses_extended_pacing_and_16_9_aspect(self):
        self._write_calendar(
            _calendar(
                long_form=[
                    {
                        "week": 1,
                        "topic": "The psychology of habit formation",
                        "topic_category": "personal_development",
                        "tone": "motivational",
                        "status": "planned",
                    }
                ]
            )
        )

        with patch.object(scheduled_generate.default_pipeline, "run_pipeline") as mock_run:
            result = scheduled_generate.run("long")

        self.assertEqual(result, 0)
        _args, kwargs = mock_run.call_args
        self.assertEqual(kwargs["pacing"], Pacing.extended)
        self.assertEqual(kwargs["video_aspect"], "16:9")
        self.assertEqual(kwargs["tone"], "motivational")
        self.assertEqual(kwargs["video_source"], "pexels")

    def test_marks_entry_generated_and_persists_to_disk_on_success(self):
        self._write_calendar(
            _calendar(shorts=[{"index": 1, "topic": "X", "status": "planned"}])
        )

        with patch.object(scheduled_generate.default_pipeline, "run_pipeline"):
            result = scheduled_generate.run("short")

        self.assertEqual(result, 0)
        on_disk = self._read_calendar()
        self.assertEqual(on_disk["shorts"][0]["status"], "generated")
        self.assertIn("OK", self.log_path.read_text(encoding="utf-8"))

    def test_calendar_untouched_and_nonzero_exit_on_pipeline_failure(self):
        self._write_calendar(
            _calendar(shorts=[{"index": 1, "topic": "X", "status": "planned"}])
        )

        with patch.object(
            scheduled_generate.default_pipeline,
            "run_pipeline",
            side_effect=RuntimeError("TTS timeout"),
        ):
            result = scheduled_generate.run("short")

        self.assertEqual(result, 1)
        on_disk = self._read_calendar()
        # Hâlâ "planned" -- bir sonraki zamanlanmış çalıştırma aynı konuyu
        # tekrar dener, hafta kaybolmaz.
        self.assertEqual(on_disk["shorts"][0]["status"], "planned")
        self.assertIn("FAILED", self.log_path.read_text(encoding="utf-8"))

    def test_calendar_schema_has_no_video_source_field_to_override_the_forced_constant(self):
        # "Haftalık Otomatik Üretim" planı MADDE 4: video_source hiçbir
        # takvim alanından okunmuyor -- bir girdiye video_source eklense
        # bile run() bunu HİÇ okumaz, FORCED_VIDEO_SOURCE değişmeden kalır.
        self._write_calendar(
            _calendar(
                shorts=[
                    {
                        "index": 1,
                        "topic": "X",
                        "status": "planned",
                        "video_source": "ai_generated",  # okunmamalı
                    }
                ]
            )
        )

        with patch.object(scheduled_generate.default_pipeline, "run_pipeline") as mock_run:
            scheduled_generate.run("short")

        _args, kwargs = mock_run.call_args
        self.assertEqual(kwargs["video_source"], "pexels")


if __name__ == "__main__":
    unittest.main()
