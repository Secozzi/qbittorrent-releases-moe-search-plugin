# VERSION: 1.0
# AUTHORS: Secozzi

import gzip
import io
import sys
from collections import defaultdict
from dataclasses import dataclass
from html.parser import HTMLParser
from collections.abc import Mapping
from typing import Any, Optional
from urllib.parse import unquote
import urllib.error
import urllib.request
import json

from helpers import htmlentitydecode, headers
from novaprinter import prettyPrinter


RENDER_HTML = False  # Use only with https://github.com/Secozzi/VueTorrent
REPLACE_TORRENT_NAME = True  # Replaces torrent name with release group + series name


@dataclass
class AnilistSearchResult:
    id: int
    name: str
    cover: str
    format: str
    year: int
    status: str
    episodes: int


@dataclass
class ReleasesMoeInfo:
    nyaa_url: str
    anilist_info: AnilistSearchResult
    release_group: str
    notes: str
    is_best: bool


def retrieve_url(url: str, custom_headers: Mapping[str, Any] = {}, request_data: Optional[Any] = None) -> str:
    """ Return the content of the url page as a string """

    request = urllib.request.Request(url, request_data, {**headers, **custom_headers})
    try:
        response = urllib.request.urlopen(request)
    except urllib.error.URLError as errno:
        print(f"Connection error: {errno.reason}", file=sys.stderr)
        return ""
    data: bytes = response.read()

    # Check if it is gzipped
    if data[:2] == b'\x1f\x8b':
        # Data is gzip encoded, decode it
        with io.BytesIO(data) as compressedStream, gzip.GzipFile(fileobj=compressedStream) as gzipper:
            data = gzipper.read()

    charset = 'utf-8'
    try:
        charset = response.getheader('Content-Type', '').split('charset=', 1)[1]
    except IndexError:
        pass

    dataStr = data.decode(charset, 'replace')
    dataStr = htmlentitydecode(dataStr)
    return dataStr


def get_pill(text_color: str, bg_color: str, text: Any) -> str:
    return (f"<span style='color: rgb({text_color});font-weight: 500;padding-top: .125rem;padding-bottom: "
            f".125rem;padding-left: .300rem;padding-right: .300rem;background-color: rgb({bg_color});border-radius: "
            f".25rem;'>{text}</span>")


def get_pill_rounded(
        text_color: str,
        bg_color: str,
        text: Any,
        title: str = "",
        style: str = "font-weight: 500;font-size: .75rem;padding-top: .125rem;padding-bottom: .125rem;padding-left: "
                     ".625rem;padding-right: .625rem",
) -> str:
    return f"<span title='{title}', style='color: rgb({text_color});background-color: rgb({bg_color});border-radius: 9999px;{style}'>{text}</span>"


def get_html(releases_info: ReleasesMoeInfo) -> str:
    group = get_pill("30 64 175", "219 234 254", releases_info.release_group)
    if releases_info.is_best:
        tag = get_pill("22 101 52", "220 252 231", "Best")
    else:
        tag = get_pill("153 27 27", "254 226 226", "Alt")

    format = get_pill_rounded("22 101 52", "220 252 231", releases_info.anilist_info.format)
    year = get_pill_rounded("30 64 175", "219 234 254", releases_info.anilist_info.year)
    if (ep_count := releases_info.anilist_info.episodes) == 1:
        episode_text = "1 Episode"
    else:
        episode_text = f"{ep_count} Episodes"
    episodes = get_pill_rounded("31 41 55", "243 244 246", episode_text) if format != "Movie" else ""
    status = get_pill_rounded("31 41 55", "243 244 246", releases_info.anilist_info.status)

    notes_svg = """<svg xmlns="http://www.w3.org/2000/svg" height="1.25rem" viewBox="0 -960 960 960" width="1.25rem" 
    fill="#000000" ><path d="M160-400v-80h280v80H160Zm0-160v-80h440v80H160Zm0-160v-80h440v80H160Zm360 
    560v-123l221-220q9-9 20-13t22-4q12 0 23 4.5t20 13.5l37 37q8 9 12.5 20t4.5 22q0 11-4 
    22.5T863-380L643-160H520Zm300-263-37-37 37 37ZM580-220h38l121-122-18-19-19-18-122 121v38Zm141-141-19-18 37 
    37-18-19Z"/></svg>"""
    notes = f"""
        {get_pill_rounded(
            "31 41 55", 
            "243 244 246",
            notes_svg,
            style="padding-left: .625rem;padding-right: .625rem;display: inline-flex;align-items: center;margin: 2px;",
            title=releases_info.notes,
        )}
    """ if releases_info.notes else ""

    return f"""<div style="margin-bottom: 8px; margin-top: 8px;display: flex;flex-direction: row; border-style: 
    solid; border-width: 1px; box-sizing: border-box; border-radius: .25rem; border-color: hsl(240 5.9% 90%);">
        <img src={releases_info.anilist_info.cover} style="border-radius: .25rem 0 0 .25rem; object-fit: cover;height: 7rem; max-width: 100%; display: block;">
        <div style="padding: .5rem; display: flex; flex-direction: column; justify-content: space-between; height: 7rem">
            <div style="display: flex; gap: 8px; align-items: center; margin: 0;">
                {group} {tag} <h3 style="font-weight: 600;font-family: ui-sans-serif, system-ui, sans-serif;padding-bottom: 5px;"> {releases_info.anilist_info.name} </h3>
            </div>

            <div style="display: flex; gap: .5rem; display: inline-flex; align-items: center; margin: 0;">
                {format} {year} {episodes} {status} {notes}
            </div>
        </div>
    </div>""".replace("\n", "")


