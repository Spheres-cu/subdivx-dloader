#!/bin/env python

import os
import sys
import logging
import argparse
import requests 
import urllib.parse
import textwrap as tr
import logging.handlers
from colorama import init
from guessit import guessit
from bs4 import BeautifulSoup
from rarfile import is_rarfile
from collections import namedtuple
from tvnamer.utils import FileFinder
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from zipfile import is_zipfile, ZipFile

init()
# For Developers can make a .exe in Windows
# def resource_path(relative_path):
#     """ Get absolute path to resource, works for dev and for PyInstaller """
#     try:
#         # PyInstaller creates a temp folder and stores path in _MEIPASS
#         base_path = sys._MEIPASS
#     except Exception:
#         base_path = os.path.abspath(".")

#     return os.path.join(base_path, relative_path)

PYTHONUTF8=1

SUBDIVX_SEARCH_URL = "https://www.subdivx.com/index.php"

SUBDIVX_DOWNLOAD_MATCHER = {'name':'a', 'rel':"nofollow", 'target': "new"}

LOGGER_LEVEL = logging.INFO
LOGGER_FORMATTER = logging.Formatter('%(asctime)-25s %(levelname)-8s %(name)-29s %(message)s', '%Y-%m-%d %H:%M:%S')

s = requests.Session()

# For setting a proxy, change 127.0.0.1:3128 for your host and port
# s.proxies = {
#   "http": "http://127.0.0.1:3128",
#   "https": "http://127.0.0.1:3128",
# }

class NoResultsError(Exception):
    pass

def setup_logger(level):
    global logger

    logger = logging.getLogger()
    """
    logfile = logging.handlers.RotatingFileHandler(logger.name+'.log', maxBytes=1000 * 1024, backupCount=9)
    logfile.setFormatter(LOGGER_FORMATTER)
    logger.addHandler(logfile)
    """
    logger.setLevel(level)


def get_subtitle_url(title, number, metadata, choose=False):
    #Filter the title to avoid 's in names
    title_f = [ x for x in title.split() if "\'s" not in x ]
    title = ' '.join(title_f)
    buscar = f"{title} {number}"
    params = {"accion": 5,
     "subtitulos": 1,
     "realiza_b": 1,
     "buscar2": buscar ,
    }
    s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"})
    try:
        page = s.post(SUBDIVX_SEARCH_URL, params=params).text
    except OSError:
        print("\n \033[31m [Error,", "Connection error! \033[0m", "Unable to reach https://www.subdivx.com servers!\n\n \033[0;33m Please check:\033[0m\n" + \
                "- Your Internet connection\n" + \
                "- Your Firewall connections\n" + \
                "- www.subdivx.com availability\n")
        sys.exit(1)

    soup = BeautifulSoup(page, 'html5lib')
    titles = soup('div', id='menu_detalle_buscador')

    # only include results for this specific serie / episode
    # ie. search terms are in the title of the result item
    descriptions = {
        t.nextSibling(id='buscador_detalle_sub')[0].text: t.next('a')[0]['href'] for t in titles
        if all(word.lower() in t.text.lower() for word in buscar.split())
    }
    descriptions_data = {
        t.nextSibling(id='buscador_detalle_sub_datos')[0].text: t.next('a')[0]['href'] for t in titles
        if all(word.lower() in t.text.lower() for word in buscar.split())
    }
    if not descriptions:
        raise NoResultsError(f'No suitable subtitles were found for: "{buscar}"')

    # then find the best result looking for metadata keywords
    # in the description
    scores = []
    for description in descriptions:

        score = 0
        for keyword in metadata.keywords:
            if keyword in description:
                score += 1
        for quality in metadata.quality:
            if quality in description:
                score += 1.1
        for codec in metadata.codec:
            if codec in description:
                score += .75
        scores.append(score)

    results = sorted(zip(descriptions.items(), scores), key=lambda item: item[1], reverse=True)
    results2 = sorted(zip(descriptions_data.items(), scores), key=lambda item: item[1], reverse=True)
    # Print video infos
    print("\n\033[33m>> Subtítulo: " + str(title) + " " + str(number).upper() + "\n\033[0m")

    if (choose):
        count = 0
        for item in (results):
            print ("  \033[92m [%i] ===> \033[0m %s " % (count , tr.fill(str(item[0][0]), width=180)))
            try:
                print("     \033[33m Detalles: \033[0m %s \r" % (tr.fill(str(results2[count][0][0]), width=180)))
            except IndexError:
                pass   
            count = count +1
        print("\033[31m [" + str(count) + "] \033[0m Cancelar descarga\n")
        res = -1
        while (res < 0 or res > count):
            try:
               res = int(input (">> Elija un [#] en las opciones. Enter para la [0]: ") or "0")
            except KeyboardInterrupt:
                print("\n\n \033[31m Interrupto por el usuario...\033[0m")
                sys.exit(1)
            except:
                res = -1
        if (res == count):
            print("\n \033[31m Cancelando descarga...\033[0m")
            sys.exit(0)
        url = (results[res][0][1]).encode("utf-8")
    else:
        # get subtitle page
        url = (results[0][0][1]).encode("utf-8")
    logger.info(f"Getting from {url}")
    page = s.get(url).text
    s.headers.update({"referer":url})
    soup = BeautifulSoup(page, 'html5lib')
    # get download link
    return soup('a', {"class": "link1"})[0]["href"]


