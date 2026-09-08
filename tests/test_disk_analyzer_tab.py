import unittest
import customtkinter as ctk
from ui.main_window import MainWindow
from features.disk_analyzer_tab import DiskAnalyzerTab
from core.disk_scanner import (
    ScanResult,
    FileItem,
    DirItem,
    ExtensionStat,
)


class TestDiskAnalyzerIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Janela invisível para testes de UI
        cls.app = MainWindow()
        cls.app.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.app.destroy()
        except Exception:
            pass

    def test_tab_exists_and_renders(self):
        self.assertIn("disk_analyzer", self.app.sidebar_buttons)
        self.app.switch_tab("disk_analyzer")
        self.assertEqual(self.app.current_feature_id, "disk_analyzer")

        tab_instance = self.app.feature_instances["disk_analyzer"]
        self.assertIsInstance(tab_instance, DiskAnalyzerTab)

    def test_mock_scan_population(self):
        self.app.switch_tab("disk_analyzer")
        tab: DiskAnalyzerTab = self.app.feature_instances["disk_analyzer"]

        # Criar resultado mock
        mock_root_dir = DirItem(
            path="C:\\TestRoot",
            name="TestRoot",
            total_size=50000,
            direct_size=10000,
            file_count=5,
            subdirs_count=2,
            children=[
                DirItem(path="C:\\TestRoot\\Videos", name="Videos", total_size=30000, direct_size=30000, file_count=2),
                DirItem(path="C:\\TestRoot\\Downloads", name="Downloads", total_size=10000, direct_size=10000, file_count=2),
            ],
        )

        mock_top_files = [
            FileItem(path="C:\\TestRoot\\Videos\\movie.mp4", name="movie.mp4", size=25000, ext=".mp4", dir_path="C:\\TestRoot\\Videos"),
            FileItem(path="C:\\TestRoot\\Downloads\\setup.exe", name="setup.exe", size=8000, ext=".exe", dir_path="C:\\TestRoot\\Downloads"),
        ]

        mock_exts = [
            ExtensionStat(ext=".mp4", total_size=25000, file_count=1, color="#3498db"),
            ExtensionStat(ext=".exe", total_size=8000, file_count=1, color="#e74c3c"),
        ]

        result = ScanResult(
            root_path="C:\\TestRoot",
            total_size=50000,
            total_files=5,
            total_dirs=3,
            elapsed_seconds=0.45,
            root_dir=mock_root_dir,
            subfolders=mock_root_dir.children,
            top_files=mock_top_files,
            extensions=mock_exts,
        )

        # Disparar preenchimento na interface
        tab._on_scan_success(result)

        # Checar se os cards foram atualizados
        self.assertIn("48.83 KB", tab.card_size.cget("text"))
        self.assertEqual(tab.card_files.cget("text"), "5")
        self.assertEqual(tab.card_dirs.cget("text"), "3")
        self.assertEqual(tab.card_time.cget("text"), "0.45s")

        # Testar navegação de subpastas
        self.assertEqual(len(tab.subdirs_scroll.winfo_children()), 2)
        tab._on_enter_subfolder(mock_root_dir.children[0])
        self.assertEqual(tab.current_browsed_dir.name, "Videos")
        tab._on_dir_back()
        self.assertEqual(tab.current_browsed_dir.name, "TestRoot")


if __name__ == "__main__":
    unittest.main()
