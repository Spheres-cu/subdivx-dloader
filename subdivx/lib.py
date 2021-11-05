import requests 
import logging
import logging.handlers
import os
import urllib.parse

from tempfile import NamedTemporaryFile
from zipfile import is_zipfile, ZipFile
from rarfile import is_rarfile
from bs4 import BeautifulSoup

PYTHONUTF8=1

SUBDIVX_SEARCH_URL = "https://www.subdivx.com/index.php"

SUBDIVX_DOWNLOAD_MATCHER = {'name':'a', 'rel':"nofollow", 'target': "new"}

LOGGER_LEVEL = logging.INFO
LOGGER_FORMATTER = logging.Formatter('%(asctime)-25s %(levelname)-8s %(name)-29s %(message)s', '%Y-%m-%d %H:%M:%S')

s = requests.Session()

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
     "oxdown": 1,
     "buscar": buscar ,
    }
    s.headers.update({"User-Agent":"Mozilla/5.0 (X11; Linux x86_64; rv:85.0) Gecko/20100101 Firefox/85.0"})
    page = s.get(SUBDIVX_SEARCH_URL, params=params).text
    soup = BeautifulSoup(page, 'html5lib')
    titles = soup('div', id='menu_detalle_buscador')

    # only include results for this specific serie / episode
    # ie. search terms are in the title of the result item
    descriptions = {
        t.nextSibling(id='buscador_detalle_sub')[0].text: t.next('a')[0]['href'] for t in titles
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
    if (choose):
        count = 0
        for item in (results):
            print ("\t \033[92m %i \033[0m %s" % (count , item[0][0]))
            count = count +1
        res = int(input ("Sub to download? (0)") or "0")
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
            ret_code = subprocess.call(['unrar', 'e', '-n*srt', '-n*txt', rar_path])
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
