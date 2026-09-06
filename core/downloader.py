import os
import sys
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import yt_dlp

from core.ffmpeg_manager import ffmpeg_manager
from core.config import config


class YouTubeDownloader:
    """Interface moderna e segura para download de mídias via yt-dlp."""

    def __init__(self):
        pass

    @staticmethod
    def clean_url(url: str) -> str:
        """
        Remove parâmetros de playlist, mix e rastreamento de URLs do YouTube quando há um vídeo individual especificado.
        Isso evita downloads em loops infinitos causados por listas automáticas de mix (ex: YouTube Mix, list=RD...).
        """
        if not url or not isinstance(url, str):
            return ""
        url = url.strip()
        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                parsed = urlparse("https://" + url)

            netloc = parsed.netloc.lower()
            yt_domains = (
                "youtube.com",
                "www.youtube.com",
                "m.youtube.com",
                "music.youtube.com",
                "gaming.youtube.com",
                "youtu.be",
            )
            is_youtube = any(netloc == d or netloc.endswith("." + d) for d in yt_domains)
            if is_youtube:
                query = parse_qs(parsed.query, keep_blank_values=True)
                path_parts = [p for p in parsed.path.split("/") if p]

                # Identifica se a URL aponta para um vídeo individual
                has_video = False
                if "v" in query and query["v"]:
                    has_video = True
                elif "youtu.be" in netloc and path_parts:
                    has_video = True
                elif path_parts and path_parts[0] in ("shorts", "live", "embed") and len(path_parts) > 1:
                    has_video = True

                if has_video:
                    # Remove parâmetros de playlist, mix e navegação contínua
                    params_to_remove = {"list", "index", "start_radio", "pp", "si", "feature"}
                    filtered_query = {k: v for k, v in query.items() if k not in params_to_remove}
                    new_query = urlencode(filtered_query, doseq=True)
                    return urlunparse(parsed._replace(query=new_query))
        except Exception:
            pass
        return url

    @staticmethod
    def is_playlist_url(url: str) -> bool:
        """Verifica se a URL aponta exclusivamente para uma playlist sem vídeo individual."""
        if not url or not isinstance(url, str):
            return False
        try:
            parsed = urlparse(url.strip())
            if not parsed.scheme:
                parsed = urlparse("https://" + url.strip())
            path = parsed.path.lower().rstrip("/")
            if path == "/playlist" or path.endswith("/playlist"):
                return True
        except Exception:
            pass
        return False

    def get_info(self, url: str) -> Dict[str, Any]:
        """Obtém metadados do vídeo sem realizar download."""
        clean_target = self.clean_url(url)
        if self.is_playlist_url(url):
            raise ValueError("O link informado aponta para uma playlist. Por favor, insira o link de um vídeo individual.")

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_target, download=False)
            if info and "entries" in info:
                entries = [e for e in info.get("entries", []) if e]
                if entries:
                    info = entries[0]
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
        clean_target = self.clean_url(url)
        if self.is_playlist_url(url):
            raise ValueError("O link informado aponta para uma playlist completa. Por favor, utilize o link de um vídeo ou música individual.")

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
            "noplaylist": True,
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
            info = ydl.extract_info(clean_target, download=True)
            if info and "entries" in info:
                entries = [e for e in info.get("entries", []) if e]
                if entries:
                    info = entries[0]
            filename = ydl.prepare_filename(info)
            if mode == "audio":
                filename = str(Path(filename).with_suffix(".mp3"))
            if on_progress:
                on_progress(1.0, "Download concluído com sucesso!")
            return filename


youtube_downloader = YouTubeDownloader()
