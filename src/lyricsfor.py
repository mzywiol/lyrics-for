#!/usr/bin/python3

import sys
from mutagen import id3, easyid3
from pathlib import Path
import re
from unidecode import unidecode
import difflib
from enum import Enum


def err(msg):
    print("!!! %s" % msg, file=sys.stderr)


def log(msg):
    print(">>> %s" % msg)


# Parsing arguments

if len(sys.argv) == 1:
    err("No file specified")
    exit(1)

songfile = Path(sys.argv[1])
if not songfile.is_file():
    err("File doesn't exist: %s" % songfile)
    exit(1)
songfile = songfile.resolve()

# Methods to easy access lyrics tag in file


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

# Finding lyrics file(s) in the song file's directory


def strip_the(name):
    return re.sub(re.compile("^the |, the$", re.IGNORECASE), "", name)


def justletters(line):
    return re.sub("\\W", "", unidecode.unidecode(line.lower()))


def normalize(string):
    return unidecode(string).lower()


class Song:

    all_songs = []

    _lyrics_parts = None

    def __init__(self, file):
        self.file = file
        # mp3_file = mp3.EasyMP3(str(file))
        # self.length = int(mp3_file.info.length)
        self.tags = tags = easyid3.EasyID3(str(file))  # mp3_file.tags
        self.title = normalize(tags['title'][0])
        self.album = normalize(tags['album'][0]) if 'album' in tags else None
        self.artist = strip_the(normalize(tags['artist'][0])) if 'artist' in tags \
            else strip_the(normalize(tags['albumartist'][0])) if 'albumartist' in tags \
            else None
        self.year = tags['date'][0] if 'date' in tags else None

        if 'tracknumber' in tags:
            trck = tags['tracknumber'][0]
            m = re.match("(\\d+)(/(\\d+))?", trck)
            if m:
                self.tracknumber = int(m.group(1))
                self.tracks = int(m.group(3)) if m.group(3) else None
        else:
            self.tracknumber = self.tracks = None

        if 'discnumber' in tags:
            trck = tags['discnumber'][0]
            m = re.match("(\\d+)(/(\\d+))?", trck)
            if m:
                self.discnumber = int(m.group(1))
                self.discs = int(m.group(3)) if m.group(3) else None
        else:
            self.discnumber = self.discs = None

        self.index = len(self.all_songs)
        Song.all_songs.append(self)
        self._lyrics_parts = None

    def lyrics_regex(self):
        regexes = ['lyrics']
        if self.album and self.artist:
            regexes += ["(the )?{0}\\W+{1}|{1}\\W+(the )?{0}".format(self.artist.lower(), self.album.lower())]
        if self.album:
            regexes += [self.album.lower()]
        return regexes

    def apply_lyrics_from_file(self, lyrics_for_songs):
        if self.index < len(lyrics_for_songs):
            lyrics_head = lyrics_for_songs[self.index]['part']  # todo: this fails when lyrics for a song are not in the file at all.
            #  todo: but this needs to be fixed anyway, as finding the end of lyrics is just wrong: see Pink Floyd - The Wall 1.13 Goodbye Cruel World
            next_song_lyrics = lyrics_for_songs[self.index + 1]['part'] if self.index+1 < len(lyrics_for_songs) else None
            self._lyrics_parts = []
            while lyrics_head != next_song_lyrics:
                self._lyrics_parts.append(lyrics_head)
                lyrics_head = lyrics_head.next

    def lyrics_from_file(self):
        if self._lyrics_parts is not None:
            return "".join([str(part) for part in self._lyrics_parts])

    def next(self):
        return self.all_songs[self.index + 1] if self.index + 1 < len(self.all_songs) else None

    def __unicode__(self):
        return "Song \"{0}\" by {1}, #{4}/{5} on the album \"{2}\" ({3}) disc {6}/{7}".format(
            self.title, self.artist, self.album, self.year, self.tracknumber or "?", self.tracks or "?",
            self.discnumber or "?", self.discs or "?"
        )

    def __str__(self):
        return self.__unicode__()


list(map(Song, sorted(iter(filter(lambda f: f.suffix == songfile.suffix, songfile.parent.iterdir())),
                      key=lambda f: f.name)))

given_song = next(iter(filter(lambda s: s.file == songfile, Song.all_songs)))

log(given_song)


# Looking for potential files with lyrics


def find_candidates(directory, rgx, album):

    txt_files = list(filter(lambda txt: txt.suffix.lower() == ".txt", directory.iterdir()))
    found = txt_files if len(txt_files) else [f for f in txt_files if any(map(lambda lr: re.match(lr, f.name), rgx))]
    return find_candidates(directory.parent, rgx, album) if len(found) == 0 and album in directory.parent.name.lower() \
        else found


