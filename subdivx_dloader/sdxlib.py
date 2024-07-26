
import os
import re
import sys
import json
import time
import logging
import certifi
import urllib3
import tempfile
import textwrap as tr
import logging.handlers
from rich import box
from colorama import init
from rich.table import Table
from rich.console import Console
from json import JSONDecodeError
from collections import namedtuple
from tempfile import NamedTemporaryFile
from zipfile import is_zipfile, ZipFile
from rarfile import is_rarfile, RarFile
from datetime import datetime, timedelta

init()

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
'torrentgalaxy', 'psa', 'nf', 'rrb', 'pcok', 'edith', 'successfulcrab', 'megusta', 'ethel',
'ntb', 'flux', 'yts', 'rbb', 'xebec', 'yify')

_codecs = ('xvid', 'x264', 'h264', 'x265', 'hevc')

_sub_extensions = ['.srt', '.ssa']

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

Metadata = namedtuple('Metadata', 'keywords quality codec')

# Configure connections
headers={"user-agent" : 
         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"}

s = urllib3.PoolManager(num_pools=1, headers=headers, cert_reqs="CERT_REQUIRED", ca_certs=certifi.where(), retries=False, timeout=15)

# Proxy: You must modify this configuration depending on the Proxy you use
#s = urllib3.ProxyManager('http://127.0.0.1:3128/', num_pools=1, headers=headers, cert_reqs="CERT_REQUIRED", ca_certs=certifi.where(), retries=False, timeout=15)

# mitmproxy test
#s = urllib3.ProxyManager('http://127.0.0.1:8080/', num_pools=1, headers=headers, retries=False, timeout=15)

class NoResultsError(Exception):
    pass

# Setting Loggers
LOGGER_LEVEL = logging.DEBUG
LOGGER_FORMATTER_LONG = logging.Formatter('%(asctime)-12s %(levelname)-6s %(message)s', '%Y-%m-%d %H:%M:%S')
LOGGER_FORMATTER_SHORT = logging.Formatter('| %(levelname)s | %(message)s')

temp_log_dir = tempfile.gettempdir()
file_log = os.path.join(temp_log_dir, 'subdivx-dloader.log')

global logger
logger = logging.getLogger(__name__)

def setup_logger(level):

    logger.setLevel(level)

def get_subtitle_url(title, number, metadata, no_choose, inf_sub):
    
    """Get a page with a list of subtitles searched by ``title`` and season/episode
        ``number`` of series or movies.
      
      The results are ordered based on a weighing of a ``metadata`` list.

      If ``no_choose`` ``(-nc)``  is true then a list of subtitles is show for chose 
        else the first subtitle is choosen
    """

    buscar = f"{title} {number}"
    fields={'buscar': buscar, 'filtros': '', 'tabla': 'resultados'}
    sEcho = "0"
    print("\r")
    logger.info(f'Searching subtitles for: ' + str(title) + " " + str(number).upper())
    
    try:
        page = s.request(
            'POST',
            SUBDIVX_SEARCH_URL,
            headers=headers,
            fields=fields
        ).data

    except (urllib3.exceptions.NewConnectionError, urllib3.exceptions.TimeoutError, urllib3.exceptions.ProxyError, urllib3.exceptions.HTTPError) as e:
        msg = Network_Connection_Error(e)
        if LOGGER_LEVEL == logging.INFO:
            print("\n" + Red + "Some Network Connection Error occurred: " + NC + msg)
        else:
            logger.error(f'Network Connection Error occurred: {msg}')
        sys.exit(1)

    try:
        sEcho = json.loads(page)['sEcho']
        if sEcho == "0" :
            attempts = 2
            backoff_factor = 2
            delay = backoff_delay(backoff_factor, attempts)
            for _ in range(attempts):
                logger.debug(f'Request Attempts #: {_}')
                time.sleep(delay)
                page = s.request('POST', SUBDIVX_SEARCH_URL, headers=headers, fields=fields).data
                sEcho = json.loads(page)['sEcho']
                if sEcho == 0 :
                    continue
                else:
                    json_aaData = json.loads(page)['aaData']
                    break
            if sEcho == "0":
                raise NoResultsError(f'Not cookies found or expired, please repeat the search')
        else:
            json_aaData = json.loads(page)['aaData']
    
    except JSONDecodeError as msg:
        logger.debug(f'Error JSONDecodeError: "{msg}"')
        raise NoResultsError(f'Error JSONDecodeError: "{msg}"')
    
    # For testing
    # store_aadata(page)
    
    # Checking Json Data Items
    aaData_Items = get_Json_Dict_list(json_aaData)
    
    if aaData_Items is not None:
        # Cleaning Items
        list_Subs_Dicts = clean_list_subs(aaData_Items)
    else:
        raise NoResultsError(f'No suitable data were found for: "{buscar}"')
    
    """" ####### For testing ########## 
    page = load_aadata()
    aaData = json.loads(page)['aaData']
    aaData_Items = get_Json_Dict_list(aaData)

    if aaData_Items is not None:
         list_Subs_Dicts = clean_list_subs(aaData_Items)
    else:
        raise NoResultsError(f'No suitable data were found for: "{buscar}"')
   
    """  ##### For testing ######### """
    # only include results for this specific serie / episode
    # ie. search terms are in the title of the result item
    
    filtered_list_Subs_Dicts = {
        subs_dict['id']: [subs_dict['descripcion'], subs_dict['titulo'], subs_dict['descargas'], subs_dict['nick'], subs_dict['fecha_subida']] for subs_dict in list_Subs_Dicts
        if match_text(title, number, inf_sub, subs_dict['titulo'])
    }

    if not filtered_list_Subs_Dicts:
        raise NoResultsError(f'No suitable subtitles were found for: "{buscar}"')

    # finding the best result looking for metadata keywords
    # in the description and max downloads
    scores = []
    downloads = []
    for x in filtered_list_Subs_Dicts.values(): 
         downloads.append(int(x[2]))
    max_dl = max(downloads)

    for subs_dict in filtered_list_Subs_Dicts.values():

        score = 0
        for keyword in metadata.keywords:
            if keyword.lower() in subs_dict[0]:
                score += .75
        for quality in metadata.quality:
            if quality.lower() in subs_dict[0]:
                score += .25
        for codec in metadata.codec:
            if codec.lower() in subs_dict[0]:
                score += .25
        if  max_dl == int(subs_dict[2]):
                score += .5
        scores.append(score)

    sorted_results = sorted(zip(filtered_list_Subs_Dicts.items(), scores), key=lambda item: item[1], reverse=True)
    results = get_clean_results(sorted_results)

    # Print subtitles search infos
    # Construct Table for console output
    
    console = Console()
    table = Table(box=box.ROUNDED, title="\n>> Subtítulo: " + str(title) + " " + str(number).upper(), caption="[white on green4]Coincidencias[default on default] [italic yellow]con los metadatos del archivo", title_style="bold green",
                  show_header=True, header_style="bold yellow", caption_style="italic yellow", show_lines=True)
    table.add_column("#", justify="center", vertical="middle", style="bold green")
    table.add_column("Título", justify="center", vertical="middle", style="bold green")
    table.add_column("Descripción", justify="center" )
    table.add_column("Descargas", justify="center", vertical="middle")
    table.add_column("Usuario", justify="center", vertical="middle")
    table.add_column("Fecha", justify="center", vertical="middle")

    if (no_choose==False):
        count = 0
        url_ids = []
        for item in results:
            try:
                url_ids.append(item['id'])
                descripcion = tr.fill(highlight_text(item['descripcion'], metadata), width=77)
                titulo = str(item['titulo'])
                descargas = str(item['descargas'])
                usuario = str(item['nick'])
                fecha = str(item['fecha_subida'])
                table.add_row(str(count), titulo, descripcion, descargas, usuario, fecha)
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
            clean_screen()
            sys.exit(0)
        url = SUBDIVX_DOWNLOAD_PAGE + str(url_ids[res])
    else:
        # get first subtitle
        url = SUBDIVX_DOWNLOAD_PAGE + str(url_ids[0])
    print("\r")
    # get download page
    if (s.request("GET", url).status == 200):
      logger.debug(f"Getting url from: {url}")
      return url

def get_subtitle(url, topath):
    """Download subtitles from ``url`` to a destination ``path``"""
    
    temp_file = NamedTemporaryFile(delete=False)
    SUCCESS = False

    # get direct download link    
    for i in range ( 9, 0, -1 ):

        logger.debug(f"Trying Download from link: {SUBDIVX_DOWNLOAD_PAGE + 'sub' + str(i) + '/' + url[24:]}")
        
        # Download file
        try:
            temp_file.write(s.request('GET', SUBDIVX_DOWNLOAD_PAGE + 'sub' + str(i) + '/' + url[24:], headers=headers).data)
            temp_file.seek(0)
        except (urllib3.exceptions.NewConnectionError, urllib3.exceptions.TimeoutError, urllib3.exceptions.ProxyError, urllib3.exceptions.HTTPError) as e:
            msg = Network_Connection_Error(e)
            if LOGGER_LEVEL == logging.INFO:
                print("\n" + Red + "Some Network Connection Error occurred: " + NC + msg)
            else:
                logger.error(f'Network Connection Error occurred: {msg}')
            sys.exit(1)
            
        # Checking if the file is zip or rar then decompress
        compressed_sub_file = ZipFile(temp_file) if is_zipfile(temp_file.name) else RarFile(temp_file) if is_rarfile(temp_file.name) else None

        if compressed_sub_file is not None:
            SUCCESS = True
            logger.debug(f"Downloaded from: {SUBDIVX_DOWNLOAD_PAGE + 'sub' + str(i) + '/' + url[24:]}")

            # In case of existence of various subtitles choose which to download
            if len(compressed_sub_file.infolist()) > 1 :
                clean_screen()
                console = Console()
                count = 0
                list_sub = []
                table = Table(box=box.ROUNDED, title=">> Subtítulos disponibles:", title_style="bold green",show_header=True, 
                              header_style="bold yellow", show_lines=True, title_justify='center')
                table.add_column("#", justify="center", vertical="middle", style="bold green")
                table.add_column("Subtítulo", justify="center" , no_wrap=True)
                for i in compressed_sub_file.infolist():
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
                    time.sleep(2)
                    clean_screen()
                    sys.exit(0)
                logger.info('Decompressing files')
                if res == count:
                    for sub in list_sub:
                        if any(sub.endswith(ext) for ext in _sub_extensions) and '__MACOSX' not in sub:
                            logger.debug(' '.join(['Decompressing subtitle:', sub, 'to', os.path.dirname(topath)]))
                            compressed_sub_file.extract(sub, os.path.dirname(topath))
                    compressed_sub_file.close()
                else:
                    if any(list_sub[res].endswith(ext) for ext in _sub_extensions) and '__MACOSX' not in list_sub[res]:
                        logger.debug(' '.join(['Decompressing subtitle:', list_sub[res], 'to', os.path.dirname(topath)]))
                        compressed_sub_file.extract(list_sub[res], os.path.dirname(topath))
                    compressed_sub_file.close()
                logger.info(f"Done extract subtitles!")
            else:
                for name in compressed_sub_file.infolist():
                    # don't unzip stub __MACOSX folders
                    if any(name.filename.endswith(ext) for ext in _sub_extensions) and '__MACOSX' not in name.filename:
                        logger.debug(' '.join(['Decompressing subtitle:', name.filename, 'to', os.path.dirname(topath)]))
                        compressed_sub_file.extract(name, os.path.dirname(topath))
                compressed_sub_file.close()
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
    time.sleep(2)
    clean_screen()

def match_text(title, number, inf_sub, text):
  """Search ``pattern`` for the whole phrase in ``text`` for a exactly match"""

  #Setting Patterns
  special_char = ["`", "'", "´", ":", ".", "?"]
  for i in special_char:
      title = title.replace(i, '')
      text = text.replace(i, '')
  aka = "aka"
  search = f"{title} {number}"
  
  # Setting searchs Patterns
  re_full_pattern = re.compile(rf"^{re.escape(title)}.*{number}.*$", re.I) if inf_sub['type'] == "movie" else re.compile(rf"^{re.escape(title.split()[0])}.*{number}.*$", re.I)
  re_title_pattern = re.compile(rf"\b{re.escape(title)}\b", re.I)

  # Perform searches
  r = True if re_full_pattern.search(text.strip()) else False
  logger.debug(f'FullMatch text: {text} Found: {r}')

  if not r :
    rtitle = True if re_title_pattern.search(text.strip()) else False
    logger.debug(f'Title Match: {title} Found: {rtitle}')

    for num in number.split(" "):
        if not inf_sub['season']:
           rnumber = True if re.search(rf"\b{num}\b", text, re.I) else False
        else:
           rnumber = True if re.search(rf"\b{num}.*\b", text, re.I) else False
    
    logger.debug(f'Number Match: {number} Found: {rnumber}')

    if inf_sub['type'] == "movie" :
        raka = True if re.search(rf"\b{aka}\b", text, re.I) else False
        logger.debug(f'Search Match: aka Found: {raka}')
        r = True if rtitle and rnumber and raka else False
    else:
        r = True if rtitle and rnumber else False

    logger.debug(f'Partial Match text: {text}: {r}')

  if not r:
    if all(re.search(rf"\b{word}\b", text, re.I) for word in search.split()) :
        r = True
    logger.debug(f'All Words Match Search: {search.split()} in {text}: {r}')
       
  return r 

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

def clean_screen():
    os.system('clear' if os.name != 'nt' else 'cls')

def highlight_text(text,  metadata):
    """Highlight all text  matches  metadata of the file"""
    highlighted = f"{text}"
    
    for keyword in metadata.keywords:
        if keyword.lower() in text.lower():
            Match_keyword = re.search(keyword, text, re.IGNORECASE).group(0)
            highlighted = highlighted.replace(f'{Match_keyword}', f'{"[white on green4]" + Match_keyword + "[default on default]"}', 1)

    for quality in metadata.quality:
        if quality.lower() in text.lower():
            Match_quality = re.search(quality, text, re.IGNORECASE).group(0)
            highlighted = highlighted.replace(f'{Match_quality}', f'{"[white on green4]" + Match_quality + "[default on default]"}', 1)

    for codec in metadata.codec:
        if codec.lower() in text.lower():
            Match_codec = re.search(codec, text, re.IGNORECASE).group(0)
            highlighted = highlighted.replace (f'{Match_codec}', f'{"[white on green4]" + Match_codec + "[default on default]"}', 1)
    
    return highlighted

def backoff_delay(backoff_factor = 2, attempts = 2):
    # backoff algorithm
    delay = backoff_factor * (2 ** attempts)
    return delay

def convert_datetime(string_datetime:str):
    """
       Convert ``string_datetime`` in a datetime obj then format it to "%d/%m/%Y %H:%M"

       Return ``--- --`` if not invalid datetime string
    """

    try:
        date_obj = datetime.strptime(string_datetime, '%Y-%m-%d %H:%M:%S').date()
        time_obj = datetime.strptime(string_datetime, '%Y-%m-%d %H:%M:%S').time()
        date_time_str = datetime.combine(date_obj, time_obj).strftime('%d/%m/%Y %H:%M')

    except ValueError as e:
        logger.debug(f'Value Error parsing: {string_datetime} Error: {e}')
        return "--- --"
    
    return date_time_str

def get_Json_Dict_list(Json_data):
    """ Checking if the JSON Data is a list of subtitles dictionary """

    if isinstance(Json_data, list) and all(isinstance(item, dict)  
        for item in Json_data):  
            list_of_dicts = Json_data
    else:
        return None
    
    return list_of_dicts

def clean_list_subs(list_dict_subs):
    """ Clean not used Items from list of subtitles dictionarys ``list_dict_subs``
        
        Convert to datetime Items ``fecha_subida``
    """
    erase_list_Item_Subs = ['cds', 'idmoderador', 'eliminado', 'id_subido_por', 'framerate', 'comentarios', 'formato', 'promedio', 'pais']

    for dictionary in list_dict_subs:
        for i in erase_list_Item_Subs:
            del dictionary[i]
    
        dictionary['fecha_subida'] = convert_datetime(str(dictionary['fecha_subida']))

    return list_dict_subs

def get_clean_results(list_results):
    """ Get a list of subs dict cleaned from `list_results` """
    results_clean = []
    for item in list_results:
         results_clean.append(item[0])
    list_Subs_results = list(map(list, results_clean))
    
    Subs_dict_results=[]
    for _sub in list_Subs_results:

        Sub_dict = {
        "id":_sub[0],
        "descripcion":_sub[1][0],
        "titulo":_sub[1][1],
        "descargas":_sub[1][2],
        "nick":_sub[1][3],
        "fecha_subida":_sub[1][4]
        }
        Subs_dict_results.append(Sub_dict)
    
    list_Subs_dict_results = get_Json_Dict_list(Subs_dict_results)

    return list_Subs_dict_results

def Network_Connection_Error(e) -> str:
    """ Return a Network Connection Error message """
    msg = e.__str__()
    error_class = e.__class__.__name__
    Network_error_msg= {
        'ConnectTimeoutError' : "Connection to www.subdivx.com timed out",
        'ReadTimeoutError'    : "Read timed out",
        'NameResolutionError' : 'Failed to resolve www.subdivx.com',
        'ProxyError' : "Unable to connect to proxy",
        'NewConnectionError' : "Failed to establish a new connection",
        'HTTPError' : msg
    }
    error_msg = f'{error_class} : {Network_error_msg[error_class] if error_class in Network_error_msg else msg }'
    return error_msg

sdxcookie_name = 'sdx-cookie'

def check_Cookie_Status():
    """Check the time and existence of the `cookie` session and return it"""
    cookie = load_Cookie()
    if cookie is None or exp_time_Cookie is True: 
        cookie = get_Cookie()
        stor_Cookie(cookie)
        cookie = load_Cookie()
        logger.debug('Cookie Loaded')

    return cookie

def exp_time_Cookie():
    """Compare modified time and return `True` if is expired"""
    # Get cookie modified time and convert it to datetime
    temp_dir = tempfile.gettempdir()
    cookiesdx_path = os.path.join(temp_dir, sdxcookie_name)
    csdx_ti_m = datetime.fromtimestamp(os.path.getmtime(cookiesdx_path))
    delta_csdx = datetime.now() - csdx_ti_m
    exp_c_time = timedelta(hours=24)

    if delta_csdx > exp_c_time:
            return True 
    else:
        return False

def get_Cookie():
    """ Retrieve sdx cookie"""
    logger.debug('Get cookie from %s', SUBDIVX_SEARCH_URL)
    try:
        cookie_sdx = s.request('GET', SUBDIVX_SEARCH_URL, timeout=5).headers.get('Set-Cookie').split(';')[0]
    except (urllib3.exceptions.NewConnectionError, urllib3.exceptions.TimeoutError, urllib3.exceptions.ProxyError, urllib3.exceptions.HTTPError) as e:
        msg = Network_Connection_Error(e)
        if LOGGER_LEVEL == logging.INFO:
            print("\n" + Red + "Some Network Connection Error occurred: " + NC + msg)
        else:
            logger.error(f'Network Connection Error occurred: {msg}')
        exit(1)
    return cookie_sdx

def stor_Cookie(sdx_cookie):
    """ Store sdx cookies """
    temp_dir = tempfile.gettempdir()
    cookiesdx_path = os.path.join(temp_dir, sdxcookie_name)

    with open(cookiesdx_path, 'w') as file:
        file.write(sdx_cookie)
        file.close()
    logger.debug('Store cookie')
    
def load_Cookie():
    """ Load stored sdx cookies return ``None`` if not exists"""
    temp_dir = tempfile.gettempdir()
    cookiesdx_path = os.path.join(temp_dir, sdxcookie_name)
    if os.path.exists(cookiesdx_path):
        with open(cookiesdx_path, 'r') as filecookie:
            sdx_cookie = filecookie.read()
    else:
        return None

    return sdx_cookie

def store_aadata(aadata):
    """ Store aadata """
    temp_dir = tempfile.gettempdir()
    aadata_path = os.path.join(temp_dir, 'sdx-aadata')

    with open(aadata_path, 'wb') as file:
        file.write(aadata)
        file.close()
    logger.debug('Store aadata')

def load_aadata():
    temp_dir = tempfile.gettempdir()
    aadata_path = os.path.join(temp_dir, 'sdx-aadata')
    if os.path.exists(aadata_path):
        with open(aadata_path, 'r') as aadata_file:
            sdx_aadata = aadata_file.read()
    else:
        return None

    return sdx_aadata

# Setting cookies
headers['Cookie'] = check_Cookie_Status()