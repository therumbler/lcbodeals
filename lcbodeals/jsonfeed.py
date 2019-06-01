"""turns a JSON Feed into various formats"""
import logging

from jinja2 import Environment, PackageLoader

TEMPLATES_DIR = "./templates/"
OUTPUT_DIR = "./public/"


def json_feed_to_html(json_feed):
    """take a JSON Feed obj and spit out HTML"""

    env = Environment(loader=PackageLoader("lcbodeals", "templates"))

    template = env.get_template("index.tmpl")

    html_string = template.render(**json_feed)
    # print(html_string)
    if not html_string:
        logging.error("html_string is empty!")
        return

    try:
        with open("/home/irumble/lcbodeals.com/public/index.html", "wb") as file_obj:
            file_obj.write(html_string.encode("utf-8"))
    except Exception as ex:
        logging.exception(ex)