class releasesmoe(object):
    url = "https://releases.moe"
    name = "releases.moe"
    supported_categories = {
        "all": "all",
        "anime": "anime",
    }

    def search(self, what: str, cat: str = "all") -> None:
        anilist_items = self.AnilistSearcher(search_query=unquote(what)).get_anilist_search_result()
        self.ReleasesMoeSearcher(anilist_items).list_releases()

    class ReleasesMoeSearcher:
        class NyaaParser(HTMLParser):
            def __init__(self, releases_data: ReleasesMoeInfo):
                HTMLParser.__init__(self)
                self.releases_data = releases_data

                self.is_panel = False
                self.parse_title = False
                self.finished_parsing = False
                self.parse_panel = False
                self.row_counter = 0
                self.col_counter = 0

                self.data = {
                    "engine_url": "https://releases.moe",
                    "desc_link": self.releases_data.nyaa_url,
                }

            def handle_starttag(self, tag: str, attr: list[tuple[str]]):
                if self.finished_parsing:
                    return

                attrs = defaultdict(str)
                for key, value in attr:
                    attrs[key] = value

                if attrs["class"].startswith("panel panel-"):
                    if self.is_panel:
                        self.finished_parsing = True
                        prettyPrinter(self.data)
                        return
                    self.is_panel = True

                if attrs["class"] == "card-footer-item" and attrs["href"].startswith("magnet:"):
                    self.data["link"] = attrs["href"]

                if self.is_panel:
                    if attrs["class"] == "panel-title":
                        self.parse_title = True
                    if "data-timestamp" in attrs:
                        self.data["pub_date"] = int(attrs["data-timestamp"])
                    if attrs["class"] == "panel-body":
                        self.parse_panel = True

                if self.parse_panel:
                    if attrs["class"] == "row" and tag == "div":
                        self.row_counter += 1
                        self.col_counter = 0

                    if attrs["class"].startswith("col-md") and tag == "div":
                        self.col_counter += 1

            def handle_data(self, data):
                if self.finished_parsing:
                    return

                if self.parse_title:
                    if RENDER_HTML:
                        self.data["name"] = get_html(self.releases_data)
                    else:
                        if REPLACE_TORRENT_NAME:
                            self.data["name"] = (f"[{'BEST' if self.releases_data.is_best else 'ALT'}] "
                                                 f"[{self.releases_data.release_group}] "
                                                 f"{self.releases_data.anilist_info.name}")
                        else:
                            self.data["name"] = f"[{'BEST' if self.releases_data.is_best else 'ALT'}] {data.strip()}"
                    self.parse_title = False

                if self.parse_panel:
                    if stripped_data := data.strip():
                        if self.row_counter == 2 and self.col_counter == 4:
                            self.data["seeds"] = int(stripped_data)
                        if self.row_counter == 3 and self.col_counter == 4:
                            self.data["leech"] = int(stripped_data)
                        if self.row_counter == 4 and self.col_counter == 2:
                            self.data["size"] = stripped_data

        def __init__(self, anilist_items: list[AnilistSearchResult]):
            self.anilist_items = anilist_items
            self.anilist_lookup = {a.id: a for a in anilist_items}

        def list_releases(self) -> None:
            filter_query = "||".join([f"alID={i.id}" for i in self.anilist_items])
            api_url = (f"https://releases.moe/api/collections/entries/records?expand=trs&filter={filter_query}&fields"
                       f"=alID,notes,expand.trs.infoHash,expand.trs.isBest,expand.trs.releaseGroup,"
                       f"expand.trs.tracker,expand.trs.url&page=1&perPage=30")
            releases_result = json.loads(retrieve_url(api_url))

            for release in releases_result["items"]:
                for torrent in release["expand"]["trs"]:
                    if torrent["tracker"] != "Nyaa":
                        continue

                    parser = self.NyaaParser(
                        ReleasesMoeInfo(
                            nyaa_url=torrent["url"],
                            is_best=torrent["isBest"],
                            anilist_info=self.anilist_lookup[release["alID"]],
                            release_group=torrent["releaseGroup"],
                            notes=release["notes"],
                        )
                    )
                    html = retrieve_url(torrent["url"])
                    parser.feed(html)
                    parser.close()

    class AnilistSearcher:
        def __init__(self, search_query: str) -> None:
            self.search_query = search_query

        ANILIST_SEARCH_QUERY = """query (
          $search: String
          $sort: [MediaSort]
          $page: Int
          $perPage: Int
        ) {
          Page(page: $page, perPage: $perPage) {
            pageInfo {
              total
            }
            media(
              type: ANIME
              search: $search
              sort: $sort
              format_not: MUSIC
              status_not_in: [NOT_YET_RELEASED, CANCELLED]
            ) {
              id
              title {
                romaji
                english
              }
              coverImage {
                extraLarge
              }
              format
              seasonYear
              status
              episodes
            }
          }
        }"""

        def get_anilist_search_result(self) -> list[AnilistSearchResult]:
            variables = {
                "page": 1,
                "perPage": 30,
                "search": self.search_query,
                "sort": "START_DATE_DESC",
            }

            data = {
                "query": self.ANILIST_SEARCH_QUERY,
                "variables": variables,
            }

            post_body = str(json.dumps(data)).encode("utf-8")
            result = json.loads(
                retrieve_url(
                    url="https://graphql.anilist.co/",
                    custom_headers={"Content-Type": "application/json"},
                    request_data=post_body,
                )
            )

            return [
                AnilistSearchResult(
                    id=m["id"],
                    name=m["title"]["english"] or m["title"]["romaji"],
                    cover=m["coverImage"]["extraLarge"],
                    format=m["format"].title(),
                    year=m["seasonYear"],
                    status=m["status"].title(),
                    episodes=m["episodes"],
                )
                for m in result["data"]["Page"]["media"]
            ]
