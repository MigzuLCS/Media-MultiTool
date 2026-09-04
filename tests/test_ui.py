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


if __name__ == "__main__":
    unittest.main()
