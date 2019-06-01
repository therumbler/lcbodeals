#!/usr/bin/env python
"""crawler to find the best deals from the lcbo website"""
import asyncio
import logging
import json  # for debug only
import re

import aiohttp
from bs4 import BeautifulSoup

# __all__ = ["get_json_feed", "check_availablity"]

PAGE_SIZE = 24
SEM = None
logger = logging.getLogger(__name__)


async def call(session, kwargs):
    """hit the server"""
    global SEM
    url = "http://www.lcbo.com/webapp/wcs/stores/servlet/CategoryNavigationResultsView"
    url = "https://www.lcbo.com/webapp/wcs/stores/servlet/SearchDisplay"

    async with SEM:
        try:
            async with session.get(url, params=kwargs) as resp:
                logger.debug(f"got response from {resp.url}")
                return await resp.text()
        except RuntimeError:
            # some other exception was likely thrown
            pass


async def _get_page(session, begin_index=0):
    """get a single page"""
    kwargs = {
        "pageSize": PAGE_SIZE,
        "tabSlotId": 6,
        "manufacturer": "",
        "searchType": 1000,
        "resultCatEntryType": 2,
        "catalogId": 10001,
        "categoryId": "",
        "langId": "-1",
        "storeId": 10203,
        "sType": "SimpleSearch",
        "filterFacet": "",
        "metaData": "bHRvOnRydWU=",
        "contentBeginIndex": 0,
        "productBeginIndex": begin_index,
        "beginIndex": begin_index,
        "orderBy": "",
        "categoryPath": "//",
        "pageView": "",
        "resultType": "products",
        "orderByContent": "",
        "searchTerm": "",
        "facet": "",
        "catalogId": 10001,
        "langId": -1,
        "fromPage": "",
        "loginError": "",
        "userId": -1002,
        "showAll": "LTO",
        "objectId": "",
        "requesttype": "ajax",
    }

    kwargs = {
        "tabSlotId": 6,
        "langId": -1,
        "urlRequestType": "Base",
        "showResultsPage": "true",
        "resultType": "both",
        "sType": "SimpleSearch",
        "ajaxStoreImageDir": "/wcsstore/LCBOStorefrontAssetStore/",
        "facetName_1": "ON SALE",
        "ddkey": "ProductListingView_6_3074457345618261807_2310",
        "resultCatEntryType": 2,
        "enableSKUListView": "false",
        "disableProductCompare": "false",
        "catalogId": 10051,
        "searchTerm": '"*"',
        "facet_1": "onsale%3A%22ON+SALE%22",
        "storeId": 10203,
        "beginIndex": begin_index,
        "pageSize": PAGE_SIZE,
        "fromPage": "catalogEntryList",
    }

    text = await call(session, kwargs=kwargs)
    parsed = await _parse_response_text(text)

    return parsed


async def _parse_product(product_soup):
    """parse an individual product"""
    url = product_soup.find("a")["href"]
    product_id = int(re.search(r"\d+", url).group())
    if not product_id:
        try:
            product_id = int(product_soup["id"].replace("product-", ""))
        except ValueError as ex:
            logger.error(str(ex))
            product_id = int(re.search(r"\d+_(\d+)", product_soup["id"]).group(1))
        except KeyError:
            logger.error("no id attribute")
            return

    title_anchor = product_soup.find("a")

    price_element = product_soup.find("span", class_="price")
    price_saved_string = product_soup.find("span", class_="listPrice_save").string
    try:
        price = float(price_element.string.replace("$", ""))
    except ValueError:
        raise ValueError(
            "cannot calculate float for price of %s" % price_element.string
        )

    price_saved = float(re.search(r"(?<=\$).*", price_saved_string).group())
    # percentage_saved = price_saved / price_was
    price_was = price + price_saved
    percentage_saved = price_saved / (price + price_saved)
    title = title_anchor.string.strip()
    # url = 'https://www.lcbo.com{}'.format(title_anchor['href'])
    url = title_anchor["href"]
    image = "https://www.lcbo.com/content/dam/lcbo/products/{:06d}.jpg/jcr:content/renditions/cq5dam.thumbnail.319.319.png".format(
        product_id
    )
    return {
        "id": url,
        "url": url,
        "title": title,
        "image": image,
        "summary": """
        ${price:.2f}. ${price_saved:.2f} ({percentage_saved:.0%}) off!""".format(
            title=title,
            price_saved=price_saved,
            percentage_saved=percentage_saved,
            price=price,
        ).strip(),
        "_lcbodeals": {
            "price": price,
            "price_was": price_was,
            "price_saved": price_saved,
            "percentage_saved": percentage_saved,
        },
    }


