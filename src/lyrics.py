#!/usr/bin/python3

import sys
import re
import difflib

# Utility functions


def err(msg):
    print(f"!!! ${msg}", file=sys.stderr)


def log(msg):
    print(f">>> ${msg}")


def truths(*bools):
    return len([b for b in bools if b])


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


regex_separator = r"^(\W\W?)\1*\W?$"
regex_numbered_line = r"^(?:#?)(\d+)(\W+)(.+)"
regex_tracklength = r"(.+)\s+(?:\(\d{1,2}[:]\d\d\)|\d{1,2}[:]\d\d)\s*$"

# Meat


class LineType:
    def __init__(self, prev):
        self.prev = prev
        self.next = None

    @staticmethod
    def of(line, prev=None):
        line = line.strip()
        this = BlankLine(prev) if len(line) == 0 \
            else TextLine(line, prev) if not re.match(regex_separator, line) \
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
    def __repr__(self):
        return ""


class Separator(LineType):
    def __repr__(self):
        return "==="


class UnderLine(LineType):
    def __init__(self, prev):
        super().__init__(prev)
        if prev is not None:
            prev.has_underline = True

    def __repr__(self):
        return "___"


class TextLine(LineType):
    def __init__(self, line, prev):
        super().__init__(prev)
        self.line = line
        number_match = re.match(regex_numbered_line, self.line)
        (self.number, self.number_separator, self.essence) = \
            (int(number_match.group(1)), number_match.group(2), number_match.group(3)) if number_match \
            else (None, None, line.strip())
        tracklen_match = re.match(regex_tracklength, self.essence)
        (self.has_tracklength, self.essence) = \
            (True, tracklen_match.group(1)) if tracklen_match \
            else (False, self.essence)
        self.is_all_uppercase = len(re.sub(r"[^a-z]", "", self.essence)) == 0

    def is_numbered(self):
        return self.number is not None

    def __repr__(self):
        return f"{self.line[:7]}..."

    def title_score(self):
        return truths(self.is_numbered(), self.has_tracklength, self.is_underlined(), self.is_all_uppercase)


def monotonic(ints):
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
            if line.is_numbered() and monotonic([l.number for l in self.lines if l.is_numbered()]):
                self.is_tracklist = True
            merged = True

        return merged

    def preceded_by_separator(self):
        return self.prev is None or self.prev.type is Separator or \
               (self.prev.type is BlankLine and self.prev.preceded_by_separator())

    def count_score(self):
        self.song_begins_score = self.lines[0].title_score() + truths(self.preceded_by_separator(), len(self.lines) == 1)

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
    return a/b if a <= b else b/a


def similarity(title, model_vector):
    normalized_title = normalize(title)

    def title_isjunk(c):
        return c in ['\'`']

    def similarity_to(line):
        normalized_line = normalize(line)
        vector = {
            # ratio of SequenceMatcher for the whole line
            "similarity_whole": difflib.SequenceMatcher(title_isjunk, normalized_title, normalized_line).ratio(),
            # "similarity_longest": 0.0,
            # "longest_length_ratio": 0.0
        }
        seqmat = difflib.SequenceMatcher(title_isjunk, normalized_title, normalized_line)
        matching = seqmat.get_matching_blocks()

        # longest exact match
        longest_exact_match = sorted(matching, key=lambda mt: mt.size, reverse=True)[0]
        vector["longest_exact_match"] = ratio(longest_exact_match.size, len(normalized_title))
        after_match = normalized_line[(longest_exact_match.b + longest_exact_match.size):]
        vector["nothing_after_match"] = (len(after_match) == 0) or (not after_match[0].isalnum())

        # longest match: where first exact match starts to where last exact match ends
        # if len(matching) > 1:
        #     longest_match_begins = matching[0].b
        #     longest_match_ends = matching[-2].b + matching[-2].size
        #     longest_match = normalized_line[longest_match_begins:longest_match_ends]
        #     vector["similarity_longest"] = difflib.SequenceMatcher(title_isjunk, normalized_title, longest_match).ratio()
        #     vector["longest_length_ratio"] = ratio(len(longest_match), len(normalized_title))

        return vector_diff(vector, model_vector)

    return similarity_to


def find_song_header(lyrics_file, song_title):
    parts = analyze_lyrics_file(read_lines_from_file(lyrics_file))
    scores = sorted(set([p.song_begins_score for p in parts if p.song_begins_score > 0]), reverse=True)
    similarity_threshold = 0.9
    model_vector = {"similarity_whole": 1.0,
                    "longest_exact_match": 1.0,
                    "nothing_after_match": True}
    similarity_to = similarity(song_title, model_vector)
    for s in scores:
        parts_with_ratio = {p: similarity_to(p.lines[0].essence) for p in parts
                            if p.song_begins_score == s}
        try:
            return sorted([p for p in parts_with_ratio if parts_with_ratio[p] <= similarity_threshold],
                          key=lambda part: parts_with_ratio[part])[0]
        except IndexError:
            continue
    return None


def strip(arr):
    first, last = 0, len(arr)-1
    while first <= last and arr[first] == "":
        first += 1
    while first <= last and arr[last] == "":
        last -= 1
    return arr[first:last+1]


def find_lyrics_in_file(lyrics_file, song_title):

    file_lines = read_lines_from_file(lyrics_file)
    if len(file_lines) == 0:
        err(f"> File {lyrics_file} is empty.")
        return None

    lyrics_header = find_song_header(lyrics_file, song_title)
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
    lyrics = strip(lyrics)
    return lyrics if len(lyrics) > 0 else None


# ======================================
# stuff for reading from and saving to mp3 tags...


from mutagen import id3, easyid3


def lyrics_getter(inst, key):
    uslt_key = 'USLT::eng'
    uslt_frame = inst.get(uslt_key)
    return uslt_frame.text if uslt_frame else None


def lyrics_setter(inst, key, lyrics_arr):
    lyrics = lyrics_arr[0]
    uslt_key = 'USLT::eng'
    uslt_frame = inst.get(uslt_key)
    if uslt_frame:
        uslt_frame.text = lyrics
    else:
        inst.add(id3.USLT(id3.Encoding.UTF8, lang='eng', desc='', text=lyrics))


def lyrics_deleter(inst, key):
    uslt_key = 'USLT::eng'
    inst.delall(uslt_key)


def lyrics_lister(inst, key):
    uslt_key = 'USLT::eng'
    return ['lyrics'] if inst.get(uslt_key) else []


easyid3.EasyID3.RegisterKey('lyrics', lyrics_getter, lyrics_setter, lyrics_deleter, lyrics_lister)


class SongMP3:

    def __init__(self, mp3file):
        self.file = mp3file
        self.tags = tags = easyid3.EasyID3(str(mp3file))  # mp3_file.tags
        self.title = tags['title'][0]
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

    def __unicode__(self):
        return f"Song \"{self.title}\" by {self.artist}, #{self.tracknumber} " \
               f"on the album \"{self.album}\" ({self.year})"

    def __str__(self):
        return self.__unicode__()
