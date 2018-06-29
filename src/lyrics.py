#!/usr/bin/python3

import sys
import re
import difflib
import itertools
from mutagen import id3, easyid3
import argparse
from pathlib import Path


# Utility functions


def err(msg):
    print(f"!!! {msg}", file=sys.stderr)


def log(msg):
    print(f">>> {msg}")


def weighed_values(*vals_with_weight):
    return sum(map(lambda val_weight: val_weight[0] * val_weight[1]
                   if type(val_weight) is tuple else val_weight, vals_with_weight))


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


def parse_roman(s, sofar=0):
    if len(s) == 0:
        return sofar
    double = {"cm": -100, "cd": -100, "xc": -10, "xl": -10, "ix": -1, "iv": -1}
    single = {"m": 1000, "d": 500, "c": 100, "l": 50, "x": 10, "v": 5, "i": 1}
    chomp = double.get(s[0:2].lower(), single.get(s[0].lower()))
    if chomp is None:
        raise ValueError("Could not parse roman numeral %s" % s)
    return parse_roman(s[1:], sofar + chomp)


# Handling ID3 tags and MP3 files

uslt_key = 'USLT::eng'


def lyrics_getter(inst, key):
    uslt_frame = inst.get(uslt_key)
    return uslt_frame.text if uslt_frame else None


def lyrics_setter(inst, key, lyrics_arr):
    lyrics = lyrics_arr[0]
    uslt_frame = inst.get(uslt_key)
    if uslt_frame:
        uslt_frame.text = lyrics
    else:
        inst.add(id3.USLT(id3.Encoding.UTF8, lang='eng', desc='', text=lyrics))


def lyrics_deleter(inst, key):
    inst.delall(uslt_key)


def lyrics_lister(inst, key):
    return ['lyrics'] if inst.get(uslt_key) else []


easyid3.EasyID3.RegisterKey('lyrics', lyrics_getter, lyrics_setter, lyrics_deleter, lyrics_lister)


class SongMP3:
    @staticmethod
    def from_path(path):
        def from_file(filename):
            maybe_song = []
            try:
                maybe_song = [SongMP3(filename)]
            finally:
                return maybe_song

        import glob
        from functools import reduce
        return list(reduce(lambda acc, val: acc+val, map(lambda f: from_file(f), sorted(glob.glob(path))), []))

    def __init__(self, mp3file):
        self.path = mp3file
        self.tags = tags = easyid3.EasyID3(str(mp3file))  # mp3_file.tags
        self.title = tags['title'][0] if 'title' in tags else Path(mp3file).stem  # TODO get title from filename only?
        self.album = tags['album'][0] if 'album' in tags else None
        self.artist = tags['artist'][0] if 'artist' in tags \
            else tags['albumartist'][0] if 'albumartist' in tags \
            else None
        self.year = tags['date'][0] if 'date' in tags else None
        if 'tracknumber' in tags:
            m = re.match("(\\d+)(/(\\d+))?", tags['tracknumber'][0])
            if m:
                self.tracknumber = int(m.group(1))
        else:
            self.tracknumber = None

    def __repr__(self):
        return f"Song \"{self.title}\" by {self.artist}, #{self.tracknumber} " \
               f"on the album \"{self.album}\" ({self.year})"


def title_of(song):
    return song.title if type(song) is SongMP3 else str(song)


# Finding song lyrics in a text file

class LineType:
    def __init__(self, prev):
        self.prev = prev
        self.next = None

    @staticmethod
    def of(line, prev=None):
        line = line.strip()
        this = BlankLine(prev) if len(line) == 0 \
            else TextLine(line, prev) if not Separator.looks_like(line) \
            else UnderLine(prev) if type(prev) is TextLine and type(prev.prev) is not TextLine \
            else Separator(prev)
        if prev is not None:
            prev.next = this
        return this

    def is_numbered(self):
        return False

    def is_underlined(self):
        return type(self.next) is UnderLine

    def title_score(self):
        return 0


class BlankLine(LineType):
    pass


