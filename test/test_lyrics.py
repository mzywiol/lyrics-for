import unittest
import json
from pathlib import Path
from src import lyrics

test_resources_dir = Path("resources")
test_data_filename = "expected_short.json"

BLANK = lyrics.BlankLine
HL = lyrics.HorizontalLine
TEXT = lyrics.TextLine


class LinesTest(unittest.TestCase):
    def test_blank(self):
        self.assertIsInstance(lyrics.LineType.of(""), BLANK)
        self.assertIsInstance(lyrics.LineType.of("   "), BLANK)
        self.assertIsInstance(lyrics.LineType.of("\t"), BLANK)

    def test_horizontal_line(self):
        def assert_hl(from_string, expected_root):
            hl = lyrics.LineType.of(from_string)
            self.assertIsInstance(hl, HL)
            self.assertEqual(hl.root, expected_root)
        assert_hl("--", "--")
        assert_hl("---", "--")
        assert_hl("------------------", "--")
        assert_hl("===", "==")
        assert_hl("=======================", "==")
        assert_hl("*****************************", "**")
        assert_hl("^^^^^^^^^^", "^^")
        assert_hl("~~~~~~", "~~")
        assert_hl("-=-=-", "-=")
        assert_hl("-=-=", "-=")
        assert_hl("*&*&*&*&*&*&*&*&*&*&*&*&*", "*&")
        assert_hl("*&*&*&*&*&*&*&*&*&*&*&*&", "*&")

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
        
        Three
        -=-=-"""
        expected_types = [TEXT, BLANK, TEXT, TEXT, HL, BLANK, TEXT, HL]
        analysis = lyrics.LyricsFileAnalysis(lines.split("\n"))
        self.assertEqual([type(l) for l in analysis.lines], expected_types)
        self.assertEqual(analysis.separators, {4: "==", 7: "-="})

    def test_underline(self):
        lines = """First line
        
        
        Single line before underline
        ======
        
        Blob line 1
        Blob line 2
        
        ---
        
        Single line after separator
        
        Blob line 1
        Blob line 2
        
        ---
        Single line between separators - below is underline
        ======
        
        Single line at the end"""
        analysis = lyrics.LyricsFileAnalysis(lines.split("\n"))
        self.assertEqual([analysis.lines[sep].root for sep in analysis.separators if analysis.lines[sep].underline],
                         ["==", "=="])


# class LyricsTest(unittest.TestCase):
#     test_data_file = test_resources_dir / test_data_filename
#     with open(test_data_file) as tf:
#         test_data = json.load(tf)
#
#     def test_lyrics_files_exist(self):
#         for single_lyrics_file in self.test_data:
#             filename = single_lyrics_file['file']
#             for single_song in single_lyrics_file['songs']:
#                 song_title = single_song['title']
#                 with self.subTest(filename=filename, song_title=song_title):
#                     found_lyrics = lyrics.find_lyrics_in_file(test_resources_dir / filename, song_title)
#                     self.assertEqual(found_lyrics[0], single_song['firstLine'])
#                     self.assertEqual(found_lyrics[-1], single_song['lastLine'])


