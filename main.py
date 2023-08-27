import datetime
import json
import os
import time

import requests
import telegram
from pydantic import BaseModel
import asyncio


URL = "https://api.divar.ir/v8/web-search/{SEARCH_CONDITIONS}".format(
    **os.environ)
BOT_TOKEN = "{BOT_TOKEN}".format(**os.environ)
BOT_CHATID = "{BOT_CHATID}".format(**os.environ)
SLEEP_SEC = "{SLEEP_SEC}".format(**os.environ)

proxy_url = None
if os.environ.get("PROXY_URL", ""):
    proxy_url = os.environ.get("PROXY_URL")

TOKENS = list()
# setup telegram bot client
req_proxy = telegram.request.HTTPXRequest(proxy_url=proxy_url)
bot = telegram.Bot(token=BOT_TOKEN, request=req_proxy)

# AD class model
class AD(BaseModel):
    title : str
    description : str
    district : str
    images : list[str] = []
    token : str
        
def get_data(page=None):
    api_url = URL
    if page:
        api_url += f"&page={page}"
    response = requests.get(api_url)
    print("{} - Got response: {}".format(datetime.datetime.now(), response.status_code))
    return response.json()

def get_ads_list(data):
    return data["web_widgets"]["post_list"]


def extract_ad_data(ad_data : dict) -> AD:
    # check widget type is post
    if not ad_data.get("widget_type") == "POST_ROW":
        return None
    # extract ad data
    data = ad_data["data"]
    print("-> AD {}: {}".format(data["token"], data))
    action_type = data.get("action").get("type")
    subtitle = ""
    district = ""
    if action_type == "VIEW_POST":
        district = data["action"]["payload"]["web_info"]["district_persian"]
    elif action_type == "LOAD_MODAL_PAGE":
        subtitle = data["action"]["payload"]["modal_page"]["title"]
    title = data["title"]
    description = f'{data["top_description_text"]} \n {data["middle_description_text"]} \n {data["bottom_description_text"]} \n {subtitle}'
    images = [img['src'] for img in data['image_url'] ]
    token = data["token"]
    ad = AD(title=title, description=description, district=district,
            images=images, token=token,
            )
    
    return ad


async def send_telegram_message(ad : AD):
    text = f"<b>{ad.title}</b>" + "\n"
    text += f"<i>{ad.district}</i>" + "\n"
    text += f"{ad.description}" + "\n"
    text += f"https://divar.ir/v/a/{ad.token}"
    
    # send photo
    if ad.images:
        await bot.send_photo(caption=text, photo=ad.images[1], chat_id=BOT_CHATID, parse_mode="HTML")
    else:
        # send just text
        await bot.send_message(text=text, chat_id=BOT_CHATID, parse_mode="HTML")


def load_tokens():
    token_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "tokens.json"
    )
    with open(token_path, "r") as content:
        if content == "":
            return []
        return json.load(content)


def save_tokns(tokens):
    token_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "tokens.json"
    )
    with open(token_path, "w") as outfile:
        json.dump(tokens, outfile)


def get_data_page(page=None):
    data = get_data(page)
    data = get_ads_list(data)
    data = data[::-1]
    return data


async def process_data(data, tokens):
    for ad in data:
        ad_data = extract_ad_data(ad)
        if ad_data is None:
            continue
        if ad_data.token in tokens:
            continue
        tokens.append(ad_data.token)
        print("sending to telegram token: {}".format(ad_data.token))
        await send_telegram_message(ad_data)
        time.sleep(1)
    return tokens


if __name__ == "__main__":
    print("Started at {}.".format(datetime.datetime.now()))
    tokens = load_tokens()
    print("Tokens length: {}".format(len(tokens)))
    pages = [""]
    while True:
        for page in pages:
            data = get_data_page(page)
            tokens =  asyncio.run(process_data(data, tokens))
        save_tokns(tokens)
        time.sleep(int(SLEEP_SEC))
