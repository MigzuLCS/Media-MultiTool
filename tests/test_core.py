import os
import sys
import unittest
import threading
import time
from pathlib import Path

# Adiciona o diretório raiz ao path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.config import ConfigManager
from core.ffmpeg_manager import ffmpeg_manager
from core.transformer import media_transformer
from core.tasks import TaskManager
from features import AVAILABLE_FEATURES
from features.base import BaseFeature


class TestConfigManager(unittest.TestCase):
    def test_config_defaults(self):
        tmp_config = ROOT_DIR / "tests" / "temp_config.json"
        if tmp_config.exists():
            tmp_config.unlink()

        cfg = ConfigManager(config_path=tmp_config)
        self.assertEqual(cfg.get("theme"), "dark")
        self.assertTrue(cfg.get("output_dir"))

        cfg.set("custom_test_key", "multitool_ok")
        self.assertEqual(cfg.get("custom_test_key"), "multitool_ok")

        if tmp_config.exists():
            tmp_config.unlink()


class TestMediaTransformerUtils(unittest.TestCase):
    def test_parse_time_to_seconds(self):
        self.assertEqual(media_transformer._parse_time_to_seconds("00:01:30"), 90.0)
        self.assertEqual(media_transformer._parse_time_to_seconds("00:01:30.500"), 90.5)
        self.assertEqual(media_transformer._parse_time_to_seconds("00:01:30,250"), 90.25)
        self.assertEqual(media_transformer._parse_time_to_seconds("01:00:00"), 3600.0)
        self.assertEqual(media_transformer._parse_time_to_seconds("02:15"), 135.0)
        self.assertEqual(media_transformer._parse_time_to_seconds("45"), 45.0)
        self.assertEqual(media_transformer._parse_time_to_seconds("invalid"), 0.0)


class TestTaskManager(unittest.TestCase):
    def test_task_execution_and_callbacks(self):
        tm = TaskManager()
        results = []

        def sample_work(cancel_event=None, on_progress=None):
            time.sleep(0.05)
            if on_progress:
                on_progress(1.0, "Pronto")
            return "resultado_ok"

        def on_success(val):
            results.append(val)

        task = tm.run_task(
            name="test_work",
            target=sample_work,
            on_success=on_success,
        )

        task.thread.join(timeout=2.0)
        self.assertIn("resultado_ok", results)
        self.assertFalse(task.is_running)

    def test_task_cancellation(self):
        tm = TaskManager()
        started = threading.Event()

        def slow_work(cancel_event=None, on_progress=None):
            started.set()
            while not cancel_event.is_set():
                time.sleep(0.01)
            return "cancelled"

        task = tm.run_task(name="slow", target=slow_work)
        started.wait(timeout=1.0)
        self.assertTrue(task.is_running)

        task.cancel()
        task.thread.join(timeout=2.0)
        self.assertFalse(task.is_running)


class TestFeatureRegistry(unittest.TestCase):
    def test_features_inherit_base(self):
        self.assertGreater(len(AVAILABLE_FEATURES), 0)
        for feat in AVAILABLE_FEATURES:
            self.assertTrue(issubclass(feat, BaseFeature))
            self.assertTrue(hasattr(feat, "id"))
            self.assertTrue(hasattr(feat, "title"))
            self.assertTrue(hasattr(feat, "icon"))
            self.assertTrue(callable(feat.render))


if __name__ == "__main__":
    unittest.main()
