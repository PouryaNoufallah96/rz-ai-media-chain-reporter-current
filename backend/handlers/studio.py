"""Studio reel drafts, script generation, and OpenRouter video jobs."""

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import database
from config import STUDIO_OUTPUT_DIR, STUDIO_SCRIPT_MODEL
from llm import (
    openrouter_chat,
    openrouter_video_content,
    openrouter_video_models,
    openrouter_video_poll,
    openrouter_video_submit,
)
from video_pipeline import (
    assemble_video_prompt,
    build_fact_ledger,
    director_messages,
    narration_within_duration,
    remember_director_brief,
    validate_director_brief,
    validate_script_facts,
)


TERMINAL_STATUSES = {'completed', 'failed', 'cancelled', 'expired'}
VOICE_PRESETS = {'News Anchor', 'Energetic', 'Calm Analyst', 'Persian Narrator'}
MUSIC_PRESETS = {'Breaking', 'Market Pulse', 'Luxury', 'Security Alert', 'Calm Analysis'}
_MODEL_CACHE_TTL = 10 * 60
_model_cache = {'at': 0.0, 'models': []}
_model_cache_lock = threading.Lock()


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _text(value, limit=5000):
    return str(value or '').strip()[:limit]


def _normalize_cards(raw_cards):
    if not isinstance(raw_cards, list) or not raw_cards:
        raise ValueError('Send at least one story from Multimedia to Studio')
    if len(raw_cards) > 8:
        raise ValueError('A Studio reel can use up to 8 stories')
    cards = []
    for index, raw in enumerate(raw_cards):
        if not isinstance(raw, dict):
            continue
        headline = _text(raw.get('headline') or raw.get('title'), 500)
        if not headline:
            continue
        cards.append({
            'id': _text(raw.get('id') or f'story-{index + 1}', 200),
            'media': _text(raw.get('media') or raw.get('brand') or 'ChainReporter', 100),
            'headline': headline,
            'copy': _text(raw.get('copy') or raw.get('desc') or raw.get('summary'), 5000),
            'source': _text(raw.get('source'), 200),
            'link': _text(raw.get('link') or raw.get('sourceUrl'), 2000),
            'publishedAt': _text(raw.get('publishedAt') or raw.get('pubDate') or raw.get('timeAgo'), 100),
            'sentiment': _text(raw.get('sentiment'), 50),
            'suitability': raw.get('suitability'),
            'impact': raw.get('impact'),
            'virality': raw.get('virality'),
            'imageUrl': _text(raw.get('imageUrl'), 4000),
        })
    if not cards:
        raise ValueError('The selected stories do not contain usable headlines')
    return cards


def _normalize_settings(raw):
    raw = raw if isinstance(raw, dict) else {}
    try:
        duration = int(raw.get('duration', 30))
    except (TypeError, ValueError):
        duration = 30
    if duration < 5 or duration > 60:
        raise ValueError('Reel length must be between 5 and 60 seconds')
    voice = _text(raw.get('voice') or 'News Anchor', 80)
    music = _text(raw.get('music') or 'Market Pulse', 80)
    return {
        'duration': duration,
        'aspectRatio': '9:16',
        'resolution': _text(raw.get('resolution') or '720p', 20),
        'model': _text(raw.get('model'), 200),
        'voice': voice if voice in VOICE_PRESETS else 'News Anchor',
        'music': music if music in MUSIC_PRESETS else 'Market Pulse',
        'language': _text(raw.get('language') or 'English', 50),
        'visualDirection': _text(
            raw.get('visualDirection') or 'Original editorial concept video with one clear visual metaphor',
            2000,
        ),
        'generateAudio': bool(raw.get('generateAudio', True)),
        'audioMode': 'model_native',
    }


def _draft_title(cards, requested=''):
    if _text(requested, 200):
        return _text(requested, 200)
    if len(cards) == 1:
        return cards[0]['headline'][:120]
    return f'{len(cards)}-story news roundup'


def _draft_brand(cards):
    brands = {card['media'] for card in cards if card.get('media')}
    return next(iter(brands)) if len(brands) == 1 else 'Mixed'


