#!/bin/env python

import os
import sys
import argparse
from .sdxlib import *
from guessit import guessit
from .sdxlib import _sub_extensions
from tvnamer.utils import FileFinder
from contextlib import contextmanager

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

_extensions = [
    'avi', 'mkv', 'mp4',
    'mpg', 'm4v', 'ogv',
    'vob', '3gp',
    'part', 'temp', 'tmp'
]

@contextmanager
def subtitle_renamer(filepath, inf_sub):
    """dectect new subtitles files in a directory and rename with
       filepath basename"""

    def extract_name(filepath):
        """ Extract Filename """
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
        new_ext = os.path.splitext(new_file)[1]
        if new_ext not in _sub_extensions:
            # only apply to subtitles
            continue
        filename = extract_name(filepath)
        new_file_dirpath = os.path.join(os.path.dirname(filename), new_file)

        try:
           if os.path.exists(filename + new_ext):
               continue
           else:
                if inf_sub['type'] == "episode" :
                    info = guessit(new_file)
                    number = f"s{info['season']:02}e{info['episode']:02}"
                    if number == inf_sub['number']:
                        os.rename(new_file_dirpath, filename + new_ext)
                    else:
                        continue
                else:
                    os.rename(new_file_dirpath, filename + new_ext)
                      
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
    parser.add_argument('--verbose', '-v', action='store_true',
                        default=False, help="Be in verbose mode")
    parser.add_argument('--no-choose', '-nc', action='store_true',
                        default=False, help="No Choose sub manually")
    parser.add_argument('--Season', '-S', action='store_true',
                        default=False, help="Search for Season")
    parser.add_argument('--force', '-f', action='store_true',
                        default=False, help="override existing file")
    parser.add_argument('--keyword','-k',type=str,help="Add keyword to search among subtitles")
    parser.add_argument('--title','-t',type=str,help="Set the title of the show")
    args = parser.parse_args()

    # Setting logger
    setup_logger(LOGGER_LEVEL if not args.verbose else logging.DEBUG)

    logfile = logging.FileHandler(file_log, mode='w', encoding='utf-8')
    logfile.setFormatter(LOGGER_FORMATTER_LONG)
    logfile.setLevel(logging.DEBUG)
    logger.addHandler(logfile)

    if not args.quiet:
        console = logging.StreamHandler()
        console.setFormatter(LOGGER_FORMATTER_SHORT)
        console.setLevel(logging.INFO if not args.verbose else logging.DEBUG)
        logger.addHandler(console)
    
    if os.path.exists(args.path):
      cursor = FileFinder(args.path, with_extension=_extensions)
    else:
        logger.error(f'No file or folder were found for: "{args.path}"')
        sys.exit(1)

    for filepath in cursor.findFiles():
        # skip if a subtitle for this file exists
        exists_sub = False
        sub_file = os.path.splitext(filepath)[0]
        for ext in _sub_extensions:
            if os.path.exists(sub_file + ext):
                if args.force:
                   os.remove(sub_file + ext)
                else:
                    exists_sub = True
                    break
    
        if exists_sub:
            logger.info(f'Subtitle already exits use -f for force downloading')
            continue

        filename = os.path.basename(filepath)
        
        try:
            info = guessit(filename, "--exclude release_group")
            if info["type"] == "episode" :
               number = f"s{info['season']:02}e{info['episode']:02}" if "episode" in info and not args.Season else f"s{info['season']:02}" 
            else:
               number = f"({info['year']})" if "year" in info  else  ""

            metadata = extract_meta_data(filename, args.keyword)

            if (args.title):
                title=args.title
            else:
                if info["type"] == "movie" :
                  title = info["title"] 
                else:
                    title=f"{info['title']} ({info['year']})" if "year" in info else info['title']
            
            inf_sub = {
                'type': info["type"],
                'season' : False if info["type"] == "movie" else args.Season,
                'number' : f"s{info['season']:02}e{info['episode']:02}" if "episode" in info else number
            }
            
            url = get_subtitle_url(
                title, number,
                metadata,
                no_choose=args.no_choose,
                inf_sub=inf_sub)
            
        except NoResultsError as e:
            logger.error(str(e))
            url = None

        if (url is not None):
            with subtitle_renamer(filepath, inf_sub=inf_sub):
                 get_subtitle(url, topath = args.path)

if __name__ == '__main__':
    main()
