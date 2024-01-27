"""
this file is for storing telegram bot functions and modules to send message from telegram
"""


import logging
import telegram
from src.schemas import AD

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(name=__name__)


async def send_telegram_message(bot: telegram.Bot, user_chat_id: int, ad: AD):
    text = f"🗄 <b>{ad.title}</b>" + "\n"
    text += f"📌 محل آگهی : <i>{ad.district}</i>" + "\n"
    _price = f"{ad.price:,} تومان" if ad.price else "توافقی"
    text += f"💰 قیمت : {_price}" + "\n\n"
    text += f"📄 توضیحات :\n{ad.description}" + "\n"
    text += f"https://divar.ir/v/a/{ad.token}"

    # send single photo
    if len(ad.images) == 1:
        await bot.send_photo(
            caption=text, photo=ad.images[0], chat_id=user_chat_id, parse_mode="HTML"
        )
    # send album
    elif len(ad.images) > 1:
        _media_list = [telegram.InputMediaPhoto(img) for img in ad.images[:10]]
        try:
            await bot.send_media_group(
                caption=text, media=_media_list, chat_id=user_chat_id, parse_mode="HTML"
            )
        except telegram.error.BadRequest as e:
            logger.error(f"Error sending photos : {e}")
            return
    else:
        # send just text
        await bot.send_message(text=text, chat_id=user_chat_id, parse_mode="HTML")