candidates_lyrics_file = find_candidates(songfile.parent, given_song.lyrics_regex(), given_song.album)
if len(candidates_lyrics_file) == 0:
    print("Didn't find any candidates for lyrics file.")
    exit(2)

lyrics_file = str(candidates_lyrics_file[0])
log("Looking for lyrics in file %s" % lyrics_file)

# Analyze the contents of lyrics file:
# 1. Label each line with a type & Combine subsequent lines of the same type into groups


def read_lines(filename):
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


file_lines = read_lines(lyrics_file)
if len(file_lines) == 0:
    err("> File %s is empty." % lyrics_file)
    exit(3)


class LineType:
    BLANK = "BLANK"  # empty line
    HL = "HL"  # horizontal line
    TEXT = "TEXT"

    @staticmethod
    def of(line):
        stripped = line.strip()
        if len(stripped) == 0:
            return LineType.BLANK
        if re.match("^(\\W)\\1+$", line):
            return LineType.HL
        return LineType.TEXT


class Part:
    class Label(Enum):
        SEPARATOR = "SEPARATOR"  # more than one blank line and separator(s)
        TEXT = "TEXT"

    class PartIterator:
        def __init__(self, head):
            self.cur = Part("")
            self.cur.next = head

        def __iter__(self):
            return self

        def __next__(self):
            if self.cur.next is None:
                raise StopIteration
            else:
                self.cur = self.cur.next
                return self.cur

    prev = None
    next = None
    underline = False
    blank_line = False

    def __init__(self, line, prev=None):
        label = LineType.of(line)
        self.label = Part.Label.TEXT if label == LineType.TEXT else Part.Label.SEPARATOR
        self.lines = [line]
        self.prev = prev
        self.next = None

    def __iter__(self):
        return Part.PartIterator(self)

    @staticmethod
    def init(line):
        return Part(line)

    def _append(self, line):
        if self.label == Part.Label.TEXT and LineType.of(line) == LineType.BLANK:
            self.blank_line = True
        elif self.label == Part.Label.TEXT and LineType.of(line) == LineType.HL:
            self.underline = True
        else:
            self.lines.append(line)
        return self

    def combine(self, line):
        should_append = {
            LineType.TEXT:  self.label == Part.Label.TEXT and not self.blank_line and not self.underline,
            LineType.BLANK: self.label == Part.Label.SEPARATOR or not self.blank_line,
            LineType.HL:    self.label == Part.Label.SEPARATOR or (self.label == Part.Label.TEXT and self.len() == 1)
        }
        if should_append[LineType.of(line)]:
            return self._append(line)
        else:
            self.next = Part(line, self)
            return self.next

    def len(self):
        return len(self.lines)

    def header(self):
        return self.lines[0].lower()

    def __str__(self):
        return "".join(self.lines) + "{0}{1}".format("=========================\n" if self.underline else "",
                                                     "\n" if self.blank_line else "")


