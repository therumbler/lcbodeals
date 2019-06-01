#!/home/irumble/lcbodeals.com/venv/bin/python
import json
import logging
import sys

from lcbodeals import get_json_feed, json_feed_to_html


def setup_logging(level=logging.DEBUG):
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

def main():
    setup_logging(logging.INFO)
    feed = get_json_feed()
    
    #with open('public/feed.json') as file_obj:
    #    feed = json.load(file_obj)

    if feed['items']:
        json_feed_to_html(feed)
    else:
        logging.error('no items in feed')

if __name__ == '__main__':
    main()
