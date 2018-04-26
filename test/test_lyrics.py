import unittest
import json
from pathlib import Path
from src import lyrics

test_resources_dir = Path("resources")
test_data_filename = "expected_short.json"


class LyricsTest(unittest.TestCase):
    test_data_file = test_resources_dir / test_data_filename
    with open(test_data_file) as tf:
        test_data = json.load(tf)

    def test_lyrics_files_exist(self):
        for single_lyrics_file in self.test_data:
            filename = single_lyrics_file['file']
            for single_song in single_lyrics_file['songs']:
                song_title = single_song['title']
                with self.subTest(filename=filename, song_title=song_title):
                    found_lyrics = lyrics.find_lyrics_in_file(test_resources_dir / filename, song_title)
                    self.assertEqual(found_lyrics[0], single_song['firstLine'])
                    self.assertEqual(found_lyrics[-1], single_song['lastLine'])


