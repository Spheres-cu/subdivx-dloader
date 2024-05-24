#!/bin/env python

import os
import re
import sys
import json
import time
import logging
import argparse
import certifi
import urllib3
import tempfile
import textwrap as tr
import logging.handlers
from colorama import init
from guessit import guessit
from rarfile import is_rarfile, RarFile
from collections import namedtuple
from tvnamer.utils import FileFinder
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from zipfile import is_zipfile, ZipFile
from json import JSONDecodeError
from rich.console import Console
from rich.table import Table
from rich import box

init()

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

SUBDIVX_SEARCH_URL = 'https://www.subdivx.com/inc/ajax.php'

SUBDIVX_DOWNLOAD_PAGE = 'https://www.subdivx.com/'

# Colors
Yellow='\033[0;33m'
BYellow='\033[1;33m'
On_Yellow='\033[33m'
Red='\033[0;31m'
BRed='\033[1;31m'
On_Green='\033[42m'
Green='\033[0;32m'
BGreen='\033[1;32m'
NC='\033[0m' # No Color

s = urllib3.PoolManager(ca_certs=certifi.where())

#Proxy: You must modify this configuration depending on the Proxy you use
#s = urllib3.ProxyManager('http://127.0.0.1:3128/', ca_certs=certifi.where())

class NoResultsError(Exception):
    pass

# Setting Loggers
LOGGER_LEVEL = logging.DEBUG
LOGGER_FORMATTER_LONG = logging.Formatter('%(asctime)-12s %(levelname)-6s %(message)s', '%Y-%m-%d %H:%M:%S')
LOGGER_FORMATTER_SHORT = logging.Formatter('| %(levelname)s | %(message)s')

temp_log_dir = tempfile.gettempdir()
file_log = os.path.join(temp_log_dir, 'subdivx-dloader.log')

def setup_logger(level):
    global logger

    logger = logging.getLogger(__name__)
    """
    logfile = logging.handlers.RotatingFileHandler(logger.name+'.log', maxBytes=1000 * 1024, backupCount=9)
    logfile.setFormatter(LOGGER_FORMATTER)
    logger.addHandler(logfile)
    """
    logger.setLevel(level)


