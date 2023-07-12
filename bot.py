import os
import re
from urllib.parse import unquote
import urllib.request
import asyncio

import feedparser
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.types import ParseMode
from aiogram.utils import executor
from dotenv import load_dotenv
import vk_api
import requests



load_dotenv()

access_token = os.getenv('VK_TOKEN')



group_id = 218671758

# Connect to VK API
vk_session = vk_api.VkApi(token=access_token)
vk = vk_session.get_api()

bot = Bot(token=os.getenv('TELEGRAM_TOKEN'))
dp = Dispatcher(bot)


def get_feed_entries(url):
    feed = feedparser.parse(url)
    return feed.entries

async def send_entries_to_channel(chat_id, entries):
    wall_posts = vk.wall.get(owner_id=-group_id)
    for entry in entries[::-1]:
        # Проверяем, опубликована ли уже запись в канале
        try:
            # проверяем, есть ли запись с таким же заголовком или содержимым
            for post in wall_posts['items']:
                if entry.link in post['text'].strip():
                    print('Запись уже опубликована в ВКонтакте')
                    break
            else:
                # Запись не найдена, публикуем ее в канале
                image_url = ('https://greatarticles.ru'+f'{entry.links[1].get("href")}')
                message = f"<b>{re.sub('<[^<]+?>', '', entry.title)}</b>\n\n{re.sub('<[^<]+?>', '', entry.summary)}\n\n<a href='{entry.link}'>{entry.link}</a>"
                message_for_vk = f"{re.sub('<[^<]+?>', '', entry.title)}\n\n{re.sub('<[^<]+?>', '', entry.summary)}\n\n{entry.link}"
                photo_file = 'photo2.jpg'
                urllib.request.urlretrieve(image_url, photo_file)

                server_vk = vk.photos.getWallUploadServer(group_id=group_id)
                server_url = server_vk['upload_url']

                with open(photo_file, 'rb') as file:
                    # Upload the image to the server
                    response = requests.post(server_url, files={'photo': file})

                response_json = response.json()

                photo = vk.photos.saveWallPhoto(group_id=group_id, photo=response_json['photo'], server=response_json['server'], hash=response_json['hash'])
                attachments = f"photo{photo[0]['owner_id']}_{photo[0]['id']}"

                vk.wall.post(owner_id=-group_id, message=message_for_vk, attachments=attachments, from_group=1,parse_mode='html')
                await bot.send_photo(chat_id, unquote(image_url), caption=message, parse_mode=ParseMode.HTML)
        except Exception as e:
            print(f'Ошибка при получении информации о чате: {e}')


async def periodic_check():
    while True:
        entries = get_feed_entries('https://greatarticles.ru/feed/rss')
        await send_entries_to_channel('@GreatArticlesChannel', entries)
        await asyncio.sleep(300)  # Ожидание 5 минут (300 секунд)
        
@dp.message_handler(commands=['send'])
async def send_entries(message: types.Message):
    entries = get_feed_entries('https://greatarticles.ru/feed/rss')
    await send_entries_to_channel('@GreatArticlesChannel', entries)

if __name__ == '__main__':
     loop = asyncio.get_event_loop()
     loop.create_task(periodic_check())
     executor.start_polling(dp, skip_updates=True)
