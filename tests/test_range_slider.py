import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import customtkinter as ctk
from ui.components.range_slider import TimeRangeSlider
from ui.components.waveform_view import WaveformView
from ui.main_window import MainWindow
from features.trim_tab import TrimTab


class TestTimeRangeSlider(unittest.TestCase):
    def setUp(self):
        self.root = ctk.CTk()
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_initialization_and_clamping(self):
        slider = TimeRangeSlider(
            self.root,
            duration=120.0,
            start_time=10.0,
            end_time=50.0,
            min_gap=1.0,
        )
        self.assertEqual(slider.duration, 120.0)
        self.assertEqual(slider.start_time, 10.0)
        self.assertEqual(slider.end_time, 50.0)
        self.assertEqual(slider.get_range(), (10.0, 50.0))

    def test_format_time_str(self):
        self.assertEqual(TimeRangeSlider.format_time_str(0, include_ms=False), "00:00:00")
        self.assertEqual(TimeRangeSlider.format_time_str(0, include_ms=True), "00:00:00.000")
        self.assertEqual(TimeRangeSlider.format_time_str(65.25, include_ms=True), "00:01:05.250")
        self.assertEqual(TimeRangeSlider.format_time_str(3661.05, include_ms=True), "01:01:01.050")

    def test_set_duration_and_reset(self):
        slider = TimeRangeSlider(self.root, duration=50.0)
        slider.set_duration(200.0, reset_range=True)
        self.assertEqual(slider.duration, 200.0)
        self.assertEqual(slider.start_time, 0.0)
        self.assertEqual(slider.end_time, 200.0)

    def test_set_range(self):
        slider = TimeRangeSlider(self.root, duration=100.0)
        slider.set_range(15.0, 45.0)
        self.assertEqual(slider.get_range(), (15.0, 45.0))

        # Testar além dos limites
        slider.set_range(-10.0, 150.0)
        start, end = slider.get_range()
        self.assertGreaterEqual(start, 0.0)
        self.assertLessEqual(end, 100.0)
        self.assertLess(start, end)

    def test_on_change_callback(self):
        changed_values = []

        def callback(s, e):
            changed_values.append((s, e))

        slider = TimeRangeSlider(self.root, duration=100.0, on_change=callback)
        slider._notify_change()
        self.assertEqual(len(changed_values), 1)


class TestWaveformView(unittest.TestCase):
    def setUp(self):
        self.root = ctk.CTk()
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_waveform_view_init_and_alignment(self):
        wv = WaveformView(self.root, height=68, pad_x=18, duration=60.0, start_time=5.0, end_time=25.0)
        self.assertEqual(wv.pad_x, 18)
        self.assertEqual(wv.duration, 60.0)
        self.assertEqual(wv.start_time, 5.0)
        self.assertEqual(wv.end_time, 25.0)

        # Atualização de range
        wv.set_range(10.0, 40.0)
        self.assertEqual(wv.start_time, 10.0)
        self.assertEqual(wv.end_time, 40.0)

        # Testar aplicação de máscara bruta
        from PIL import Image
        mask_img = Image.new("RGBA", (1200, 68), color=(255, 255, 255, 128))
        wv.set_raw_waveform(mask_img)
        self.assertIsNotNone(wv._raw_mask)

        # Testar limpeza
        wv.clear()
        self.assertIsNone(wv._raw_mask)


class TestTrimTabIntegration(unittest.TestCase):
    def setUp(self):
        self.app = MainWindow()
        self.app.withdraw()

    def tearDown(self):
        self.app.destroy()

    def test_trim_tab_components(self):
        self.app.switch_tab("trim")
        trim_feature = self.app.feature_instances.get("trim")
        self.assertIsInstance(trim_feature, TrimTab)

        # Configurar duração conhecida de 100s
        trim_feature.range_slider.set_duration(100.0, reset_range=True)
        trim_feature.waveform_view.set_duration(100.0)

        # Verificar presença dos componentes principais, miniaturas de vídeo e componente de forma de onda
        self.assertIsNotNone(trim_feature.range_slider)
        self.assertIsNotNone(trim_feature.start_entry)
        self.assertIsNotNone(trim_feature.end_entry)
        self.assertIsNotNone(trim_feature.selection_summary_lbl)
        self.assertIsNotNone(trim_feature.previews_frame)
        self.assertIsNotNone(trim_feature.start_preview_card)
        self.assertIsNotNone(trim_feature.end_preview_card)
        self.assertIsNotNone(trim_feature.start_preview_lbl)
        self.assertIsNotNone(trim_feature.end_preview_lbl)
        self.assertIsNotNone(trim_feature.waveform_view)

        # Simular alteração pelo slider
        trim_feature.range_slider.set_range(10.0, 40.0)
        trim_feature._on_slider_range_changed(10.0, 40.0)
        self.assertEqual(trim_feature.start_entry.get(), "00:00:10.000")
        self.assertEqual(trim_feature.end_entry.get(), "00:00:40.000")
        self.assertEqual(trim_feature.waveform_view.start_time, 10.0)
        self.assertEqual(trim_feature.waveform_view.end_time, 40.0)

        # Simular ajuste fino via botões (+1s e -2s)
        trim_feature._adjust_start(1.0)
        self.assertEqual(trim_feature.start_entry.get(), "00:00:11.000")
        self.assertEqual(trim_feature.waveform_view.start_time, 11.0)
        trim_feature._adjust_end(-2.0)
        self.assertEqual(trim_feature.end_entry.get(), "00:00:38.000")
        self.assertEqual(trim_feature.waveform_view.end_time, 38.0)

        # Resetar para zero e máximo
        trim_feature._reset_start_to_zero()
        self.assertEqual(trim_feature.start_entry.get(), "00:00:00.000")
        trim_feature._set_end_to_max()
        self.assertEqual(trim_feature.end_entry.get(), "00:01:40.000")

        # Testar aplicação de imagem na miniatura
        from PIL import Image
        sample_img = Image.new("RGB", (240, 135), color=(30, 144, 255))
        trim_feature._apply_preview_image(sample_img, is_start=True, req_id=trim_feature._start_preview_req_id, timestamp_sec=0.0)
        self.assertIn("00:00:00", trim_feature.start_preview_title.cget("text"))

        # Testar aplicação de forma de onda no WaveformView
        wave_sample = Image.new("RGBA", (1200, 68), color=(255, 255, 255, 200))
        trim_feature._waveform_req_id += 1
        trim_feature._apply_waveform_image(wave_sample, req_id=trim_feature._waveform_req_id)
        self.assertIsNotNone(trim_feature.waveform_view._raw_mask)


if __name__ == "__main__":
    unittest.main()

