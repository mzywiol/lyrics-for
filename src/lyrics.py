#!/usr/bin/python3

'''
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
'''

import sys
from pathlib import Path


def err(msg):
    print(f"!!! ${msg}", file=sys.stderr)


def log(msg):
    print(f">>> ${msg}")


# Find lyrics in file

def find_lyrics_in_file(lyricsfile, songtitle):
    pass


# Parsing arguments

lyricsfilename = sys.argv[1] if len(sys.argv) > 1 else None
songtitle = sys.argv[2].strip() if len(sys.argv) > 2 else None

if lyricsfilename and songtitle:
    lyricsfile = Path(lyricsfilename)
    if not lyricsfile.is_file():
        err("File doesn't exist: %s" % lyricsfile)
        exit(1)
    if len(songtitle) == 0:
        err("Song title empty")
        exit(1)
    lyricsfile = lyricsfile.resolve()


