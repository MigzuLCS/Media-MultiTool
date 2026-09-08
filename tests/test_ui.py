import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ui.main_window import MainWindow
from features import AVAILABLE_FEATURES


class TestMainWindow(unittest.TestCase):
    def test_window_initialization_and_tabs(self):
        # Cria a janela sem iniciar o mainloop
        app = MainWindow()
        self.assertIsNotNone(app)

        # Testa se todas as abas podem ser instanciadas e alternadas
        for feat_cls in AVAILABLE_FEATURES:
            app.switch_tab(feat_cls.id)
            self.assertIn(feat_cls.id, app.feature_instances)
            self.assertIn(feat_cls.id, app.feature_frames)

        # Destrói a janela para liberar recursos
        app.destroy()

    def test_selective_modules_and_reload(self):
        from core.module_manager import module_manager

        # Habilita apenas youtube, convert e settings (como solicitado pelo usuário)
        module_manager.set_enabled_modules(["youtube", "convert", "settings"])

        app = MainWindow()
        active_ids = list(app.sidebar_buttons.keys())
        self.assertIn("youtube", active_ids)
        self.assertIn("convert", active_ids)
        self.assertIn("settings", active_ids)
        self.assertNotIn("compress", active_ids)
        self.assertNotIn("trim", active_ids)
        self.assertNotIn("disk_analyzer", active_ids)

        # Ativar compressor dinamicamente
        module_manager.enable_module("compress")
        app.reload_sidebar()
        self.assertIn("compress", app.sidebar_buttons)

        # Restaurar todos os módulos para os demais testes
        all_ids = [m.id for m in module_manager.get_all_modules()]
        module_manager.set_enabled_modules(all_ids)
        app.destroy()


if __name__ == "__main__":
    unittest.main()
