"""Editorial direction and deterministic prompt assembly for Studio videos."""

import json
import re


VIDEO_FORMATS = {
    'systems_map': {
        'name': 'Systems Map',
        'use_for': 'several actors or connected actions',
        'hero_objects': ['layered map silhouette', 'connected asset network', 'editorial command table'],
        'palettes': ['light editorial paper and red accents', 'charcoal and icy blue'],
        'cameras': ['slow top-down drift', 'measured push-in'],
    },
    'mechanism_reveal': {
        'name': 'Mechanism Reveal',
        'use_for': 'an overlooked cause behind a visible event',
        'hero_objects': ['transparent mechanism', 'split-path financial flow', 'single symbolic machine'],
        'palettes': ['black, graphite, and mint highlights', 'soft grey and one red accent'],
        'cameras': ['controlled orbit', 'slow push through'],
    },
    'signal_matrix': {
        'name': 'Signal Matrix',
        'use_for': 'variables, conditions, and possible outcomes',
        'hero_objects': ['abstract signal board', 'three-way balance', 'layered market field'],
        'palettes': ['deep charcoal and violet', 'matte grey and coral'],
        'cameras': ['precise lateral slide', 'slow overhead descent'],
    },
    'structural_scarcity': {
        'name': 'Structural Scarcity',
        'use_for': 'supply, infrastructure, or a long-term resource gap',
        'hero_objects': ['monumental material object', 'glowing supply channel', 'architectural resource vault'],
        'palettes': ['black, metallic gold, and amber', 'stone, copper, and soft black'],
        'cameras': ['monumental low-angle move', 'slow vertical reveal'],
    },
    'scenario_map': {
        'name': 'Scenario Map',
        'use_for': 'uncertain next steps or several possible outcomes',
        'hero_objects': ['central decision object', 'branching pathways', 'orbiting outcome tokens'],
        'palettes': ['black and white with restrained red', 'dark navy and silver'],
        'cameras': ['slow circular move', 'centered push-in'],
    },
    'number_thesis': {
        'name': 'Number Thesis',
        'use_for': 'one important verified figure or calculation',
        'hero_objects': ['single luminous data monolith', 'floating value object', 'abstract rising plane'],
        'palettes': ['near-black and lime green', 'black and polished silver'],
        'cameras': ['minimal locked composition', 'slow push-in'],
    },
    'binary_debate': {
        'name': 'Binary Debate',
        'use_for': 'a credible bull-versus-bear or two-sided argument',
        'hero_objects': ['two opposing structures', 'balanced suspended objects', 'forked pathway'],
        'palettes': ['black with cold blue and warm red', 'soft white with black contrast'],
        'cameras': ['symmetrical push-in', 'slow cross-frame glide'],
    },
    'hero_diagram': {
        'name': 'Hero Diagram',
        'use_for': 'one person, organisation, or data set with multiple parts',
        'hero_objects': ['central portrait-like figure with orbiting symbols', 'radial data sculpture', 'layered institutional seal'],
        'palettes': ['deep green and black', 'charcoal and ivory'],
        'cameras': ['slow orbit around centre', 'measured frontal push-in'],
    },
    'capital_flow': {
        'name': 'Capital Flow',
        'use_for': 'rotation, liquidity, demand, or attention moving between themes',
        'hero_objects': ['glowing asset moving through channels', 'liquid light stream', 'two connected economic worlds'],
        'palettes': ['metallic black and electric amber', 'black and soft cyan'],
        'cameras': ['tracking move following the flow', 'slow forward glide'],
    },
}