def get_subtitle(url, path):
    temp_file = NamedTemporaryFile(delete=False)
    logger.info(f"downloading https://www.subdivx.com/{url}")
    
    temp_file.write(s.get('https://www.subdivx.com/' + url).content)
    temp_file.seek(0)
    
    if is_zipfile(temp_file.name):
        zip_file = ZipFile(temp_file)
        for name in zip_file.infolist():
            # don't unzip stub __MACOSX folders
            if '.srt' in name.filename and '__MACOSX' not in name.filename:
                logger.info(' '.join(['Unpacking zipped subtitle', name.filename, 'to', os.path.dirname(path)]))
                zip_file.extract(name, os.path.dirname(path))

        zip_file.close()

    elif (is_rarfile(temp_file.name)):
        rar_path = path + '.rar'
        logger.info('Saving rared subtitle as %s' % rar_path)
        with open(rar_path, 'wb') as out_file:
            out_file.write(temp_file.read())

        try:
            import subprocess
            #extract all .srt in the rared file
            
            # For Make a .exe in Windows
            #unrar_path = resource_path('unrar.exe')
            #ret_code = subprocess.call([unrar_path, 'e', '-inul', '-n*srt', '-n*txt', rar_path])
            
            ret_code = subprocess.call(['unrar', 'e', '-inul', '-n*srt', '-n*txt', rar_path])
            if ret_code == 0:
                logger.info('Unpacking rared subtitle to %s' % os.path.dirname(path))
                os.remove(rar_path)
        except OSError:
            logger.info('Unpacking rared subtitle failed.'
                        'Please, install unrar to automate this step.')
    else:
        logger.info(f"unknown file type")


    temp_file.close()
    os.unlink(temp_file.name)

_extensions = [
    'avi', 'mkv', 'mp4',
    'mpg', 'm4v', 'ogv',
    'vob', '3gp',
    'part', 'temp', 'tmp'
]

#obtained from http://flexget.com/wiki/Plugins/quality
_qualities = ('1080i', '1080p', '1080p1080', '10bit', '1280x720',
              '1920x1080', '360p', '368p', '480', '480p', '576p',
               '720i', '720p', 'bdrip', 'brrip', 'bdscr', 'bluray',
               'blurayrip', 'cam', 'dl', 'dsrdsrip', 'dvb', 'dvdrip',
               'dvdripdvd', 'dvdscr', 'hdtv', 'hr', 'ppvrip',
               'preair', 'r5', 'rc', 'sdtvpdtv', 'tc', 'tvrip',
               'web', 'web-dl', 'web-dlwebdl', 'webrip', 'workprint')
