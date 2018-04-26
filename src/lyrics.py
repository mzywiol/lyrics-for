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
from enum import Enum


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


class LineType(Enum):
    BLANK = 1
    SEPARATOR = 2
    TEXT = 3

    @staticmethod
    def of(line):
        if len(line) == 0:
            return LineType.BLANK
        if re.match(regex_separator, line):
            return LineType.SEPARATOR
        return LineType.TEXT


class FileData:
    def __init__(self):
        self.lines = []
        self.separators = {}  # line number => separator type (i.e. specific symbols used)


class Line:
    def __init__(self, line):
        self.line = line.strip()
        self.type = LineType.of(self.line)


def find_lyrics_in_file(lyrics_file, songtitle):
    file_lines = read_lines_from_file(lyrics_file)
    if len(file_lines) == 0:
        err("> File %s is empty." % lyrics_file)
        return None

    return None