# Derived from the latest Elite Crypto reel run: the visual language is not
# generic crypto b-roll. It is sparse, high-contrast editorial direction with
# one subject, a disciplined accent, and room for post-production typography.
STYLE_SYSTEMS = {
    'obsidian_portrait': {
        'name': 'Obsidian Editorial Portrait',
        'use_for': 'power, geopolitics, institutions, or a named public figure',
        'palette': 'near-black void, charcoal skin tones, soft silver, one restrained signal-red accent',
        'lighting': 'single sculpting key light, deep falloff, subtle halo separation, premium editorial contrast',
        'composition': 'one monumental portrait or silhouette, centred low in the frame, calm negative space in the upper third',
        'motion': 'slow push-in or restrained parallax, one deliberate reveal per narration beat',
        'transitions': 'hard cut on a thesis turn, otherwise slow dissolve through black',
    },
    'obsidian_sculpture': {
        'name': 'Obsidian Asset Sculpture',
        'use_for': 'crypto, money, infrastructure, supply, or an abstract mechanism',
        'palette': 'matte black, graphite, polished silver, one controlled mint, violet, amber, or lime accent',
        'lighting': 'soft studio rim light, restrained reflections, deep black negative space',
        'composition': 'one floating asset, sculptural mechanism, or monolithic object with generous empty space',
        'motion': 'slow orbit, minimal levitation, or a single tracked movement along a capital flow',
        'transitions': 'clean match cuts between related forms, no fast montage or decorative particles',
    },
    'institutional_paper': {
        'name': 'Institutional Paper Grid',
        'use_for': 'systems maps, decision trees, timelines, and multi-actor reporting',
        'palette': 'warm off-white, pale grey grid, black ink, one muted red or green accent',
        'lighting': 'even editorial daylight with soft paper texture and low-shadow depth',
        'composition': 'one central card or map-like form on a quiet grid, arranged with precise editorial balance',
        'motion': 'slow top-down drift, cards and symbols entering with measured spacing',
        'transitions': 'paper cuts, clean wipes, or brief held frames; never chaotic motion',
    },
    'minimal_signal': {
        'name': 'Minimal Signal Thesis',
        'use_for': 'one contradiction, a warning, or a focused conclusion',
        'palette': 'absolute black, soft white, graphite, and one narrow accent colour',
        'lighting': 'minimal gradient light with a subtle atmospheric bloom around the hero form',
        'composition': 'one symbolic shape or anonymous sculptural figure, isolated in a large black field',
        'motion': 'almost still at first, then one slow reveal or scale shift to mark the thesis',
        'transitions': 'brief fade through black and a single decisive cut at the reversal',
    },
}

_BANNED_PROMPT_TERMS = (
    'readable text', 'on-screen text', 'caption', 'label', 'logo', 'watermark',
    'ticker', 'small print', 'price tag', 'chart with numbers',
)
_RECENT_BRIEFS = {}
_NUMBER_RE = re.compile(r'(?<![\w.])(?:[$€£]?\d[\d,]*(?:\.\d+)?%?|\d{4})(?![\w.])')


def _clean(value, limit=1200):
    return str(value or '').strip()[:limit]


def _brand(cards):
    names = {str(card.get('media') or '').strip() for card in cards if card.get('media')}
    return next(iter(names)) if len(names) == 1 else 'Mixed'


def build_fact_ledger(cards):
    """Produce a deterministic, inspectable boundary around Studio source facts."""
    items = []
    source_text = []
    for card in cards:
        headline = _clean(card.get('headline'), 500)
        description = _clean(card.get('copy'), 5000)
        source = _clean(card.get('source'), 200)
        link = _clean(card.get('link'), 2000)
        published_at = _clean(card.get('publishedAt'), 100)
        items.append({
            'headline': headline,
            'description': description,
            'source': source,
            'link': link,
            'publishedAt': published_at,
        })
        source_text.extend([headline, description, published_at])
    combined = ' '.join(source_text)
    return {
        'sources': items,
        'approvedNumbers': sorted(set(_NUMBER_RE.findall(combined))),
        'approvedHeadlines': [item['headline'] for item in items if item['headline']],
    }


def _default_format(cards):
    combined = ' '.join(f"{card.get('headline', '')} {card.get('copy', '')}" for card in cards).lower()
    if len(cards) > 1:
        return 'systems_map'
    if any(word in combined for word in ('scenario', 'could', 'may', 'next', 'if ')):
        return 'scenario_map'
    if any(word in combined for word in ('inflow', 'billion', 'million', 'percent', '%', 'price')):
        return 'number_thesis'
    if any(word in combined for word in ('supply', 'demand', 'mine', 'scarcity', 'infrastructure')):
        return 'structural_scarcity'
    if any(word in combined for word in ('flow', 'rotation', 'liquidity', 'capital')):
        return 'capital_flow'
    return 'mechanism_reveal'


def _default_style_system(cards, format_key):
    combined = ' '.join(f"{card.get('headline', '')} {card.get('copy', '')}" for card in cards).lower()
    if format_key in {'systems_map', 'scenario_map', 'signal_matrix'}:
        return 'institutional_paper'
    if any(word in combined for word in (
        'president', 'trump', 'government', 'iran', 'china', 'russia', 'war', 'sanction', 'ceasefire',
        'minister', 'central bank', 'treasury',
    )):
        return 'obsidian_portrait'
    if format_key in {'number_thesis', 'structural_scarcity', 'capital_flow', 'hero_diagram'}:
        return 'obsidian_sculpture'
    return 'minimal_signal'


