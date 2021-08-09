
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telethon import TelegramClient
from bs4 import BeautifulSoup
import asyncio
import yaml
import plain_db
from telegram_util import isCN, isUrl
import webgram
import text_2_img
import telepost
import random
import os

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
    source_tmp = ''
    for item in soup:
        if item.name == 'a':
            if 'source' in item.text:
                source = item['href']
            source_tmp = item['href']
            item.decompose()
        if item.name == 'br':
            item.replace_with('\n')
        if str(item).startswith('译者'):
            item.replace_with('')
        for subitem in str(item).split():
            if isUrl(subitem) or subitem.startswith('http'):
                source_tmp = subitem
    text = soup.text.strip()
    append1 = '\n\n原文： %s' % (source or source_tmp)
    result = text + append1
    text_byte_len = sum([isCN(c) + 1 for c in result])
    append2 = '\n翻译： https://t.me/%s/%d' % (setting['src_name'], post.id)
    result += append2
    short_text = text.split('\n')[0] + append1 + append2
    return result, text_byte_len, short_text

def save(post_id, imgs, text):
    for index, path in enumerate(imgs):
        ext = path.rsplit('.', 1)[1]
        os.system('cp "%s" result/%d_%d.%s' % (path, post_id, index + 1, ext))
    with open('result/%d.txt' % post_id, 'w') as f:
        f.write(text)

async def postTelegramImg(src, post):
    orig_imgs = await telepost.getImagesV2(src, post)
    text, text_byte_len, short_text = getText(post)
    client = await telepost.getTelethonClient()
    chat = await client.get_entity(setting['dest'])
    if text_byte_len < 280:
        imgs_to_save = orig_imgs
    else:
        text_imgs = text_2_img.gen(text, background = random.choice(backgrounds)) 
        imgs_to_save = text_imgs + orig_imgs
        to_post_imgs = text_imgs + orig_imgs
        to_post_imgs = to_post_imgs[:10]
    save(post.id, imgs_to_save, text)
    if text_byte_len < 280:
        return
    if sum([isCN(c) + 1 for c in short_text]) > 280:
        print('short text too long', short_text)
        short_text = ''
    await client.send_file(chat, to_post_imgs, caption=short_text)

async def process(client):
    src = await client.get_entity(setting['src'])
    last_sync = cache.get('last_sync', 0)
    if last_sync > 5600: # testing
        return
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
    for _ in range(3000):
        await process(client)
    await process(client)
    await client.disconnect()
    
if __name__ == "__main__":
    # cache.update('last_sync', 0)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run())
    loop.close()