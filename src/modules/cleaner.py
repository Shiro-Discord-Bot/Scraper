import logging
from pathlib import Path
from typing import List, Dict

from pymongo import MongoClient


class Cleaner:
    """Removes unnecessary garbage from the filesystem and the database"""
    def __init__(self, db: MongoClient):
        self.db = db

    def run(self) -> None:
        """Start the cleaning process"""
        logging.info("Running cleaning process")
        animes = [anime["mal_id"] for anime in list(self.db.animes.find({}, ["mal_id"]))]
        themes = [theme["mal_id"] for theme in list(self.db.themes.find({}, ["mal_id"]))]
        urls = {file.stem: f"https://animethemes.moe/video/{file.stem}.webm" for file in Path("themes").iterdir()}

        self.clear_themes(animes, urls)
        self.clear_files(urls)
        self.clear_animes(themes)
        self.clear_cache()

    def clear_themes(self, animes: List[int], urls: Dict[str, str]) -> None:
        """Deletes themes from database without anime or file relation"""
        deleted = self.db.themes.delete_many({
            "$or": [{
                "mal_id": {
                    "$not": {
                        "$in": animes
                    }
                }
            }, {
                "url": {
                    "$not": {
                        "$in": list(urls.values())
                    }
                }
            }]
        }).deleted_count
        logging.info(f"Deleted {deleted} themes from database")

    def clear_files(self, urls: Dict[str, str]) -> None:
        """Removes all themes from storage which have no entry in the database"""
        deleted = 0
        for file, url in urls.items():
            if self.db.themes.count_documents({"url": url}, limit=1) == 0:
                Path(f"themes/{file}.mp3").unlink(missing_ok=True)
                deleted += 1

        logging.info(f"Deleted {deleted} files from storage")

    def clear_animes(self, themes: List[int]) -> None:
        """Deletes animes from database without theme relation"""
        deleted = self.db.animes.delete_many({
            "mal_id": {
                "$not": {
                    "$in": themes
                }
            }
        }).deleted_count
        logging.info(f"Deleted {deleted} animes from database")

    def clear_cache(self) -> None:
        """Purges all remaining files in cache"""
        deleted = 0
        for file in Path("cache").iterdir():
            file.unlink(missing_ok=True)
            deleted += 1

        logging.info(f"Deleted {deleted} files from cache")
