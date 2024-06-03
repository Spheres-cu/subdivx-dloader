Changelog
=========

1.5.4 (2024-06-03)
---------------
- Fixed some filename info retrieve.
- Update CLI.

1.5.3 (2024-05-29)
---------------
- Added title column.

1.5.2 (2024-05-28)
---------------
- Fixed error of files  without year or season-episode number.

1.5.1 (2024-05-28)
---------------
- Better search results filter.
- Now show more faster the search results.

1.5 (2024-05-24)
---------------

- Highlighted file metadata in search results.
- Added --Season, -S parameter for search by season.
- Refactored code for better ordered search results based in filename metadata and more faster load results.

1.4.1 (2024-05-09)
---------------
- Fixed error for rename various subtitles with same filename.

1.4 (2024-05-08)
---------------
Several change made to cli:
- Now you can select which subtitle download inside a zip o rar file.
- Also you can download all subtitles at once.
- You can download a complete season if you name one episode with the show + season : Young.Sheldon.S01.mkv
- The Logging config a has been updated.

1.3 (2024-05-05)
---------------
- Fixed download subtitle no getting old server url
- Added file log
- Some cosmetic changes

1.2 (2024-05-01)
---------------
Fixed search subtitles with year in the title

1.1 (2024-04-29)
---------------
- Fixed error when the filename hasn't episode number
- Fixed search movies with years without parenthesis

1.0 (2024-04-28)
---------------
- Modified cli.py, now allows you to obtain information about series and movies from the new design and format of sudivx.

- The rich module has been added to display the results in a table for better visibility.

- The -c (choose) argument has been modified to -nc (no-choose), now with this the option to display the results is by default unless -nc is passed and the first search result is obtained.
- Some bugs have been fixed


