import unittest
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import customtkinter as ctk
from ui.components.duplicate_dialog import DuplicateConflictDialog


class TestDuplicateDialog(unittest.TestCase):
    def setUp(self):
        self.root = ctk.CTk()
        self.root.withdraw()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_dialog_creation_and_choices(self):
        dialog = DuplicateConflictDialog(self.root, "test_song.mp3", "C:/downloads")
        self.assertEqual(dialog.result, "skip")

        # Testa escolha 'copy'
        dialog._choose("copy")
        self.assertEqual(dialog.result, "copy")

    def test_dialog_overwrite_choice(self):
        dialog = DuplicateConflictDialog(self.root, "another_song.mp3", "C:/downloads")
        dialog._choose("overwrite")
        self.assertEqual(dialog.result, "overwrite")


if __name__ == "__main__":
    unittest.main()
