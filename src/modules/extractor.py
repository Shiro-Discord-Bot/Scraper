from modules.utils import cooldown

import re
import logging
from typing import Iterator, Tuple, Dict, Union, Optional, Any

import praw
import requests
from pymongo import MongoClient
from jikanpy import Jikan, APIException


class Extractor:
    """Fetches theme data from subreddit and parses it"""
    def __init__(self, db: MongoClient, reddit: praw.Reddit, session: requests.Session):
        self.db = db
        self.reddit = reddit
        self.jikan = Jikan(session=session)
        self.next_jikan_call = 0
        self.last_anime = 0

    def run(self) -> Iterator[Tuple[Dict[str, Union[int, str]], Dict[str, Union[int, str]]]]:
        """Returns a generator which handles the fetching and extracting process of animes and themes"""
        entries = self.fetch_entries()
        for entry in entries:
            themes = self.extract_themes(entry)
            for theme in themes:
                if self.db.themes.count_documents({"url": theme["url"]}, limit=1) != 0:
                    continue

                anime = None
                if self.last_anime != theme["mal_id"]:
                    data = self.fetch_anime(theme["mal_id"])
                    if not data:
                        continue

                    anime = self.extract_anime(data)
                    self.last_anime = theme["mal_id"]

                logging.info(f"Extracted theme {theme['title']}")
                yield anime, theme

    def fetch_entries(self) -> Iterator[str]:
        """Fetch anime entries from wiki of the subreddit /r/AnimeThemes"""
        year_index = self.reddit.subreddit("AnimeThemes").wiki["year_index"].content_md
        years = re.finditer(r"###\[.*?\]\(/r/AnimeThemes/wiki/(.*?)\)", year_index)

        for year_match in years:
            year = year_match.groups()[0]
            entries = self.reddit.subreddit("AnimeThemes").wiki[year].content_md.split("###")
            for entry in entries:
                yield entry

    def extract_themes(self, entry: str) -> Iterator[Dict[str, Union[int, str]]]:
        """Extract animes and themes from entries"""
        theme_metas = re.finditer(r"(.*?) \"(.*?)\"\|\[.*?\]\((https://animethemes\.moe/video/.*?.webm)\)", entry)
        try:
            mal_id = int(re.findall(r"\[.*?\]\(https://myanimelist.net/anime/(\d+).*?\)", entry)[0])
        except IndexError:
            return

        for theme_meta in theme_metas:
            theme = {
                "mal_id": mal_id,
                "type": theme_meta.groups()[0].lower(),
                "title": theme_meta.groups()[1],
                "url": theme_meta.groups()[2]
            }
            yield theme

    @cooldown
    def fetch_anime(self, mal_id: int) -> Optional[Dict[str, Any]]:
        """Fetch anime from Jikan"""
        try:
            return self.jikan.anime(mal_id)
        except APIException:
            logging.warning(f"Fetching anime {mal_id} failed")

    def extract_anime(self, data: Dict[str, Any]) -> Dict[str, Union[id, str]]:
        """Extract necessary data from fetched anime"""
        anime = {
            "mal_id": data["mal_id"],
            "title": data.get("english_title") or data["title"],
            "rank": data["rank"],
            "popularity": data["popularity"]
        }
        return anime
