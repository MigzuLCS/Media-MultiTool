import os
import sys
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import yt_dlp

from core.ffmpeg_manager import ffmpeg_manager
from core.config import config
from core.metadata_enricher import (
    spotify_resolver,
    genre_tag_resolver,
    audio_tagger,
    clean_title_for_search,
)


class YouTubeDownloader:
    """Interface moderna e segura para download de mídias via yt-dlp e Spotify."""

    def __init__(self):
        pass

    @staticmethod
    def detect_platform(url: str) -> str:
        """Identifica a plataforma com base na URL informada."""
        if not url or not isinstance(url, str):
            return "generic"
        u = url.lower().strip()
        if "open.spotify.com" in u or "spotify.com" in u:
            return "spotify"
        if any(d in u for d in ("youtube.com", "youtu.be", "music.youtube.com")):
            return "youtube"
        if "tiktok.com" in u:
            return "tiktok"
        if "instagram.com" in u:
            return "instagram"
        if any(d in u for d in ("twitter.com", "x.com")):
            return "twitter_x"
        if "reddit.com" in u:
            return "reddit"
        if "twitch.tv" in u:
            return "twitch"
        if "vimeo.com" in u:
            return "vimeo"
        if "soundcloud.com" in u:
            return "soundcloud"
        return "generic"

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

    @staticmethod
    def has_playlist(url: str) -> bool:
        """Verifica se a URL contém parâmetros de playlist ou mix."""
        if not url or not isinstance(url, str):
            return False
        u = url.lower().strip()
        return "list=" in u or "/playlist" in u

    @staticmethod
    def is_mix_playlist(url: str) -> bool:
        """Verifica se a URL aponta para um mix/rádio contínuo do YouTube (ex: list=RD...)."""
        if not url or not isinstance(url, str):
            return False
        u = url.lower().strip()
        return "list=rd" in u or "start_radio=1" in u


    def get_info(self, url: str) -> Dict[str, Any]:
        """Obtém metadados do vídeo/áudio sem realizar download."""
        platform = self.detect_platform(url)

        if platform == "spotify":
            sp_meta = spotify_resolver.resolve(url)
            return {
                "title": f"{sp_meta['artist']} - {sp_meta['title']}",
                "duration": sp_meta.get("duration", 0),
                "uploader": sp_meta.get("artist", "Spotify"),
                "thumbnail": sp_meta.get("cover_url", ""),
                "view_count": 0,
            }

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

    def _resolve_best_audio_candidate(
        self,
        query: str,
        expected_duration: int = 0,
        cancel_event: Optional[threading.Event] = None
    ) -> str:
        """
        Pesquisa faixas no YouTube e seleciona a mais confiável baseada na duração e canal Topic.
        """
        search_target = f"ytsearch5:{query}"
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if cancel_event and cancel_event.is_set():
                raise Exception("Operação cancelada pelo usuário.")
            search_res = ydl.extract_info(search_target, download=False)
            entries = search_res.get("entries", []) if search_res else []
            entries = [e for e in entries if e]

            if not entries:
                raise RuntimeError(f"Nenhum áudio correspondente foi encontrado para: '{query}'")

            best_entry = entries[0]
            if expected_duration > 0 and len(entries) > 1:
                # Ordena por menor discrepância de duração e preferência por canais "Topic" / "Official"
                def score(entry):
                    dur = entry.get("duration") or 0
                    diff = abs(dur - expected_duration) if dur > 0 else 999
                    uploader = (entry.get("uploader") or "").lower()
                    title = (entry.get("title") or "").lower()
                    is_topic = 1 if "topic" in uploader else 0
                    is_audio = 1 if "audio" in title or "official audio" in title else 0
                    return (diff, -is_topic, -is_audio)

                entries.sort(key=score)
                best_entry = entries[0]

            return best_entry.get("webpage_url") or best_entry.get("url") or f"https://www.youtube.com/watch?v={best_entry.get('id')}"

    def download(
        self,
        url: str,
        output_dir: str,
        mode: str = "video",
        quality: str = "best",
        auto_tag: bool = True,
        is_playlist: bool = False,
        on_progress: Optional[Callable[[float, str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> str:
        """
        Realiza o download de vídeo ou extração de áudio de múltiplas plataformas (incluindo Playlists e Mix).
        Args:
            url: URL da mídia (YouTube, Spotify, TikTok, etc.).
            output_dir: Pasta de destino.
            mode: 'video' ou 'audio'.
            quality: 'best', '1080p', '720p', etc.
            auto_tag: Se True, identifica e injeta metadados (gênero, artista, capa) via FFmpeg.
            is_playlist: Se True, baixa todas as faixas da playlist (com limite de 20 para Mix RD).
            on_progress: Callback para barra de progresso (frac, mensagem).
            cancel_event: Evento para cancelamento.
        Returns:
            Caminho do arquivo ou pasta gerada.
        """
        platform = self.detect_platform(url)
        is_mix = self.is_mix_playlist(url)

        # Se o usuário solicitou playlist ou a URL for puramente de playlist
        if platform == "youtube" and (is_playlist or self.is_playlist_url(url)):
            is_playlist = True
            clean_target = url.strip()
        else:
            clean_target = self.clean_url(url)

        ffmpeg_bin = ffmpeg_manager.get_ffmpeg_path()
        spotify_info: Optional[Dict[str, Any]] = None
        target_download_url = clean_target

        # 1. Tratamento específico para Spotify
        if platform == "spotify":
            if on_progress:
                on_progress(0.05, "Extraindo informações da faixa no Spotify...")

            spotify_info = spotify_resolver.resolve(url)
            mode = "audio"  # Spotify sempre baixa áudio

            sp_title = spotify_info["title"]
            sp_artist = spotify_info["artist"]
            expected_dur = spotify_info.get("duration", 0)

            if on_progress:
                on_progress(0.12, f"Buscando áudio oficial de '{sp_title}' ({sp_artist})...")

            search_query = f"{sp_artist} - {sp_title} Official Audio"
            target_download_url = self._resolve_best_audio_candidate(
                search_query,
                expected_duration=expected_dur,
                cancel_event=cancel_event
            )

        # 2. Configurações do yt-dlp
        if spotify_info:
            safe_title = f"{spotify_info['artist']} - {spotify_info['title']}"
            safe_title = "".join(c for c in safe_title if c not in '<>:"/\\|?*')
            out_template = str(Path(output_dir) / f"{safe_title}.%(ext)s")
        elif is_playlist:
            out_template = str(Path(output_dir) / "%(playlist_index&{:02d} - |)s%(title)s.%(ext)s")
        else:
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
                    if is_playlist:
                        item_idx = d.get("playlist_index") or 1
                        item_total = d.get("n_entries") or (20 if is_mix else 0)
                        overall_frac = ((item_idx - 1) + frac) / (item_total if item_total > 0 else 20)
                        tot_str = str(item_total) if item_total > 0 else "?"
                        on_progress(
                            min(overall_frac, 0.95),
                            f"Faixa {item_idx}/{tot_str} ({pct}%): {speed_str} | Restante: {eta_str}"
                        )
                    else:
                        prog_val = 0.15 + (frac * 0.70) if platform == "spotify" else (frac * 0.85)
                        on_progress(
                            min(prog_val, 0.88),
                            f"Baixando: {pct}% | {speed_str} | Restante: {eta_str}"
                        )
            elif status == "finished":
                if on_progress:
                    on_progress(0.90, "Convertendo / unindo faixas de mídia...")

        ydl_opts: Dict[str, Any] = {
            "outtmpl": out_template,
            "progress_hooks": [hook],
            "quiet": True,
            "no_warnings": True,
            "noplaylist": not is_playlist,
        }

        if is_playlist and is_mix:
            # Limita a 20 músicas no caso de Mix RD contínuo
            ydl_opts["playlistend"] = 20

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
            if cancel_event and cancel_event.is_set():
                raise Exception("Download cancelado pelo usuário.")

            info = ydl.extract_info(target_download_url, download=True)

        # 3. Pós-processamento para Playlist completa
        if is_playlist:
            entries = info.get("entries", []) if info else []
            entries = [e for e in entries if e]
            saved_count = 0

            for e in entries:
                if cancel_event and cancel_event.is_set():
                    break
                try:
                    f = ydl.prepare_filename(e)
                    if mode == "audio":
                        f = str(Path(f).with_suffix(".mp3"))
                    p = Path(f)

                    if p.exists():
                        # Renomeia para remover ruídos do nome
                        clean_stem = clean_title_for_search(p.stem)
                        if clean_stem:
                            safe_stem = "".join(c for c in clean_stem if c not in '<>:"/\\|?*')
                            new_p = p.with_name(f"{safe_stem}{p.suffix}")
                            if new_p != p:
                                if new_p.exists():
                                    new_p.unlink()
                                p.rename(new_p)
                                p = new_p
                                f = str(p)

                        # Auto-tagging
                        if mode == "audio" and auto_tag:
                            raw_t = e.get("title") or ""
                            clean_t = clean_title_for_search(raw_t)
                            mb_info = genre_tag_resolver.query_musicbrainz(
                                title=clean_t,
                                artist=e.get("artist") or "",
                                raw_title=raw_t,
                                categories=e.get("categories") or [],
                                tags=e.get("tags") or [],
                            )
                            audio_tagger.tag_mp3(
                                mp3_path=f,
                                title=clean_t or raw_t,
                                artist=mb_info.get("artist") or e.get("artist") or (clean_t.split(" - ")[0].strip() if " - " in clean_t else (e.get("uploader") or "")),
                                album=mb_info.get("album") or e.get("album") or (clean_t.split(" - ")[0].strip() if " - " in clean_t else ""),
                                genre=mb_info.get("genre") or "",
                                date=mb_info.get("date") or "",
                                cover_url=e.get("thumbnail") or "",
                            )
                        saved_count += 1
                except Exception:
                    pass

            if on_progress:
                on_progress(1.0, f"Download da playlist concluído! {saved_count} faixas salvas com sucesso.")
            return output_dir

        # 4. Pós-processamento para Mídia Individual
        if info and "entries" in info:
            entries = [e for e in info.get("entries", []) if e]
            if entries:
                info = entries[0]
        filename = ydl.prepare_filename(info)
        if mode == "audio":
            filename = str(Path(filename).with_suffix(".mp3"))

        # Renomeia o arquivo físico para remover ruídos do nome (ex: " - Original Game Soundtrack")
        if Path(filename).exists():
            clean_stem = clean_title_for_search(Path(filename).stem)
            if clean_stem:
                safe_stem = "".join(c for c in clean_stem if c not in '<>:"/\\|?*')
                clean_path = Path(filename).with_name(f"{safe_stem}{Path(filename).suffix}")
                if clean_path != Path(filename):
                    try:
                        if clean_path.exists():
                            clean_path.unlink()
                        Path(filename).rename(clean_path)
                        filename = str(clean_path)
                    except Exception:
                        pass

        # Enriquecimento de Metadados e Gênero via FFmpeg
        if mode == "audio" and auto_tag and Path(filename).exists():
            if on_progress:
                on_progress(0.94, "Identificando gênero e tags ID3...")

            tag_title = ""
            tag_artist = ""
            tag_album = ""
            tag_genre = ""
            tag_date = ""
            tag_cover = ""

            if spotify_info:
                tag_title = spotify_info.get("title", "")
                tag_artist = spotify_info.get("artist", "")
                tag_album = spotify_info.get("album", "")
                tag_date = spotify_info.get("release_date", "")
                tag_cover = spotify_info.get("cover_url", "")

                # Busca gênero no MusicBrainz ou deduz
                mb_info = genre_tag_resolver.query_musicbrainz(
                    title=tag_title,
                    artist=tag_artist,
                    raw_title=f"{tag_artist} - {tag_title}",
                )
                tag_genre = mb_info.get("genre", "")
                if not tag_album:
                    tag_album = mb_info.get("album", "")
                if not tag_date:
                    tag_date = mb_info.get("date", "")
            else:
                # YouTube ou outra plataforma web
                raw_title = info.get("title") or info.get("track") or ""
                official_artist = info.get("artist") or ""
                uploader = info.get("uploader") or ""
                clean_t = clean_title_for_search(raw_title)

                mb_info = genre_tag_resolver.query_musicbrainz(
                    title=clean_t,
                    artist=official_artist,
                    raw_title=raw_title,
                    categories=info.get("categories") or [],
                    tags=info.get("tags") or [],
                )

                tag_title = clean_t or raw_title
                tag_artist = mb_info.get("artist") or official_artist or (clean_t.split(" - ")[0].strip() if " - " in clean_t else uploader)
                tag_album = mb_info.get("album") or info.get("album") or (clean_t.split(" - ")[0].strip() if " - " in clean_t else "")
                tag_genre = mb_info.get("genre") or info.get("genre") or ""
                tag_date = mb_info.get("date") or (str(info.get("release_year")) if info.get("release_year") else "")
                tag_cover = info.get("thumbnail") or ""

            if on_progress and tag_genre:
                on_progress(0.97, f"Gravando tags ID3: Gênero [{tag_genre}]...")

            audio_tagger.tag_mp3(
                mp3_path=filename,
                title=tag_title,
                artist=tag_artist,
                album=tag_album,
                genre=tag_genre,
                date=tag_date,
                cover_url=tag_cover,
            )

        if on_progress:
            on_progress(1.0, "Download e processamento concluídos com sucesso!")

        return filename


# Instância global e aliases
youtube_downloader = YouTubeDownloader()
media_downloader = youtube_downloader
MediaDownloader = YouTubeDownloader
