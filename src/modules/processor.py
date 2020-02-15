from modules.utils import storage, Timeout

import re
import time
import requests
import logging
from pathlib import Path
from typing import Optional, Dict, Union

from pymongo import MongoClient
from moviepy.editor import VideoFileClip


class Processor:
    """Downloads themes and adds them to the database"""
    def __init__(self, db: MongoClient, session: requests.Session):
        self.db = db
        self.session = session

    def run(self, anime, theme) -> None:
        """Download themes and add them to the database after converted"""
        file = self.download_theme(theme["url"])
        if not file:
            return

        file = self.convert_webm(file)
        if not file:
            return

        self.update_theme(theme)
        if anime:
            self.update_anime(anime)

    @storage
    def download_theme(self, url: str) -> Optional[str]:
        """Try to download theme from url and return file name"""
        file = re.findall(r"https://animethemes\.moe/video/(.*?)\.webm", url)[0]
        resp = self.session.get(url)
        if resp.status_code == 200:
            with open(f"cache/{file}.webm", mode="wb") as f:
                f.write(resp.content)
            logging.info(f"Downloaded {url}")
            return file

        if resp.status_code == 429:
            retry = resp.headers.get("Retry-After")
            time.sleep(retry)

        logging.warning(f"Download failed with code {resp.status_code}")

    def convert_webm(self, file: str) -> Optional[str]:
        """Converts a webm to mp3"""
        try:
            with Timeout(), VideoFileClip(f"cache/{file}.webm") as clip:
                clip.audio.write_audiofile(f"themes/{file}.mp3", verbose=False, logger=None)
            logging.info(f"Converted file {file}")
            return file
        except (OSError, TimeoutError, IndexError):
            logging.warning(f"Converting of file {file} failed")
        finally:
            Path(f"cache/{file}.webm").unlink(missing_ok=True)

    def update_anime(self, anime: Dict[str, Union[int, str]]) -> None:
        """Adds or updates an anime in the database"""
        self.db.animes.replace_one(
            {
                "mal_id": anime["mal_id"]
            },
            {
                **anime
            },
            upsert=True
        )

    def update_theme(self, theme: Dict[str, Union[int, str]]) -> None:
        """Adds or updates a theme in the database"""
        self.db.themes.replace_one(
            {
                "url": theme["url"]
            },
            {
                **theme
            },
            upsert=True
        )
