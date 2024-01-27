import datetime
import json
import os
import time
from typing import Any
from pathlib import Path

import requests
import asyncio
import telegram

from src.schemas import AD
from src.telegram import send_telegram_message

URL = "https://api.divar.ir/v8/web-search/{}".format(os.getenv("SEARCH_CONDITIONS"))
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_CHATID = os.getenv("BOT_CHATID")
SLEEP_SEC = os.getenv("SLEEP_SEC")

proxy_url = None
if os.getenv("PROXY_URL", ""):
    proxy_url = os.getenv("PROXY_URL")

# setup telegram bot client
req_proxy = telegram.request.HTTPXRequest(proxy_url=proxy_url)
bot = telegram.Bot(token=BOT_TOKEN, request=req_proxy)


def get_data(page=None):
    api_url = URL
    if page:
        api_url += f"&page={page}"
    response = requests.get(api_url)
    print("{} - Got response: {}".format(datetime.datetime.now(), response.status_code))
    return response.json()


def fetch_ad_data(token: str) -> AD:
    # send request
    data = requests.get(f"https://api.divar.ir/v8/posts-v2/web/{token}").json()
    images = []
    # check post exists
    if not "sections" in data:
        return None

    # get data
    for section in data["sections"]:
        # find title section
        if section["section_name"] == "TITLE":
            title = section["widgets"][0]["data"]["title"]

        # find images section
        if section["section_name"] == "IMAGE":
            images = section["widgets"][0]["data"]["items"]
            images = [img["image"]["url"] for img in images]

        # find description section
        if section["section_name"] == "DESCRIPTION":
            description = section["widgets"][1]["data"]["text"]

    # get district
    district = data["seo"]["web_info"]["district_persian"]
    price = data["webengage"]["price"]

    # create ad object
    ad = AD(
        token=token,
        title=title,
        district=district,
        description=description,
        images=images,
        price=price,
    )

    return ad


def load_tokens() -> list[str]:
    # load tokens list from json file
    token_path = Path("tokens.json")
    try:
        with open(token_path) as file:
            content = file.read()
    except FileNotFoundError:
        return []
    # check empty list
    if not content:
        return []
    # parse json
    return json.loads(content)


def save_tokns(tokens):
    token_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "tokens.json"
    )
    with open(token_path, "w") as outfile:
        json.dump(tokens, outfile)


def get_tokens_page(page=None) -> list[Any]:
    data = get_data(page)
    data = data["web_widgets"]["post_list"]
    data = data[::-1]
    # get tokens
    data = filter(lambda x: x["widget_type"] == "POST_ROW", data)
    tokens = list(map(lambda x: x["data"]["token"], data))
    return tokens


async def process_data(tokens):
    for token in tokens:
        # get the ad data
        ad = fetch_ad_data(token)
        if not ad:
            continue
        print("AD - {} - {}".format(token, vars(ad)))
        # send message to telegram
        print("sending to telegram token: {}".format(ad.token))
        await send_telegram_message(bot=bot, user_chat_id=BOT_CHATID, ad=ad)
        time.sleep(1)


if __name__ == "__main__":
    print("Started at {}.".format(datetime.datetime.now()))
    tokens = load_tokens()
    print("Tokens length: {}".format(len(tokens)))
    pages = [""]
    while True:
        for page in pages:
            # get new tokens list
            tokens_list = get_tokens_page(page)
            # remove repeated tokens
            tokens_list = list(filter(lambda t: not t in tokens, tokens_list))
            tokens = list(set(tokens_list + tokens))
            asyncio.run(process_data(tokens_list))
        # save new tokens
        save_tokns(tokens)
        time.sleep(int(SLEEP_SEC))
