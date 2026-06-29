"""Publishing: Telegram channel posts + X (Twitter) OAuth-1.0a posts."""
import base64
import hashlib
import hmac
import random
import re
import string
import time
import urllib.parse

import requests
from config import (TELEGRAM_TOKEN, TELEGRAM_CHANNEL, TELEGRAM_PROXY,
                    X_API_KEY, X_API_SECRET, X_TOKEN, X_TOKEN_SEC)


def handle_telegram_post(body):
    if not TELEGRAM_TOKEN:
        raise ValueError('TELEGRAM_BOT_TOKEN not set in .env')
    image_b64 = body.get('imageB64', '')
    headline  = body.get('headline', '')
    copy_text = body.get('copy', '')
    hashtags  = body.get('hashtags', [])
    link      = body.get('link', '')
    tg_base   = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}'
    tg_proxies = {'https': TELEGRAM_PROXY} if TELEGRAM_PROXY else None

    hashtag_line = ' '.join(hashtags)
    if hashtag_line:
        # The AI-generated copy often already ends with its own hashtags (e.g. folded into a
        # "Source: ... · #Tag1 #Tag2" line) — strip a trailing run so they aren't duplicated.
        copy_text = re.sub(r'\s*[·\-—|:]?\s*(?:#\w+\s*)+$', '', copy_text)
    source_line  = f'\n\n[🔗 Read full story]({link})' if link and link != '#' else ''
    full_text    = '\n\n'.join(filter(None, [copy_text, hashtag_line, source_line.strip()]))

    if image_b64:
        img_bytes = base64.b64decode(image_b64)
        safe_headline = re.sub(r'([*_`\[\]])', r'\\\1', headline)
        # Build suffix (hashtags + link) — always kept intact
        suffix_parts = [p for p in [hashtag_line, source_line.strip()] if p]
        suffix = '\n\n'.join(suffix_parts)
        head = f'*{safe_headline}*' if safe_headline else ''
        # How much room is left for the body copy?
        # Format: head + \n\n + copy + \n\n + suffix  (omit empty parts)
        overhead = len(head) + (2 if head else 0) + (2 + len(suffix) if suffix else 0)
        available = 1024 - overhead
        body = copy_text[:available].rstrip() if len(copy_text) > available else copy_text
        if body and len(copy_text) > available:
            body = body[:body.rfind(' ')] + '…' if ' ' in body else body + '…'
        parts = [p for p in [head, body, suffix] if p]
        caption = '\n\n'.join(parts)
        r = requests.post(f'{tg_base}/sendPhoto',
                          data={'chat_id': TELEGRAM_CHANNEL, 'caption': caption,
                                'parse_mode': 'Markdown'},
                          files={'photo': ('image.png', img_bytes, 'image/png')},
                          proxies=tg_proxies, timeout=60)
        r.raise_for_status()
        result = r.json()
        if not result.get('ok'):
            raise ValueError(result.get('description', 'Telegram sendPhoto failed'))
        return result
    else:
        # Escape special Markdown chars for the bold headline
        safe_headline = re.sub(r'([*_`\[\]])', r'\\\1', headline)
        message = f'*{safe_headline}*\n\n{full_text}' if safe_headline else full_text
        r = requests.post(f'{tg_base}/sendMessage',
                          data={'chat_id': TELEGRAM_CHANNEL, 'text': message,
                                'parse_mode': 'Markdown',
                                'disable_web_page_preview': 'false'},
                          proxies=tg_proxies, timeout=30)
        r.raise_for_status()
        result = r.json()
        if not result.get('ok'):
            raise ValueError(result.get('description', 'Telegram sendMessage failed'))
        return result


# ── X (Twitter) OAuth 1.0a ─────────────────────────────────────────────────────
def _oauth_header(method, url, extra_params, consumer_key, consumer_secret, token, token_secret):
    nonce     = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    timestamp = str(int(time.time()))
    oauth = {
        'oauth_consumer_key':     consumer_key,
        'oauth_nonce':            nonce,
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp':        timestamp,
        'oauth_token':            token,
        'oauth_version':          '1.0',
    }
    all_params = {**extra_params, **oauth}
    enc = lambda s: urllib.parse.quote(str(s), safe='')
    param_str = '&'.join(f'{enc(k)}={enc(v)}' for k, v in sorted(all_params.items()))
    base = '&'.join([method.upper(), enc(url), enc(param_str)])
    key  = f'{enc(consumer_secret)}&{enc(token_secret)}'
    sig  = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    oauth['oauth_signature'] = sig
    return 'OAuth ' + ', '.join(f'{enc(k)}="{enc(v)}"' for k, v in sorted(oauth.items()))


def handle_twitter_post(body):
    if not all([X_API_KEY, X_API_SECRET, X_TOKEN, X_TOKEN_SEC]):
        raise ValueError('X API credentials not fully configured in .env')
    if X_TOKEN.startswith('PASTE_') or X_TOKEN_SEC.startswith('PASTE_'):
        raise ValueError('X Access Token not yet set — paste real values in .env')

    image_b64 = body.get('imageB64', '')
    copy_text = body.get('copy', '')
    hashtags  = body.get('hashtags', [])
    hashtag_str = ' '.join(hashtags) if isinstance(hashtags, list) else str(hashtags)
    tweet_text = f'{copy_text}\n\n{hashtag_str}'.strip()
    if len(tweet_text) > 280:
        tweet_text = tweet_text[:277] + '…'

    media_id = None
    if image_b64:
        upload_url = 'https://upload.twitter.com/1.1/media/upload.json'
        auth = _oauth_header('POST', upload_url, {}, X_API_KEY, X_API_SECRET, X_TOKEN, X_TOKEN_SEC)
        # multipart keeps the large base64 out of the OAuth signature base string
        ur = requests.post(upload_url,
                           files=[('media_data', (None, image_b64))],
                           headers={'Authorization': auth}, timeout=90)
        ur.raise_for_status()
        media_id = ur.json().get('media_id_string')

    tweet_url = 'https://api.twitter.com/2/tweets'
    auth = _oauth_header('POST', tweet_url, {}, X_API_KEY, X_API_SECRET, X_TOKEN, X_TOKEN_SEC)
    tweet_body = {'text': tweet_text}
    if media_id:
        tweet_body['media'] = {'media_ids': [media_id]}
    tr = requests.post(tweet_url, json=tweet_body,
                       headers={'Authorization': auth, 'Content-Type': 'application/json'},
                       timeout=30)
    tr.raise_for_status()
    data = tr.json()
    return {'success': True, 'tweetId': data.get('data', {}).get('id', ''), 'mediaId': media_id}