def _script_prompt(cards, settings):
    format_note = (
        'Use a tight three-act structure: hook, context, takeaway.'
        if len(cards) == 1 else
        'Use a market/news roundup with one short, clearly separated segment per story.'
    )
    source_json = json.dumps(cards, ensure_ascii=False, indent=2)
    return [
        {
            'role': 'system',
            'content': (
                'You are the senior short-form video producer for a crypto newsroom. '
                'Create a factual Instagram reel script using only the supplied source cards. '
                'Never invent or infer numbers, prices, dates, quotes, names, causes, or outcomes. '
                'If a detail is not in the cards, omit it. Return valid JSON only with exactly these keys: '
                'hook (string), narration (string), shots (array of objects with start, end, visual, caption), '
                'on_screen_captions (array of strings), cta (string), hashtags (array of strings), '
                'video_prompt (string). Keep captions brief, but do not add facts beyond the source cards.'
            ),
        },
        {
            'role': 'user',
            'content': (
                f'Create a {settings["duration"]}-second, 9:16 reel in {settings["language"]}. '
                f'{format_note}\n'
                f'Narration style: {settings["voice"]}. Music mood: {settings["music"]}.\n'
                f'Visual direction: {settings["visualDirection"]}.\n'
                'The narration must fit naturally inside the duration and cover every selected story.\n'
                f'SOURCE CARDS:\n{source_json}'
            ),
        },
    ]


