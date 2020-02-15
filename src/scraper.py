from modules.cleaner import Cleaner
from modules.extractor import Extractor
from modules.processor import Processor

import os
import time

import logging
import praw
import requests
from sentry_sdk import init
from pymongo import MongoClient


class Scraper:
    def __init__(self):
        self.db = MongoClient(os.environ.get("MONGODB_CONNECTION")).shiro
        self.reddit = praw.Reddit(
            client_id=os.environ.get("REDDIT_CLIENT_ID"),
            client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
            user_agent=f"python:scraper:{os.environ.get('SCRAPER_RELEASE')} (by /u/Spinneeee)"
        )
        self.session = requests.Session()
        self.session.headers = {"User-Agent": "Mozilla/5.0"}
        self.run()

    def run(self):
        """Start updating themes and anime in the database"""
        logging.info("Initializing")
        cleaner = Cleaner(self.db)
        extractor = Extractor(self.db, self.reddit, self.session)
        processor = Processor(self.db, self.session)
        while True:
            logging.info("Starting new cycle")
            cleaner.run()
            for anime, theme in extractor.run():
                processor.run(anime, theme)

            logging.info("Finished cycle, waiting 3 hours")
            time.sleep(10800)


if __name__ == "__main__":
    init(dsn=os.environ.get("SENTRY_SCRAPER_DSN"), release=f"scraper-{os.environ.get('SCRAPER_RELEASE')}")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s :: %(levelname)s :: %(message)s")
    SCRAPER = Scraper()