class Separator(LineType):
    regex = r"^(\W\W?)\1+\W?$"

    @staticmethod
    def looks_like(line):
        return re.match(Separator.regex, line) is not None


class UnderLine(LineType):
    def __init__(self, prev):
        super().__init__(prev)
        if prev is not None:
            prev.has_underline = True


class TextLine(LineType):
    regex_numbered_line = r"^(?:#?)(\d+|[mdclxvi]+)(\W+)(.+)"
    regex_tracklength = r"(.+)\s+(?:\(\d{1,2}[:]\d\d\)|\d{1,2}[:]\d\d)\s*$"

    def __init__(self, line, prev):
        super().__init__(prev)
        self.number = self.number_separator = None
        self.line = line
        self.essence = line.strip()
        number_match = re.match(TextLine.regex_numbered_line, self.essence)
        if number_match:
            number = number_match.group(1)
            try:
                self.number = int(number) if re.match(r"\d+", number) else parse_roman(number)
            except ValueError:
                pass
            else:
                self.number_separator = number_match.group(2)
                self.essence = number_match.group(3)

        tracklen_match = re.match(TextLine.regex_tracklength, self.essence)
        self.has_tracklength = tracklen_match is not None
        self.essence = tracklen_match.group(1) if self.has_tracklength else self.essence

        self.is_all_uppercase = len(re.sub(r"[^a-z]", "", self.essence)) == 0

    def is_numbered(self):
        return self.number is not None

    def title_score(self):
        return weighed_values((self.is_numbered(), 2), self.has_tracklength, self.is_underlined(), self.is_all_uppercase)


def is_monotonic(ints):
    for idx in range(1, len(ints)):
        if ints[idx] < ints[idx - 1]:
            return False
    return True


class Blob:
    def __init__(self, first_line, prev_part):
        self.type = type(first_line)
        self.lines = [first_line]
        self.is_tracklist = False
        self.prev = prev_part
        self.next = None
        self.blanks = 0
        self.song_begins_score = 0

    def header(self):
        return self.lines[0]

    def merge(self, line):
        merged = False
        if type(line) is BlankLine:
            self.blanks += 1
            merged = True
        elif (type(line) is UnderLine) or (type(line) is self.type
                                           and self.blanks == 0 and not self.header().is_underlined()):
            self.lines.append(line)
            if line.is_numbered() and is_monotonic([l.number for l in self.lines if l.is_numbered()]):
                self.is_tracklist = True
            merged = True
        return merged

    def preceded_by_separator(self):
        return self.prev is None or self.prev.type is Separator or \
               (self.prev.type is BlankLine and self.prev.preceded_by_separator())

    def count_score(self):
        self.song_begins_score = self.header().title_score() + weighed_values(self.preceded_by_separator(), len(self.lines) == 1)

    def to_lines(self):
        return [l.line for l in self.lines] + [""] * self.blanks

    def __repr__(self):
        return self.lines.__repr__()


def analyze_lyrics_file(file_lines):
    first_line, last_line = None, None
    for line in file_lines:
        last_line = LineType.of(line, last_line)
        if first_line is None and type(last_line) is TextLine:
            first_line = last_line

    parts = [Blob(first_line, None)]
    cur_line = first_line.next
    while cur_line is not None:
        if not parts[-1].merge(cur_line):
            last_part = parts[-1]
            parts.append(Blob(cur_line, last_part))
            last_part.next = parts[-1]
        cur_line = cur_line.next

    for part in parts:
        if part.type is TextLine and not part.is_tracklist:
            part.count_score()

    return parts


def normalize(line):
    return re.sub(r"\s", "", line.lower())


def vector_diff(of, model):
    import math
    diffs = 0.0
    for key in model:
        diffs += (of[key] - model[key]) ** 2
    return math.sqrt(diffs)


def ratio(a, b):
    return a / b if a <= b else b / a


