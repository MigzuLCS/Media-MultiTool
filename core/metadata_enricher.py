import os
import sys
import re
import json
import urllib.request
import urllib.parse
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

from core.ffmpeg_manager import ffmpeg_manager


def clean_title_for_search(raw_title: str) -> str:
    """
    Remove ruídos comuns de títulos de vídeos (ex: [OST], Original Game Soundtrack, 1 Hour, Official Audio, etc.)
    para permitir buscas precisas em bases de metadados e nomeação limpa de arquivos.
    """
    if not raw_title:
        return ""

    title = raw_title.strip()

    # 1. Padrões entre colchetes ou parênteses
    bracket_patterns = [
        r"\[\s*(original\s+)?(video\s+game\s+|game\s+)?(soundtrack|score|ost|o\.s\.t\.)\s*\]",
        r"\(\s*(original\s+)?(video\s+game\s+|game\s+)?(soundtrack|score|ost|o\.s\.t\.)\s*\)",
        r"\[\s*(official\s+)?(music\s+)?(video|audio|visualizer|lyric\s+video|track)\s*\]",
        r"\(\s*(official\s+)?(music\s+)?(video|audio|visualizer|lyric\s+video|track)\s*\)",
        r"\[\s*(1\s*hour|10\s*hours|loop|extended(\s+version)?|hq|hd|4k|60fps|remaster(ed)?)\s*\]",
        r"\(\s*(1\s*hour|10\s*hours|loop|extended(\s+version)?|hq|hd|4k|60fps|remaster(ed)?)\s*\)",
        r"\[\s*(lyrics?|letra|audio)\s*\]",
        r"\(\s*(lyrics?|letra|audio)\s*\)",
        r"【.*?】",
        r"『.*?』",
    ]
    for pat in bracket_patterns:
        title = re.sub(pat, "", title, flags=re.IGNORECASE)

    # 2. Cláusulas finais ou iniciais separadas por traços, barras ou pipes (ex: ' - Original Game Soundtrack')
    clause_patterns = [
        r"\s*[-–—|]\s*(original\s+)?(video\s+game\s+|game\s+)?(soundtrack|score|ost|o\.s\.t\.)\s*$",
        r"\s*[-–—|]\s*(official\s+)?(music\s+video|audio|video|visualizer|lyrics?)\s*$",
        r"\s*[-–—|]\s*(extended(\s+version)?|1\s*hour(\s+loop)?|remaster(ed)?)\s*$",
        r"^(original\s+)?(video\s+game\s+|game\s+)?(soundtrack|score|ost|o\.s\.t\.)\s*[-–—|]\s*",
    ]
    for pat in clause_patterns:
        title = re.sub(pat, "", title, flags=re.IGNORECASE)

    # 3. Padrões de termos isolados
    title = re.sub(
        r"\b(full\s+soundtrack|original\s+game\s+soundtrack|video\s+game\s+soundtrack|game\s+soundtrack|original\s+soundtrack|original\s+score)\b",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(r"\b(official\s+music\s+video|official\s+audio|official\s+video)\b", "", title, flags=re.IGNORECASE)

    # 4. Limpeza de múltiplos espaços e traços
    title = re.sub(r"\s*[-–—]\s*[-–—]\s*", " - ", title)
    title = re.sub(r"\s+", " ", title).strip(" -–—|")
    return title


def infer_genre_from_text(
    title: str = "",
    raw_title: str = "",
    categories: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
) -> str:
    """
    Deduz o gênero musical com base no contexto do título, tags e categoria do vídeo/mídia.
    Essencial para trilhas de jogos (OSTs), chiptunes, lo-fi, etc., mesmo quando não catalogadas no MusicBrainz.
    """
    combined = f"{title} {raw_title} {' '.join(tags or [])} {' '.join(categories or [])}".lower()

    # Trilhas de Jogos
    is_game = (
        any(k in combined for k in (
            "original game soundtrack", "video game soundtrack", "game ost",
            "game soundtrack", "vgm", "video game music", "gamerip", "game rip"
        ))
        or (categories and any(c.lower() == "gaming" for c in categories) and any(k in combined for k in ("soundtrack", "ost", "theme", "bgm")))
    )

    if is_game:
        if any(k in combined for k in ("electronic", "techno", "house", "edm", "dance")):
            return "Electronic / Game Soundtrack"
        if any(k in combined for k in ("chiptune", "8-bit", "16-bit", "8bit", "16bit")):
            return "Chiptune / Game Soundtrack"
        if any(k in combined for k in ("orchestral", "symphon", "orchestra")):
            return "Orchestral / Game Soundtrack"
        if any(k in combined for k in ("rock", "metal")):
            return "Rock / Game Soundtrack"
        if any(k in combined for k in ("ambient", "atmospheric")):
            return "Ambient / Game Soundtrack"
        return "Video Game Music"

    if any(k in combined for k in ("chiptune", "8-bit", "16-bit", "8bit", "16bit")):
        return "Chiptune / 8-Bit"

    if any(k in combined for k in ("lo-fi", "lofi", "chillhop")):
        return "Lo-Fi / Chillhop"

    if any(k in combined for k in ("synthwave", "retrowave", "cyberpunk", "vaporwave")):
        return "Synthwave"

    if any(k in combined for k in ("ambient", "atmospheric", "meditation")):
        return "Ambient"

    if any(k in combined for k in ("soundtrack", "ost", "o.s.t.", "original score", "bgm")):
        return "Soundtrack"

    if any(k in combined for k in ("rock", "hard rock", "heavy metal", "punk")):
        return "Rock"

    if any(k in combined for k in ("electronic", "techno", "trance", "house", "dubstep")):
        return "Electronic"

    return ""



class SpotifyResolver:
    """
    Extrai metadados de links do Spotify sem a necessidade de chaves de API pagas ou autenticação.
    Utiliza uma combinação da API pública oEmbed e scraping dos metadados OpenGraph da página.
    """

    USER_AGENT = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"

    @staticmethod
    def is_spotify_url(url: str) -> bool:
        if not url:
            return False
        return "open.spotify.com" in url.lower() or "spotify.com" in url.lower()

    @staticmethod
    def extract_track_id(url: str) -> Optional[str]:
        if not url:
            return None
        # Suporta open.spotify.com/track/ID, open.spotify.com/intl-pt/track/ID, spotify:track:ID, etc.
        match = re.search(r"(?:spotify\.com/(?:[a-zA-Z0-9\-_]+/)?track/|spotify:track:)([a-zA-Z0-9]+)", url)
        if match:
            return match.group(1)
        return None

    def resolve(self, url: str) -> Dict[str, Any]:
        """
        Retorna informações da faixa:
        {
            "title": str,
            "artist": str,
            "album": str,
            "duration": int (segundos),
            "cover_url": str,
            "release_date": str
        }
        """
        track_id = self.extract_track_id(url)
        if not track_id:
            raise ValueError("URL do Spotify inválida ou não aponta para uma faixa de música (track).")

        clean_url = f"https://open.spotify.com/track/{track_id}"

        metadata: Dict[str, Any] = {
            "title": "",
            "artist": "",
            "album": "",
            "duration": 0,
            "cover_url": "",
            "release_date": "",
        }

        # 1. Tentar obter metadados OpenGraph via página HTML pública com User-Agent de bot
        try:
            req = urllib.request.Request(
                clean_url,
                headers={"User-Agent": self.USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="replace")

                # Extrai og:title ou twitter:title
                og_title_match = re.search(r'<meta\s+(?:property|name)="(?:og:title|twitter:title)"\s+content="([^"]+)"', html)
                if og_title_match:
                    metadata["title"] = og_title_match.group(1).strip()

                # Extrai músico/artista (music:musician_description)
                musician_match = re.search(r'<meta\s+(?:property|name)="music:musician_description"\s+content="([^"]+)"', html)
                if musician_match:
                    metadata["artist"] = musician_match.group(1).strip()

                # Extrai descrição (og:description ou twitter:description) - formato: "Artist · Album · Song · Year"
                og_desc_match = re.search(r'<meta\s+(?:property|name)="(?:og:description|twitter:description)"\s+content="([^"]+)"', html)
                if og_desc_match:
                    desc = og_desc_match.group(1).strip()
                    parts = [p.strip() for p in desc.split("·") if p.strip()]
                    if parts:
                        if not metadata["artist"]:
                            metadata["artist"] = parts[0]
                        if len(parts) >= 2 and parts[1].lower() != "song":
                            metadata["album"] = parts[1]
                        if parts[-1].isdigit() and len(parts[-1]) == 4:
                            metadata["release_date"] = parts[-1]

                # Extrai og:image ou twitter:image
                og_img_match = re.search(r'<meta\s+(?:property|name)="(?:og:image|twitter:image)"\s+content="([^"]+)"', html)
                if og_img_match:
                    metadata["cover_url"] = og_img_match.group(1).strip()

                # Extrai music:duration (segundos)
                duration_match = re.search(r'<meta\s+(?:property|name)="music:duration"\s+content="(\d+)"', html)
                if duration_match:
                    metadata["duration"] = int(duration_match.group(1))

                # Extrai data de lançamento (music:release_date)
                date_match = re.search(r'<meta\s+(?:property|name)="music:release_date"\s+content="(\d{4})', html)
                if date_match and not metadata["release_date"]:
                    metadata["release_date"] = date_match.group(1)
        except Exception:
            pass

        # 2. Se título ou capa faltarem, consulta o endpoint oficial de oEmbed
        if not metadata["title"] or not metadata["cover_url"]:
            try:
                oembed_url = f"https://open.spotify.com/oembed?url={urllib.parse.quote(clean_url)}"
                req = urllib.request.Request(oembed_url, headers={"User-Agent": self.USER_AGENT})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if not metadata["title"] and "title" in data:
                        metadata["title"] = data["title"]
                    if not metadata["cover_url"] and "thumbnail_url" in data:
                        metadata["cover_url"] = data["thumbnail_url"]
            except Exception:
                pass

        # Normaliza caso o título venha no formato "Música - song by Artista"
        if " - song by " in metadata["title"]:
            t_parts = metadata["title"].split(" - song by ")
            metadata["title"] = t_parts[0].strip()
            if not metadata["artist"] and len(t_parts) > 1:
                metadata["artist"] = t_parts[1].split("|")[0].strip()

        if not metadata["title"]:
            raise RuntimeError("Não foi possível extrair os metadados da faixa do Spotify. Verifique o link ou a conexão.")

        return metadata


class GenreTagResolver:
    """
    Consulta o banco de dados aberto e livre do MusicBrainz para identificar
    gêneros musicais, compositores, álbuns e anos de lançamento.
    Ideal para trilhas de videogame (VGM) e músicas em geral.
    Totalmente gratuito e livre de chaves de API.
    """

    USER_AGENT = "MediaMultiTool/1.0 (https://github.com/MigzuLCS/Media-MultiTool)"

    def query_musicbrainz(
        self,
        title: str,
        artist: str = "",
        raw_title: str = "",
        categories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Pesquisa metadados no MusicBrainz de forma inteligente:
        1. Busca por gravação (recording) e artista.
        2. Se não houver tags na gravação, busca na publicação (release) do álbum/jogo.
        3. Se não houver retorno do MusicBrainz, deduz o gênero contextual por regras (infer_genre_from_text).
        """
        clean_t = clean_title_for_search(title or raw_title)
        if not clean_t and not raw_title:
            return {}

        result: Dict[str, Any] = {
            "genre": "",
            "album": "",
            "artist": "",
            "date": "",
        }

        # 1. Tentar busca no MusicBrainz por Recording
        try:
            query_str = f'recording:"{clean_t}"'
            if artist:
                query_str += f' AND artist:"{artist}"'

            url = f"https://musicbrainz.org/ws/2/recording?query={urllib.parse.quote(query_str)}&fmt=json&limit=3"
            req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT, "Accept": "application/json"})

            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                recordings = data.get("recordings", [])

                if recordings:
                    rec = recordings[0]
                    if "artist-credit" in rec and rec["artist-credit"]:
                        result["artist"] = rec["artist-credit"][0].get("name", "")

                    if "releases" in rec and rec["releases"]:
                        rel = rec["releases"][0]
                        result["album"] = rel.get("title", "")
                        result["date"] = rel.get("date", "")[:4] if rel.get("date") else ""

                    rec_tags = rec.get("tags", [])
                    genre_names = [t.get("name", "").strip().title() for t in sorted(rec_tags, key=lambda x: x.get("count", 0), reverse=True) if t.get("name")]
                    if genre_names:
                        result["genre"] = " / ".join(genre_names[:2])
        except Exception:
            pass

        # 2. Se o gênero ou álbum não foram encontrados, verificar se o título tem formato "Jogo/Artista - Faixa"
        if (not result["genre"] or not result["album"]) and " - " in clean_t:
            parts = clean_t.split(" - ")
            part_a = parts[0].strip()
            try:
                # Pesquisa o álbum/jogo na base de Releases do MusicBrainz
                rel_url = f"https://musicbrainz.org/ws/2/release?query={urllib.parse.quote('release:' + part_a)}&fmt=json&limit=3"
                rel_req = urllib.request.Request(rel_url, headers={"User-Agent": self.USER_AGENT, "Accept": "application/json"})
                with urllib.request.urlopen(rel_req, timeout=6) as r_resp:
                    r_data = json.loads(r_resp.read().decode("utf-8"))
                    releases = r_data.get("releases", [])
                    if releases:
                        best_rel = releases[0]
                        if not result["album"]:
                            result["album"] = best_rel.get("title", "")
                        if not result["artist"] and "artist-credit" in best_rel and best_rel["artist-credit"]:
                            result["artist"] = best_rel["artist-credit"][0].get("name", "")
                        if not result["date"] and best_rel.get("date"):
                            result["date"] = best_rel.get("date", "")[:4]

                        # Extrai tags da release (ex: electronic, house, ambient house)
                        rel_tags = best_rel.get("tags", [])
                        tag_names = [t.get("name", "").strip().title() for t in sorted(rel_tags, key=lambda x: x.get("count", 0), reverse=True) if t.get("name")]
                        if tag_names and not result["genre"]:
                            result["genre"] = " / ".join(tag_names[:2])
            except Exception:
                pass

        # 3. Fallback inteligente de gênero por regras contextuais do vídeo (OST, Game, Chiptune, etc.)
        if not result["genre"]:
            inferred = infer_genre_from_text(
                title=clean_t,
                raw_title=raw_title,
                categories=categories,
                tags=tags,
            )
            if inferred:
                result["genre"] = inferred

        return result


class AudioTagger:
    """
    Grava tags ID3v2 (Título, Artista, Álbum, Gênero, Ano) e Capa (Cover Art)
    diretamente no arquivo MP3 gerado usando o FFmpeg, sem perda de qualidade (copy audio codec).
    """

    @staticmethod
    def tag_mp3(
        mp3_path: str,
        title: str = "",
        artist: str = "",
        album: str = "",
        genre: str = "",
        date: str = "",
        cover_url: str = "",
    ) -> bool:
        mp3_file = Path(mp3_path)
        if not mp3_file.exists():
            return False

        ffmpeg_bin = ffmpeg_manager.get_ffmpeg_path()
        if not ffmpeg_bin:
            return False

        temp_cover: Optional[Path] = None
        temp_output = mp3_file.with_name(f"{mp3_file.stem}_tagged.mp3")

        try:
            # 1. Download temporário da capa se fornecida
            if cover_url and cover_url.startswith("http"):
                try:
                    req = urllib.request.Request(
                        cover_url,
                        headers={"User-Agent": SpotifyResolver.USER_AGENT}
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        cover_data = resp.read()
                        if cover_data:
                            # Converte para JPEG compatível com ID3 usando Pillow
                            from PIL import Image
                            import io
                            img = Image.open(io.BytesIO(cover_data)).convert("RGB")
                            fd, tmp_name = tempfile.mkstemp(suffix=".jpg")
                            os.close(fd)
                            temp_cover = Path(tmp_name)
                            img.save(temp_cover, format="JPEG", quality=92)
                except Exception:
                    temp_cover = None

            # 2. Monta comando FFmpeg
            cmd = [ffmpeg_bin, "-y", "-i", str(mp3_file)]
            if temp_cover and temp_cover.exists():
                cmd.extend(["-i", str(temp_cover), "-map", "0:a", "-map", "1:0", "-c:a", "copy", "-c:v", "copy"])
                cmd.extend(["-metadata:s:v", 'title="Album cover"', "-metadata:s:v", 'comment="Cover (front)"'])
            else:
                cmd.extend(["-c", "copy"])

            cmd.extend(["-id3v2_version", "3"])

            if title:
                cmd.extend(["-metadata", f"title={title}"])
            if artist:
                cmd.extend(["-metadata", f"artist={artist}"])
            if album:
                cmd.extend(["-metadata", f"album={album}"])
            if genre:
                cmd.extend(["-metadata", f"genre={genre}"])
            if date:
                cmd.extend(["-metadata", f"date={date}"])

            cmd.append(str(temp_output))

            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creation_flags,
                timeout=30,
            )

            if result.returncode == 0 and temp_output.exists() and temp_output.stat().st_size > 0:
                # Substitui com segurança o arquivo original pelo arquivo taggeado
                temp_output.replace(mp3_file)
                return True
            else:
                if temp_output.exists():
                    temp_output.unlink()
                return False
        except Exception:
            if temp_output.exists():
                try:
                    temp_output.unlink()
                except Exception:
                    pass
            return False
        finally:
            if temp_cover and temp_cover.exists():
                try:
                    temp_cover.unlink()
                except Exception:
                    pass


spotify_resolver = SpotifyResolver()
genre_tag_resolver = GenreTagResolver()
audio_tagger = AudioTagger()
