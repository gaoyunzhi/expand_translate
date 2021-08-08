#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telethon import TelegramClient
from bs4 import BeautifulSoup
import asyncio
import yaml
import plain_db
from telegram_util import isCN
import webgram
import text_2_img
import telepost
import random

backgrounds = [(227, 227, 255), (223, 242, 253), (226, 252, 230),
(252, 250, 222), (255, 238, 226), (255, 219, 219)]

with open('credential') as f:
    credential = yaml.load(f, Loader=yaml.FullLoader)

with open('setting') as f:
    setting = yaml.load(f, Loader=yaml.FullLoader)

cache = plain_db.load('cache')

def getNextPost(posts):
    for post in posts[::-1]:
        if post.text and isCN(post.text):
            return post

def getText(post):
    soup = webgram.getPost(setting['src_name'], post.id).text
    source = ''
    for item in soup:
        if item.name == 'a':
            if 'source' in item.text:
                source = item['href']
            item.decompose()
        if item.name == 'br':
            item.replace_with('\n')
    text = soup.text.strip()
    result = '%s\n\n原文： %s' % (text, source)
    text_byte_len = sum([isCN(c) + 1 for c in result])
    result += '\n翻译： https://t.me/%s/%d' % (setting['src_name'], post.id)
    return result, text_byte_len

async def postTelegramImg(src, post):
    orig_imgs = await telepost.getImagesV2(src, post)
    text, text_byte_len = getText(post)
    if text_byte_len < 140:
        return
    text_imgs = text_2_img.gen(text, background = random.choice(backgrounds)) 
    to_post_imgs = text_imgs + orig_imgs
    if len(to_post_imgs) > 10:
        to_post_imgs = text_imgs
    to_post_text = text.split('\n')[0]
    client = await telepost.getTelethonClient()
    chat = await client.get_entity(setting['dest'])
    # print('https://t.me/%s/%d' % (setting['src_name'], post.id))
    for index, path in enumerate(text_imgs + orig_imgs):
        ext = path.rsplit('.', 1)[1]
        os.system('cp %s result/%d_%d.%s' % (path, post.id, index + 1, ext))
    with open('result/%d.txt', w) as f:
        f.write(text)
    await client.send_file(chat, to_post_imgs, caption=to_post_text)

async def process(client):
    src = await client.get_entity(setting['src'])
    last_sync = cache.get('last_sync', 0)
    posts = await client.get_messages(src, min_id=last_sync, max_id = last_sync + 100, limit = 100)
    post = getNextPost(posts)
    if not post:
        cache.update('last_sync', last_sync + 99)
        return
    await postTelegramImg(src, post)
    cache.update('last_sync', post.id)
        
async def run():
    client = await telepost.getTelethonClient()
    # await client.get_dialogs()
    for _ in range(10):
        await process(client)
    await process(client)
    await client.disconnect()
    
if __name__ == "__main__":
    # cache.update('last_sync', cache.get('last_sync') - 1)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run())
    loop.close()