def _get_total_product_count(soup):
    """get the total product count for the search"""
    el = soup.find("span", id="searchTabProdCount")
    return int(el.string)


async def _parse_response_text(text):
    """Parse the response text using BeautifulSoup"""
    if text is None:
        logger.error("no text")
        return None
    soup = BeautifulSoup(text, "html.parser")
    total_product_count = _get_total_product_count(soup)

    product_elements = soup.find_all("div", class_="product-info-section")

    if not product_elements:
        print(text)
        raise Exception("no elements")

    products = []
    for element in product_elements:
        parsed = await _parse_product(element)
        if parsed:
            products.append(parsed)

    return {"total_product_count": total_product_count, "products": products}


async def _crawl():
    """crawl the deals"""
    global SEM
    SEM = asyncio.Semaphore(2)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        # first page
        page_one = await _get_page(session, begin_index=0)
        total_product_count = page_one["total_product_count"]
        logger.info("total_product_count = %s", total_product_count)

        start = len(page_one["products"])

        begin_indexes = range(start, total_product_count, PAGE_SIZE)
        more_responses = await asyncio.gather(
            *(_get_page(session, begin_index=i) for i in begin_indexes)
        )
        for resp in more_responses:
            page_one["products"].extend(resp["products"])

    page_one["products"].sort(key=lambda d: -d["_lcbodeals"]["percentage_saved"])
    return page_one


def get_json_feed():
    """turn it into a JSON Feed dict"""
    logger.info("starting get_json_feed...")
    loop = asyncio.get_event_loop()
    try:
        resp = loop.run_until_complete(_crawl())
    finally:
        loop.close()

    if not resp["products"]:
        logger.error("no products found")
    logger.info("%s products found", len(resp["products"]))

    feed = {
        "version": "https://jsonfeed.org/version/1",
        "title": "LCBO Deals",
        "description": "The best deals on the LCBO site",
        "home_page_url": "https://www.lcbodeals.com",
        "feed_url": "https://www.lcbodeals.com/feed.json",
        "items": resp["products"],
    }

    logger.info("finished get_json_feed")
    return feed


async def get_deals():
    """crawl the site for the deals"""
    resp = await _crawl()
    return resp


def _html_to_availablity(html: str):
    soup = BeautifulSoup(html, "html.parser")
    home_delivery = soup.find("div", class_="productDelivery")
    p_elem = home_delivery.find("p", role="button")
    resp = {"home_delivery": p_elem.string.strip()}

    store_pickup = soup.find("div", class_="storePickup")

    p_elem = store_pickup.find("p", role="button")
    resp["store_pickup"] = p_elem.string.strip()
    walk_in = soup.find("div", class_="walkIn")
    p_elem = walk_in.find("p", role="button")
    resp["walk_in"] = p_elem.string.strip()

    return resp


async def check_availablity(slug: str):
    url = f"https://www.lcbo.com/webapp/wcs/stores/servlet/en/lcbo/{slug}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            html = await resp.text()
    availability = _html_to_availablity(html)
    return availability


def _html_to_inventory(html: str):
    soup = BeautifulSoup(html, "html.parser")

    pattern = r"var storesArray = (.*?\]);"
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return None

    json_str = match.group(1)

    # wrap the keys in double-quotes
    pattern = r"\t{4}(.*?)\s*:"
    json_str = re.sub(pattern, r'"\1" :', json_str)

    # remove the Math.floor and the trailing comma
    pattern = r'Math.floor\("(.*)"\),'
    json_str = re.sub(pattern, r"\1", json_str)
    return json.loads(json_str)


async def check_inventory(product_id: int):
    url = f"https://www.lcbo.com/webapp/wcs/stores/servlet/PhysicalStoreInventoryView"

    params = {"langId": -1, "storeId": 10203, "catalogId": "", "productId": product_id}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            html = await resp.text()
    inventory = _html_to_inventory(html)
    return inventory
