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

    def test_download_rejects_playlist_url(self):
        with self.assertRaises(ValueError):
            self.dl.download('https://www.youtube.com/playlist?list=PL12345', output_dir='C:/tmp')

    def test_get_info_rejects_playlist_url(self):
        with self.assertRaises(ValueError):
            self.dl.get_info('https://www.youtube.com/playlist?list=PL12345')


if __name__ == '__main__':
    unittest.main()
