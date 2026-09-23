import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace as NS
import unittest
import uuid

REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / "project_039_skill_ai-video-director/scripts/video_pipeline.py"
spec = importlib.util.spec_from_file_location("pipeline", TOOL)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        base = Path(os.environ.get("VIDEO_SOP_TEST_ROOT", str(REPO / "work/tests")))
        self.root = base / uuid.uuid4().hex
        p.init(NS(project=str(self.root), mode="quick", idea="A cup in rain", duration=2, fps=24, aspect="16:9"))
        self.m = p.read(self.root / "production.json")
        self.m["video"].update(width=320, height=180)
        self.m["shots"] = [self.shot("S01", 24), self.shot("S02", 24)]
        self.persist()

    def shot(self, name, frames):
        return {"id": name, "frames": frames, "purpose": "Reveal warmth", "image_prompt": "A cream cup beside rain",
                "camera_prompt": "Close shot, locked camera", "action_prompt": "Steam rises; cup remains on table"}

    def persist(self):
        p.save(self.root / "production.json", self.m)

    def authorize(self, limit=100):
        self.m["authorization"].update(paid_generation=True, credit_limit=limit)
        self.persist()
        p.save(self.root / "receipts/request.json", {"model": "test-only", "shot": "S01"})

    def reserve(self, shot="S01", estimate=40, retry=""):
        return p.reserve(NS(project=str(self.root), shot=shot, estimate=estimate,
                            request="receipts/request.json", retry_authorization=retry))

    def record(self, status, credits=None, generation="test-id", job="S01-a1"):
        p.save(self.root / "receipts/receipt.json", {"TEST_FIXTURE": True, "status": status})
        return p.record(NS(project=str(self.root), job=job, status=status, credits=credits,
                           generation_id=generation, receipt="receipts/receipt.json"))

    def test_valid_timeline(self):
        self.assertEqual(p.validation(self.m, self.root)["frames"], 48)

    def test_no_fake_init_completion(self):
        m = copy.deepcopy(self.m)
        m["shots"] = []
        with self.assertRaisesRegex(ValueError, "No authored"):
            p.validation(m, self.root)

    def test_quick_over_30_is_rejected(self):
        self.m["video"]["target_frames"] = 721
        with self.assertRaisesRegex(ValueError, "30 seconds"):
            p.validation(self.m, self.root)

    def test_init_over_30_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "30 seconds"):
            p.init(NS(project=str(self.root / "bad"), mode="quick", idea="Rain", duration=31, fps=30, aspect=None))

    def test_frame_mismatch_rejected(self):
        self.m["shots"][0]["frames"] = 23
        with self.assertRaisesRegex(ValueError, "Timeline"):
            p.validation(self.m, self.root)

    def test_duplicate_shot_id_rejected(self):
        self.m["shots"][1]["id"] = "S01"
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            p.validation(self.m, self.root)

    def test_subtitle_overlap_rejected(self):
        self.m["captions"] = [{"start_frame": 0, "end_frame": 30, "text": "one"},
                               {"start_frame": 20, "end_frame": 40, "text": "two"}]
        with self.assertRaisesRegex(ValueError, "caption"):
            p.validation(self.m, self.root)

    def test_missing_action_rejected(self):
        self.m["shots"][0]["action_prompt"] = ""
        with self.assertRaisesRegex(ValueError, "action_prompt"):
            p.validation(self.m, self.root)

    def test_path_escape_rejected(self):
        with self.assertRaisesRegex(ValueError, "escapes"):
            p.local(self.root, "../outside.mp4")

    def test_negative_audio_fade_rejected(self):
        self.m["audio"] = [{"role": "music", "file": "audio/test.wav", "start_frame": 0,
                            "in": 0, "out": 2, "fade_out": -1}]
        with self.assertRaisesRegex(ValueError, "fade_out"):
            p.validation(self.m, self.root)

    def test_authorization_required(self):
        with self.assertRaisesRegex(ValueError, "authorization"):
            self.reserve()

    def test_budget_required(self):
        self.authorize(None)
        with self.assertRaisesRegex(ValueError, "credit limit"):
            self.reserve()

    def test_duplicate_pending_reservation_rejected(self):
        self.authorize()
        self.reserve()
        with self.assertRaisesRegex(ValueError, "Unresolved"):
            self.reserve(retry="Even with permission, reconcile first")

    def test_unknown_job_blocks_resubmission(self):
        self.authorize()
        self.reserve()
        self.record("UNKNOWN", generation=None)
        with self.assertRaisesRegex(ValueError, "Unresolved"):
            self.reserve()

    def test_actual_credits_replace_estimate(self):
        self.authorize(100)
        self.reserve(estimate=60)
        self.record("SUBMITTED", credits=20)
        self.record("SUCCEEDED")
        result = self.reserve("S02", estimate=70)
        self.assertEqual(result["reserved_total"], 90)

    def test_failure_does_not_imply_refund(self):
        self.authorize(50)
        self.reserve(estimate=40)
        self.record("FAILED", generation=None)
        with self.assertRaisesRegex(ValueError, "exceed"):
            self.reserve("S02", estimate=20)

    def test_retry_requires_specific_authorization(self):
        self.authorize()
        self.reserve()
        self.record("FAILED", credits=0, generation=None)
        with self.assertRaisesRegex(ValueError, "retry authorization"):
            self.reserve()
        result = self.reserve(retry="Test fixture: user explicitly approved second attempt")
        self.assertEqual(result["job"], "S01-a2")

    def test_paid_id_is_immutable(self):
        self.authorize()
        self.reserve()
        self.record("SUBMITTED")
        with self.assertRaisesRegex(ValueError, "replace"):
            self.record("SUCCEEDED", generation="different-id")

    def test_succeeded_requires_task_id(self):
        self.authorize()
        self.reserve()
        self.record("UNKNOWN", generation=None)
        with self.assertRaisesRegex(ValueError, "ID required"):
            self.record("SUCCEEDED", generation=None)

    def test_terminal_job_cannot_be_regressed(self):
        self.authorize()
        self.reserve()
        self.record("SUBMITTED")
        self.record("SUCCEEDED")
        with self.assertRaisesRegex(ValueError, "transition"):
            self.record("SUBMITTED")

    def test_srt_hour_boundary(self):
        self.assertEqual(p.srt_time(24 * 3600, 24), "01:00:00,000")

    def test_unicode_roundtrip(self):
        file = self.root / "测试.json"
        p.save(file, {"text": "锦与陶，动静之间"})
        self.assertEqual(p.read(file)["text"], "锦与陶，动静之间")

    def test_lock_prevents_concurrent_writer(self):
        with p.lock(self.root):
            with self.assertRaisesRegex(ValueError, "locked"):
                with p.lock(self.root):
                    pass


