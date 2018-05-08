import unittest
import json
from pathlib import Path
from src import lyrics

test_resources_dir = Path("resources")
test_data_filename = "expected2.json"

BLANK = lyrics.BlankLine
SEP = lyrics.Separator
UND = lyrics.UnderLine
TEXT = lyrics.TextLine


class CompareEasily:
    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class UtilTest(unittest.TestCase):
    def test_monotonic(self):
        self.assertTrue(lyrics.monotonic([]))
        self.assertTrue(lyrics.monotonic([1]))
        self.assertTrue(lyrics.monotonic([1, 2]))
        self.assertTrue(lyrics.monotonic([1, 2, 3]))
        self.assertTrue(lyrics.monotonic([1, 1, 3]))
        self.assertTrue(lyrics.monotonic([1, 3, 100]))
        self.assertTrue(lyrics.monotonic([1, 3, 100, 100, 101]))
        self.assertFalse(lyrics.monotonic([2, 1]))
        self.assertFalse(lyrics.monotonic([2, 2, 1]))
        self.assertFalse(lyrics.monotonic([2, 3, 4, 5, 4]))


class LinesTest(unittest.TestCase):
    def test_blank(self):
        self.assertIsInstance(lyrics.LineType.of(""), BLANK)
        self.assertIsInstance(lyrics.LineType.of("   "), BLANK)
        self.assertIsInstance(lyrics.LineType.of("\t"), BLANK)

    def test_text_line(self):
        def assert_unnumbered(from_string):
            tl = lyrics.LineType.of(from_string)
            self.assertIsInstance(tl, TEXT)
            self.assertIsNone(tl.number)
            self.assertIsNone(tl.number_separator)
            
        assert_unnumbered("abc")
        assert_unnumbered("Litwo, ojczyzno moja!")
        assert_unnumbered("*) Litwo")
        assert_unnumbered("ii) Litwo 0:45")
        assert_unnumbered("*** aaa ***")
        assert_unnumbered("*****************a**************")
        
    def test_numbered_line(self):
        def assert_numbered(from_string, expected_number, expected_separator):
            tl = lyrics.LineType.of(from_string)
            self.assertIsInstance(tl, TEXT)
            self.assertEqual(tl.number, expected_number)
            self.assertEqual(tl.number_separator, expected_separator)

        assert_numbered("1. Litwo", 1, ". ")
        assert_numbered("2.Litwo", 2, ".")
        assert_numbered("3>>Litwo", 3, ">>")
        assert_numbered("#4 Litwo", 4, " ")
        assert_numbered("#10# Litwo", 10, "# ")
        assert_numbered("01-Litwo", 1, "-")
        assert_numbered("009 ))* Litwo", 9, " ))* ")


class LyricsFileAnalysis(unittest.TestCase):
    def test_init(self):
        lines = """First
        
        
        1. One
        02>>Two
        ===
        
        3. Three
        -=-=-
        
        4. Four
        -=-="""
        parts = lyrics.analyze_lyrics_file(lines.split("\n"))
        self.assertEqual(len([t for t in parts if t.is_tracklist]), 1)


class LyricsTest(unittest.TestCase):
    def test_lyrics_begin(self):
        expecteds = {"abneypark.txt": {"No Such Song": None,
                                       "Under the Radar": "Under the Radar",
                                       "Building Steam": "Building Steam",
                                       "Until The Day You Die": "Until The Day You Die",
                                       "Too Far To Turn Back": "Too Far To Turn Back"},
                     "efrafa.txt": {"Simulacrum": "1. Simulacrum",
                                    "Fu Inle": "2. Fu Inl�",
                                    "Republic Of Heaven": "3. Republic Of Heaven",
                                    "The Sky Suspended": "6. The Sky Suspended",
                                    "Warren Of Snares": "7. Warren Of Snares"},
                     "pinkfloyd.txt": {"In The Flesh?": "IN THE FLESH ?",
                                       "The Thin Ice": "THE THIN ICE",
                                       "Goodbye Blue Sky": "GOODBYE BLUE SKY",
                                       "In The Flesh": "IN THE FLESH"},
                     "mesh.txt": {"Firefly": "1. Firefly",
                                  "The Place You Hide": "10. The Place You Hide",
                                  "Friends Like These": None}}

        for file in expecteds:
            for song in expecteds[file]:
                with self.subTest(filename=file, songtitle=song):
                    header = lyrics.find_song_header(test_resources_dir / file, song)
                    self.assertEqual(None if header is None else header.lines[0].line,
                                     expecteds[file][song])

    test_data_file = test_resources_dir / test_data_filename
    with open(test_data_file) as tf:
        test_data = json.load(tf)

    def test_find_lyrics_in_txt_file(self):
        for single_lyrics_file in self.test_data:
            filename = single_lyrics_file['file']
            for single_song in single_lyrics_file['songs']:
                song_title = single_song['title']
                with self.subTest(filename=filename, song_title=song_title):
                    found_lyrics = lyrics.find_lyrics_in_file(test_resources_dir / filename, song_title)
                    if "notFound" in single_song:
                        self.assertIsNone(found_lyrics)
                    else:
                        self.assertIsNotNone(found_lyrics)
                        self.assertEqual(found_lyrics[0], single_song['firstLine'])
                        self.assertEqual(found_lyrics[-1], single_song['lastLine'])


