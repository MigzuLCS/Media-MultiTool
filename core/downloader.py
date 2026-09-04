import os
import sys
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any
import yt_dlp

from core.ffmpeg_manager import ffmpeg_manager
from core.config import config


class YouTubeDownloader:
    """Interface moderna e segura para download de mídias via yt-dlp."""

    def __init__(self):
        pass

    def get_info(self, url: str) -> Dict[str, Any]:
        """Obtém metadados do vídeo sem realizar download."""
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", "Sem título"),
                "duration": info.get("duration", 0),
                "uploader": info.get("uploader", "Desconhecido"),
                "thumbnail": info.get("thumbnail", ""),
                "view_count": info.get("view_count", 0),
            }

    def download(
        self,
        url: str,
        output_dir: str,
        mode: str = "video",
        quality: str = "best",
        on_progress: Optional[Callable[[float, str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> str:
        """
        Realiza o download de vídeo ou extração de áudio.
        Args:
            url: URL do YouTube / plataforma.
            output_dir: Pasta de destino.
            mode: 'video' ou 'audio'.
            quality: 'best', '1080p', '720p', etc.
            on_progress: Callback para barra de progresso (frac, mensagem).
            cancel_event: Evento para cancelamento.
        Returns:
            Caminho do arquivo gerado ou mensagem de sucesso.
        """
        ffmpeg_bin = ffmpeg_manager.get_ffmpeg_path()
        out_template = str(Path(output_dir) / "%(title)s.%(ext)s")

        def hook(d):
            if cancel_event and cancel_event.is_set():
                raise Exception("Download cancelado pelo usuário.")

            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                speed = d.get("speed") or 0
                eta = d.get("eta") or 0

                frac = (downloaded / total) if total > 0 else 0.0
                speed_str = f"{speed / (1024 * 1024):.1f} MB/s" if speed else "--"
                eta_str = f"{eta}s" if eta else "--"
                pct = int(frac * 100)

                if on_progress:
                    on_progress(
                        frac * 0.95,
                        f"Baixando: {pct}% | {speed_str} | Restante: {eta_str}"
                    )
            elif status == "finished":
                if on_progress:
                    on_progress(0.98, "Convertendo / unindo faixas de mídia...")

        ydl_opts: Dict[str, Any] = {
            "outtmpl": out_template,
            "progress_hooks": [hook],
            "quiet": True,
            "no_warnings": True,
        }

        if ffmpeg_bin:
            ydl_opts["ffmpeg_location"] = str(Path(ffmpeg_bin).parent)

        if mode == "audio":
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            })
        else:
            # Mode: Video
            if quality == "1080p":
                fmt = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
            elif quality == "720p":
                fmt = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
            elif quality == "480p":
                fmt = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
            else:
                fmt = "bestvideo+bestaudio/best"

            ydl_opts.update({
                "format": fmt,
                "merge_output_format": "mp4",
            })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if mode == "audio":
                filename = str(Path(filename).with_suffix(".mp3"))
            if on_progress:
                on_progress(1.0, "Download concluído com sucesso!")
            return filename


youtube_downloader = YouTubeDownloader()