class TitleIndicator:
    class HeaderFactors(Enum):
        SIMILAR_RATIO = 1
        TRACK_NUMBER = 2
        TRACK_NUMBER_CORRECT = 3
        TRACK_LENGTH = 4

    class ContextFactors(Enum):
        PRECEDED_BY_SEPARATOR = 101
        UNDERLINE = 102
        SINGLE_LINE = 103
        TRACKLIST = 104

    weights = {
        HeaderFactors.SIMILAR_RATIO: 14,
        HeaderFactors.TRACK_NUMBER: 1,
        HeaderFactors.TRACK_NUMBER_CORRECT: 1,
        HeaderFactors.TRACK_LENGTH: 1,
        ContextFactors.PRECEDED_BY_SEPARATOR: 1,
        ContextFactors.UNDERLINE: 1,
        ContextFactors.SINGLE_LINE: 2,
        ContextFactors.TRACKLIST: -10
    }

    title_threshold = 14

    cache = {}

    def factor_for(self, fac):
        return self.factors[fac] if fac in self.factors else 0

    def header_factors(self, header, song):
        seqmat = difflib.SequenceMatcher(lambda c: c in ['\'`'], song.title, header)
        matching = seqmat.get_matching_blocks()
        factors = {self.HeaderFactors.SIMILAR_RATIO: 0}
        if len(matching) > 1:
            longest_match_begins = matching[0].b
            longest_match_ends = matching[-2].b + matching[-2].size
            longest_match = header[longest_match_begins:longest_match_ends] if len(matching) > 1 else ""
            factors[self.HeaderFactors.SIMILAR_RATIO] = difflib.SequenceMatcher(None, song.title, longest_match).ratio()
            pre_title = header[:longest_match_begins]
            post_title = header[longest_match_ends:]

            re_trackno = "(?:.*\\D|^)(\\d{1,2})\\D"
            match_trackno = re.match(re_trackno, pre_title)
            if match_trackno:
                factors[self.HeaderFactors.TRACK_NUMBER] = True
                trackno = int(match_trackno.group(1))
                factors[self.HeaderFactors.TRACK_NUMBER_CORRECT] = trackno == song.tracknumber

            re_tracklen = "(?:.*\\D|^)((\\d{1,2})[^\\d\\s](\\d{2}))(?:\\D|$)"
            match_tracklen = re.match(re_tracklen, post_title)
            factors[self.HeaderFactors.TRACK_LENGTH] = match_tracklen is not None
        return factors

    def context_headers(self, part):
        factors = {}
        if part.len() == 1:
            factors[self.ContextFactors.SINGLE_LINE] = True
        if part.is_underline:
            factors[self.ContextFactors.UNDERLINE] = True
        if part.prev is None or part.prev.label == Part.Label.SEPARATOR:
            factors[self.ContextFactors.PRECEDED_BY_SEPARATOR] = True
        return factors

    def check_if_tracklist(self, part, songs):
        def index_of(predicate, sequence):
            for i, val in enumerate(sequence):
                if predicate(val):
                    return i
            return -1

        title_similarity_threshold = 0.6
        rem_lines_idx = 0
        titles_found = 0
        for s in songs:
            found_at_idx = index_of(
                lambda l: self.header_factors(l, s)[self.HeaderFactors.SIMILAR_RATIO] >= title_similarity_threshold,
                part.lines[rem_lines_idx:]
            )
            if found_at_idx >= 0:
                titles_found += 1
                rem_lines_idx = found_at_idx

        return {self.ContextFactors.TRACKLIST: True} if titles_found >= 0.6 * len(songs) else {}

    def __init__(self, part, song):
        self.factors = {}
        if (song, part) in TitleIndicator.cache:
            self.factors = TitleIndicator.cache[song, part].factors
            return

        self.factors.update(self.header_factors(part.header().strip(), song))
        self.factors.update(self.context_headers(part))
        if song.index == 0 and self.score() >= self.title_threshold and part.len() >= len(song.all_songs):
            self.factors.update(self.check_if_tracklist(part, song.all_songs))
        TitleIndicator.cache[song, part] = self

    def score(self):
        return sum([self.factors[f] * self.weights[f] for f in self.factors])

    @staticmethod
    def of(song, part):
        if (song, part) in TitleIndicator.cache:
            return TitleIndicator.cache.get((song, part))
        else:
            return TitleIndicator(part, song)

    @staticmethod
    def score_for(song, part):
        return TitleIndicator.of(song, part).score()


def cut_into_parts(lines):
    tail = head = Part.init(lines[0])
    for line in lines[1:]:
        tail = tail.combine(line)
    return head


head_part = cut_into_parts(file_lines)


def candidates_for_song_lyrics(songs, head):
    def updated_list(original, with_value, on_index):
        from copy import copy
        new_array = copy(original)
        new_array[on_index] = with_value
        return new_array

    def find_candidate_for_song_lyrics(song, from_part, titles_for_songs, candidates_with_score):
        went_deeper = False
        if song and from_part:
            for part in iter(from_part):
                if part.label == Part.Label.SEPARATOR:
                    continue
                score = TitleIndicator.score_for(song, part)
                if score >= TitleIndicator.title_threshold:
                    went_deeper = True
                    find_candidate_for_song_lyrics(song.next(),
                                                   part.next,
                                                   updated_list(titles_for_songs,
                                                                {'part': part, 'score': score},
                                                                song.index),
                                                   candidates_with_score)

        if not went_deeper:
            candidates_with_score.append({'parts': titles_for_songs,
                                          'score': sum(map(lambda ps: 0 if ps is None else ps['score'],
                                                           titles_for_songs))})

        return candidates_with_score

    return sorted(find_candidate_for_song_lyrics(songs[0], head, [None] * len(songs), []),
                  key=lambda can: can['score'],
                  reverse=True)


candidates_for_lyrics_per_song = candidates_for_song_lyrics(given_song.all_songs, head_part)

log("Found %s options for song lyrics:" % len(candidates_for_lyrics_per_song))
# for c in candidates_for_lyrics_per_song:
#     log("{0}, score: {1}".format(list(map(lambda tfs: None if tfs is None else tfs['score'], c['parts'])), c['score']))

given_song.apply_lyrics_from_file(candidates_for_lyrics_per_song[0]['parts'])

print(given_song.lyrics_from_file())


