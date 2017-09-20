#!/usr/bin/python3

import sys
import mutagen
from mutagen import easyid3 as easy
from pathlib import Path
import re

# Parsing arguments

filename = Path(sys.argv[1]).resolve()
if not filename.is_file():
    print("File doesn't exist: %s" % filename)
    exit(1)

# Methods to easy access lyrics tag in file

lang = 'eng'


def lyrics_getter(inst, key):
    uslt_key = 'USLT::%s' % lang
    uslt_frame = inst.get(uslt_key)
    return uslt_frame.text if uslt_frame else None


def lyrics_setter(inst, key, lyrics_arr):
    lyrics = lyrics_arr[0]
    uslt_key = 'USLT::%s' % lang
    uslt_frame = inst.get(uslt_key)
    if uslt_frame:
        uslt_frame.text = lyrics
    else:
        inst.add(mutagen.id3.USLT(mutagen.id3.Encoding.UTF8, lang=lang, desc='', text=lyrics))


def lyrics_deleter(inst, key):
    uslt_key = 'USLT::%s' % lang
    inst.delall(uslt_key)


def lyrics_lister(inst, key):
    uslt_key = 'USLT::%s' % lang
    return ['lyrics'] if inst.get(uslt_key) else []


easy.EasyID3.RegisterKey('lyrics', lyrics_getter, lyrics_setter, lyrics_deleter, lyrics_lister)

# Finding lyrics file(s) in the song file's directory

lyrics_regex = ['lyrics']


def strip_the(name):
    re_the = re.compile("^the |, the$", re.IGNORECASE)
    return re.sub(re_the, "", name)


tags = easy.EasyID3(str(filename))
album = tags['album'][0] if 'album' in tags else None
artist = strip_the(tags['artist']) if 'artist' in tags \
    else strip_the(tags['albumartist']) if 'albumartist' in tags \
    else None
year = tags['date'][0] if 'date' in tags else None
tracknumber = tags['tracknumber'][0] if 'tracknumber' in tags else None

if album and artist:
    lyrics_regex += ["(the )?{0}\\W+{1}|{1}\\W+(the )?{0}".format(artist.lower(), album.lower())]
if album:
    lyrics_regex += [album.lower()]

file_dir = filename.parent

txt_files = list(file_dir.glob("*.txt"))
if len(txt_files) == 1:
    candidates = txt_files
else:
    candidates = [file for file in txt_files if len(list(filter(lambda lr: re.match(lr, file.name), lyrics_regex))) > 0]

print(candidates)

if len(candidates) == 0:
    print("Didn't find any candidates for lyrics file.")
    exit(2)


lyrics_file = str(candidates[0])

# Analyze the contents of lyrics file:
# 1. Label each line with a type


def read_lines(fn):
    f = open(fn, "r", encoding="utf-8")
    try:
        file_lines = f.readlines()
    except UnicodeDecodeError:
        f = open(fn, "r", encoding="latin-1")
        file_lines = f.readlines()
    return file_lines


re_sep = re.compile("^(\\W)\\1+$")


def line_type(string):
    stripped = string.strip()
    if len(stripped) == 0:
        return "EMPTY"
    if re_sep.match(stripped):
        return "SEPARATOR"
    return "BLOB"


lines = read_lines(lyrics_file)
if len(lines) == 0:
    print("File %s is empty." % lyrics_file)
    exit(3)

labeled_lines = [{'text': line, 'label': line_type(line)} for line in lines]

# 2. Combine subsequent lines of the same type into groups

parts = [{'label': labeled_lines[0]['label'], 'text': [labeled_lines[0]['text']]}]
for line in labeled_lines[1:]:
    prev_line = parts[-1]
    if prev_line['label'] == line['label']:
        prev_line['text'].append(line['text'])
    else:
        parts.append({'label': line['label'], 'text': [line['text']]})

print(list(map(lambda p: "%s (%s)" % (p['label'], len(p['text'])), parts)))

# 2.1. Put together pieces between separators
# 3. Figure out if file contains prelude and coda, and if prelude contains the tracklist
# 4. Figure out how songs are separated
# 5. Find the separator and title of the song, then the lyrics, then the next separator