def _fallback_brief(cards, settings):
    key = _default_format(cards)
    spec = VIDEO_FORMATS[key]
    style_key = _default_style_system(cards, key)
    style = STYLE_SYSTEMS[style_key]
    return {
        'format': key,
        'formatName': spec['name'],
        'styleSystem': style_key,
        'styleSystemName': style['name'],
        'visualConcept': _clean(cards[0].get('headline'), 500),
        'heroObject': spec['hero_objects'][0],
        'palette': style['palette'],
        'camera': spec['cameras'][0],
        'composition': style['composition'],
        'transitionLanguage': style['transitions'],
        'motionArc': [
            'Open with the isolated hero object and a held composition that creates tension.',
            'Reveal the relationship between story elements through one controlled visual transformation.',
            'Resolve on a calm editorial tableau with mobile-safe negative space and no generated text.',
        ],
        'negativeConstraints': 'No generated readable text, logos, watermarks, tickers, stock footage, photo montage, UI cards, or decorative particles.',
        'rationale': f"{spec['name']} is the clearest original editorial treatment for these source facts.",
    }


def _recent_for(cards):
    return list(_RECENT_BRIEFS.get(_brand(cards), []))


def director_messages(cards, script, settings):
    ledger = build_fact_ledger(cards)
    catalog = '\n'.join(f"- {key}: {item['name']} - {item['use_for']}" for key, item in VIDEO_FORMATS.items())
    styles = '\n'.join(f"- {key}: {item['name']} - {item['use_for']}" for key, item in STYLE_SYSTEMS.items())
    return [
        {
            'role': 'system',
            'content': (
                'You are a short-form editorial video art director. Create an original visual direction for '
                'one continuous 9:16 news video. Use only the supplied facts and script. Do not use real article '
                'photos, brand marks, readable text, captions, labels, numbers, charts, logos, or watermarks. '
                'Never choose generic b-roll, a talking head, floating UI, or a busy montage. Choose exactly one format '\
                'from this list:\n' + catalog + '\n\nChoose exactly one visual system from this list:\n' + styles + '\n\n'
                'Return valid JSON only with these exact keys: format, styleSystem, visualConcept, heroObject, palette, '
                'camera, composition, transitionLanguage, motionArc (array of exactly 3 short beats), negativeConstraints, '
                'rationale. Make the concept cinematic but restrained: one dominant subject, a single controlled accent, '
                'large areas of negative space, and motion that reveals the argument one beat at a time. Reserve the upper '\
                'third for post-production typography but do not ask the model to render any text.'
            ),
        },
        {
            'role': 'user',
            'content': (
                f"Duration: {settings['duration']} seconds. Language: {settings['language']}. "
                f"Creative preference: {settings['visualDirection']}\n\n"
                f"SCRIPT:\n{json.dumps(script, ensure_ascii=False)}\n\n"
                f"FACT LEDGER:\n{json.dumps(ledger, ensure_ascii=False)}"
            ),
        },
    ]


def _has_banned_instruction(value):
    lowered = _clean(value, 5000).lower()
    return any(term in lowered for term in _BANNED_PROMPT_TERMS)


def validate_director_brief(raw, cards, settings):
    fallback = _fallback_brief(cards, settings)
    if not isinstance(raw, dict):
        return fallback
    format_key = _clean(raw.get('format'), 80).lower().replace(' ', '_')
    if format_key not in VIDEO_FORMATS:
        return fallback
    style_key = _clean(raw.get('styleSystem'), 80).lower().replace(' ', '_')
    if style_key not in STYLE_SYSTEMS:
        style_key = _default_style_system(cards, format_key)
    style = STYLE_SYSTEMS[style_key]
    fields = {
        'visualConcept': _clean(raw.get('visualConcept'), 1000),
        'heroObject': _clean(raw.get('heroObject'), 300),
        'palette': _clean(raw.get('palette'), 300) or style['palette'],
        'camera': _clean(raw.get('camera'), 300),
        'composition': _clean(raw.get('composition'), 600) or style['composition'],
        'transitionLanguage': _clean(raw.get('transitionLanguage'), 500) or style['transitions'],
        'negativeConstraints': _clean(raw.get('negativeConstraints'), 600),
        'rationale': _clean(raw.get('rationale'), 600),
    }
    arc = raw.get('motionArc')
    if not isinstance(arc, list):
        return fallback
    motion_arc = [_clean(item, 350) for item in arc if _clean(item, 350)][:3]
    if len(motion_arc) != 3 or not all(fields[key] for key in ('visualConcept', 'heroObject', 'palette', 'camera', 'composition')):
        return fallback
    if any(_has_banned_instruction(value) for value in [
        fields['visualConcept'], fields['heroObject'], fields['palette'], fields['camera'],
        fields['composition'], fields['transitionLanguage'], *motion_arc,
    ]):
        return fallback
    brief = {
        'format': format_key,
        'formatName': VIDEO_FORMATS[format_key]['name'],
        'styleSystem': style_key,
        'styleSystemName': style['name'],
        **fields,
        'motionArc': motion_arc,
    }
    signature = (brief['format'], brief['styleSystem'], brief['heroObject'].lower(),
                 brief['palette'].lower(), brief['camera'].lower())
    recent = _recent_for(cards)
    if any(tuple(item.get('signature', ())) == signature for item in recent[-5:]):
        return fallback
    return brief