_keywords = (
    '2hd',
    'adrenaline',
    'amnz',
    'asap',
    'axxo',
    'compulsion',
    'crimson',
    'ctrlhd',
    'ctrlhd',
    'ctu',
    'dimension',
    'ebp',
    'ettv',
    'eztv',
    'fanta',
    'fov',
    'fqm',
    'ftv',
    'galaxyrg',
    'galaxytv',
    'hazmatt',
    'immerse',
    'internal',
    'ion10',
    'killers',
    'loki',
    'lol',
    'mement',
    'minx',
    'notv',
    'phoenix',
    'rarbg',
    'sfm',
    'sva',
    'sparks',
    'turbo',
    'torrentgalaxy'
)

_codecs = ('xvid', 'x264', 'h264', 'x265')


Metadata = namedtuple('Metadata', 'keywords quality codec')

def extract_meta_data(filename, kword):
    f = filename.lower()[:-4]
    def _match(options):
        try:
            matches = [option for option in options if option in f]
        except IndexError:
            matches = []
        return matches
    keywords = _match(_keywords)
    quality = _match(_qualities)
    codec = _match(_codecs)
    #Split keywords and add to the list
    if (kword):
        keywords = keywords + kword.split(' ')
    return Metadata(keywords, quality, codec)


@contextmanager
def subtitle_renamer(filepath):
    """dectect new subtitles files in a directory and rename with
       filepath basename"""

    def extract_name(filepath):
        filename, fileext = os.path.splitext(filepath)
        if fileext in ('.part', '.temp', '.tmp'):
            filename, fileext = os.path.splitext(filename)
        return filename

    dirpath = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    before = set(os.listdir(dirpath))
    yield
    after = set(os.listdir(dirpath))
    for new_file in after - before:
        if not new_file.lower().endswith('srt'):
            # only apply to subtitles
            continue
        filename = extract_name(filepath)
        # Fix windows error for rename various subtitles with same filename
        filecount = 0
        try:
           os.rename(new_file, filename + '.srt')
        except WindowsError:
            filecount += 1
            os.rename(new_file, filename + '['+ "% s" % filecount + ']' +'.srt')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('path', type=str,
                        help="file or directory to retrieve subtitles")
    parser.add_argument('--quiet', '-q', action='store_true')
    parser.add_argument('--choose', '-c', action='store_true',
                        default=False, help="Choose sub manually")
    parser.add_argument('--force', '-f', action='store_true',
                        default=False, help="override existing file")
    parser.add_argument('--keyword','-k',type=str,help="Add keyword to search among subtitles")
    parser.add_argument('--title','-t',type=str,help="Set the title of the show")
    args = parser.parse_args()
    setup_logger(LOGGER_LEVEL)

    if not args.quiet:
        console = logging.StreamHandler()
        console.setFormatter(LOGGER_FORMATTER)
        logger.addHandler(console)

    cursor = FileFinder(args.path, with_extension=_extensions)

    for filepath in cursor.findFiles():
        # skip if a subtitle for this file exists
        sub_file = os.path.splitext(filepath)[0] + '.srt'
        if os.path.exists(sub_file):
            if args.force:
                os.remove(sub_file)
            else:
                continue

        filename = os.path.basename(filepath)
        
        try:
            info = guessit(filename)
            number = f"s{info['season']:02}e{info['episode']:02}" if info["type"] == "episode" else ""

            metadata = extract_meta_data(filename, args.keyword)
            
            if (args.title):
                title=args.title
            else:
                title = info["title"]
            url = get_subtitle_url(
                title, number,
                metadata,
                args.choose)
        except NoResultsError as e:
            logger.error(str(e))
            url=''
        if(url !=''):
            with subtitle_renamer(filepath):
                 get_subtitle(url, 'temp__' + filename )


if __name__ == '__main__':
    main()