def get_subtitle_url(title, number, metadata, no_choose=True):
    
    """Get a page with a list of subtitles searched by ``title`` and season/episode
        ``number`` of series or movies.
      
      The results are ordered based on a weighing of a ``metadata`` list.

      If ``no_choose`` ``(-nc)``  is true then a list of subtitles is show for chose 
        else the first subtitle is choosen
    """
    #Filter the title to avoid 's in names
    title_f = [ x for x in title.split() if "\'s" not in x ]
    title = ' '.join(title_f)
    buscar = f"{title} {number}"
    print("\r")
    logger.info(f'Searching subtitles for: ' + str(title) + " " + str(number).upper())
    try:
        page = s.request(
            'POST',
            SUBDIVX_SEARCH_URL,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"},
            fields={'buscar': buscar, 'filtros': '', 'tabla': 'resultados'},
            retries=False,
            timeout=5.0
        ).data

    except urllib3.exceptions.NewConnectionError:
        print("\n"  + Red + "[Error,", "Failed to establish a new connection!] " + NC + "\n\n" + Yellow + " Please check: " + NC + "- Your Internet connection!")
        sys.exit(1)

    except urllib3.exceptions.TimeoutError:
        print("\n"  + Red + "[Error,", "Connection Timeout!]: " + NC + Yellow + "Unable to reach https://www.subdivx.com servers!" + NC + "\n\n" + Yellow + " Please check: " + NC + "\n" + \
                "- Your Internet connection\n" + \
                "- Your Firewall connections\n" + \
                "- www.subdivx.com availability\n")
        sys.exit(1)

    except urllib3.exceptions.ProxyError:
        print("\n"  + Red + "[Error,", "Cannot connect to proxy!] " + NC + "\n\n" + Yellow + " Please check: " + NC + "\n\n - Your proxy configuration!")
        sys.exit(1)

    try:
       soup = json.loads(page).get('aaData')
    except JSONDecodeError:
        raise NoResultsError(f'Not suitable subtitles were found for: "{buscar}"')

    id_list = list()
    title_list = list()
    description_list = list()
    download_list = list()
    user_list = list()
    date_list = list()

    for key in soup:
        id_list.append(key['id'])
        title_list.append(key['titulo'])
        description_list.append(key['descripcion'])
        download_list.append(key['descargas'])
        user_list.append(key['nick'])

        # Format date (year/month/day HH:MM)
        match = re.search(r'(\d+-\d+-\d+\s+\d+:\d+)', str(key['fecha_subida']))
        if (match is None):
            date_list.append('--- --')
        else:
            date_list.append(match.group(1).replace("-", "/"))

    titles = title_list

    # only include results for this specific serie / episode
    # ie. search terms are in the title of the result item
    descriptions = {
         description_list[i]: [id_list[i], download_list[i], user_list[i], date_list[i]] for i, t in enumerate(titles) 
        if all(word.lower() in t.lower() for word in buscar.split())
    }
   
    if not descriptions:
        raise NoResultsError(f'No suitable subtitles were found for: "{buscar}"')

    # then find the best result looking for metadata keywords
    # in the description
    scores = []
    for description in descriptions:

        score = 0
        for keyword in metadata.keywords:
            if keyword.lower() in description:
                score += 1
        for quality in metadata.quality:
            if quality.lower() in description:
                score += .25
        for codec in metadata.codec:
            if codec.lower() in description:
                score += .50
        scores.append(score)

    results = sorted(zip(descriptions.items(), scores), key=lambda item: item[1], reverse=True)

    # Print subtitles search infos
    # Construct Table for console output
    
    console = Console()
    table = Table(box=box.ROUNDED, title="\n>> Subtítulo: " + str(title) + " " + str(number).upper(), caption="[white on green4]Coincidencias[default on default] [italic yellow]con los metadatos del archivo", title_style="bold green",
                  show_header=True, header_style="bold yellow", caption_style="italic yellow", show_lines=True)
    table.add_column("#", justify="center", vertical="middle", style="bold green")
    table.add_column("Descripción", justify="center" )
    table.add_column("Descargas", justify="center", vertical="middle")
    table.add_column("Usuario", justify="center", vertical="middle")
    table.add_column("Fecha", justify="center", vertical="middle")

    if (no_choose==False):
        count = 0
        url_ids = []
        for item in (results):
            try:
                descripcion = tr.fill(highlight_text(item[0][0], metadata), width=77)
                detalles = item[0]
                url_ids.append(detalles[1][0])
                descargas = str(detalles[1][1])
                usuario = str(detalles[1][2])
                fecha = str(detalles[1][3])
                table.add_row(str(count), descripcion, descargas, usuario, fecha)
            except IndexError:
                pass   
            count = count +1
        console.print(table)
        print("\n" + Red + ">> [" + str(count) + "] Cancelar descarga\n" + NC )
        res = -1

        while (res < 0 or res > count):
            try:
               res = int(input (BYellow + ">> Elija un [" + BGreen + "#" + BYellow +"] para descargar el sub. Enter para la [" + BGreen + "0"+ BYellow +"]: " + NC) or "0")
            except KeyboardInterrupt:
                logger.debug('Interrupted by user')
                print(BRed + "\n\n Interrupto por el usuario..." + NC)
                time.sleep(2)
                clean_screen()
                sys.exit(1)
            except:
                res = -1
        if (res == count):
            logger.debug('Download Canceled')
            print(BRed + "\n Cancelando descarga..." + NC)
            time.sleep(2)
            #clean_screen()
            sys.exit(0)
        url = SUBDIVX_DOWNLOAD_PAGE + str(url_ids[res])
    else:
        # get first subtitle
        url = SUBDIVX_DOWNLOAD_PAGE + str(url_ids[0])
    print("\r")
    # get download page
    if (s.request("GET", url).status == 200):
      logger.info(f"Getting url from: {url}")
      return url

