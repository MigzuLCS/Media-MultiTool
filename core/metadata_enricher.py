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
    title = re.sub(r"\.(mp3|m4a|flac|wav|ogg|opus|mp4|mkv|webm)$", "", title, flags=re.IGNORECASE).strip()

    # 1. Padrões entre colchetes ou parênteses
    bracket_patterns = [
        r"\[\s*(original\s+)?(video\s+game\s+|game\s+|video\s+)?(soundtrack|score|ost|o\.s\.t\.)\s*\]",
        r"\(\s*(original\s+)?(video\s+game\s+|game\s+|video\s+)?(soundtrack|score|ost|o\.s\.t\.)\s*\)",
        r"\[\s*(official\s+)?(music\s+)?(video|audio|visualizer|lyric\s+video|track)\s*\]",
        r"\(\s*(official\s+)?(music\s+)?(video|audio|visualizer|lyric\s+video|track)\s*\)",
        r"\[\s*(1\s*hour|10\s*hours|loop|extended(\s+version)?|hq|hd|4k|60fps|remaster(ed)?|recreated?)\s*\]",
        r"\(\s*(1\s*hour|10\s*hours|loop|extended(\s+version)?|hq|hd|4k|60fps|remaster(ed)?|recreated?)\s*\)",
        r"\[\s*(lyrics?|letra|audio)\s*\]",
        r"\(\s*(lyrics?|letra|audio)\s*\)",
        r"【.*?】",
        r"『.*?』",
    ]
    for pat in bracket_patterns:
        title = re.sub(pat, "", title, flags=re.IGNORECASE)

    # 2. Cláusulas finais ou iniciais separadas por traços, barras ou pipes (ex: ' - Original Game Soundtrack')
    clause_patterns = [
        r"\s*[-–—|]\s*(original\s+)?(video\s+game\s+|game\s+|video\s+)?(soundtrack|score|ost|o\.s\.t\.)\s*$",
        r"\s*[-–—|]\s*(official\s+)?(music\s+video|audio|video|visualizer|lyrics?)\s*$",
        r"\s*[-–—|]\s*(extended(\s+version)?|1\s*hour(\s+loop)?|remaster(ed)?|recreated?)\s*$",
        r"^(original\s+)?(video\s+game\s+|game\s+|video\s+)?(soundtrack|score|ost|o\.s\.t\.)\s*[-–—|]\s*",
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

    # 4. Limpeza de prefixo numérico de faixa/playlist inicial (ex: "01 - ", "02. ", "1 - ")
    title = re.sub(r"^\d{1,2}\s*[-–—._]\s+", "", title)

    # 5. Limpeza de múltiplos espaços e traços
    title = re.sub(r"\s*[-–—]\s*[-–—]\s*", " - ", title)
    title = re.sub(r"\s+", " ", title).strip(" -–—|")
    return title


# Constantes e Vocabulário Especializado de Videogames (VGM)
GAME_HARDWARE_KEYWORDS = {
    "snes", "nes", "famicom", "super nintendo", "super famicom", "n64", "nintendo 64",
    "gamecube", "game cube", "wii", "wii u", "switch", "nintendo switch", "game boy",
    "gameboy", "gba", "gbc", "nds", "nintendo ds", "3ds", "ps1", "psx", "ps2", "ps3",
    "ps4", "ps5", "psp", "ps vita", "playstation", "dreamcast", "sega genesis", "mega drive",
    "megadrive", "sega saturn", "game gear", "master system", "sega cd", "pc-98", "pc98",
    "msx", "msx2", "neo geo", "neo-geo", "arcade", "pc engine", "turbografx", "amiga",
    "x68000", "c64", "commodore 64"
}

GAME_STUDIOS_KEYWORDS = {
    "sega", "nintendo", "square enix", "squaresoft", "konami", "capcom", "bandai namco",
    "namco", "atlus", "falcom", "nihon falcom", "snk", "fromsoftware", "koei tecmo", "valve",
    "blizzard", "bethesda", "bungie", "bioware", "rare", "rareware", "rare ltd", "game freak",
    "wayforward", "hal laboratory", "monolith soft", "level-5", "game arts", "treasure",
    "sunsoft", "taito", "data east", "technos", "hudson soft", "irem", "spike chunsoft",
    "sound team", "falcom sound team", "sega sound team", "capcom sound team", "zuntata",
    "kukeiha club", "s.s.t. band", "jdk band", "alph lyla", "gamadelic"
}

GAME_TERMS_KEYWORDS = {
    "bgm", "ost", "soundtrack", "gamerip", "game rip", "soundfont", "sound version",
    "boss theme", "battle theme", "stage theme", "area theme", "title theme", "menu theme",
    "victory theme", "overworld", "dungeon theme", "final boss", "character theme", "chiptune",
    "8-bit", "16-bit", "32-bit", "demake", "recreated", "vgm", "video game music",
    "game music", "original game soundtrack", "video game soundtrack", "game ost"
}

GAME_FRANCHISES_KEYWORDS = {
    "mario", "zelda", "pokemon", "pokémon", "metroid", "donkey kong", "kirby", "sonic",
    "mega man", "rockman", "final fantasy", "chrono trigger", "chrono cross", "kingdom hearts",
    "persona", "shin megami tensei", "smt", "street fighter", "tekken", "guilty gear",
    "castlevania", "silent hill", "resident evil", "biohazard", "metal gear", "yakuza",
    "like a dragon", "monster hunter", "dark souls", "elden ring", "bloodborne", "touhou",
    "undertale", "deltarune", "cuphead", "hollow knight", "celeste", "minecraft", "terraria",
    "doom", "halo", "the elder scrolls", "skyrim", "fallout", "witcher", "genshin impact",
    "gran turismo", "ridge racer", "wipeout", "ace combat", "xenoblade", "fire emblem",
    "napple tale", "rasetsu", "the conveni", "sega marine fishing", "net de tennis",
    "chaindive", "littlebigplanet", "animal crossing", "splatoon", "smash bros", "banjo kazooie",
    "spyro", "crash bandicoot", "katamari", "parappa", "shenmue", "jet set radio",
    "phantasy star", "golden sun", "mother", "earthbound", "advance wars", "f-zero",
    "star fox", "saya no uta", "nitroplus", "clannad", "fate/stay night", "danganronpa",
    "phoenix wright", "ace attorney"
}


def detect_vgm_genre(combined: str) -> str:
    """
    Identifica de forma precisa se a mídia se trata de uma música de videogame
    e refina o subgênero correspondente.
    """
    c = f" {combined.lower()} "
    has_hw = any(re.search(rf"\b{re.escape(k)}\b", c) for k in GAME_HARDWARE_KEYWORDS)
    has_studio = any(re.search(rf"\b{re.escape(k)}\b", c) for k in GAME_STUDIOS_KEYWORDS)
    has_term = any(re.search(rf"\b{re.escape(k)}\b", c) for k in GAME_TERMS_KEYWORDS)
    has_franchise = any(re.search(rf"\b{re.escape(k)}\b", c) for k in GAME_FRANCHISES_KEYWORDS)

    is_game = (
        has_franchise
        or (has_hw and (has_term or "track" in c or "music" in c or "bgm" in c))
        or (has_studio and (has_term or "theme" in c or "bgm" in c))
        or any(k in c for k in ("video game music", "vgm", "gamerip", "game rip", "game soundtrack", "original game soundtrack", "video game soundtrack", "game ost"))
        or (has_term and any(term in c for term in ("bgm", "stage", "boss", "battle", "area", "dungeon", "overworld")))
    )

    if is_game:
        if any(k in c for k in ("dnb", "drum and bass", "drum & bass")):
            return "Drum & Bass / Game Music"
        if any(k in c for k in ("chiptune", "8-bit", "16-bit", "8bit", "16bit")):
            return "Chiptune / 8-Bit"
        if any(k in c for k in ("orchestral", "orchestra", "symphon", "waltz")):
            return "Orchestral / Game Soundtrack"
        if any(k in c for k in ("rock", "metal")):
            return "Rock / Game Soundtrack"
        if any(k in c for k in ("ambient", "atmospheric")):
            return "Ambient / Game Soundtrack"
        if any(k in c for k in ("jazz", "samba", "bossa")):
            return "Jazz / Game Soundtrack"
        if any(k in c for k in ("electronic", "techno", "house", "edm", "dance", "synth")):
            return "Electronic / Game Soundtrack"
        return "Video Game Music"
    return ""


def infer_broad_genre(combined: str) -> str:
    """
    Deduz o gênero musical abrangente com base em termos semânticos e contextuais.
    """
    c = f" {combined.lower()} "
    if any(k in c for k in ("anime", "anison", "monogatari", "evangelion", "vocaloid", "utaite", "opening", "ending", "saya no uta")):
        return "Anime / Soundtrack"
    if any(k in c for k in ("soundtrack", "ost", "o.s.t.", "original score", "score", "cinematic music", "film score")):
        return "Soundtrack"
    if any(k in c for k in ("chiptune", "8-bit", "16-bit", "8bit", "16bit")):
        return "Chiptune"
    if any(k in c for k in ("lo-fi", "lofi", "chillhop")):
        return "Lo-Fi / Chillhop"
    if any(k in c for k in ("synthwave", "retrowave", "cyberpunk", "vaporwave")):
        return "Synthwave"
    if any(k in c for k in ("bossa nova", "bossa", "samba", "mpb")):
        return "Bossa Nova"
    if any(k in c for k in ("latin jazz", "smooth jazz", "bebop", "jazz")):
        return "Jazz"
    if any(k in c for k in ("classical", "piano solo", "solo piano", "neoclassical", "orchestra", "symphony", "concerto")):
        return "Classical"
    if any(k in c for k in ("ambient", "atmospheric", "meditation", "drone", "new age")):
        return "Ambient"
    if any(k in c for k in ("heavy metal", "death metal", "metal")):
        return "Metal"
    if any(k in c for k in ("indie rock", "alternative rock", "punk", "rock", "grunge")):
        return "Rock"
    if any(k in c for k in ("drum and bass", "dnb", "jungle")):
        return "Drum & Bass"
    if any(k in c for k in ("house", "deep house", "techno", "electronic", "trance", "edm", "shibuya-kei")):
        return "Electronic"
    if "city pop" in c:
        return "City Pop"
    if any(k in c for k in ("j-pop", "jpop", "japanese pop")):
        return "J-Pop"
    if any(k in c for k in ("hip-hop", "hip hop", "rap", "trap")):
        return "Hip-Hop"
    if any(k in c for k in ("r&b", "soul", "funk", "motown")):
        return "R&B / Soul"
    if any(k in c for k in ("reggae", "dub", "ska")):
        return "Reggae"
    if any(k in c for k in ("indie pop", "synthpop", "pop")):
        return "Pop"
    return ""


def search_itunes_metadata(query: str) -> Optional[Dict[str, Any]]:
    """
    Consulta o endpoint de pesquisa público da Apple/iTunes (gratuito, sem autenticação/chave).
    Retorna gênero principal oficial, artista, álbum e data de lançamento.
    """
    if not query or not query.strip():
        return None
    try:
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query.strip())}&entity=song&limit=3"
        req = urllib.request.Request(url, headers={"User-Agent": "MediaMultiTool/1.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
            results = data.get("results", [])
            if results:
                return results[0]
    except Exception:
        pass
    return None


def infer_genre_from_text(
    title: str = "",
    raw_title: str = "",
    categories: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    album: str = "",
    description: str = "",
) -> str:
    """
    Deduz o gênero musical com base no contexto do título, tags, categorias, álbum e descrição.
    """
    combined = f"{title} {raw_title} {album} {' '.join(tags or [])} {' '.join(categories or [])} {description}"
    vgm = detect_vgm_genre(combined)
    if vgm:
        return vgm
    broad = infer_broad_genre(combined)
    if broad:
        return broad
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
    Identifica gêneros musicais, compositores, álbuns e anos de lançamento utilizando
    uma arquitetura em múltiplas camadas de alta disponibilidade e precisão:
    1. Detecção Especializada para Músicas de Videogame (VGM)
    2. Consulta rápida via iTunes Search API (100% gratuita, pública e sem limitação de 1 req/s)
    3. Consulta ao banco aberto MusicBrainz (com escape de caracteres e verificação de artista)
    4. Inferência semântica e contextual avançada
    """

    USER_AGENT = "MediaMultiTool/1.0 (https://github.com/MigzuLCS/Media-MultiTool)"

    def query_musicbrainz(
        self,
        title: str,
        artist: str = "",
        raw_title: str = "",
        categories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        album: str = "",
        description: str = "",
        existing_genre: str = "",
    ) -> Dict[str, Any]:
        """
        Pesquisa metadados e gênero de forma inteligente e multi-camadas:
        1. Identificação instantânea de VGM / Músicas de Jogos por hardware, estúdios, franquias e termos.
        2. Pesquisa de alta velocidade no iTunes Search API público.
        3. Consulta ao MusicBrainz com queries sanitizadas e proteção contra 503.
        4. Inferência semântica ampla por palavras-chave e tags.
        """
        clean_t = clean_title_for_search(title or raw_title)
        if not clean_t and not raw_title:
            return {}

        result: Dict[str, Any] = {
            "genre": existing_genre or "",
            "album": album or "",
            "artist": artist or "",
            "date": "",
        }

        cand_artist = artist
        cand_title = clean_t
        if not cand_artist and " - " in clean_t:
            parts = clean_t.split(" - ")
            cand_artist = parts[0].strip()
            cand_title = " - ".join(parts[1:]).strip()

        combined = f"{clean_t} {raw_title} {artist} {album} {' '.join(tags or [])} {' '.join(categories or [])} {description}"

        # 1. Detecção Especializada para Músicas de Videogame (VGM)
        vgm_genre = detect_vgm_genre(combined)
        if vgm_genre:
            result["genre"] = vgm_genre
            if not result["album"] and " - " in clean_t:
                result["album"] = clean_t.split(" - ")[0].strip()
            if not result["artist"] and " - " in clean_t:
                result["artist"] = clean_t.split(" - ")[0].strip()
            return result

        # 2. Consulta rápida à API pública do iTunes (alta disponibilidade para faixas comerciais, clássica, jazz, anime, etc.)
        itunes_queries = []
        if cand_artist and cand_title:
            itunes_queries.append(f"{cand_artist} {cand_title}")
        if clean_t and clean_t not in itunes_queries:
            itunes_queries.append(clean_t)
        if raw_title and raw_title not in itunes_queries:
            itunes_queries.append(raw_title)
        if cand_artist and cand_artist not in itunes_queries:
            itunes_queries.append(cand_artist)

        for q in itunes_queries:
            itunes_match = search_itunes_metadata(q)
            if itunes_match:
                itunes_genre = itunes_match.get("primaryGenreName", "")
                ret_artist = (itunes_match.get("artistName") or "").lower()
                ret_track = (itunes_match.get("trackName") or "").lower()

                # Validação de relevância para evitar falsos positivos
                if cand_artist:
                    ca = cand_artist.lower()
                    if ca not in ret_artist and ret_artist not in ca:
                        ct = cand_title.lower() if cand_title else ""
                        if not ct or (ct not in ret_track and ret_track not in ct):
                            continue
                elif cand_title:
                    ct = cand_title.lower()
                    if ct not in ret_track and ret_track not in ct:
                        continue

                if itunes_genre:
                    result["genre"] = itunes_genre
                    if not result["artist"]:
                        result["artist"] = itunes_match.get("artistName", "")
                    if not result["album"]:
                        result["album"] = itunes_match.get("collectionName", "")
                    if not result["date"] and itunes_match.get("releaseDate"):
                        result["date"] = itunes_match.get("releaseDate")[:4]
                    return result

        # 3. Consulta ao MusicBrainz com queries protegidas por escape
        try:
            clean_rec = re.sub(r'([+\-&|!(){}\[\]^"~*?:\\/])', r'\\\1', cand_title or clean_t)
            query_str = f'recording:"{clean_rec}"'
            if cand_artist:
                clean_art = re.sub(r'([+\-&|!(){}\[\]^"~*?:\\/])', r'\\\1', cand_artist)
                query_str += f' AND artist:"{clean_art}"'

            url = f"https://musicbrainz.org/ws/2/recording?query={urllib.parse.quote(query_str)}&fmt=json&limit=3"
            req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT, "Accept": "application/json"})

            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                recordings = data.get("recordings", [])

                if recordings:
                    rec = recordings[0]
                    if not result["artist"] and "artist-credit" in rec and rec["artist-credit"]:
                        result["artist"] = rec["artist-credit"][0].get("name", "")

                    if not result["album"] and "releases" in rec and rec["releases"]:
                        rel = rec["releases"][0]
                        result["album"] = rel.get("title", "")
                        if not result["date"]:
                            result["date"] = rel.get("date", "")[:4] if rel.get("date") else ""

                    rec_tags = rec.get("tags", [])
                    genre_names = [t.get("name", "").strip().title() for t in sorted(rec_tags, key=lambda x: x.get("count", 0), reverse=True) if t.get("name")]
                    if genre_names and not result["genre"]:
                        result["genre"] = " / ".join(genre_names[:2])
                        return result
        except Exception:
            pass

        # 4. Fallback semântico e contextual
        if not result["genre"]:
            inferred = infer_broad_genre(combined)
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
