from setuptools import setup

setup(name='lyricsfor',
      version='0.2',
      description='Manage lyrics for MP3 files',
      url='https://github.com/mzywiol/lyrics-for',
      author='mzywiol',
      author_email='maciej.zywiol+git@gmail.com',
      license='free',
      install_requires=[
          'mutagen',
          'unidecode',
          'chardet'
      ],
      zip_safe=False)