qBittorrent search engine for releases.moe
==========================================

Installation
------------

Download the [plugin file](https://github.com/Secozzi/qbittorrent-releases-moe-search-plugin/blob/master/engines/releasesmoe.py).

Options
-------

There are two settings you can change, both present at the top of the .py file just after the imports.

* RENDER_HTML - Show more info about the show in a similar way to how releases.moe does it. Note: requires https://github.com/Secozzi/VueTorrent since it relies on rendering custom html.
* REPLACE_TORRENT_NAME - Set to true if you only want to see the release group and series name (from anilist) instead of the name of the torrent.
