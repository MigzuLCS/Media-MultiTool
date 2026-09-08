import os
import tempfile
import threading
import unittest
from core.disk_scanner import (
    DiskScanner,
    format_size,
    get_color_for_ext,
    compute_squarified_treemap,
    get_windows_drives,
)


class TestDiskScanner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = self.temp_dir.name

        # Criar estrutura de teste:
        # root/
        #   file1.txt (1000 bytes)
        #   video.mp4 (5000 bytes)
        #   sub1/
        #     audio.mp3 (3000 bytes)
        #     sub2/
        #       big.iso (10000 bytes)
        #       empty.txt (0 bytes)

        self._create_file(os.path.join(self.root, "file1.txt"), 1000)
        self._create_file(os.path.join(self.root, "video.mp4"), 5000)

        sub1 = os.path.join(self.root, "sub1")
        os.makedirs(sub1, exist_ok=True)
        self._create_file(os.path.join(sub1, "audio.mp3"), 3000)

        sub2 = os.path.join(sub1, "sub2")
        os.makedirs(sub2, exist_ok=True)
        self._create_file(os.path.join(sub2, "big.iso"), 10000)
        self._create_file(os.path.join(sub2, "empty.txt"), 0)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_file(self, path: str, size: int):
        with open(path, "wb") as f:
            f.write(b"x" * size)

    def test_format_size(self):
        self.assertEqual(format_size(0), "0 B")
        self.assertEqual(format_size(500), "500 B")
        self.assertEqual(format_size(1024), "1.00 KB")
        self.assertEqual(format_size(1024 * 1024), "1.00 MB")
        self.assertEqual(format_size(1024 * 1024 * 1024 * 2), "2.00 GB")

    def test_scan_basic(self):
        scanner = DiskScanner(max_top_files=10)
        result = scanner.scan(self.root)

        # Total esperado: 1000 + 5000 + 3000 + 10000 + 0 = 19000 bytes
        self.assertEqual(result.total_size, 19000)
        self.assertEqual(result.total_files, 5)
        # total_dirs: root, sub1, sub2 -> 3
        self.assertEqual(result.total_dirs, 3)

        # Verificar maiores arquivos (devem vir ordenados do maior para o menor)
        self.assertGreaterEqual(len(result.top_files), 4)
        self.assertEqual(result.top_files[0].name, "big.iso")
        self.assertEqual(result.top_files[0].size, 10000)
        self.assertEqual(result.top_files[1].name, "video.mp4")
        self.assertEqual(result.top_files[1].size, 5000)
        self.assertEqual(result.top_files[2].name, "audio.mp3")
        self.assertEqual(result.top_files[2].size, 3000)

        # Verificar extensões
        ext_dict = {stat.ext: stat.total_size for stat in result.extensions}
        self.assertEqual(ext_dict[".iso"], 10000)
        self.assertEqual(ext_dict[".mp4"], 5000)
        self.assertEqual(ext_dict[".mp3"], 3000)
        self.assertEqual(ext_dict[".txt"], 1000)

        # Subpastas imediatas
        self.assertEqual(len(result.subfolders), 1)
        self.assertEqual(result.subfolders[0].name, "sub1")
        # Tamanho acumulado de sub1: audio.mp3 (3000) + big.iso (10000) = 13000
        self.assertEqual(result.subfolders[0].total_size, 13000)

    def test_scan_cancel(self):
        cancel_event = threading.Event()
        cancel_event.set()  # Já começa cancelado
        scanner = DiskScanner()
        result = scanner.scan(self.root, cancel_event=cancel_event)
        self.assertEqual(result.total_files, 0)

    def test_treemap_generation(self):
        items = [
            {"label": "Item A", "size": 1000, "color": "#ff0000", "data": "A"},
            {"label": "Item B", "size": 500, "color": "#00ff00", "data": "B"},
            {"label": "Item C", "size": 250, "color": "#0000ff", "data": "C"},
        ]
        rects = compute_squarified_treemap(items, width=800, height=600)
        self.assertEqual(len(rects), 3)

        for r in rects:
            # Todas as coordenadas devem estar dentro do canvas
            self.assertGreaterEqual(r.x0, 0)
            self.assertGreaterEqual(r.y0, 0)
            self.assertLessEqual(r.x1, 800)
            self.assertLessEqual(r.y1, 600)
            self.assertGreater(r.x1, r.x0)
            self.assertGreater(r.y1, r.y0)

    def test_get_windows_drives(self):
        drives = get_windows_drives()
        self.assertIsInstance(drives, list)
        self.assertGreater(len(drives), 0)


if __name__ == "__main__":
    unittest.main()
