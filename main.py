#!/home/irumble/lcbodeals.com/venv/bin/python
import asyncio
import json
import logging
import sys

from lcbodeals import (
    get_json_feed,
    json_feed_to_html,
    check_availablity,
    check_inventory,
)


logger = logging.getLogger(__name__)


def setup_logging(level=logging.DEBUG):
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)


def main():
    setup_logging(logging.INFO)
    slug = "blantons-single-barrel-special-reserve-kentucky-straight-bourbon-558320"
    # availablity = asyncio.run(check_availablity(slug))
    # logger.info("availability = %s", availablity)
    # inventory = asyncio.run(check_inventory(64174))
    # logger.info("inventory = %s", inventory)
    feed = get_json_feed()

    # with open('public/feed.json') as file_obj:
    #    feed = json.load(file_obj)

    if feed["items"]:
        json_feed_to_html(feed)
    else:
        logging.error("no items in feed")


if __name__ == "__main__":
    main()