def get_subtitle(url, path):
    """Download subtitles from ``url`` to a destination ``path``"""
    temp_file = NamedTemporaryFile(delete=False)
    SUCCESS = False
    # get direct download link
    headers = {'cookie': 
     s.request('GET', url , redirect=False, preload_content=False).headers.get('set-cookie')
    }
    
    for i in range ( 9, 1, -1 ):

        logger.debug(f"Trying Download from link: {SUBDIVX_DOWNLOAD_PAGE + 'sub' + str(i) + '/' + url[24:]}")
        
        # Download file
        temp_file.write(s.request('GET', SUBDIVX_DOWNLOAD_PAGE + 'sub' + str(i) + '/' + url[24:], headers=headers).data)
        temp_file.seek(0)

        # Checking if the file is zip or rar then decompress
        if is_zipfile(temp_file.name):
            SUCCESS = True
            logger.debug(f"Downloaded from: {SUBDIVX_DOWNLOAD_PAGE + 'sub' + str(i) + '/' + url[24:]}")

            zip_file = ZipFile(temp_file)
            # In case of existence of various subtitles choice vich download
            if len(zip_file.infolist()) > 1 :
                clean_screen()
                console = Console()
                count = 0
                list_sub = []
                table = Table(box=box.ROUNDED, title=">> Subtítulos disponibles:", title_style="bold green",show_header=True, 
                              header_style="bold yellow", show_lines=True, title_justify='center')
                table.add_column("#", justify="center", vertical="middle", style="bold green")
                table.add_column("Subtítulo", justify="center" , no_wrap=True)
                for i in zip_file.infolist():
                    list_sub.append(i.filename)
                    table.add_row(str(count), str(i.filename))
                    count += 1
                console.print(table)
                print("\n" + BGreen + ">> [" + str(count) + "] Descargar todos" + NC )
                print("\n" + Red + ">> [" + str(count+1) + "] Cancelar descarga\n" + NC )
                res = -1
                while (res < 0 or res > count + 1):
                    try:
                       res = int(input (BYellow + ">> Elija un [" + BGreen + "#" + BYellow + "]: " + NC) or "0")
                    except:
                        res = -1
                if (res == count + 1):
                    logger.debug('Canceled Download Subtitle')
                    print(BRed + "\n Cancelando descarga..." + NC)
                    temp_file.close()
                    os.unlink(temp_file.name)
                    time.sleep(3)
                    clean_screen()
                    sys.exit(0)
                logger.info('Decompressing files')
                if res == count:
                    for sub in list_sub:
                        logger.debug(' '.join(['Unpacking zip file subtitle', sub, 'to', os.path.basename(path)]))
                        zip_file.extract(sub, os.path.dirname(path))
                    zip_file.close
                else:
                    if '.srt' in list_sub[res] and '__MACOSX' not in list_sub[res]:
                        logger.debug(' '.join(['Unpacking zip file subtitle', list_sub[res], 'to', os.path.basename(path)]))
                        zip_file.extract(list_sub[res], os.path.dirname(path))
                    zip_file.close()
                logger.info(f"Done extract subtitles!")
            else:
                for name in zip_file.infolist():
                    # don't unzip stub __MACOSX folders
                    if '.srt' in name.filename and '__MACOSX' not in name.filename:
                        logger.debug(' '.join(['Unpacking zip file subtitle', name.filename, 'to', os.path.basename(path)]))
                        zip_file.extract(name, os.path.dirname(path))

                zip_file.close()
                logger.info(f"Done extract subtitle!")

            break

        elif (is_rarfile(temp_file.name)):
            SUCCESS = True
            logger.debug(f"Downloaded from: {SUBDIVX_DOWNLOAD_PAGE + 'sub' + str(i) + '/' + url[24:]}")
            logger.info('Decompressing files')
            rar_file = RarFile(temp_file)
            # Check for existence of various subtitles
            ### TODO: ###
            # -Extract files without folder with '-e' parameter
            if len(rar_file.infolist()) > 1:
                clean_screen()
                console = Console()
                count = 0
                list_sub = []
                table = Table(box=box.ROUNDED, title=">> Subtítulos disponibles:", title_style="bold green",show_header=True, 
                              header_style="bold yellow", show_lines=True, title_justify='center')
                table.add_column("#", justify="center", vertical="middle", style="bold green")
                table.add_column("Subtítulo", justify="center" , no_wrap=True)
                for i in rar_file.namelist():
                    list_sub.append(i)
                    table.add_row(str(count), i)
                    count += 1
                console.print(table)
                print("\n" + BGreen + ">> [" + str(count) + "] Descargar todos" + NC )
                print("\n" + Red + ">> [" + str(count+1) + "] Cancelar descarga\n" + NC )
                res = -1
                while (res < 0 or res > count + 1):
                    try:
                       res = int(input (BYellow + ">> Elija un [" + BGreen + "#" + BYellow + "]: " + NC) or "0")
                    except:
                        res = -1
                if (res == count + 1):
                    logger.debug('Canceled Download Subtitle')
                    print(BRed + "\n Cancelando descarga..." + NC)
                    temp_file.close()
                    os.unlink(temp_file.name)
                    time.sleep(3)
                    #clean_screen()
                    sys.exit(0)
                logger.info('Decompressing files')
                if res == count:
                    for sub in list_sub:
                        logger.debug(' '.join(['Unpacking rar file subtitle', sub, 'to', os.path.basename(path)]))
                        rar_file.extract(sub, os.path.dirname(path))
                    rar_file.close()
                    logger.info(f"Done extract subtitles!")
                else:
                    if '.srt' in list_sub[res] and '__MACOSX' not in list_sub[res]:
                        logger.debug(' '.join(['Unpacking rar file subtitle', list_sub[res], 'to', os.path.basename(path)]))
                        rar_file.extract(list_sub[res], os.path.dirname(path))
                        rar_file.close()
                        logger.info(f"Done extract subtitle!")
            else:
                for name in rar_file.namelist():
                    if '.srt' in name and '__MACOSX' not in name:
                        logger.debug(' '.join(['Unpacking rar file subtitle', name, 'to', os.path.basename(path)]))
                        rar_file.extract(name, os.path.dirname(path))
                rar_file.close()
                logger.info(f"Done extract subtitle!")
            break
        else:
            SUCCESS = False
            time.sleep(2)
    
    temp_file.close()
    os.unlink(temp_file.name)
    
    if not SUCCESS :
        raise NoResultsError(f'No suitable subtitles download for : "{url}"')
   
    # Cleaning
    time.sleep(3)
    #clean_screen()

