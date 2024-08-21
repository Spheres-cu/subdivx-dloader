
import os
import json
import time
from rich import box
from rich.table import Table
from rich.prompt import IntPrompt
from rich.live import Live
from .console import console
from readchar import readkey, key
from json import JSONDecodeError
from tempfile import NamedTemporaryFile
from zipfile import is_zipfile, ZipFile
from rarfile import is_rarfile, RarFile

from .sdxutils import *

_sub_extensions = ['.srt', '.ssa']

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
    console.print("\r")
    logger.debug(f'Searching subtitles for: ' + str(title) + " " + str(number).upper())
    with console.status(f'Searching subtitles for: ' + str(title) + " " + str(number).upper()):
        try:
            page = s.request(
                'POST',
                SUBDIVX_SEARCH_URL,
                headers=headers,
                fields=fields
            ).data

        except (urllib3.exceptions.NewConnectionError, urllib3.exceptions.TimeoutError, urllib3.exceptions.ProxyError, urllib3.exceptions.HTTPError) as e:
            msg = Network_Connection_Error(e)
            console.print(":no_entry: [bold red]Some Network Connection Error occurred[/]: " + msg, new_line_start=True, emoji=True)
            if LOGGER_LEVEL == logging.DEBUG:
               logger.debug(f'Network Connection Error occurred: {msg}')
            exit(1)

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
    aaData_Items = get_list_Dict(json_aaData)
    
    if aaData_Items is not None:
        # Cleaning Items
        list_Subs_Dicts = clean_list_subs(aaData_Items)
    else:
        raise NoResultsError(f'No suitable data were found for: "{buscar}"')
    
    """" ####### For testing ########## 
    page = load_aadata()
    aaData = json.loads(page)['aaData']
    aaData_Items = get_list_Dict(aaData)

    if aaData_Items is not None:
         list_Subs_Dicts = clean_list_subs(aaData_Items)
    else:
        raise NoResultsError(f'No suitable data were found for: "{buscar}"')
   
    ##### For testing ######### """
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
    
    table_title = str(title) + " " + str(number).upper()
    results_pages = paginate(results, 10)

    if (no_choose==False):
        
        try:
            selected = 0
            page = 0
            with Live(
                generate_results (table_title, results_pages, metadata, page, selected),auto_refresh=False
            ) as live:
                while True:
                    ch = readkey()
                    if ch == key.UP or ch == key.PAGE_UP:
                        selected = max(0, selected - 1)

                    if ch == key.DOWN or ch == key.PAGE_DOWN:
                        selected = min(len(results_pages['pages'][page]) - 1, selected + 1)

                    if ch == key.RIGHT :
                        page = min(results_pages["pages_no"] - 1, page + 1)
                        selected = 0

                    if ch == key.LEFT :
                        page = max(0, page - 1)
                        selected = 0

                    if ch == key.ENTER:
                        live.stop()
                        res = results_pages['pages'][page][selected]['id']
                        break

                    if ch in ["S", "s"]:
                        live.stop()
                        res = -1
                        break
                    live.update(generate_results(table_title, results_pages, metadata, page, selected), refresh=True)

        except KeyboardInterrupt:
            logger.debug('Interrupted by user')
            clean_screen()
            console.print(":slightly_frowning_face: [bold red]Interrupto por el usuario...", emoji=True, new_line_start=True)
            time.sleep(0.8)
            clean_screen()
            exit(1)

        if (res == -1):
            logger.debug('Download Canceled')
            clean_screen()
            console.print("\r\n" + ":confused_face: [bold red] Cancelando descarga...", emoji=True, new_line_start=True)
            time.sleep(0.8)
            clean_screen()
            exit(0)
        url = SUBDIVX_DOWNLOAD_PAGE + str(res)
    else:
        # get first subtitle
        url = SUBDIVX_DOWNLOAD_PAGE + str(results_pages['pages'][0][0]['id'])
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
    clean_screen()
    for i in range ( 9, 0, -1 ):

        logger.debug(f"Trying Download from link: {SUBDIVX_DOWNLOAD_PAGE + 'sub' + str(i) + '/' + url[24:]}")
        # Download file
        with console.status("Downloading Subtitle... ", spinner="dots4"):
            try:
                temp_file.write(s.request('GET', SUBDIVX_DOWNLOAD_PAGE + 'sub' + str(i) + '/' + url[24:], headers=headers).data)
                temp_file.seek(0)
            except (urllib3.exceptions.NewConnectionError, urllib3.exceptions.TimeoutError, urllib3.exceptions.ProxyError, urllib3.exceptions.HTTPError) as e:
                msg = Network_Connection_Error(e)
                console.print(":no_entry: [bold red]Some Network Connection Error occurred[/]: " + msg, new_line_start=True, emoji=True)
                if LOGGER_LEVEL == logging.DEBUG:
                    logger.debug(f'Network Connection Error occurred: {msg}')
                exit(1)

        # Checking if the file is zip or rar then decompress
        compressed_sub_file = ZipFile(temp_file) if is_zipfile(temp_file.name) else RarFile(temp_file) if is_rarfile(temp_file.name) else None

        if compressed_sub_file is not None:
            SUCCESS = True
            logger.debug(f"Downloaded from: {SUBDIVX_DOWNLOAD_PAGE + 'sub' + str(i) + '/' + url[24:]}")

            # In case of existence of various subtitles choose which to download
            if len(compressed_sub_file.infolist()) > 1 :
                clean_screen()
                count = 0
                choices = []
                choices.append(str(count))
                list_sub = []
                table = Table(box=box.ROUNDED, title=">> Subtítulos disponibles:", title_style="bold green",show_header=True, 
                            header_style="bold yellow", show_lines=True, title_justify='center')
                table.add_column("#", justify="center", vertical="middle", style="bold green")
                table.add_column("Subtítulos", justify="center" , no_wrap=True)

                for i in compressed_sub_file.infolist():
                    if i.is_dir() or os.path.basename(i.filename).startswith("._"):
                        continue
                    i.filename = os.path.basename(i.filename)
                    list_sub.append(i.filename)
                    table.add_row(str(count + 1), str(i.filename))
                    count += 1
                    choices.append(str(count))
            
                choices.append(str(count + 1))
                console.print(table)
                console.print("[bold green]>> [0] Descargar todos\r", new_line_start=True)
                console.print("[bold red]>> [" + str(count + 1) + "] Cancelar descarga\r", new_line_start=True)

                try:
                    res = IntPrompt.ask("[bold yellow]>> Elija un [" + "[bold green]#" + "][bold yellow]. Por defecto:", 
                                show_choices=False, show_default=True, choices=choices, default=0)
                except KeyboardInterrupt:
                    logger.debug('Interrupted by user')
                    console.print(":slightly_frowning_face: [bold red]Interrupto por el usuario...", emoji=True, new_line_start=True)
                    time.sleep(0.5)
                    clean_screen()
                    exit(1)
            
                if (res == count + 1):
                    logger.debug('Canceled Download Subtitle')
                    console.print(":confused_face: [bold red] Cancelando descarga...", emoji=True, new_line_start=True)
                    temp_file.close()
                    os.unlink(temp_file.name)
                    time.sleep(2)
                    clean_screen()
                    exit(0)

                logger.debug('Decompressing files')
                if res == 0:
                    with compressed_sub_file as csf:
                        for sub in csf.infolist():
                            if not sub.is_dir():
                                sub.filename = os.path.basename(sub.filename)
                            if any(sub.filename.endswith(ext) for ext in _sub_extensions) and '__MACOSX' not in sub.filename:
                                logger.debug(' '.join(['Decompressing subtitle:', sub.filename, 'to', os.path.dirname(topath)]))
                                csf.extract(sub, os.path.dirname(topath))
                    compressed_sub_file.close()
                else:
                    if any(list_sub[res - 1].endswith(ext) for ext in _sub_extensions) and '__MACOSX' not in list_sub[res - 1]:
                        with compressed_sub_file as csf:
                            for sub in csf.infolist():
                                if not sub.is_dir():
                                    sub.filename = os.path.basename(sub.filename)
                                    if list_sub[res - 1] == sub.filename :
                                        logger.debug(' '.join(['Decompressing subtitle:', list_sub[res - 1], 'to', os.path.dirname(topath)]))
                                        csf.extract(sub, os.path.dirname(topath))
                                        break
                    compressed_sub_file.close()
                logger.debug(f"Done extract subtitles!")
                console.print(":Smiley: Done extract subtitle!", emoji=True, new_line_start=True)
            else:
                for name in compressed_sub_file.infolist():
                    # don't unzip stub __MACOSX folders
                    if any(name.filename.endswith(ext) for ext in _sub_extensions) and '__MACOSX' not in name.filename:
                        logger.debug(' '.join(['Decompressing subtitle:', name.filename, 'to', os.path.dirname(topath)]))
                        compressed_sub_file.extract(name, os.path.dirname(topath))
                compressed_sub_file.close()
                logger.debug(f"Done extract subtitle!")
                console.print(":Smiley: Done extract subtitle!", emoji=True, new_line_start=True)
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