def remember_director_brief(cards, brief):
    key = _brand(cards)
    recent = _RECENT_BRIEFS.setdefault(key, [])
    recent.append({
        'signature': (brief.get('format'), brief.get('styleSystem'),
                      _clean(brief.get('heroObject')).lower(),
                      _clean(brief.get('palette')).lower(),
                      _clean(brief.get('camera')).lower()),
    })
    del recent[:-10]


def narration_within_duration(script, settings):
    narration = _clean(script.get('narration'), 6000)
    # Two words a second is deliberately conservative for model-native narration.
    budget = max(12, int(settings['duration']) * 2)
    return len(narration.split()) <= budget, budget


def validate_script_facts(script, cards):
    """Reject numeric claims that are not represented in the selected source cards."""
    ledger = build_fact_ledger(cards)
    approved = {token.replace(',', '') for token in ledger['approvedNumbers']}
    content = ' '.join([
        _clean(script.get('hook'), 500),
        _clean(script.get('narration'), 6000),
        _clean(script.get('cta'), 500),
        ' '.join(_clean(item, 180) for item in (script.get('on_screen_captions') or [])),
    ])
    discovered = {token.replace(',', '') for token in _NUMBER_RE.findall(content)}
    unexpected = sorted(token for token in discovered if token not in approved)
    if unexpected:
        raise ValueError('Script contains figures not present in the selected stories: ' + ', '.join(unexpected[:5]))
    return ledger


def assemble_video_prompt(script, director_brief, settings, cards):
    ledger = validate_script_facts(script, cards)
    valid, budget = narration_within_duration(script, settings)
    if not valid:
        raise ValueError(f'Narration is too long for this model duration. Keep it to {budget} words or fewer.')
    brief = validate_director_brief(director_brief, cards, settings)
    style = STYLE_SYSTEMS[brief['styleSystem']]
    narration = _clean(script.get('narration'), 6000)
    audio = (
        f"Generate natural {settings['language']} narration in a {settings['voice']} voice, speaking exactly: {narration}. "
        f"Add original, subtle background music with a {settings['music']} mood below the narration."
        if settings.get('generateAudio') else
        'Do not generate narration or music.'
    )
    approved_facts = '; '.join(ledger['approvedHeadlines'])
    return (
        f"Create one continuous {settings['duration']}-second vertical 9:16 editorial news video at "
        f"{settings['resolution']}. Build an original conceptual visual treatment, not a photo montage.\n\n"
        f"FORMAT: {brief['formatName']}.\n"
        f"VISUAL SYSTEM: {style['name']}.\n"
        f"HOUSE PALETTE: {style['palette']}.\n"
        f"LIGHTING: {style['lighting']}.\n"
        f"VISUAL CONCEPT: {brief['visualConcept']}\n"
        f"HERO OBJECT: {brief['heroObject']}\n"
        f"PALETTE: {brief['palette']}\n"
        f"CAMERA: {brief['camera']}\n"
        f"COMPOSITION: {brief['composition']}\n"
        f"STYLE MOTION: {style['motion']}\n"
        f"TRANSITIONS: {brief['transitionLanguage']}\n"
        f"MOTION ARC: 0-33% {brief['motionArc'][0]} 33-66% {brief['motionArc'][1]} "
        f"66-100% {brief['motionArc'][2]}\n"
        f"AUDIO: {audio}\n"
        f"APPROVED FACT BOUNDARY: {approved_facts}\n"
        f"CONSTRAINTS: {brief['negativeConstraints']} No readable words, numbers, captions, logos, watermarks, "
        'tickers, charts, article photographs, or recognisable brands. Do not invent facts, people, quotes, '
        'dates, prices, outcomes, or causal claims beyond the approved boundary. Keep all compositions clean, '
        'credible, and mobile-first. Reserve the upper third as quiet negative space for post-production copy, '
        'but do not render text. Do not use stock footage, generic crypto b-roll, talking-head delivery, '
        'dashboard UI, floating data panels, busy montage editing, or decorative particles.'
    )
