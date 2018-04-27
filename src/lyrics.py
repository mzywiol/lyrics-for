#!/usr/bin/python3

"""
approach: analyze file, look for structure: separators, song lyric headlines format, look for promising lines and

record separators (their format, symbols used)
    are they before headline? SEPARATOR or UNDERLINE or both
        if there are pairs very close to each other, then both
record lines starting with numbers
    analyze: are they incremental?
    is there more than one incremental set? -> may be multiple disc, may be tracklist at the beginning
        divide into incremental sets
        secord separator after number (. or ) or anything else)
        is there tracklength at the end?
            record for this set
        are the numbered lines close to each other? -> indicates tracklist
        are there separators before or after each numbered line? -> indicates lyrics; record
    ignore tracklists
if SEPARATORS and NUMBERED LINES:
    find numbered line with song title just before or after a SEPARATOR -> this is where LYRIC BEGIN
    //ignore UNDERLINE
    find another separator -> this is where LYRIC ENDS
if NUMBERED LINES only:
    find numbered line with song title -> this is where LYRIC BEGIN
    find next numbered line -> this is where LYRIC ENDS
if SEPARATOR only:
    check lines just before and just after the SEPARATORS for their similarity to the title
    if just before, SEPARATOR is UNDERLINE -> this is where LYRIC BEGIN
    find another separator -> this is where LYRIC ENDS
if neither:
    find lines containing title
    lines ending with song length are good candidates for headline -> this is where LYRIC BEGIN
        otherwise, evaluate by similarity
        the first most similar will be where LYRIC BEGIN
    consume lines until first GAP longer than previous GAPS. -> this is where LYRIC ENDS
"""

import sys
import re


def err(msg):
    print(f"!!! ${msg}", file=sys.stderr)


def log(msg):
    print(f">>> ${msg}")


# Find lyrics in file

def read_lines_from_file(filename):
    import chardet
    with open(filename, 'rb') as bytefile:
        encoding = chardet.detect(bytefile.read())['encoding']
    with open(filename, "r", encoding=encoding) as f:
        try:
            filelines = f.readlines()
        except UnicodeDecodeError:
            with open(filename, "r", encoding='ansi') as ansif:
                filelines = ansif.readline()
    return filelines


class LyricsFile:
    parts = []  # sequence of file parts: blobs, blank spaces and separators
    separators = []


regex_separator = r"^(\W\W?)\1*\W?$"
regex_numbered_line = r"^(?:#?)(\d+)(\W+)\w*"
regex_tracklength = r"\d{1,2}[:]\d\d\s*$"


class LineType:

    @staticmethod
    def of(line):
        line = line.strip()
        if len(line) == 0:
            return BlankLine()
        hl_match = re.match(regex_separator, line)
        if hl_match:
            return HorizontalLine()
        return TextLine(line)

    def is_numbered(self):
        return False

    def is_underline(self):
        return False


class BlankLine(LineType):
    def __repr__(self):
        return ""


class HorizontalLine(LineType):
    def __init__(self):
        self.underline = False

    def is_underline(self):
        return self.underline

    def __repr__(self):
        return "___" if self.is_underline() else "==="


class TextLine(LineType):
    def __init__(self, line):
        self.line = line
        number_match = re.match(regex_numbered_line, self.line)
        (self.number, self.number_separator) = \
            (int(number_match.group(1)), number_match.group(2)) if number_match \
            else (None, None)

    def is_numbered(self):
        return self.number is not None

    def __repr__(self):
        return f"${self.line[:7]}..."


def monotonic(ints):
    for idx in range(1, len(ints)):
        if ints[idx] < ints[idx - 1]:
            return False
    return True


def windows(seq, siz=2):
    return [seq[ln:ln + siz] for ln in range(0, len(seq) - siz + 1)]


class LyricsFileAnalysis:
    class FilePart:
        def __init__(self, file, first_line, line_no):
            self.file = file
            self.type = type(first_line)
            self.range_starts = line_no
            self.range_ends = line_no
            self.tracklist = False

        def lines(self):
            return self.file.lines[slice(self.range_starts, self.range_ends + 1)]

        def __len__(self):
            return self.range_ends - self.range_starts + 1

        def merge(self, line):
            if self.type == HorizontalLine:
                return False

            if type(line) is self.type:
                self.range_ends += 1
                if line.is_numbered() and monotonic([l.number for l in self.lines() if l.is_numbered()]):
                    self.tracklist = True
                return True
            return False

    def __init__(self, lines):
        self.lines = [BlankLine()] + [LineType.of(line) for line in lines]
        for win in windows(self.lines, 3):
            if [type(l) for l in win[1:]] == [TextLine, HorizontalLine] and type(win[0]) in [BlankLine, HorizontalLine]:
                win[2].underline = True

        self.parts = [self.FilePart(self, self.lines[0], 0)]
        for ln, line in enumerate(self.lines[1:]):
            if not self.parts[-1].merge(line):
                self.parts.append(self.FilePart(self, line, ln))


def find_lyrics_in_file(lyrics_file, songtitle):
    file_lines = read_lines_from_file(lyrics_file)
    if len(file_lines) == 0:
        err("> File %s is empty." % lyrics_file)
        return None

    return None





