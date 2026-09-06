import unittest
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.downloader import YouTubeDownloader, youtube_downloader


class TestYouTubeDownloader(unittest.TestCase):
    def setUp(self):
        self.dl = YouTubeDownloader()

    def test_clean_url_youtube_mix(self):
        # O caso relatado pelo usuario: video dentro de mix RD
        url = 'https://www.youtube.com/watch?v=d0UoMF-cWls&list=RDARdAUiqJ2qU&index=3'
        cleaned = self.dl.clean_url(url)
        self.assertEqual(cleaned, 'https://www.youtube.com/watch?v=d0UoMF-cWls')

    def test_clean_url_inverted_query_params(self):
        url = 'https://www.youtube.com/watch?list=RDARdAUiqJ2qU&v=d0UoMF-cWls&index=3'
        cleaned = self.dl.clean_url(url)
        self.assertEqual(cleaned, 'https://www.youtube.com/watch?v=d0UoMF-cWls')

    def test_clean_url_music_youtube(self):
        url = 'https://music.youtube.com/watch?v=d0UoMF-cWls&list=RDAMVMd0UoMF-cWls'
        cleaned = self.dl.clean_url(url)
        self.assertEqual(cleaned, 'https://music.youtube.com/watch?v=d0UoMF-cWls')

    def test_clean_url_mobile_youtube(self):
        url = 'https://m.youtube.com/watch?v=d0UoMF-cWls&list=RDARdAUiqJ2qU'
        cleaned = self.dl.clean_url(url)
        self.assertEqual(cleaned, 'https://m.youtube.com/watch?v=d0UoMF-cWls')

    def test_clean_url_youtu_be(self):
        url = 'https://youtu.be/d0UoMF-cWls?list=RDARdAUiqJ2qU&index=3'
        cleaned = self.dl.clean_url(url)
        self.assertEqual(cleaned, 'https://youtu.be/d0UoMF-cWls')

    def test_clean_url_shorts(self):
        url = 'https://www.youtube.com/shorts/d0UoMF-cWls?list=RDARdAUiqJ2qU'
        cleaned = self.dl.clean_url(url)
        self.assertEqual(cleaned, 'https://www.youtube.com/shorts/d0UoMF-cWls')

    def test_clean_url_preserves_timestamp(self):
        url = 'https://www.youtube.com/watch?v=d0UoMF-cWls&t=45s&list=RD123'
        cleaned = self.dl.clean_url(url)
        self.assertIn('v=d0UoMF-cWls', cleaned)
        self.assertIn('t=45s', cleaned)
        self.assertNotIn('list=', cleaned)

    def test_clean_url_without_scheme(self):
        url = 'youtube.com/watch?v=d0UoMF-cWls&list=RDARdAUiqJ2qU&index=3'
        cleaned = self.dl.clean_url(url)
        self.assertEqual(cleaned, 'https://youtube.com/watch?v=d0UoMF-cWls')

    def test_clean_url_non_youtube(self):
        url = 'https://vimeo.com/123456789?list=abc'
        cleaned = self.dl.clean_url(url)
        self.assertEqual(cleaned, url)

    def test_is_playlist_url(self):
        self.assertTrue(self.dl.is_playlist_url('https://www.youtube.com/playlist?list=PL12345'))
        self.assertTrue(self.dl.is_playlist_url('https://music.youtube.com/playlist?list=PL12345'))
        self.assertTrue(self.dl.is_playlist_url('www.youtube.com/playlist?list=RD12345'))

        # Videos com parametro list NAO sao playlist pura
        self.assertFalse(self.dl.is_playlist_url('https://www.youtube.com/watch?v=d0UoMF-cWls&list=RD123'))
        self.assertFalse(self.dl.is_playlist_url('https://youtu.be/d0UoMF-cWls?list=RD123'))
        self.assertFalse(self.dl.is_playlist_url('https://www.youtube.com/watch?v=d0UoMF-cWls'))

    @patch('yt_dlp.YoutubeDL')
    def test_download_uses_noplaylist_and_cleaned_url(self, mock_ydl_cls):
        mock_ydl_instance = MagicMock()
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = {'id': 'd0UoMF-cWls', 'title': 'Test Song'}
        mock_ydl_instance.prepare_filename.return_value = 'C:/tmp/Test Song.mp4'

        raw_url = 'https://www.youtube.com/watch?v=d0UoMF-cWls&list=RDARdAUiqJ2qU&index=3'
        result = self.dl.download(raw_url, output_dir='C:/tmp', mode='video')

        # Verifica que o ydl_opts passado para YoutubeDL contem noplaylist: True
        ydl_opts = mock_ydl_cls.call_args[0][0]
        self.assertTrue(ydl_opts.get('noplaylist'))

        # Verifica que a URL extraida foi limpa (sem list e index)
        mock_ydl_instance.extract_info.assert_called_once_with(
            'https://www.youtube.com/watch?v=d0UoMF-cWls',
            download=True
        )

    @patch('yt_dlp.YoutubeDL')
    def test_download_accepts_playlist_url(self, mock_ydl_cls):
        mock_ydl_instance = MagicMock()
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = {'entries': []}

        self.dl.download('https://www.youtube.com/playlist?list=PL12345', output_dir='C:/tmp', is_playlist=True)
        ydl_opts = mock_ydl_cls.call_args[0][0]
        self.assertFalse(ydl_opts.get('noplaylist'))

    @patch('yt_dlp.YoutubeDL')
    def test_download_mix_playlist_limits_to_20(self, mock_ydl_cls):
        mock_ydl_instance = MagicMock()
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = {'entries': []}

        self.dl.download('https://www.youtube.com/watch?v=123&list=RDARdAUiqJ2qU', output_dir='C:/tmp', is_playlist=True)
        ydl_opts = mock_ydl_cls.call_args[0][0]
        self.assertFalse(ydl_opts.get('noplaylist'))
        self.assertEqual(ydl_opts.get('playlistend'), 20)

    def test_playlist_detection_helpers(self):
        self.assertTrue(self.dl.has_playlist("https://www.youtube.com/watch?v=123&list=PL123"))
        self.assertTrue(self.dl.has_playlist("https://www.youtube.com/watch?v=123&list=RD123"))
        self.assertTrue(self.dl.has_playlist("https://www.youtube.com/playlist?list=PL123"))
        self.assertFalse(self.dl.has_playlist("https://www.youtube.com/watch?v=123"))

        self.assertTrue(self.dl.is_mix_playlist("https://www.youtube.com/watch?v=123&list=RD123"))
        self.assertTrue(self.dl.is_mix_playlist("https://www.youtube.com/watch?v=123&start_radio=1"))
        self.assertFalse(self.dl.is_mix_playlist("https://www.youtube.com/playlist?list=PL123"))

    def test_detect_platform(self):
        self.assertEqual(self.dl.detect_platform("https://www.youtube.com/watch?v=123"), "youtube")
        self.assertEqual(self.dl.detect_platform("https://youtu.be/123"), "youtube")
        self.assertEqual(self.dl.detect_platform("https://open.spotify.com/track/123"), "spotify")
        self.assertEqual(self.dl.detect_platform("https://www.tiktok.com/@user/video/123"), "tiktok")
        self.assertEqual(self.dl.detect_platform("https://www.instagram.com/reel/123/"), "instagram")
        self.assertEqual(self.dl.detect_platform("https://x.com/user/status/123"), "twitter_x")
        self.assertEqual(self.dl.detect_platform("https://twitter.com/user/status/123"), "twitter_x")
        self.assertEqual(self.dl.detect_platform("https://www.reddit.com/r/videos/comments/123/"), "reddit")
        self.assertEqual(self.dl.detect_platform("https://vimeo.com/123"), "vimeo")
        self.assertEqual(self.dl.detect_platform("https://example.com/video.mp4"), "generic")

    @patch('core.downloader.spotify_resolver.resolve')
    @patch('core.downloader.YouTubeDownloader._resolve_best_audio_candidate')
    @patch('yt_dlp.YoutubeDL')
    def test_spotify_download_flow(self, mock_ydl_cls, mock_resolve_audio, mock_sp_resolve):
        mock_sp_resolve.return_value = {
            "title": "Sweden",
            "artist": "C418",
            "album": "Minecraft - Volume Alpha",
            "duration": 215,
            "cover_url": "https://cover.jpg",
            "release_date": "2011"
        }
        mock_resolve_audio.return_value = "https://www.youtube.com/watch?v=yt_sweden"

        mock_ydl_instance = MagicMock()
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl_instance
        mock_ydl_instance.extract_info.return_value = {'id': 'yt_sweden', 'title': 'C418 - Sweden'}
        mock_ydl_instance.prepare_filename.return_value = 'C:/tmp/C418 - Sweden.mp3'

        spotify_url = "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"
        with patch('pathlib.Path.exists', return_value=True), \
             patch('core.downloader.audio_tagger.tag_mp3', return_value=True):
            res = self.dl.download(spotify_url, output_dir='C:/tmp', mode='video', auto_tag=False)

        mock_sp_resolve.assert_called_once_with(spotify_url)
        mock_resolve_audio.assert_called_once()
        mock_ydl_instance.extract_info.assert_called_once_with(
            "https://www.youtube.com/watch?v=yt_sweden",
            download=True
        )


if __name__ == '__main__':
    unittest.main()