def similarity(title, model_vector):
    normalized_title = normalize(title)

    def title_isjunk(c):
        return c in ['\'`']

    def similarity_to(line, init_vector):
        normalized_line = normalize(line)
        seqmat = difflib.SequenceMatcher(title_isjunk, normalized_title, normalized_line)
        matching = seqmat.get_matching_blocks()
        longest_exact_match = sorted(matching, key=lambda mt: mt.size, reverse=True)[0]
        after_match = normalized_line[(longest_exact_match.b + longest_exact_match.size):]
        vector = {**init_vector, **{
            "similarity_whole": seqmat.ratio(),
            "longest_exact_match": ratio(longest_exact_match.size, len(normalized_title)),
            "nothing_after_match": (len(after_match) == 0) or (not after_match[0].isalnum())
        }}

        return vector_diff(vector, model_vector)

    return similarity_to


def find_song_header(file_lines, song_title):
    parts = analyze_lyrics_file(file_lines)
    similarity_threshold = 0.9
    song_title_score_histogram = dict(map(lambda k: (k[0], list(k[1])),
                                          itertools.groupby(sorted(filter(lambda p: p.song_begins_score > 0, parts),
                                                                   key=lambda p: p.song_begins_score),
                                                            key=lambda p: p.song_begins_score)))
    model_song_title_score = \
        sorted(song_title_score_histogram, key=lambda k: k ** 2 * len(song_title_score_histogram[k]), reverse=True)[0]
    model_vector = {"similarity_whole": 1.0,
                    "longest_exact_match": 1.0,
                    "nothing_after_match": True,
                    "title_score": 1.0}
    similarity_to = similarity(song_title, model_vector)
    parts_with_ratio = {
        p: similarity_to(p.header().essence, {"title_score": p.song_begins_score / model_song_title_score})
        for p in parts if p.song_begins_score > 0}
    try:
        return sorted([p for p in parts_with_ratio if parts_with_ratio[p] <= similarity_threshold],
                      key=lambda part: parts_with_ratio[part])[0]
    except IndexError:
        return None


def trim_empty_lines(arr):
    first, last = 0, len(arr) - 1
    while first <= last and arr[first] == "":
        first += 1
    while first <= last and arr[last] == "":
        last -= 1
    return arr[first:last + 1]


def get_lyrics_from_file(lyrics_file, song):
    song_title = title_of(song)
    file_lines = read_lines_from_file(lyrics_file)
    if len(file_lines) == 0:
        err(f"> File {lyrics_file} is empty.")
        return None

    lyrics_header = find_song_header(file_lines, song_title)
    if lyrics_header is None:
        err(f"> Lyrics for {song_title} not found in {lyrics_file}.")
        return None

    title_score = lyrics_header.song_begins_score
    lyrics = [] if lyrics_header.header().is_underlined() else lyrics_header.to_lines()[1:]
    cur_part = lyrics_header
    while cur_part.next is not None:
        next_part = cur_part.next
        if next_part.type is Separator or ((next_part.type is TextLine)
                                           and (next_part.song_begins_score >= title_score)):
            break
        if next_part.type in [TextLine, BlankLine]:
            lyrics += next_part.to_lines()
        cur_part = cur_part.next
    lyrics = trim_empty_lines(lyrics)
    return "\r\n".join(lyrics) if len(lyrics) > 0 else None


# Parsing arguments


parser = argparse.ArgumentParser(prog="LYRICS",
                                 description="Find lyrics for given song(s) within mp3 tags or text file.\n"
                                             "Prints it out to console, to a txt file or saves it to mp3 tags.")

# SONGS - this can be a (possibly wildcard) path if you want one (or more) mp3 files.
# If path doesn't resolve to any mp3 files, this is treated as a explicitly given song title.
parser.add_argument('songs',
                    help="Song or songs to look for lyrics to. By default resolves to mp3 file "
                         "(or multiple files if wildcard path is given, to resolve one file at a time).\n"
                         "If it doesn't point to any mp3 file, it is treated as explicitly given song title.")

