
import os
import re
import logging
import certifi
import urllib3
import tempfile
import logging.handlers
from collections import namedtuple
from datetime import datetime, timedelta
from rich import box
from rich.layout import Layout
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.align import Align
from rich.text import Text

from .sdxlib import console

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

SUBDIVX_SEARCH_URL = 'https://www.subdivx.com/inc/ajax.php'

SUBDIVX_DOWNLOAD_PAGE = 'https://www.subdivx.com/'

Metadata = namedtuple('Metadata', 'keywords quality codec')

# Configure connections
headers={"user-agent" : 
         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"}

s = urllib3.PoolManager(num_pools=1, headers=headers, cert_reqs="CERT_REQUIRED", ca_certs=certifi.where(), retries=False, timeout=15)

# Proxy: You must modify this configuration depending on the Proxy you use
#s = urllib3.ProxyManager('http://127.0.0.1:3128/', num_pools=1, headers=headers, cert_reqs="CERT_REQUIRED", ca_certs=certifi.where(), retries=False, timeout=15)

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

def match_text(title, number, inf_sub, text):
  """Search ``pattern`` for the whole phrase in ``text`` for a exactly match"""

  #Setting Patterns
  special_char = ["`", "'", "´", ":", ".", "?", "&"]
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
#   logger.debug(f'FullMatch text: {text} Found: {r}')

  if not r :
    rtitle = True if re_title_pattern.search(text.strip()) else False
    # logger.debug(f'Title Match: {title} Found: {rtitle}')

    for num in number.split(" "):
        if not inf_sub['season']:
           rnumber = True if re.search(rf"\b{num}\b", text, re.I) else False
        else:
           rnumber = True if re.search(rf"\b{num}.*\b", text, re.I) else False
    
    # logger.debug(f'Number Match: {number} Found: {rnumber}')

    if inf_sub['type'] == "movie" :
        raka = True if re.search(rf"\b{aka}\b", text, re.I) else False
        logger.debug(f'Search Match: aka Found: {raka}')
        r = True if rtitle and rnumber and raka else False
    else:
        r = True if rtitle and rnumber else False

    # logger.debug(f'Partial Match text: {text}: {r}')

  if not r:
    if all(re.search(rf"\b{word}\b", text, re.I) for word in search.split()) :
        r = True
    # logger.debug(f'All Words Match Search: {search.split()} in {text}: {r}')
       
  return r 

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

def get_list_Dict(Data):
    """ Checking if ``Data`` is a list of dictionarys """

    if isinstance(Data, list) and all(isinstance(item, dict)  
        for item in Data):  
            list_of_dicts = Data
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
    
    list_Subs_dict_results = get_list_Dict(Subs_dict_results)

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
        console.print(":no_entry: [bold red]Some Network Connection Error occurred[/]: " + msg, new_line_start=True, emoji=True)
        if LOGGER_LEVEL == logging.DEBUG:
           logger.debug(f'Network Connection Error occurred: {msg}')
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

def make_layout() -> Layout:
    """Define the layout."""
    layout = Layout(name="results")

    layout.split_column(
        Layout(name="table"),
        Layout(name="description", size=8, ratio=1),
    )
    return layout

def make_description_panel(description) -> Panel:
    """Define a description Panel"""
    descriptions = Table.grid(padding=1)
    descriptions.add_column()
    descriptions.add_row(description)
    descriptions_panel = Panel(
        Align.center(descriptions, vertical = "middle"),
        box = box.ROUNDED,
        title = "[bold yellow]Descripción:[/]",
        title_align = "left",
        subtitle = "[white on green4]Coincidencias[/] [italic yellow]con los metadatos del archivo[/]",
        subtitle_align = "center",
        padding = 1 
    )

    return descriptions_panel


def generate_results(title, results, metadata: Metadata, page, selected) -> Layout:
    """Generate Selectable results Table"""

    SELECTED = Style(color="green", bgcolor="medium_purple4", bold=True)
    layout_results = make_layout() 

    table = Table(box=box.SIMPLE_HEAD, title=">> Resultados para: " + str(title), 
                  caption="[[bold red]:arrow_forward:[/]]:SELECCIÓN | [[bold green]:arrow_down::arrow_up: -:arrow_forward: " \
                    ":arrow_backward:- [/]]: MOVERSE | " \
                   "[[bold green]:right_arrow_curving_left:[/] ] DESCARGAR [[bold green]S[/]] SALIR \n" \
                    "[italic] Mostrando página " + str(page + 1) +" de " + str(results['pages_no']) + " de " + str(results['total']) + " resultado(s)[/]",
                    title_style="bold green",
                  show_header=True, header_style="bold yellow", caption_style="bold yellow", show_lines=False)
    table.add_column("#", justify="right", vertical="middle", style="bold green")
    table.add_column("Título", justify="left", vertical="middle", style="bold white")
    table.add_column("Descargas", justify="center", vertical="middle")
    table.add_column("Usuario", justify="center", vertical="middle")
    table.add_column("Fecha", justify="center", vertical="middle")

    count = page * 10
    rows = []
    descriptions = []
 
    for item in results['pages'][page]:
        try:
            titulo = str(item['titulo'])
            descargas = str(item['descargas'])
            usuario = str(item['nick'])
            fecha = str(item['fecha_subida'])
            descriptions.append(MetadataHighlighter(item['descripcion'], metadata))

            items = [str(count + 1), titulo, descargas, usuario, fecha]
            rows.append(items)
        except IndexError:
            pass
        count = count +1
    
    for i, row in enumerate(rows):
        row[0] =  "[bold red]:arrow_forward:[/]" + row[0] if i == selected else " " + row[0]
        table.add_row(*row, style=SELECTED if i == selected else "bold white")
 
    layout_results["table"].update(table)
    layout_results["description"].update(make_description_panel(descriptions[selected]))
    
    return layout_results

def MetadataHighlighter(text, metadata: Metadata) -> Text :
    """Apply style Highlight to all text  matches metadata and return a `Text` object"""
    
    highlighted = Text(text, justify="full")
    highlighted.highlight_words(metadata.keywords, style = "white on green4", case_sensitive=False)
    highlighted.highlight_words(metadata.quality, style = "white on green4", case_sensitive=False)
    highlighted.highlight_words(metadata.codec, style = "white on green4", case_sensitive=False)
    
    return highlighted

def paginate(items, per_page):
    """ Paginate `items` in perpage lists 
    and return a `Dict` with:
     * Total items
     * Number of pages
     * Per page amount
     * List of pages
    """
    pages = [items[i:i+per_page] for i in range(0, len(items), per_page)]
    return {
        'total': len(items),
        'pages_no': len(pages),
        'per_page': per_page,
        'pages': pages
    }