_extensions = [
    'avi', 'mkv', 'mp4',
    'mpg', 'm4v', 'ogv',
    'vob', '3gp',
    'part', 'temp', 'tmp'
]

#obtained from http://flexget.com/wiki/Plugins/quality
_qualities = ('1080i', '1080p', '2160p', '10bit', '1280x720',
              '1920x1080', '360p', '368p', '480', '480p', '576p',
               '720i', '720p', 'ddp5.1', 'dd5.1', 'bdrip', 'brrip', 'bdscr', 'bluray',
               'blurayrip', 'cam', 'dl', 'dsrdsrip', 'dvb', 'dvdrip',
               'dvdripdvd', 'dvdscr', 'hdtv', 'hr', 'ppvrip',
               'preair', 'sdtvpdtv', 'tvrip','web', 'web-dl',
               'web-dlwebdl', 'webrip', 'workprint')
_keywords = (
'2hd', 'adrenaline', 'amzn', 'asap', 'axxo', 'compulsion', 'crimson', 'ctrlhd', 
'ctrlhd', 'ctu', 'dimension', 'ebp', 'ettv', 'eztv', 'fanta', 'fov', 'fqm', 'ftv', 
'galaxyrg', 'galaxytv', 'hazmatt', 'immerse', 'internal', 'ion10', 'killers', 'loki', 
'lol', 'mement', 'minx', 'notv', 'phoenix', 'rarbg', 'sfm', 'sva', 'sparks', 'turbo', 
'torrentgalaxy', 'psa', 'nf', 'rrb', 'pcok', 'edith', 'successfulcrab', 'megusta', 'ethel', 'ntb', 'flux')

_codecs = ('xvid', 'x264', 'h264', 'x265', 'hevc')


Metadata = namedtuple('Metadata', 'keywords quality codec')

def clean_screen():
    os.system('clear' if os.name != 'nt' else 'cls')

