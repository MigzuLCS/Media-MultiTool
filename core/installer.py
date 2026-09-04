import os
import sys
import shutil
import zipfile
import urllib.request
import threading
from pathlib import Path
from typing import Optional, Callable


class FFmpegInstaller:
    """Assistente para instalação ou download automático do FFmpeg no Windows."""

    FFMPEG_RELEASE_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

    def __init__(self):
        self.app_root = Path(__file__).resolve().parent.parent
        self.bin_dir = self.app_root / "bin"

    def download_and_extract(
        self,
        on_progress: Optional[Callable[[float, str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> bool:
        """
        Baixa a versão estática oficial do FFmpeg para Windows (BtbN)
        e extrai ffmpeg.exe e ffprobe.exe diretamente para mediamultitool/bin/.
        """
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        zip_path = self.bin_dir / "ffmpeg_temp.zip"

        try:
            if on_progress:
                on_progress(0.05, "Iniciando download do FFmpeg oficial...")

            req = urllib.request.Request(
                self.FFMPEG_RELEASE_URL,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )

            with urllib.request.urlopen(req, timeout=30) as response, open(zip_path, "wb") as out_file:
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                block_size = 1024 * 64  # 64 KB

                while True:
                    if cancel_event and cancel_event.is_set():
                        if on_progress:
                            on_progress(0.0, "Download cancelado.")
                        if zip_path.exists():
                            zip_path.unlink(missing_ok=True)
                        return False

                    buffer = response.read(block_size)
                    if not buffer:
                        break

                    out_file.write(buffer)
                    downloaded += len(buffer)

                    if total_size > 0 and on_progress:
                        frac = downloaded / total_size
                        mb_down = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        on_progress(frac * 0.8, f"Baixando FFmpeg... {mb_down:.1f}MB / {mb_total:.1f}MB ({int(frac * 100)}%)")

            if on_progress:
                on_progress(0.85, "Extraindo executáveis (ffmpeg.exe, ffprobe.exe)...")

            # Extrair apenas ffmpeg.exe e ffprobe.exe
            with zipfile.ZipFile(zip_path, "r") as z:
                for file_info in z.infolist():
                    name = file_info.filename
                    if name.endswith("ffmpeg.exe"):
                        with z.open(file_info) as source, open(self.bin_dir / "ffmpeg.exe", "wb") as target:
                            shutil.copyfileobj(source, target)
                    elif name.endswith("ffprobe.exe"):
                        with z.open(file_info) as source, open(self.bin_dir / "ffprobe.exe", "wb") as target:
                            shutil.copyfileobj(source, target)

            # Limpar zip temporário
            if zip_path.exists():
                zip_path.unlink(missing_ok=True)

            ffmpeg_exe = self.bin_dir / "ffmpeg.exe"
            ffprobe_exe = self.bin_dir / "ffprobe.exe"

            if ffmpeg_exe.exists() and ffprobe_exe.exists():
                if on_progress:
                    on_progress(1.0, "FFmpeg instalado com sucesso em bin/!")
                return True
            else:
                raise RuntimeError("Falha ao extrair os executáveis do pacote compactado.")

        except Exception as e:
            if zip_path.exists():
                zip_path.unlink(missing_ok=True)
            raise RuntimeError(f"Erro ao baixar FFmpeg: {e}")


ffmpeg_installer = FFmpegInstaller()
