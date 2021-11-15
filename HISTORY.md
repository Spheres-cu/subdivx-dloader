Changelog
=========

0.9 (2021-11-15)
---------------
- Redited cli.py, now you no longer need lib.py, all necessary modules and dependencies are in cli.py

- Added the colorama module to enable the color output of texts in multiplatform (Win, Linux, Mac)

- Now allows you to cancel the download in "choose" mode (-c), also avoid entering an invalid number in the options. Also exit with some keyboard interrupt (Ex. Control + C in Win)

-An error is thrown if you do not have access to the Internet when searching for subtitles.

0.8 (2021-11-05)
----------------
Forked [kabutor]

-  Fix error [Errno 13] Permission denied in Windows :  Fixed  with NamedTemporaryFile(delete=False) and delete temp_file with os.unlink(temp_file.name)
-  Added rarfile  and delete is_rarfile() and is_rar5file  and sustitute for is_rarfile() of rarfile API
-  Added torrentgalaxy keyword

0.7 (2021-02-17)
----------------
Forked from [Martin Gaitan]

- It will process the post request to subdivx.com and download and extract the subtitle.
- Added support for rar5+ file format

0.6 (2020-06-06)
----------------

- use guessit to parse the filename
- fix scraping the link by getting it from subtitle's detail page.


0.5 (2019-04-23)
----------------

- Changed best matching algorithm by a simpler <the one that contains
  more metadata values in description> [Martin Gaitan]
- Cleanup. exclude results not matching the title. [Martin Gaitan]


0.4 (2017-08-25)
----------------
- Gitignore. [Martin Gaitan]
- Still alive. [Martin Gaitan]
- Force flag. [Martín Gaitán]
- Merge pull request #1 from p4bloch/master. [Martín Gaitán]

  Update smarter.py
- Update smarter.py. [p4bloch]
- Merge branch 'master' of https://github.com/nqnwebs/subdivx.com-
  subtitle-retriever. [Martín Gaitán]
- Log storage handled automatically (workaround to no permission issue
  when it's installed as system package) [Martín Gaitán]
- Epic copy&paste fix. [Martín Gaitán]
- Added --skip parameter. [Martín Gaitán]
- Readme updates. [Martín Gaitán]
- Can retrieve subtitles for partially downloaded videos (with extension
  .part, .temp or .tmp) [Martín Gaitán]
- Rename after unpack. better readme. tag 0.2.2. [Martín Gaitán]
- More robustness on extra meta data. [Martín Gaitán]
- Version 0.2.1. [Martín Gaitán]
- Now the argument could be a directory. retrieve a subtitle for each
  video there if doesn't exist. [Martín Gaitán]
- Changed url to this fork. [Martín Gaitán]
- Tag version in setup.py. [Martín Gaitán]
- Use tvnamer and some simple parsing to retrieve the best matching
  subtitle for an episode filename. Instead of many mandatory argument
  now you can pass just the filename of your video. [Martín Gaitán]
- Packaging and spliting into a lib and executable. [Martín Gaitán]
- Unpack rared subtitles with external tool unrar. [Martín Gaitán]
- Better logging information. [Michel Peterson]
- A little bit of pythonification. [Michel Peterson]
- Respect import ordering. [Michel Peterson]
- Removed debugging lines. [Michel Peterson]
- Get_subtitle_archive(...) renamed to get_subtitle(...) [Michel
  Peterson]
- Removed newlines at eof. [Michel Peterson]


