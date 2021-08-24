from expand_img import *
import tweepy
from moviepy.editor import VideoFileClip

auth = tweepy.OAuthHandler(credential['twitter_consumer_key'], credential['twitter_consumer_secret'])
auth.set_access_token(credential['access_key'], credential['access_secret'])
api = tweepy.API(auth)

async def getMediaSingle(fn):
    if fn.endswith('.mp4'): # no video
        return
    try:
        return api.media_upload(fn).media_id
    except Exception as e:
        print('media upload failed:', str(e))

async def getMedia(imgs):
    result = []
    for img in imgs:
        media = await getMediaSingle(img)
        if media:
            result.append(media)
        if len(result) >= 4:
            return result
    return result

async def postTwitterCore(imgs, text):
    media_ids = await getMedia(imgs)
    result = api.update_status(status=text, media_ids=media_ids)
    print('https://twitter.com/%s/status/%d' % (setting['twitter_channel'], result.id))

async def postTwitter(src, post):
    text = post.raw_text
    orig_post_id = int(text.strip().rsplit('/', 1)[1])
    client = await telepost.getTelethonClient()
    orig_channel = await client.get_entity(setting['src'])
    orig_post = await client.get_messages(orig_channel, ids=orig_post_id)
    orig_imgs = await telepost.getImagesV2(orig_channel, orig_post)
    orig_text, _, _ = getText(orig_post)
    text_imgs = text_2_img.gen(orig_text, background = (255, 255, 255)) 
    to_post_imgs = text_imgs + orig_imgs
    save(orig_post.id, to_post_imgs, text)
    print(text)
    await postTwitterCore(to_post_imgs, text)

def tooNewForTwitter(post):
    dt = post.edit_date or post.date
    if not post.edit_date:
        return (datetime.datetime.now(datetime.timezone.utc) - dt).total_seconds() < 60 * 60 * 24    
    else:
        return (datetime.datetime.now(datetime.timezone.utc) - dt).total_seconds() < 60 * 60 * 5

async def processExpandTwitter(client):
    src = await client.get_entity(setting['dest'])
    last_sync = cache.get('last_sync_twitter', 0)
    posts = await client.get_messages(src, min_id=last_sync, max_id = last_sync + 100, limit = 100)
    post = getNextPost(posts)
    if not post or tooNewForTwitter(post):
        return
    await postTwitter(src, post)
    cache.update('last_sync_twitter', post.id)

async def expand_twitter_run():
    client = await telepost.getTelethonClient()
    # await client.get_dialogs()
    await processExpandTwitter(client)
    await client.disconnect()
    
if __name__ == "__main__":
    # cache.update('last_sync_twitter', cache.get('last_sync_twitter') - 1)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    if random.random() < 0.5:
        loop.run_until_complete(expand_img_run())
    else:
        loop.run_until_complete(expand_twitter_run())
    loop.close()