# SOURCE - source of lyrics: if not given, defaults to, in that order: mp3 tag, local txt file.
# If given, is resolved to a txt file to look for lyrics in.
parser.add_argument('--from', '-f',  dest='source', nargs='?', default='TAG', const='DEFAULT FILE',
                    help="Name of the lyrics text file to look in. If not given, looks for default file.\n"
                         "If argument is omitted entirely, looks first in mp3 tag (if available) and then default file.")

# TARGET - what to do with obtained lyrics? Save to txt file? Append to file? Print out to stdout?
# By default prints out.
parser.add_argument('--to', '-t', '-2', dest='target',
                    help="Target for the obtained lyrics. Defaults to print out to console.\n"
                         "If given, saves to given txt file. If the file exists, the lyrics will be appended.")
# OUT - flag to print lyrics to console
parser.add_argument('--out', '-o', action='store_true',
                    help="Flag to print obtained lyrics out to console. Need to be explicitly given if any other "
                         "target argument (--out or --save) is used and you still want to print out the lyrics.")
# SAVE - flag to save lyrics to mp3 file(s) tags
parser.add_argument('--save', action='store_true',
                    help="Flag to save obtained lyrics to an ID3 tag in respective mp3 file(s)'.\n"
                         "If given, lyrics will not be printed out unless --to option is given specifically")

args = parser.parse_args()

# existing files matching the given path
songs = SongMP3.from_path(args.songs)
if not songs:
    songs = [args.songs]


def find_default_files(song):
    directory = Path(".")
    txt_file_templates = [r'lyrics']
    if type(song) is SongMP3:
        directory = Path(song.path).parent
        if song.album is not None:
            txt_file_templates.append(song.album.lower())
            if song.artist is not None:
                txt_file_templates.append(song.artist.lower() + " - " + song.album.lower())
    simi_threshold = 0.6
    txt_files = [f for f in directory.iterdir() if f.suffix == ".txt"]
    return (triple[0] for triple in sorted(
        filter(lambda triple: triple[2] > simi_threshold,
               [(file, template, difflib.SequenceMatcher(None, file.stem.lower(), template).ratio())
                for file in txt_files
                for template in txt_file_templates]),
        key=lambda triple: triple[2], reverse=True))


def get_lyrics_from_default_file(song):
    for filename in find_default_files(song):
        lyrics = get_lyrics_from_file(filename, title_of(song))
        if lyrics is not None:
            return lyrics, filename


def get_lyrics_from_tag(song, failover=get_lyrics_from_default_file):
    if type(song) is SongMP3 and song.tags['lyrics']:
        return song.tags['lyrics'], 'TAG'
    elif failover is not None:
        return failover(song)


def find_song_lyrics(song, source):
    if source == 'TAG':  # from tags or find txt file
        return get_lyrics_from_tag(song)
    elif source == 'DEFAULT FILE':
        return get_lyrics_from_default_file(song)
    else:
        return get_lyrics_from_file(source, title_of(song)), source


song_lyrics = {}
for song in songs:
    lyrics = find_song_lyrics(song, args.source)
    if lyrics is not None:
        log(f"Found lyrics for {title_of(song)} in {lyrics[1]}")
        song_lyrics[song] = lyrics[0]

for song in songs:
    if song in song_lyrics:
        print(song_lyrics[song])



### params:
# $ lyrics.py
# $ -4 --for [song mp3 file(s) or song title(s); REQUIRED]
# $ -s --source [txt file if 'txt' or specified and exists, tag in mp3 file if 'tag', url to a lyrics service if given, DEFAULT mp3 tag or automatically found lyrics file]
# $ --to [txt file if given, mp3 tag if 'tag', DEFAULT write to screen]
# $ --write [shorthand for --to tag]

# TODO:
# parsing args
# reading tags from mp3 file (see lyricsfor.py) -> done
# reading lyrics from txt file (see lyricsfor.py)
# finding default txt file (see lyricsfor.py)
# saving lyrics to txt file
# saving lyrics to mp3 tag
# querying internet lyrics databases:
#    ???
