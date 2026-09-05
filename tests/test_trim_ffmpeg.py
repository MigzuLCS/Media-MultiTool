import unittest
import subprocess
from pathlib import Path
from core.ffmpeg_manager import ffmpeg_manager
from core.transformer import media_transformer

class TestFFmpegTrimIntegration(unittest.TestCase):
    def setUp(self):
        if not ffmpeg_manager.is_available():
            self.skipTest("FFmpeg não disponível neste ambiente.")

    def test_ffmpeg_cut(self):
        test_dir = Path("tests/temp_media")
        test_dir.mkdir(parents=True, exist_ok=True)
        sample_vid = test_dir / "sample.mp4"
        trimmed_vid = test_dir / "sample_trimmed.mp4"

        try:
            if trimmed_vid.exists():
                trimmed_vid.unlink()

            ffmpeg_exe = ffmpeg_manager.get_ffmpeg_path()
            self.assertIsNotNone(ffmpeg_exe)

            # Gera vídeo de teste de 5 segundos
            cmd = [
                ffmpeg_exe, "-y",
                "-f", "lavfi", "-i", "testsrc=duration=5:size=320x240:rate=30",
                "-f", "lavfi", "-i", "sine=frequency=1000:duration=5",
                "-c:v", "libx264", "-c:a", "aac",
                str(sample_vid)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)

            # Valida metadados
            info = ffmpeg_manager.get_media_info(str(sample_vid))
            self.assertGreaterEqual(info.get("duration", 0), 4.5)

            # Corta de 00:00:01 a 00:00:03
            out = media_transformer.trim_video(
                input_path=str(sample_vid),
                output_path=str(trimmed_vid),
                start_time="00:00:01",
                end_time="00:00:03",
                lossless=False
            )
            self.assertTrue(Path(out).exists())

            trim_info = ffmpeg_manager.get_media_info(out)
            self.assertAlmostEqual(trim_info.get("duration", 0), 2.0, delta=0.5)

            # Valida extração de frame
            frame_img = ffmpeg_manager.extract_frame(str(sample_vid), 2.0, width=240, height=135)
            self.assertIsNotNone(frame_img)
            self.assertEqual(frame_img.size, (240, 135))

        finally:
            if sample_vid.exists():
                sample_vid.unlink()
            if trimmed_vid.exists():
                trimmed_vid.unlink()
            if test_dir.exists():
                test_dir.rmdir()

    def test_ffmpeg_audio_waveform(self):
        test_dir = Path("tests/temp_media")
        test_dir.mkdir(parents=True, exist_ok=True)
        sample_audio = test_dir / "sample_audio.wav"

        try:
            ffmpeg_exe = ffmpeg_manager.get_ffmpeg_path()
            self.assertIsNotNone(ffmpeg_exe)

            # Gera áudio de teste de 3 segundos com modulação de amplitude
            cmd = [
                ffmpeg_exe, "-y",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
                "-c:a", "pcm_s16le",
                str(sample_audio)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)

            # Extrai gráfico de onda sonora
            wave_img = ffmpeg_manager.extract_audio_waveform(str(sample_audio), width=600, height=120)
            self.assertIsNotNone(wave_img)
            self.assertEqual(wave_img.size, (600, 120))
            self.assertEqual(wave_img.mode, "RGB")

            # Valida cache na segunda chamada
            cached_img = ffmpeg_manager.extract_audio_waveform(str(sample_audio), width=600, height=120)
            self.assertIs(wave_img, cached_img)

        finally:
            if sample_audio.exists():
                sample_audio.unlink()
            if test_dir.exists():
                test_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