HAS_FFMPEG = bool((os.environ.get("FFMPEG") or shutil.which("ffmpeg")) and
                  (os.environ.get("FFPROBE") or shutil.which("ffprobe")))


@unittest.skipUnless(HAS_FFMPEG, "FFmpeg/ffprobe not found; integration tests explicitly skipped")
class MediaTests(unittest.TestCase):
    setUp = PipelineTests.setUp
    shot = PipelineTests.shot
    persist = PipelineTests.persist
    def media(self):
        ff = p.executable("ffmpeg")
        source = self.root / "sources/测试源.mp4"
        p.run([ff, "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30",
               "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000", "-t", "3",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", source])
        music = self.root / "audio/music.wav"
        p.run([ff, "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=48000", "-t", "2", music])
        for index, shot in enumerate(self.m["shots"]):
            shot["source"] = {"file": "sources/测试源.mp4", "in": index, "out": index + 1}
            shot["review"] = {"status": "accepted", "sha256": p.sha(source), "in": index, "out": index + 1,
                              "notes": "SYNTHETIC TEST FIXTURE, not human or AI visual certification"}
        self.m["shots"][0]["native_audio"] = True
        self.m["audio"] = [{"file": "audio/music.wav", "role": role, "start_frame": 0, "in": 0, "out": 2,
                            "gain_db": gain, "fade_out": .15} for role, gain in (("music", -12), ("voice", -6))]
        self.m["captions"] = [{"start_frame": 2, "end_frame": 44, "text": "测试字幕 · Demo"}]
        self.persist()
        return source

    def test_real_render_unicode_audio_captions_and_frame_count(self):
        self.media()
        result = p.assemble(NS(project=str(self.root), output="test-final.mp4"))
        file = Path(result["video"])
        self.assertTrue(file.is_file())
        report = p.qa_file(self.root, self.m, file)
        self.assertTrue(report["technical_pass"])
        self.assertEqual(report["frames"], 48)
        self.assertEqual(report["visual_review"], "NOT_PERFORMED_BY_SCRIPT")
        self.assertTrue(file.with_suffix(".srt").is_file())
        self.assertTrue(file.with_name("test-final-cover.jpg").is_file())
        with self.assertRaisesRegex(ValueError, "already exists"):
            p.assemble(NS(project=str(self.root), output="test-final.mp4"))

    def test_changed_source_invalidates_acceptance(self):
        source = self.media()
        source.write_bytes(source.read_bytes() + b"CHANGED")
        with self.assertRaisesRegex(ValueError, "changed after review"):
            p.validation(self.m, self.root, ready=True)

    def test_unreviewed_extension_rejected(self):
        self.media()
        self.m["shots"][0]["source"]["out"] = 1.1
        with self.assertRaisesRegex(ValueError, "beyond reviewed"):
            p.validation(self.m, self.root, ready=True)

    def test_missing_required_audio_rejected(self):
        self.media()
        self.m["audio"] = []
        for shot in self.m["shots"]:
            shot["native_audio"] = False
        with self.assertRaisesRegex(ValueError, "sound is missing"):
            p.validation(self.m, self.root, ready=True)


if __name__ == "__main__":
    unittest.main()
