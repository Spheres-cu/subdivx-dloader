A fork of kabutor fork of  Martín Gaitán's fork of Michel Peterson's subdivx.com-subtitle-retriever
Retrieve the best matching subtitle (in spanish) for a show episode from subdivx.com

Bumb! Working with Python 3.12 version 

Also added these features:

 (20240524)
 - Added highlighted of video file metadata.
 - Added -S  or --Season argument for Search by Season. 

 (20240508)
- Ability to select which subtitle download inside zip or rar file or download them All!
- Now a logfile is generate with info and debug.

- Added logfile 20240505
- Unpack rared (rar5+ file format) subtitles beside zipped and old rar version files
- **Change option (-c)  now is (-nc) to not manually choose wich subtitle to download, manually download is the default** 20240428
- Change the way links are used to UTF-8 to avoid weird characters bug 20210302
- <strike>When searching for a tvshow if the year is present it will use it also to improve search 20210321</strike> removed as 20210701
- You can add keywords (-k) to improve the automatic selection among the subtitles available for a show. 20210405
- You can define the title of the show manually (-t) Useful when you have a folder with all the episodes titles, but not the show main title 20210406
- If no subtitle is available, program will continue for next title (in case you try to download several episodes with one command), also error is cleaner 20211018

Install
-------
```
$ git clone https://github.com/Spheres-cu/subdivx-dloader.git
cd subdivx-dloader
python3 -m pip install .
 
 OR

pip install build
python3 -m build
python3 -m pip install ./dist/subdivx_dloader-<version>

```

My recomendation is to use a virtual env and install it there:

```
mkdir subs
python3 -m venv subs
source subs/bin/activate
then clone with git and install with all the dependencies among them:
pip install guessit
pip install tvnamer
pip install rich
pip install rarfile
pip install colorama
pip install urllib3
pip install certifi
```


Usage
-----


```
usage: subdivx [-h] [--quiet] [--skip SKIP] [--force] path

positional arguments:
  path                  file or directory to retrieve subtitles

optional arguments:
  -h, --help            show this help message and exit
  --quiet, -q
  --no-choose, -nc          Download the default match subtitle avaible. Now show all the available subtitle to download is de default behavior
  --Season, -S          Search for Season 
  --force, -f           override existing file
  --keyword -k "<string>" _ Add the <string> to the list of keywords. Keywords are used when you have 

10 subtitles for a show or movie,and you know in the description there is a keyword for that subtitle.
  Example if rama966 is the creator of the subtitle you want to download, add it to the keyword and the 
  script will download that one. Combine -c with -k to see how subtitles are picked. 
  --title -t "<string>" _ Set the show main title to use instead of getting it from the file name


.. tip::
    If you want to look for a subtitle with an 's apostrophe, check that the file name is "zoey's.extraordinary.playlist.s01e01.mp4" 
    and no "zoeys.extraordinary.playlist.s01e01.mp4". Also you can remove the problematic words from the file name and leave it as
    "extraordinary.playlist.s01e04.mp4" and it may work.
    Also can use the -t option to set the name, and then use the apostrophe escaped (\')

```
**The results is show in a beautiful table**

![Design with tables !](https://github.com/Spheres-cu/subdivx-dloader/blob/master/captures/capture03.png)

**Now  you can select wich subtitle download !**

![Select subtitle file to Download !](https://github.com/Spheres-cu/subdivx-dloader/blob/master/captures/capture04.gif)


**New feature: file metadata highlighted!**

![ Highlighted file metadata !](https://github.com/Spheres-cu/subdivx-dloader/blob/master/captures/capture05.gif)

**New feature: Search by Season!**

![ Search by Season !](https://github.com/Spheres-cu/subdivx-dloader/blob/master/captures/capture06.gif)

**More accurate search results!**

![ More accurate search results! !](https://github.com/Spheres-cu/subdivx-dloader/blob/master/captures/capture07.gif)