def _normalize_script(raw, cards, settings):
    if not isinstance(raw, dict):
        raise ValueError('The script model returned an invalid response')
    hook = _text(raw.get('hook'), 500) or cards[0]['headline']
    narration = _text(raw.get('narration'), 6000)
    if not narration:
        narration = ' '.join(card['headline'] for card in cards)
    valid_length, word_budget = narration_within_duration({'narration': narration}, settings)
    if not valid_length:
        narration = ' '.join(narration.split()[:word_budget])
    cta = _text(raw.get('cta'), 500) or 'Follow for the next market update.'
    captions = raw.get('on_screen_captions')
    if not isinstance(captions, list):
        captions = []
    captions = [_text(item, 180) for item in captions if _text(item, 180)][:10]
    if not captions:
        captions = [card['headline'][:100] for card in cards]
    hashtags = raw.get('hashtags')
    if not isinstance(hashtags, list):
        hashtags = []
    hashtags = [_text(tag, 80) for tag in hashtags if _text(tag, 80)][:12]
    shots = []
    for shot in raw.get('shots') or []:
        if not isinstance(shot, dict):
            continue
        shots.append({
            'start': _text(shot.get('start'), 30),
            'end': _text(shot.get('end'), 30),
            'visual': _text(shot.get('visual'), 1000),
            'caption': _text(shot.get('caption'), 180),
        })
    if not shots:
        segment = max(1, settings['duration'] // len(cards))
        shots = [
            {
                'start': f'{index * segment}s',
                'end': f'{min(settings["duration"], (index + 1) * segment)}s',
                'visual': card['headline'],
                'caption': card['headline'][:100],
            }
            for index, card in enumerate(cards)
        ]
    return {
        'hook': hook,
        'narration': narration,
        'shots': shots[:10],
        'on_screen_captions': captions,
        'cta': cta,
        'hashtags': hashtags,
        'video_prompt': _text(raw.get('video_prompt'), 6000),
        'factLedger': build_fact_ledger(cards),
        'directorBrief': raw.get('directorBrief') if isinstance(raw.get('directorBrief'), dict) else None,
    }


def _save_draft(user_id, body, cards, settings, script=None):
    draft_id = body.get('draftId')
    if draft_id not in (None, ''):
        try:
            draft_id = int(draft_id)
        except (TypeError, ValueError):
            raise ValueError('Invalid Studio draft id')
    return database.save_studio_draft(
        user_id,
        {
            'title': _draft_title(cards, body.get('title')),
            'brand': _draft_brand(cards),
            'cards': cards,
            'script': script if script is not None else (body.get('script') or {}),
            'settings': settings,
        },
        draft_id=draft_id,
    )


def _video_models():
    now = time.monotonic()
    with _model_cache_lock:
        if _model_cache['models'] and now - _model_cache['at'] < _MODEL_CACHE_TTL:
            return list(_model_cache['models'])
        raw = openrouter_video_models()
        records = raw.get('data', []) if isinstance(raw, dict) else []
        models = []
        for record in records:
            if not isinstance(record, dict):
                continue
            ratios = record.get('supported_aspect_ratios') or []
            if '9:16' not in ratios or not record.get('id'):
                continue
            pricing = record.get('pricing_skus') or {}
            durations = [int(value) for value in (record.get('supported_durations') or []) if str(value).isdigit()]
            resolutions = record.get('supported_resolutions') or []
            if not durations or not resolutions:
                continue
            models.append({
                'id': record['id'],
                'name': record.get('name') or record['id'],
                'description': record.get('description', ''),
                'resolutions': resolutions,
                'durations': durations,
                'aspectRatios': ratios,
                'generateAudio': record.get('generate_audio') is True,
                'supportsReferences': bool(record.get('supported_input_references') or record.get('supported_frame_images')),
                'pricePerSecond': pricing.get('per-video-second') or pricing.get('generate'),
            })
        _model_cache.update({'at': now, 'models': list(models)})
        return models


def _apply_model_capabilities(settings):
    model_id = settings.get('model')
    if not model_id:
        raise ValueError('Choose a video model before generating')
    model = next((item for item in _video_models() if item['id'] == model_id), None)
    if not model:
        raise ValueError('The selected video model is no longer available for 9:16 generation')
    durations = model['durations']
    if durations and settings['duration'] not in durations:
        supported = ', '.join(f'{duration}s' for duration in durations)
        raise ValueError(f"{model['name']} supports these reel lengths: {supported}")
    resolutions = model['resolutions']
    if resolutions and settings['resolution'] not in resolutions:
        raise ValueError(f"{model['name']} does not support {settings['resolution']}")
    if not model['generateAudio']:
        settings = {**settings, 'generateAudio': False}
    return settings, model


def handle_studio_models():
    return {
        'models': _video_models(),
        'audioMode': 'model_native',
    }


def handle_studio_jobs(user_id):
    return {'jobs': database.get_studio_jobs(user_id)}


def handle_studio_draft(user_id, body):
    cards = _normalize_cards(body.get('cards'))
    settings = _normalize_settings(body.get('settings'))
    return {'draft': _save_draft(user_id, body, cards, settings)}


def handle_studio_script(user_id, body):
    cards = _normalize_cards(body.get('cards'))
    settings = _normalize_settings(body.get('settings'))
    raw_script = openrouter_chat(
        STUDIO_SCRIPT_MODEL,
        _script_prompt(cards, settings),
        temperature=0.25,
        max_tokens=3000,
    )
    script = _normalize_script(raw_script, cards, settings)
    validate_script_facts(script, cards)
    draft = _save_draft(user_id, body, cards, settings, script=script)
    return {'draft': draft, 'script': script}


def handle_studio_direct(user_id, body):
    cards = _normalize_cards(body.get('cards'))
    settings = _normalize_settings(body.get('settings'))
    script = _normalize_script(body.get('script') or {}, cards, settings)
    validate_script_facts(script, cards)
    raw_brief = openrouter_chat(
        STUDIO_SCRIPT_MODEL,
        director_messages(cards, script, settings),
        temperature=0.45,
        max_tokens=1800,
    )
    brief = validate_director_brief(raw_brief, cards, settings)
    script['directorBrief'] = brief
    draft = _save_draft(user_id, body, cards, settings, script=script)
    return {'draft': draft, 'script': script, 'directorBrief': brief}


def handle_studio_generate(user_id, body):
    cards = _normalize_cards(body.get('cards'))
    settings = _normalize_settings(body.get('settings'))
    script = _normalize_script(body.get('script') or {}, cards, settings)
    validate_script_facts(script, cards)
    settings, model = _apply_model_capabilities(settings)
    raw_brief = body.get('script', {}).get('directorBrief') if isinstance(body.get('script'), dict) else None
    if not isinstance(raw_brief, dict):
        raise ValueError('Create and review art direction before generating the reel')
    brief = validate_director_brief(raw_brief, cards, settings)
    script['directorBrief'] = brief
    draft = _save_draft(user_id, body, cards, settings, script=script)
    prompt = assemble_video_prompt(script, brief, settings, cards)
    payload = {
        'model': model['id'],
        'prompt': prompt,
        'duration': settings['duration'],
        'aspect_ratio': settings['aspectRatio'],
        'resolution': settings['resolution'],
        'generate_audio': settings['generateAudio'],
    }
    submitted = openrouter_video_submit(payload)
    provider_job_id = _text(submitted.get('id'), 300) if isinstance(submitted, dict) else ''
    if not provider_job_id:
        raise ValueError('OpenRouter accepted the request but did not return a video job id')
    job = database.create_studio_job(user_id, {
        'draftId': draft['id'],
        'openrouterJobId': provider_job_id,
        'pollingUrl': _text(submitted.get('polling_url'), 2000),
        'model': model['id'],
        'status': _text(submitted.get('status') or 'pending', 40),
        'prompt': prompt,
        'settings': settings,
    })
    remember_director_brief(cards, brief)
    return {'draft': draft, 'job': job}


def _error_text(value):
    if isinstance(value, dict):
        return _text(value.get('message') or json.dumps(value), 1000)
    return _text(value, 1000)


def _persist_video(user_id, local_job_id, provider_job_id):
    content, content_type = openrouter_video_content(provider_job_id)
    if not content:
        raise ValueError('OpenRouter returned an empty video file')
    user_dir = Path(STUDIO_OUTPUT_DIR) / f'user-{int(user_id)}'
    user_dir.mkdir(parents=True, exist_ok=True)
    path = user_dir / f'reel-{int(local_job_id)}.mp4'
    path.write_bytes(content)
    return path.resolve(), content_type


def handle_studio_poll(user_id, body):
    try:
        local_job_id = int(body.get('id'))
    except (TypeError, ValueError):
        raise ValueError('A valid Studio job id is required')
    job = database.get_studio_job(local_job_id, user_id)
    if not job:
        raise ValueError('Studio job not found')
    if job['status'] in TERMINAL_STATUSES:
        return {'job': job}
    provider = openrouter_video_poll(job['openrouterJobId'])
    status = _text(provider.get('status') or job['status'], 40).lower()
    if status == 'canceled':
        status = 'cancelled'
    usage = provider.get('usage') if isinstance(provider.get('usage'), dict) else {}
    cost = usage.get('cost')
    try:
        cost = float(cost) if cost is not None else None
    except (TypeError, ValueError):
        cost = None
    urls = provider.get('unsigned_urls') or []
    result_url = _text(urls[0], 4000) if urls else job.get('resultUrl', '')
    patch = {
        'status': status,
        'pollingUrl': _text(provider.get('polling_url') or job.get('pollingUrl'), 2000),
        'resultUrl': result_url,
        'usage': usage,
        'cost': cost,
        'error': _error_text(provider.get('error')),
    }
    if status in TERMINAL_STATUSES:
        patch['completedAt'] = _now_iso()
    updated = database.update_studio_job(local_job_id, user_id, patch)
    if status == 'completed' and updated and not updated.get('hasLocalVideo'):
        try:
            path, _ = _persist_video(user_id, local_job_id, job['openrouterJobId'])
            updated = database.update_studio_job(local_job_id, user_id, {
                'contentPath': str(path),
                'error': '',
            })
        except Exception as exc:
            updated = database.update_studio_job(local_job_id, user_id, {
                'error': f'Video completed, but the local copy is not ready: {exc}',
            })
    return {'job': updated}


def handle_studio_download(user_id, job_id):
    try:
        job_id = int(job_id)
    except (TypeError, ValueError):
        raise ValueError('A valid Studio job id is required')
    record = database.get_studio_job_record(job_id, user_id)
    if not record:
        raise ValueError('Studio job not found')
    if record['status'] != 'completed':
        raise ValueError('This reel is not ready to download')
    root = Path(STUDIO_OUTPUT_DIR).resolve()
    path = Path(record.get('content_path') or '').resolve() if record.get('content_path') else None
    if not path or not path.is_file() or not path.is_relative_to(root):
        path, _ = _persist_video(user_id, job_id, record['openrouter_job_id'])
        database.update_studio_job(job_id, user_id, {'contentPath': str(path), 'error': ''})
    return {
        'path': path,
        'contentType': 'video/mp4',
        'filename': f'chainreporter-reel-{job_id}.mp4',
    }
