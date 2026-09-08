import os
import sys
import unittest
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.module_manager import ModuleManager, ModuleInfo
from features.base import BaseFeature
from features import AVAILABLE_FEATURES, ALL_FEATURES, module_manager


class DummyFeatureA(BaseFeature):
    id = "dummy_a"
    title = "Ferramenta A"
    icon = "🅰️"
    description = "Teste A"
    category = "Teste"
    is_core = False
    requires_ffmpeg = True

    def render(self, parent):
        return None


class DummyCoreFeature(BaseFeature):
    id = "dummy_core"
    title = "Núcleo"
    icon = "⚙️"
    description = "Módulo Essencial"
    category = "Sistema"
    is_core = True

    def render(self, parent):
        return None


class TestModuleManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = ROOT_DIR / "tests" / "temp_modules_test"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.temp_manifest = self.temp_dir / "modules.json"
        if self.temp_manifest.exists():
            self.temp_manifest.unlink()

        self.mgr = ModuleManager(config_dir=self.temp_dir)
        self.mgr.register(DummyFeatureA)
        self.mgr.register(DummyCoreFeature)

    def tearDown(self):
        if self.temp_manifest.exists():
            self.temp_manifest.unlink()
        if self.temp_dir.exists():
            try:
                self.temp_dir.rmdir()
            except Exception:
                pass

    def test_registration_and_defaults(self):
        all_mods = self.mgr.get_all_modules()
        self.assertEqual(len(all_mods), 2)
        mod_a = next(m for m in all_mods if m.id == "dummy_a")
        self.assertEqual(mod_a.title, "Ferramenta A")
        self.assertTrue(mod_a.requires_ffmpeg)
        self.assertFalse(mod_a.is_core)

        mod_core = next(m for m in all_mods if m.id == "dummy_core")
        self.assertTrue(mod_core.is_core)

    def test_enable_disable_and_core_protection(self):
        # Desabilitar dummy_a deve funcionar
        success = self.mgr.disable_module("dummy_a")
        self.assertTrue(success)
        self.assertFalse(self.mgr.is_module_enabled("dummy_a"))

        # Desabilitar core NÃO deve ser permitido
        success_core = self.mgr.disable_module("dummy_core")
        self.assertFalse(success_core)
        self.assertTrue(self.mgr.is_module_enabled("dummy_core"))

        # Reabilitar dummy_a
        self.mgr.enable_module("dummy_a")
        self.assertTrue(self.mgr.is_module_enabled("dummy_a"))

    def test_save_and_load_manifest(self):
        self.mgr.disable_module("dummy_a")
        self.mgr.save_manifest()
        self.assertTrue(self.mgr.manifest_path.exists())

        # Novo manager lendo o mesmo diretório
        mgr2 = ModuleManager(config_dir=self.temp_dir)
        mgr2.register(DummyFeatureA)
        mgr2.register(DummyCoreFeature)
        mgr2.load_manifest()

        self.assertFalse(mgr2.is_module_enabled("dummy_a"))
        self.assertTrue(mgr2.is_module_enabled("dummy_core"))

    def test_manifest_dict_format(self):
        # Suporte a formato de dicionário {"modules": {"dummy_a": false}}
        with open(self.temp_manifest, "w", encoding="utf-8") as f:
            json.dump({"modules": {"dummy_a": False, "dummy_core": True}}, f)

        self.mgr.load_manifest()
        self.assertFalse(self.mgr.is_module_enabled("dummy_a"))
        self.assertTrue(self.mgr.is_module_enabled("dummy_core"))

    def test_listener_notification(self):
        notifications = []
        listener = lambda: notifications.append(True)
        self.mgr.add_listener(listener)

        self.mgr.disable_module("dummy_a")
        self.assertEqual(len(notifications), 1)

        self.mgr.enable_module("dummy_a")
        self.assertEqual(len(notifications), 2)

        self.mgr.remove_listener(listener)
        self.mgr.disable_module("dummy_a")
        self.assertEqual(len(notifications), 2)

    def test_app_features_integration(self):
        # Verifica se o singleton module_manager possui as features principais registradas
        all_main_mods = module_manager.get_all_modules()
        ids = [m.id for m in all_main_mods]
        self.assertIn("youtube", ids)
        self.assertIn("convert", ids)
        self.assertIn("compress", ids)
        self.assertIn("trim", ids)
        self.assertIn("disk_analyzer", ids)
        self.assertIn("settings", ids)

        # AVAILABLE_FEATURES deve responder a iterações
        self.assertGreater(len(AVAILABLE_FEATURES), 0)


if __name__ == "__main__":
    unittest.main()
