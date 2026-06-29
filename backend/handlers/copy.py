"""Social-copy generation: platform prompts, length enforcement, variants."""
import sys

from config import (PLAT_RULES, EDITORIAL_MODELS, BRAND_HASHTAGS, BRAND_PROMO_PITCH,
                    _EMOJI_RE, _EMOJI_CAP, clean_emojis, smart_truncate, _sibling_block)
from llm import openrouter_chat
from _branddoc import _brand_doc


def handle_generate_copy(body):
    article      = body.get('article', {})
    platform     = body.get('platform', '')
    media        = body.get('mediaBrand', '')
    sentiment    = body.get('sentiment', 'Neutral')
    model_key    = body.get('modelKey', 'gpt')   # 'gpt' | 'gemini' | 'claude'
    sibling_copy = body.get('siblingCopy') or None
    variant_count = max(1, min(3, body.get('variantCount', 2)))
    is_promo = bool(body.get('promoMode'))
    # In promo mode, load the FULL brand bible so compliance guardrails bind the copy too
    # (not just the short pitch). Falls back to the short blurb if the doc is unavailable.
    promo_pitch = _brand_doc(media) if is_promo else ''

    if not article or not platform or not media:
        raise ValueError('Missing article, platform, or mediaBrand')

    rule = PLAT_RULES.get(platform)
    if not rule:
        raise ValueError(f'Unknown platform: {platform}')

    user_msg = (
        f"Article title: {article.get('title', '')}\n"
        f"Source: {article.get('source', '')}\n"
        f"Description: {article.get('desc', '')}\n"
        f"Keywords: {', '.join(article.get('matchedKeywords', []))}"
    )

    def call(extra=''):
        sys_prompt = rule['system'](media, sentiment, sibling_copy)
        if promo_pitch:
            # Replace the editorial opening line with a promotional framing; keep all format rules.
            after_first = sys_prompt.split('\n', 1)
            promo_header = (
                f'You are writing promotional {platform} content for {media}. Sentiment: {sentiment}.\n'
                f'BRAND BIBLE (authoritative — respect its positioning, voice, and "do not say" '
                f'compliance rules; never use forbidden phrases or forbidden product framings):\n'
                f'{promo_pitch}\n\n'
                'YOUR JOB: Open with a hook that fits the post idea, then present the product in a way '
                'that is credible, mechanism-led, and fully on-brand. Stay compliant — no hype, no profit '
                'promises, no risk-free language, no forbidden vocabulary. End with the brand benefit. '
                'All platform format rules below still apply.\n'
            )
            sys_prompt = promo_header + (after_first[1] if len(after_first) > 1 else '')
        if extra:
            sys_prompt += '\n' + extra
        msgs = [{'role': 'system', 'content': sys_prompt},
                {'role': 'user',   'content': user_msg}]
        cfg = EDITORIAL_MODELS.get(model_key, EDITORIAL_MODELS['gpt'])
        return openrouter_chat(cfg['id'], msgs, rule['temperature'], rule['maxTokens'])

    def safe_call(extra=''):
        """One retry on a malformed/unparseable model response — most JSON misses are one-off hiccups,
        and a single bad variant shouldn't fail the whole batch (the user sees 'nothing generated')."""
        try:
            return call(extra)
        except ValueError:
            return call(extra)

    angles = rule.get('variant_angles')

    def _enforce_length(copy, hashtags, extra=''):
        """Re-roll toward the platform's char-count bounds; hard-truncate over the max as a last resort."""
        lo, hi = rule.get('minChars'), rule.get('maxChars')
        if hi is None:
            return copy, hashtags
        n = len(copy)
        if n <= hi and (lo is None or n >= lo):
            return copy, hashtags
        if lo is not None and n < lo:
            note = f'Your previous attempt was only {n} characters — too short. This format requires {lo}-{hi} characters; add more relevant detail or context (do not invent facts) to reach at least {lo}.'
        else:
            note = f'Your previous attempt was {n} characters — too long. This format requires at most {hi} characters; tighten it without dropping the key facts.'
        try:
            result = safe_call(f'{extra}\nIMPORTANT: {note}'.strip())
        except ValueError:
            # Couldn't get a usable re-roll — keep the original draft rather than losing the variant.
            return copy, hashtags
        copy     = clean_emojis(result.get('copy', copy), platform)
        hashtags = result.get('hashtags', hashtags)
        if len(copy) > hi:
            copy = smart_truncate(copy, hi)
        return copy, hashtags

    variants = []
    if angles:
        # Each angle is a distinct, intentional framing — generate exactly one variant per angle.
        for angle in angles:
            try:
                result   = safe_call(angle['instruction'])
                copy     = clean_emojis(result.get('copy', ''), platform)
                hashtags = result.get('hashtags', [])
                copy, hashtags = _enforce_length(copy, hashtags, angle['instruction'])
            except ValueError as e:
                # This one angle never produced a usable response — skip it rather than
                # failing the whole request (the user would otherwise see nothing generated).
                print(f'[copy/generate] dropped {platform}/{angle["label"]} variant: {e}', file=sys.stderr)
                continue
            variants.append({'copy': copy, 'hashtags': hashtags, 'label': angle['label']})

        if not variants:
            raise ValueError(f'{platform} copy generation failed for all variants — try again')
    else:
        for i in range(variant_count):
            result   = call()
            copy     = clean_emojis(result.get('copy', ''), platform)
            hashtags = result.get('hashtags', [])
            variants.append({'copy': copy, 'hashtags': hashtags})

    brand_tag = BRAND_HASHTAGS.get(media)
    if brand_tag:
        for v in variants:
            v['hashtags'] = [brand_tag] + [t for t in v['hashtags'] if t.lower() != brand_tag.lower()]

    primary = variants[0]
    return {
        'variants': variants,
        'copy': primary['copy'],
        'hashtags': primary['hashtags'],
        'charCount': len(primary['copy']),
        'platform': platform,
    }
