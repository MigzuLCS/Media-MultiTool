import os
import sys
import shutil
import json
import re
import io
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from PIL import Image, ImageOps
from core.config import config
from core.paths import get_app_root


class FFmpegManager:
    """Gerencia a detecção, inspeção e execução de comandos FFmpeg e ffprobe."""

    def __init__(self):
        self.app_root = get_app_root()
        self.bin_dir = self.app_root / "bin"
        self._frame_cache = {}
        self._cache_lock = threading.Lock()

    def get_ffmpeg_path(self) -> Optional[str]:
        """Localiza o executável do ffmpeg."""
        # 1. Configuração salva pelo usuário
        saved = config.get("ffmpeg_path")
        if saved and Path(saved).exists():
            return str(saved)

        # 2. Pasta bin/ local do app
        local_exe = self.bin_dir / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
        if local_exe.exists():
            return str(local_exe)

        # 3. Variável PATH do sistema
        which_path = shutil.which("ffmpeg")
        if which_path:
            return which_path

        # 4. Locais comuns no Windows
        if sys.platform == "win32":
            common_paths = [
                Path("C:/ffmpeg/bin/ffmpeg.exe"),
                Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
                Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Links/ffmpeg.exe",
            ]
            for cp in common_paths:
                if cp.exists():
                    return str(cp)

        return None

    def get_ffprobe_path(self) -> Optional[str]:
        """Localiza o executável do ffprobe."""
        ffmpeg = self.get_ffmpeg_path()
        if ffmpeg:
            ffmpeg_p = Path(ffmpeg)
            sibling = ffmpeg_p.parent / ("ffprobe.exe" if sys.platform == "win32" else "ffprobe")
            if sibling.exists():
                return str(sibling)

        # Local bin
        local_exe = self.bin_dir / ("ffprobe.exe" if sys.platform == "win32" else "ffprobe")
        if local_exe.exists():
            return str(local_exe)

        which_path = shutil.which("ffprobe")
        if which_path:
            return which_path

        return None

    def is_available(self) -> bool:
        """Retorna True se ffmpeg estiver disponível no sistema."""
        return self.get_ffmpeg_path() is not None

    def get_media_info(self, file_path: str) -> Dict[str, Any]:
        """Usa ffprobe para extrair metadados detalhados de um arquivo de mídia."""
        ffprobe = self.get_ffprobe_path()
        if not ffprobe:
            # Fallback básico com os.path se ffprobe não estiver presente
            p = Path(file_path)
            size_mb = p.stat().st_size / (1024 * 1024) if p.exists() else 0
            return {
                "duration": 0.0,
                "duration_str": "00:00:00",
                "width": 0,
                "height": 0,
                "resolution": "Desconhecida",
                "size_mb": round(size_mb, 2),
                "format_name": p.suffix.replace(".", "").upper(),
                "has_video": False,
                "has_audio": False,
            }

        cmd = [
            ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]

        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NO_WINDOW

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creation_flags,
                check=True,
            )
            data = json.loads(res.stdout)
            fmt = data.get("format", {})
            duration = float(fmt.get("duration", 0.0))

            streams = data.get("streams", [])
            video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

            if duration <= 0.0:
                for s in streams:
                    d = float(s.get("duration", 0.0))
                    if d > duration:
                        duration = d

            width = int(video_stream.get("width", 0)) if video_stream else 0
            height = int(video_stream.get("height", 0)) if video_stream else 0
            size_bytes = int(fmt.get("size", Path(file_path).stat().st_size if Path(file_path).exists() else 0))

            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = int(duration % 60)
            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            return {
                "duration": duration,
                "duration_str": duration_str,
                "width": width,
                "height": height,
                "resolution": f"{width}x{height}" if width and height else "N/A",
                "size_mb": round(size_bytes / (1024 * 1024), 2),
                "format_name": fmt.get("format_name", ""),
                "has_video": video_stream is not None,
                "has_audio": audio_stream is not None,
                "video_codec": video_stream.get("codec_name") if video_stream else None,
                "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
            }
        except Exception as e:
            p = Path(file_path)
            size_mb = p.stat().st_size / (1024 * 1024) if p.exists() else 0
            return {
                "duration": 0.0,
                "duration_str": "00:00:00",
                "width": 0,
                "height": 0,
                "resolution": "Erro ao ler",
                "size_mb": round(size_mb, 2),
                "format_name": p.suffix.replace(".", "").upper(),
                "has_video": False,
                "has_audio": False,
                "error": str(e),
            }

    def run_ffmpeg(
        self,
        args: list,
        total_duration: float = 0.0,
        on_progress: Optional[Callable[[float, str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> bool:
        """
        Executa comando ffmpeg com leitura de progresso em tempo real e suporte a cancelamento.
        Args:
            args: Lista de argumentos (sem o executável ffmpeg no início).
            total_duration: Duração esperada em segundos para cálculo percentual.
            on_progress: Callback recebendo (progresso_0_a_1, texto_status).
            cancel_event: threading.Event que, se setado, aborta a execução.
        """
        ffmpeg = self.get_ffmpeg_path()
        if not ffmpeg:
            raise RuntimeError("FFmpeg não encontrado no sistema!")

        full_cmd = [ffmpeg, "-y", "-progress", "pipe:1"] + args

        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NO_WINDOW

        proc = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=creation_flags,
        )

        stderr_lines = []

        def _drain_stderr():
            try:
                for sline in iter(proc.stderr.readline, ""):
                    stderr_lines.append(sline)
            except Exception:
                pass

        err_thread = threading.Thread(target=_drain_stderr, daemon=True)
        err_thread.start()

        time_pattern = re.compile(r"out_time_ms=(\d+)")
        progress_done = False

        try:
            while True:
                if cancel_event and cancel_event.is_set():
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    if on_progress:
                        on_progress(0.0, "Operação cancelada.")
                    return False

                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break

                line = line.strip()
                match = time_pattern.search(line)
                if match and total_duration > 0:
                    current_us = int(match.group(1))
                    current_sec = current_us / 1_000_000.0
                    frac = min(1.0, max(0.0, current_sec / total_duration))
                    if on_progress:
                        pct = int(frac * 100)
                        on_progress(frac, f"Processando... {pct}% ({current_sec:.1f}s / {total_duration:.1f}s)")

                if "progress=end" in line:
                    progress_done = True

            retcode = proc.wait()
            err_thread.join(timeout=1.0)
            if retcode == 0:
                if on_progress:
                    on_progress(1.0, "Concluído com sucesso!")
                return True
            else:
                stderr_output = "".join(stderr_lines)
                raise RuntimeError(f"FFmpeg encerrou com código {retcode}: {stderr_output[-400:]}")
        finally:
            if proc.poll() is None:
                proc.kill()
            try:
                proc.stdout.close()
            except Exception:
                pass
            try:
                proc.stderr.close()
            except Exception:
                pass

    def extract_frame(
        self,
        file_path: str,
        timestamp_sec: float,
        width: int = 240,
        height: int = 135,
    ) -> Optional[Image.Image]:
        """Extrai um frame único de um arquivo de vídeo em uma posição de tempo específica."""
        ffmpeg = self.get_ffmpeg_path()
        if not ffmpeg or not Path(file_path).exists():
            return None

        cache_key = (str(file_path), round(max(0.0, timestamp_sec), 1), width, height)
        with self._cache_lock:
            if cache_key in self._frame_cache:
                return self._frame_cache[cache_key]

        scale_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2"
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

        s = max(0.0, timestamp_sec)
        candidates = [s]
        if s > 0.3:
            candidates.append(max(0.0, s - 0.25))

        for target_time in candidates:
            h = int(target_time // 3600)
            m = int((target_time % 3600) // 60)
            sec = target_time % 60
            time_str = f"{h:02d}:{m:02d}:{sec:05.2f}"

            cmd = [
                ffmpeg,
                "-ss", time_str,
                "-i", file_path,
                "-frames:v", "1",
                "-vf", scale_filter,
                "-f", "image2pipe",
                "-vcodec", "mjpeg",
                "pipe:1",
            ]

            try:
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    creationflags=creation_flags,
                    check=False,
                    timeout=3.5,
                )
                if res.stdout:
                    raw_img = Image.open(io.BytesIO(res.stdout)).convert("RGB")
                    img = ImageOps.pad(raw_img, (width, height), color=(18, 18, 18))
                    with self._cache_lock:
                        if len(self._frame_cache) > 120:
                            keys = list(self._frame_cache.keys())[:60]
                            for k in keys:
                                del self._frame_cache[k]
                        self._frame_cache[cache_key] = img
                    return img
            except Exception:
                continue

        return None

    def extract_audio_waveform(
        self,
        file_path: str,
        width: int = 700,
        height: int = 135,
        color: str = "#3B82F6",
        raw_rgba: bool = False,
    ) -> Optional[Image.Image]:
        """Gera um gráfico visual da forma de onda / variação de volume do áudio usando showwavespic."""
        ffmpeg = self.get_ffmpeg_path()
        if not ffmpeg or not Path(file_path).exists():
            return None

        cache_key = (str(file_path), "waveform_raw" if raw_rgba else "waveform", width, height, color)
        with self._cache_lock:
            if cache_key in self._frame_cache:
                return self._frame_cache[cache_key]

        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        cmd = [
            ffmpeg,
            "-vn",
            "-i", str(file_path),
            "-filter_complex", f"[0:a]aformat=channel_layouts=mono,showwavespic=s={width}x{height}:colors={color}[v]",
            "-map", "[v]",
            "-frames:v", "1",
            "-f", "image2pipe",
            "-vcodec", "png",
            "pipe:1",
        ]

        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
                check=False,
                timeout=10.0,
            )
            if res.stdout:
                raw_img = Image.open(io.BytesIO(res.stdout)).convert("RGBA")
                if raw_rgba:
                    with self._cache_lock:
                        if len(self._frame_cache) > 120:
                            keys = list(self._frame_cache.keys())[:60]
                            for k in keys:
                                del self._frame_cache[k]
                        self._frame_cache[cache_key] = raw_img
                    return raw_img

                # Compor sobre fundo escuro elegante
                bg = Image.new("RGBA", (width, height), (20, 20, 24, 255))
                final_img = Image.alpha_composite(bg, raw_img).convert("RGB")
                with self._cache_lock:
                    if len(self._frame_cache) > 120:
                        keys = list(self._frame_cache.keys())[:60]
                        for k in keys:
                            del self._frame_cache[k]
                    self._frame_cache[cache_key] = final_img
                return final_img
        except Exception:
            pass

        return None


ffmpeg_manager = FFmpegManager()
