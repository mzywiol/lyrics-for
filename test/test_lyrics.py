import unittest
import json
from pathlib import Path
from src import lyrics

test_resources_dir = Path("resources")
test_data_filename = "expected.json"

BLANK = lyrics.BlankLine
HL = lyrics.HorizontalLine
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
        analysis = lyrics.LyricsFileAnalysis(lines.split("\n"))
        self.assertEqual(len([t for t in analysis.parts if t.is_tracklist]), 1)

    def test_files(self):
        class FileData(CompareEasily):
            def __init__(self, tracklist_lengths, underlines, has_separators, lines_with_scores={}, parts_with_scores={}):
                self.tracklist_lengths = tracklist_lengths
                self.underlines = underlines
                self.has_separators = has_separators
                self.lines_with_scores = lines_with_scores
                self.parts_with_scores = parts_with_scores

        expecteds = {"abneypark.txt": FileData([], 0, True, {"Under the Radar": 0},
                                               {"Under The Radar": 0,
                                                "Under the Radar": 2}),
                     "efrafa.txt": FileData([9], 0, False, {"1. Simulacrum": 1},
                                            {"1. Simulacrum": 2,
                                             "FALL OF EFRAFA LYRICS": 0,
                                             "These throws of rapture": 1}),
                     "pinkfloyd.txt": FileData([13, 13], 27, True, {"2. The Thin Ice 2:30": 2, "THE THIN ICE": 2},
                                               {"1. In the Flesh? 3:19": 0,
                                                "IN THE FLESH ?": 3}),
                     "mesh.txt": FileData([12], 10, True, {"04 - Retaliation.mp3": 1, "4. Retaliation": 2},
                                          {"01 - Firefly.mp3": 0,
                                           "4. Retaliation": 4})}

        for filename in expecteds:
            with self.subTest(filename=filename):
                expected = expecteds[filename]
                analysis = lyrics.LyricsFileAnalysis(lyrics.read_lines_from_file(test_resources_dir / filename))
                actual = FileData([len(tl.lines) for tl in analysis.parts if tl.is_tracklist],
                                  len([und for und in analysis.lines if type(und) is UND]),
                                  analysis.has_separators,
                                  {line: next((l for l in analysis.lines
                                               if type(l) is TEXT and l.line == line)).title_score()
                                   for line in expected.lines_with_scores},
                                  {line: next((p for p in analysis.parts
                                               if p.type is TEXT and p.lines[0].line.startswith(line))).song_begins_score
                                   for line in expected.parts_with_scores})
                self.assertEqual(actual, expected)


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
                    self.assertEqual(lyrics.lyrics_begin_in_file(test_resources_dir / file, song).lines[0].line,
                                     expecteds[file][song])

    test_data_file = test_resources_dir / test_data_filename
    with open(test_data_file) as tf:
        test_data = json.load(tf)

    def test_lyrics_files_exist(self):
        for single_lyrics_file in self.test_data:
            filename = single_lyrics_file['file']
            for single_song in single_lyrics_file['songs']:
                song_title = single_song['title']
                with self.subTest(filename=filename, song_title=song_title):
                    last_line = lyrics.lyrics_end_in_file(test_resources_dir / filename, song_title)
                    self.assertEqual(last_line, single_song['lastLine'])
                    # found_lyrics = lyrics.find_lyrics_in_file(test_resources_dir / filename, song_title)
                    # self.assertEqual(found_lyrics[0], single_song['firstLine'])
                    # self.assertEqual(found_lyrics[-1], single_song['lastLine'])


