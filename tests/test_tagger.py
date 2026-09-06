import unittest
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.metadata_enricher import (
    clean_title_for_search,
    SpotifyResolver,
    GenreTagResolver,
    AudioTagger,
    spotify_resolver,
    genre_tag_resolver,
    audio_tagger,
)


class TestMetadataEnricher(unittest.TestCase):
    def test_clean_title_for_search_ost(self):
        raw = "Minecraft - Sweden [OST] (1 Hour)"
        cleaned = clean_title_for_search(raw)
        self.assertEqual(cleaned, "Minecraft - Sweden")

    def test_clean_title_for_search_official_audio(self):
        raw = "Persona 5 - Life Will Change (Official Audio) [HQ]"
        cleaned = clean_title_for_search(raw)
        self.assertEqual(cleaned, "Persona 5 - Life Will Change")

    def test_clean_title_asian_brackets(self):
        raw = "Undertale - Megalovania 【Original Soundtrack】"
        cleaned = clean_title_for_search(raw)
        self.assertEqual(cleaned, "Undertale - Megalovania")

    def test_clean_title_chaindive_original_game_soundtrack(self):
        raw = "ChainDive - Track 24 (Movin' On) - Original Game Soundtrack"
        cleaned = clean_title_for_search(raw)
        self.assertEqual(cleaned, "ChainDive - Track 24 (Movin' On)")

    def test_infer_genre_from_text(self):
        from core.metadata_enricher import infer_genre_from_text
        self.assertEqual(infer_genre_from_text("ChainDive - Track 24 - Original Game Soundtrack"), "Video Game Music")
        self.assertEqual(infer_genre_from_text("Title", categories=["Gaming"], raw_title="Boss Theme OST"), "Video Game Music")
        self.assertEqual(infer_genre_from_text("Mega Man 2 - Wily Stage Chiptune 8-Bit"), "Chiptune / 8-Bit")
        self.assertEqual(infer_genre_from_text("Coffee Shop Lofi Chillhop"), "Lo-Fi / Chillhop")

    def test_spotify_url_detection(self):
        resolver = SpotifyResolver()
        self.assertTrue(resolver.is_spotify_url("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT?si=abc"))
        self.assertFalse(resolver.is_spotify_url("https://youtube.com/watch?v=12345"))

    def test_spotify_extract_track_id(self):
        resolver = SpotifyResolver()
        track_id = resolver.extract_track_id("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT?si=abc")
        self.assertEqual(track_id, "4cOdK2wGLETKBW3PvgPWqT")

    @patch("urllib.request.urlopen")
    def test_spotify_resolve_opengraph(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        html_content = """
        <html>
        <head>
            <meta property="og:title" content="Sweden" />
            <meta property="og:description" content="C418 · Minecraft - Volume Alpha · 2011" />
            <meta property="og:image" content="https://i.scdn.co/image/ab67616d0000b273minecraft" />
            <meta name="music:duration" content="215" />
            <meta property="music:album" content="Minecraft - Volume Alpha" />
        </head>
        </html>
        """
        mock_resp.read.return_value = html_content.encode("utf-8")
        mock_urlopen.return_value = mock_resp

        resolver = SpotifyResolver()
        info = resolver.resolve("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT")

        self.assertEqual(info["title"], "Sweden")
        self.assertEqual(info["artist"], "C418")
        self.assertEqual(info["album"], "Minecraft - Volume Alpha")
        self.assertEqual(info["duration"], 215)
        self.assertEqual(info["release_date"], "2011")
        self.assertEqual(info["cover_url"], "https://i.scdn.co/image/ab67616d0000b273minecraft")

    @patch("urllib.request.urlopen")
    def test_musicbrainz_genre_resolver(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mb_json = {
            "recordings": [
                {
                    "title": "Sweden",
                    "artist-credit": [{"name": "C418"}],
                    "releases": [{"title": "Minecraft - Volume Alpha", "date": "2011-03-04"}],
                    "tags": [
                        {"name": "ambient", "count": 10},
                        {"name": "video game music", "count": 15},
                        {"name": "soundtrack", "count": 20},
                    ],
                }
            ]
        }
        import json
        mock_resp.read.return_value = json.dumps(mb_json).encode("utf-8")
        mock_urlopen.return_value = mock_resp

        resolver = GenreTagResolver()
        res = resolver.query_musicbrainz("Sweden", "C418")

        self.assertIn("Soundtrack", res["genre"])
        self.assertEqual(res["artist"], "C418")
        self.assertEqual(res["album"], "Minecraft - Volume Alpha")
        self.assertEqual(res["date"], "2011")

    @patch("subprocess.run")
    @patch("core.metadata_enricher.ffmpeg_manager.get_ffmpeg_path")
    def test_audio_tagger_command_construction(self, mock_get_ffmpeg, mock_run):
        mock_get_ffmpeg.return_value = "C:/bin/ffmpeg.exe"
        mock_run.return_value = MagicMock(returncode=0)

        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.stat") as mock_stat, \
             patch("pathlib.Path.replace") as mock_replace:
            mock_stat.return_value.st_size = 1024

            success = AudioTagger.tag_mp3(
                mp3_path="C:/music/test.mp3",
                title="Sweden",
                artist="C418",
                album="Minecraft",
                genre="Ambient / Video Game",
                date="2011",
            )
            self.assertTrue(success)
            args, kwargs = mock_run.call_args
            cmd = args[0]
            self.assertIn("-metadata", cmd)
            self.assertIn("genre=Ambient / Video Game", cmd)
            self.assertIn("artist=C418", cmd)
            self.assertIn("title=Sweden", cmd)


if __name__ == "__main__":
    unittest.main()