def highlight_text(text,  metadata):
    """Highlight all text  matches  metadata of the file"""
    highlighted = f"{text}"
    
    for keyword in metadata.keywords:
        if keyword.lower() in text.lower():
            Match_keyword = re.search(keyword, text, re.IGNORECASE).group(0)
            highlighted = highlighted.replace(f'{Match_keyword}', f'{"[white on green4]" + Match_keyword + "[default on default]"}', 1)
            logger.debug(f'Highlighted keywords: {Match_keyword}')

    for quality in metadata.quality:
        if quality.lower() in text.lower():
            Match_quality = re.search(quality, text, re.IGNORECASE).group(0)
            highlighted = highlighted.replace(f'{Match_quality}', f'{"[white on green4]" + Match_quality + "[default on default]"}', 1)
            logger.debug(f'Highlighted quality: {Match_quality}')

    for codec in metadata.codec:
        if codec.lower() in text.lower():
            Match_codec = re.search(codec, text, re.IGNORECASE).group(0)
            highlighted = highlighted.replace (f'{Match_codec}', f'{"[white on green4]" + Match_codec + "[default on default]"}', 1)
            logger.debug(f'Highlighted codec: {Match_codec}')
    
    return highlighted

def extract_meta_data(filename, kword):
    """Extract metadata from a filename based in matchs of keywords
    the lists of keywords includen quality and codec for videos""" 
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

    # Fixed error for rename various subtitles with same filename
    for new_file in after - before:
        if not new_file.lower().endswith('srt'):
            # only apply to subtitles
            continue
        filename = extract_name(filepath)

        try:
           if os.path.exists(filename + '.srt'):
               continue
           else:
               os.rename(new_file, filename + '.srt')
        
        except OSError as e:
              print(e)
              logger.error(e)
              exit(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('path', type=str,
                        help="file or directory to retrieve subtitles")
    parser.add_argument('--quiet', '-q', action='store_true',
                        default=False, help="No verbose mode")
    parser.add_argument('--no-choose', '-nc', action='store_true',
                        default=False, help="No Choose sub manually")
    parser.add_argument('--force', '-f', action='store_true',
                        default=False, help="override existing file")
    parser.add_argument('--keyword','-k',type=str,help="Add keyword to search among subtitles")
    parser.add_argument('--title','-t',type=str,help="Set the title of the show")
    args = parser.parse_args()

    setup_logger(LOGGER_LEVEL)

    logfile = logging.FileHandler(file_log, mode='w', encoding='utf-8')
    logfile.setFormatter(LOGGER_FORMATTER_LONG)
    logfile.setLevel(logging.DEBUG)
    logger.addHandler(logfile)

    if not args.quiet:
        console = logging.StreamHandler()
        console.setFormatter(LOGGER_FORMATTER_SHORT)
        console.setLevel(logging.INFO)
        logger.addHandler(console)

    if os.path.exists(args.path):
      cursor = FileFinder(args.path, with_extension=_extensions)
    else:
        logger.error(f'No file or folder were found for: "{args.path}"')
        sys.exit(1)
    
    for filepath in cursor.findFiles():
        # skip if a subtitle for this file exists
        sub_file = os.path.splitext(filepath)[0] + '.srt'
        if os.path.exists(sub_file):
            if args.force:
                os.remove(sub_file)
            else:
                logger.info(f'Subtitle already exits use -f for force downloading')
                continue

        filename = os.path.basename(filepath)
        
        try:
            info = guessit(filename)
            if info["type"] == "episode" :
               number = f"s{info['season']:02}e{info['episode']:02}" if "episode" in info else f"s{info['season']:02}" 
            else:
               number = f"({info['year']})"

            metadata = extract_meta_data(filename, args.keyword)
            logger.debug(f'Metadata extracted:  {metadata}')

            if (args.title):
                title=args.title
            else:
                if info["type"] == "movie" :
                  title = info["title"] 
                else:
                    title=f"{info['title']} ({info['year']})" if "year" in info  else info['title']
            
            url = get_subtitle_url(
                title, number,
                metadata,
                args.no_choose)
        except NoResultsError as e:
            logger.error(str(e))
            url=''
        if(url !=''):
            with subtitle_renamer(filepath):
                 get_subtitle(url, 'temp__' + filename )


if __name__ == '__main__':
    main()