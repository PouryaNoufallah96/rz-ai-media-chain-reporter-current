"""Per-brand Art-Director image profiles — the large brand-style contract dicts.
Extracted verbatim from server.py so the rest of the codebase can stay small.
"""

BRAND_IMAGE_PROFILES = {
    'RZ Prime': {
        'brand_name': 'RZ Prime',
        'brand_tagline': (
            'a premium crypto/Web3 reservation-protocol brand: clean product-visualization 3D, '
            'glass UI panels on circuit-board platforms, educational comparisons, and two recurring '
            'mascot characters (Blue Kid and Wolf)'
        ),
        'headline_max_words': 10,
        'headline_uppercase': True,
        'mood_accent_default': 'cyan',
        'mood_accent_restricted': {
            'cyan_vs_red':   {'families': ['versus', 'shatter', 'table']},
            'cyan_vs_green': {'families': ['versus', 'product', 'table', 'data_tiles']},
        },
        'axis_optional':          {'wolf': True},
        'axis_inject_after_data': ['wolf'],
        'passthrough_fields':     ['read'],
        'brief_prefix_schema':    {'read': 'CONTRAST | NUMBER | PROCESS | THREAT | LAUNCH | EDUCATION'},
        'brand_keywords': ['rz prime', 'rzprime'],
        'wolf_descriptions': {
            'none':    'no mascot characters in the scene (default when the layout is already visually complex)',
            'kid':     ('the Blue Kid mascot stands in the scene -- a round-faced child character with electric-blue '
                        'hair, an orange-brown fuzzy beanie hat, an oversized fuzzy blue sweater, dark shorts, and '
                        'bright green sneakers -- pointing at, touching, or presenting a glass UI panel'),
            'wolfman': ('the Wolf mascot stands in the scene -- a low-poly faceted blue wolf at human height, wearing '
                        'a tailored dark business suit with white shirt and tie -- gesturing toward or presenting '
                        'information on a glass panel'),
            'both':    ('both mascot characters appear together in the scene: the Blue Kid (round-faced child with '
                        'blue hair, orange beanie, oversized fuzzy blue sweater, dark shorts, green sneakers) and '
                        'the Wolf (low-poly faceted blue wolf in a dark suit with white shirt and tie) -- they flank '
                        'or interact with glass UI panels, pointing and presenting'),
        },
        'data_element_template': 'a clear glass UI panel displaying the value "{value}"{label_part}',
        'data_element_label_template': ' with the label "{label}"',
        'legibility_line': "All in-scene text is large, bold, crisp and clearly legible, each rendered on its own clear glass panel or surface.",
        'anti_repetition_rules': (
            "Hard rules: do not pick the same family 3 times in a row; do not use the "
            "'circuit_floor' environment more than 4 times in a row (it is the dominant default but still "
            "needs occasional variation); vary the wolf/character value -- do not use the same value twice "
            "in a row; use 'both' at most once every 4 posts; rotate camera and energy so consecutive "
            "posts don't feel identical."
        ),
        'frozen_style': {
            'format': "vertical 4:5 editorial poster, 1080x1350",
            'palette': (
                "near-black deep-navy base (#05080F-#0A1422) -- the background is genuinely dark in EVERY frame. "
                "Electric cyan/teal is the primary neon accent (#1FE0C2-#2FF0E0). Bright emerald green (#2BE38A) "
                "marks the positive/RZ Prime side (checkmarks, up-arrows, the Reserve action, the 'RZ Prime' label). "
                "Alarm red (#FF3B3B) marks the negative/legacy side (X marks, down-arrows, broken systems). "
                "Amber-orange (#FF8A3C) is reserved for caution cards and the Blue Kid's beanie hat. "
                "Soft violet-purple (#7A5BFF) is a SECONDARY glow only (rim light, atmosphere) and never leads. "
                "Typography is white, bold, UPPERCASE."
            ),
            'materials': (
                "clear glass UI panels and app-mockup screens (NOT frosted glassmorphism) with glowing cyan edges; "
                "circuit-board floor platform with illuminated trace lines; dark reflective surfaces; "
                "semi-transparent glass cubes and structures with visible internals; holographic accents."
            ),
            'rendering': (
                "clean product-visualization 3D, closer to a polished app-mockup render than a heavy octane-render "
                "scene. Still cinematic with volumetric light rays, soft fog, and floating particles, but more "
                "accessible and readable than hyper-detailed CG. Glow is the primary light source. No daylight. "
                "Two recurring mascot characters may appear across any family: "
                "(1) 'Blue Kid' -- a 3D character with a round face, simple features, electric-blue hair, an "
                "orange-brown fuzzy beanie hat, an oversized fuzzy blue sweater, dark shorts, and bright green "
                "sneakers; rendered with soft materials, NOT low-poly. "
                "(2) 'Wolf' -- a low-poly faceted blue wolf at human height, wearing a tailored dark business suit "
                "with a white shirt and tie; rendered in ice-blue and navy triangular planes. "
                "They interact with UI panels -- pointing, presenting, standing beside displays."
            ),
            'background_vocab': (
                "circuit-board floor with glowing cyan trace lines is THE dominant backdrop, appearing in the "
                "majority of images. Server corridor with perspective lines is the secondary environment. "
                "Network nodes and constellation-like connections fill deep backgrounds. Dark void with subtle "
                "tech elements for minimal scenes."
            ),
            'headline_zone': (
                "the top 25-35% of the frame is reserved for the headline; the headline is large, bold, "
                "UPPERCASE, white sans-serif. One key word MAY be solid cyan or green. Headlines are often "
                "conversational questions or provocative statements, 8-10 words."
            ),
            'never': (
                "no photorealistic humans (only the Blue Kid and Wolf mascot characters described above); "
                "no frosted or blurred glassmorphism (glass is always CLEAR); "
                "no daylight or outdoor photography; no white, pastel, or light-blue backgrounds; "
                "no stock-photo look; no flat 2D illustration; no real third-party logos or branded coins "
                "(competitors appear only as abstract glass tokens); no wallet addresses (0x...); "
                "no tiny labels or micro-text."
            ),
        },
        'metaphors': {
            "blockchain / smart contracts":   "clear glass cubes with glowing edges and visible circuit internals",
            "UI / interface / data":          "glass app-mockup panels and screens on pedestals",
            "security / verification":        "glowing green checkmarks, VERIFIED / AUDITED / ON-CHAIN badges on glass panels",
            "legacy finance / old model":     "dim greyscale elements, crumbling structures, X marks in red, broken screens",
            "tokens / capital / reserve":     "glass coins, the green RZ coin icon, streams of light",
            "network / market":               "constellation-like nodes connected by glowing lines",
            "risk / failure":                 "cracked glass with red glow and shattering fragments",
            "comparison / choices":           "left/right split frame with red (bad) vs cyan-green (good) sides",
            "process / flow":                 "connected glass panels with directional arrows between stages",
            "countdown / expiry":             "digital countdown display on a glass panel, timer UI elements",
        },
        'families': {
            'versus': {
                'name': "VERSUS / SPLIT",
                'skeleton': (
                    "The frame is divided left/right. The negative side glows dim alarm red with X marks, "
                    "down-arrows, broken or crumbling elements representing legacy finance, middlemen, or a "
                    "flawed system -- optionally shown as a failing UI screen. The positive side is ordered, "
                    "pristine, glowing cyan-green glass with checkmarks, up-arrows, and the RZ Prime answer. "
                    "Glass UI panels on each side may carry comparison labels. The Blue Kid and/or Wolf mascots "
                    "may stand on the positive side, presenting or gesturing toward the RZ panels."
                ),
                'text_policy': (
                    "Headline plus up to 6 short labels or phrases across both sides (large, on glass surfaces). "
                    "Each side may carry 2-3 labels identifying what it represents. Labels on the negative side "
                    "may be struck-through or dimmed. Full short sentences on panels are permitted."
                ),
                'default_axes': {'environment': 'circuit_floor', 'camera': 'eye_level_symmetric', 'energy': 'dramatic_tension'},
                'data_budget': 6,
            },
            'product': {
                'name': "PRODUCT SHOWCASE",
                'skeleton': (
                    "A central glass UI panel or app-mockup screen sits on a circuit-board platform, showcasing "
                    "the RZ Prime interface, a reserve mechanism, or a protocol concept. The panel looks like an "
                    "actual app screen with fields, buttons, and status indicators rendered in glass. Supporting "
                    "elements (smaller panels, glass cubes, coin icons) may orbit at the edges. The Blue Kid "
                    "and/or Wolf may stand beside the central panel, presenting it."
                ),
                'text_policy': (
                    "Headline plus up to 4 UI labels or values on the central panel (e.g. 'RESERVE $500', "
                    "'RZUSD', 'AVAILABLE', status fields). These are part of the UI mockup, not floating labels. "
                    "Keep each label to 1-4 words."
                ),
                'default_axes': {'environment': 'circuit_floor', 'camera': 'low_angle_hero', 'energy': 'calm_premium'},
                'data_budget': 4,
            },
            'flow': {
                'name': "FLOW / DECISION TREE",
                'skeleton': (
                    "A sequence of 3-5 connected glass panels or steps showing a process, decision tree, or "
                    "user journey. Glowing arrows or light paths connect the stages. The flow may branch into "
                    "two outcome panels at the bottom (e.g. 'Pay' vs 'Walk Away'). Panels sit on a circuit-board "
                    "platform or float in a structured arrangement. The Blue Kid and/or Wolf may stand at the "
                    "start or end of the flow, or beside a key decision point."
                ),
                'text_policy': (
                    "Headline plus up to 5 short phrases (1-5 words each) written large on the connected panels. "
                    "Each panel carries one step or outcome label. Weave the phrases directly into the scene "
                    "description. Full short sentences are permitted on panels."
                ),
                'default_axes': {'environment': 'circuit_floor', 'camera': 'eye_level_symmetric', 'energy': 'calm_premium'},
                'data_budget': 5,
            },
            'table': {
                'name': "COMPARISON TABLE",
                'skeleton': (
                    "A glass comparison panel fills the center of the frame on a circuit-board platform: a "
                    "feature column on the left, one or two comparison columns (e.g. 'OLD MODEL' dim/red, "
                    "'RZ PRIME' glowing cyan-green). Each row is a clear glass shelf with crisp large text. "
                    "Alternatively, a 'Myth vs Reality' format with two columns. The Blue Kid and/or Wolf "
                    "may flank the table, gesturing toward key rows."
                ),
                'text_policy': (
                    "Headline plus up to 8 row labels (1-4 words each) inside the table, plus column headers. "
                    "Tables can be text-heavy -- this is intentional. Column headers and row labels count toward "
                    "the budget. Each cell is large and legible on its own glass surface."
                ),
                'default_axes': {'environment': 'circuit_floor', 'camera': 'eye_level_symmetric', 'energy': 'calm_premium'},
                'data_budget': 8,
            },
            'character': {
                'name': "CHARACTER SCENE",
                'skeleton': (
                    "The Blue Kid and/or Wolf mascots are the heroes of the scene, prominently placed and "
                    "interacting with glass UI panels, countdown timers, verification badges, or data displays. "
                    "The characters may be pointing at panels, touching interfaces, looking at verification "
                    "results, or standing together flanking a central display. Glass speech-bubble panels may "
                    "float near them. The setting is a circuit-board platform with the characters at roughly "
                    "center-frame."
                ),
                'text_policy': (
                    "Headline plus up to 4 in-scene text elements: speech bubbles (5 words or fewer each), "
                    "UI panel labels (1-4 words), or badge text (VERIFIED, ON-CHAIN, etc.). The characters and "
                    "their interaction with the panels tell the story."
                ),
                'default_axes': {'environment': 'circuit_floor', 'camera': 'eye_level_symmetric', 'energy': 'calm_premium'},
                'data_budget': 4,
            },
            'shatter': {
                'name': "SHATTER / DISRUPT",
                'skeleton': (
                    "A pristine central RZ glass object (cube, shield, or smart-contract panel) stands intact "
                    "and luminous, bearing VERIFIED / AUDITED / ON-CHAIN badges in green. At the edges of the "
                    "frame, legacy elements labeled CUSTODY, MIDDLEMAN, BUREAUCRACY shatter outward in "
                    "slow-motion fragments with red X marks, alarm-red cracks radiating from impact points. "
                    "The circuit-board floor anchors the central object."
                ),
                'text_policy': (
                    "Headline plus up to 5 labels: 2-3 on the central intact object (VERIFIED, AUDITED, "
                    "ON-CHAIN, 1-2 words each, green-tinted) and 2-3 shattering labels at the edges "
                    "(CUSTODY, MIDDLEMAN, etc., 1-2 words each, red-tinted with X marks)."
                ),
                'default_axes': {'environment': 'circuit_floor', 'camera': 'low_angle_hero', 'energy': 'explosive_dynamic'},
                'data_budget': 5,
            },
            'data_tiles': {
                'name': "DATA TILES / CARDS",
                'skeleton': (
                    "2-3 ascending glass tiles, cards, or phone-screen mockups sit on a circuit-board platform, "
                    "each carrying ONE large value and ONE short label. They may be arranged as ascending stairs "
                    "to convey growth, or as side-by-side comparison cards (e.g. 'Traditional Market' red vs "
                    "'RZ Prime' cyan). A relevant hero element (coin icon, chart silhouette) may float above."
                ),
                'text_policy': (
                    "Headline plus a maximum of 3 data elements. Each value is 1-5 characters (e.g. 3%, 6%, 9%), "
                    "each label is 1-3 words. Values are rendered larger than labels. Cards may have a colored "
                    "accent edge (red for negative comparison, cyan/green for RZ)."
                ),
                'default_axes': {'environment': 'circuit_floor', 'camera': 'low_angle_hero', 'energy': 'calm_premium'},
                'data_budget': 3,
            },
            'blueprint': {
                'name': "BLUEPRINT / ARCHITECTURE",
                'skeleton': (
                    "A technical architecture view: a glass desk or platform with floating holographic panels "
                    "showing a system diagram, smart contract structure, or protocol architecture. Elements "
                    "may include a Smart Contract file panel, a magnifying glass over code, an on-chain explorer "
                    "window, blockchain cubes, or a schematic wall with connecting lines. The Wolf may stand "
                    "inside a glass cube or beside the architecture. Legacy elements (dim, warm) may contrast "
                    "with on-chain elements (bright, cyan) to show transformation."
                ),
                'text_policy': (
                    "Headline plus up to 4 short labels on panels or elements (e.g. 'Smart Contract', "
                    "'On-Chain Explorer', 'VERIFIED', 'Legacy Rails'). The architecture diagram itself "
                    "may contain abstract connecting lines and icons."
                ),
                'default_axes': {'environment': 'circuit_floor', 'camera': 'eye_level_symmetric', 'energy': 'calm_premium'},
                'data_budget': 4,
            },
        },
        'axes': {
            'environment': {
                'circuit_floor':    ("The setting is a dark reflective circuit-board floor with glowing cyan trace "
                                     "lines radiating outward beneath the main subject, the brand's signature platform."),
                'server_corridor':  ("The setting is a neon-lit futuristic corridor with strong perspective lines "
                                     "converging toward a glowing vanishing point."),
                'deep_network':     ("The setting is a deep dark void filled with faint network nodes and "
                                     "constellation-like connections, a vast digital space."),
                'glass_chamber':    ("The setting is an enclosed glass chamber with translucent walls showing "
                                     "circuit patterns, a controlled tech environment."),
            },
            'camera': {
                'eye_level_symmetric': ("The camera is at eye level, centered symmetrically, giving a balanced "
                                        "architectural view of the scene."),
                'low_angle_hero':      ("The camera looks up at the scene from a low angle, making the central "
                                        "subject feel monumental."),
                'one_point_corridor':  ("The camera is positioned frontally with one-point perspective, pulling "
                                        "the eye straight down the depth of the scene."),
                'slight_overhead':     ("The camera looks down at a slight overhead angle, giving a clear view "
                                        "of panels and platform layout."),
            },
            'energy': {
                'calm_premium':      "The lighting is still and confident, with a soft, even glow throughout the scene.",
                'dramatic_tension':  ("The lighting is high-contrast with deep shadows and drifting fog, creating "
                                      "dramatic tension."),
                'explosive_dynamic': ("The scene is full of motion, with fragments hanging mid-air and bursts of "
                                      "light radiating outward, conveying explosive energy."),
            },
            'mood_accent': {
                'cyan':          "The dominant accent color throughout the scene is electric cyan/teal.",
                'cyan_vs_red':   ("The scene contrasts electric cyan/green on the positive side against "
                                  "dim alarm red on the negative side."),
                'cyan_vs_green': ("The scene features both electric cyan/teal for analytical elements and "
                                  "bright emerald green for active/positive/RZ elements."),
            },
            'wolf': {
                'none':    '',
                'kid':     ("The Blue Kid mascot stands in the scene -- a round-faced 3D character with electric-blue "
                            "hair, an orange-brown fuzzy beanie hat, an oversized fuzzy blue sweater, dark shorts, and "
                            "bright green sneakers -- pointing at or interacting with a glass UI panel."),
                'wolfman': ("The Wolf mascot stands in the scene -- a low-poly faceted blue wolf at human height, "
                            "wearing a tailored dark business suit with white shirt and tie -- gesturing toward or "
                            "presenting information on a glass panel."),
                'both':    ("Both mascot characters appear together: the Blue Kid (round-faced, blue hair, orange "
                            "beanie, fuzzy blue sweater, dark shorts, green sneakers) and the Wolf (low-poly faceted "
                            "blue wolf in a dark suit with white shirt and tie) -- flanking or interacting with glass "
                            "UI panels, pointing and presenting."),
            },
        },
        'routing_table': """
Classify the article's sharpest claim as one READ, then pick the family:

CONTRAST (A vs B, custody vs on-chain, with/without RZ, fee comparison, old vs new model)
  general contrast / two sides ........ versus        (fallback: table)
  explicit feature-by-feature ......... table         (fallback: versus)
  myths vs reality / fact-check ....... table         (fallback: versus)

NUMBER (stat, price, record, fee structure, metric comparison)
  ascending metrics / fee tiers ....... data_tiles    (fallback: product)
  product screen IS the proof ......... product       (fallback: data_tiles)

PROCESS (how-it-works, lifecycle, expiry, reservation mechanism, decision tree)
  ordered steps / user journey ........ flow          (fallback: product)
  conditional / what-if outcomes ...... flow          (fallback: versus)

THREAT (regulation, crackdown, hack, scam, trust, verification)
  regulation / compliance positive .... shatter       (fallback: blueprint)
  scam / trust / verification ......... shatter       (fallback: versus)
  legacy-to-onchain transition ........ blueprint     (fallback: shatter)

LAUNCH (product feature, protocol update, new capability)
  product / interface showcase ........ product       (fallback: data_tiles)
  architecture / infrastructure ....... blueprint     (fallback: product)

EDUCATION (explainer, guide, FAQ, newcomer onboarding)
  how-it-works / newcomer guide ....... flow          (fallback: product)
  architecture / audit / infra ........ blueprint     (fallback: flow)
  character-led explanation ........... character     (fallback: flow)

Anything ambiguous .................... product       (fallback: versus)
""".strip(),
        'text_rules': """
1. Headline: 10 words or fewer, UPPERCASE, punchy and often a conversational question or provocative
   statement. Big numbers and tickers are encouraged. One key word MAY be solid cyan or green.
   Never use hard-to-spell proper nouns -- tickers (BTC, ETH, RZUSD) are fine.
2. In-scene text budget per family: versus up to 6 labels across both sides, product up to 4 UI labels,
   flow up to 5 step/outcome phrases, table up to 8 row labels plus headers, character up to 4
   (speech bubbles + panel labels), shatter up to 5 (center badges + edge labels), data_tiles up to 3
   value+label pairs, blueprint up to 4 panel labels.
3. Every in-scene text string must sit on its own clear glass panel or surface.
4. Values are 1-5 characters; labels and phrases are 1-5 words; render them large and crisp.
5. UI labels like RESERVED, AVAILABLE, VERIFIED, AUDITED, ON-CHAIN are encouraged where relevant.
6. Full short sentences on glass panels are permitted (up to 8 words) -- this brand is text-heavy
   by design. Speech bubbles may carry conversational phrases.
7. No real company/exchange names anywhere in the image. No wallet addresses (0x...).
""".strip(),
        'fallback_brief': {
            'read': 'LAUNCH',
            'family': 'product',
            'headline': 'CRYPTO MARKETS MOVE',
            'data_elements': [],
            'environment': 'circuit_floor',
            'camera': 'eye_level_symmetric',
            'energy': 'calm_premium',
            'mood_accent': 'cyan',
            'wolf': 'none',
            'subject_scene': (
                "A single clear glass UI panel sits on a dark circuit-board platform with glowing cyan "
                "trace lines, displaying a clean app-mockup interface with a status indicator and the "
                "green RZ coin icon, radiating soft cyan light."
            ),
        },
        'brief_examples': """
Worked examples (for guidance only -- do not copy headlines or scenes verbatim):

A. Article: "Why custodial exchanges still hold your crypto hostage"
{"read": "CONTRAST", "family": "versus", "headline": "NOT YOUR KEYS, NOT YOUR CRYPTO", "data_elements": [{"value": "CUSTODY", "label": ""}, {"value": "ON-CHAIN", "label": ""}, {"value": "MIDDLEMAN", "label": ""}, {"value": "DIRECT", "label": ""}], "environment": "circuit_floor", "camera": "eye_level_symmetric", "energy": "dramatic_tension", "mood_accent": "cyan_vs_red", "wolf": "both", "subject_scene": "On the left, a dim red-tinted panel shows CUSTODY and MIDDLEMAN with red X marks, broken glass fragments drifting from it. On the right, a pristine cyan-green panel shows ON-CHAIN and DIRECT with green checkmarks. The Blue Kid and Wolf stand on the right side, the Kid pointing at the positive panel while the Wolf gestures dismissively at the broken left side. Circuit-board floor with glowing traces beneath."}

B. Article: "RZ Prime launches structured early access for token reservations"
{"read": "LAUNCH", "family": "product", "headline": "EARLY ACCESS SHOULD BE STRUCTURED", "data_elements": [{"value": "RESERVE", "label": ""}, {"value": "RZUSD", "label": ""}, {"value": "AVAILABLE", "label": ""}], "environment": "circuit_floor", "camera": "low_angle_hero", "energy": "calm_premium", "mood_accent": "cyan_vs_green", "wolf": "none", "subject_scene": "A large clear glass UI panel sits on a circuit-board platform, displaying an app-mockup reserve interface with RESERVE, RZUSD, and AVAILABLE fields glowing in cyan and green, the green RZ coin icon hovering beside it."}

C. Article: "What actually happens when your reservation window expires"
{"read": "PROCESS", "family": "flow", "headline": "WHAT ACTUALLY HAPPENS IF I DO NOTHING", "data_elements": [{"value": "EXPIRES", "label": "WINDOW"}, {"value": "RELEASED", "label": "TOKENS"}, {"value": "$0", "label": "COST"}], "environment": "circuit_floor", "camera": "eye_level_symmetric", "energy": "calm_premium", "mood_accent": "cyan", "wolf": "both", "subject_scene": "Three connected clear glass panels descend diagonally on a circuit-board platform, arrows linking them: WINDOW EXPIRES at top, TOKENS RELEASED in middle, YOU PAY ZERO at bottom with a green checkmark. The Blue Kid touches the top panel while the Wolf stands at the bottom, gesturing calmly toward the zero-cost outcome."}

D. Article: "The old model vs RZ Prime: a feature comparison"
{"read": "CONTRAST", "family": "table", "headline": "WHY ARE PEOPLE STILL USING THE OLD MODEL", "data_elements": [{"value": "CeFi", "label": ""}, {"value": "RZ", "label": ""}, {"value": "FEES", "label": ""}, {"value": "KYC", "label": ""}, {"value": "CUSTODY", "label": ""}], "environment": "circuit_floor", "camera": "slight_overhead", "energy": "calm_premium", "mood_accent": "cyan_vs_red", "wolf": "kid", "subject_scene": "A glass comparison table fills the center on a circuit-board platform: CeFi column dim and red-tinted on the left, RZ PRIME column glowing cyan-green on the right, with rows for FEES, KYC, and CUSTODY. The Blue Kid stands beside the table, pointing at the RZ PRIME column. Green checkmarks on the RZ side, red X marks on the CeFi side."}

E. Article: "RZ Prime fees are transparent: 3%, 6%, or 9%"
{"read": "NUMBER", "family": "data_tiles", "headline": "CLEAR FEE, CLEAR TIMING, CLEAR OUTCOME", "data_elements": [{"value": "3%", "label": "TIER 1"}, {"value": "6%", "label": "TIER 2"}, {"value": "9%", "label": "TIER 3"}], "environment": "circuit_floor", "camera": "low_angle_hero", "energy": "calm_premium", "mood_accent": "cyan_vs_green", "wolf": "none", "subject_scene": "Three ascending clear glass tiles rise from a circuit-board platform like stairs, each displaying a fee percentage in large cyan text with a tier label below, the tiles growing taller left to right, soft green glow on the highest tier."}

F. Article: "In a space where humans make mistakes, code doesn't"
{"read": "THREAT", "family": "shatter", "headline": "IN A SPACE WHERE HUMANS MAKE MISTAKES CODE DOESN'T", "data_elements": [{"value": "VERIFIED", "label": ""}, {"value": "AUDITED", "label": ""}, {"value": "ON-CHAIN", "label": ""}, {"value": "CUSTODY", "label": ""}, {"value": "MIDDLEMAN", "label": ""}], "environment": "circuit_floor", "camera": "low_angle_hero", "energy": "explosive_dynamic", "mood_accent": "cyan_vs_red", "wolf": "none", "subject_scene": "A pristine glass cube at center glows cyan with VERIFIED, AUDITED, and ON-CHAIN badges in green on its faces. At the edges, crumbling legacy elements labeled CUSTODY and MIDDLEMAN shatter outward with red X marks and alarm-red cracks, fragments suspended mid-air. Circuit-board floor with glowing traces radiates beneath the intact cube."}
""".strip(),
    },
    'Coin Hall': {
        'brand_name': 'Coin Halls',
        'brand_tagline': "a luxury Web3 prediction-game brand set in a 1920s Art Deco mansion world, where "
                         "holographic on-chain data lives inside classical opulence",
        'headline_max_words': 7,
        'headline_uppercase': False,
        'mood_accent_default': 'gold',
        'mood_accent_restricted': {'gold_vs_mono': 'contrast'},
        'axis_optional': {'hall_theme': True},
        'data_element_template': 'an engraved gold plaque or glowing holographic panel displaying "{value}"{label_part}',
        'data_element_label_template': ' next to the label "{label}"',
        'legibility_line': "All lettering is large, elegant, crisp and clearly legible, engraved gold serif style.",
        'anti_repetition_rules': (
            "Hard rules: do not repeat the same family more than 2 times in a row; do not use the "
            "'grand_hall' environment more than 3 times in a row; use the 'society' family at most "
            "once every 4 posts; include a hall_theme other than 'none' at least once every 5 posts; "
            "include a holographic/on-chain element in at least 2 of every 3 posts."
        ),
        # §0 — Frozen brand layer: never varies, never touches an LLM.
        'frozen_style': {
            'format': "vertical 4:5 editorial poster set in a 1920s Art Deco / Gatsby-era luxury world -- grand "
                      "mansion interiors and estates, rendered as cinematic photographic realism, NOT glossy "
                      "3D-render and NOT neon sci-fi",
            'palette': "near-black and deep warm brown base, with champagne gold, brass and amber as the dominant "
                       "accent, and warm candlelight / chandelier glow throughout. The one permitted tech color is "
                       "a faint teal-emerald holographic glow, used sparingly",
            'materials': "black marble with gold veining, polished brass, crystal chandeliers, aged paper, "
                         "leather-bound ledgers, velvet, gold engraving, candle flame",
            'rendering': "warm, low-key, candlelit / chandelier-lit cinematic photography with dramatic shadows "
                         "and golden reflections on polished marble floors; elegant figures in evening wear, "
                         "silhouettes and candlelit crowds are allowed and encouraged, with faces stylized-cinematic "
                         "and never recognizable real people",
            'background_vocab': "the brand's signature fusion -- holographic on-chain data living inside the "
                                 "classical world: teal glass panels with predictions or timestamps floating over "
                                 "marble, data light-streams entering windows, glowing verified-price tags. Most "
                                 "images contain at least one subtle on-chain element; the technology is a guest "
                                 "in the mansion, never the architecture",
            'headline_zone': "the top zone carries the headline in elegant letter-spaced SERIF type in gold or "
                             "champagne, often framed by Art Deco ornamental borders with corner flourishes; mixed "
                             "case or small-caps is allowed",
            'never': "no neon cyberpunk, no sci-fi corridors, no frosted-glass cube aesthetics, no daylight or "
                     "office settings, no casual or cartoon style, no white backgrounds, no recognizable real "
                     "people, no real luxury-brand logos or names, no paragraphs of text, no small dense labels",
        },
        # §0 metaphor library — shared visual vocabulary the Art Director can draw on.
        'metaphors': {
            "timing / timestamps":               "an antique pocket watch, grandfather clock, or hourglass",
            "oracle / verified price":            "brass scales of justice, a wax-sealed verdict, or an illuminated 'verified' tag",
            "entries / records / on-chain log":   "a handwritten ledger, fountain pen, wax seal, or holographic registry board",
            "the pot / prize":                    "a golden trophy cup overflowing with light or coins",
            "the halls / choices":                "grand doors, archways, or corridors of doors with engraved signs",
            "blockchain / on-chain proof":        "teal holographic glass panels, data light-streams, or glowing constellation lines",
            "skill / precision":                  "a chess piece, telescope, compass, or magnifying glass over numbers",
            "chaos / gambling / the old way":     "blurred monochrome casino noise, roulette motion blur, or scattered chips",
            "the platform itself":                "the mansion or chateau at night, with glowing windows",
            "hall themes":                        "a sculptural luxury automobile (car), a diamond on velvet (jewelry), vintage "
                                                   "luggage with a glass horizon (trip), brass machinery and gears (industrial), "
                                                   "or a skyline beyond arched windows (real estate)",
        },
        # §1 — Layout families F1-F8 (artifact/contrast/registry/doors/procession/reveal/hologram/society).
        'families': {
            'artifact': {
                'name': "ARTIFACT",
                'skeleton': "ONE exquisite object sits in macro/close-up on black marble -- a pocket watch, brass "
                            "scales, trophy, ledger, diamond, or key -- candlelit with shallow depth of field, a "
                            "dim mansion room blurred behind. The object may carry one short engraved or displayed value.",
                'text_policy': "Headline plus at most ONE in-scene value displayed on the object itself (a number, "
                               "a date, or 1-4 words). Prefer art_only or a single data element.",
                'default_axes': {'environment': 'marble_table', 'camera': 'close_up_macro', 'energy': 'quiet_prestige'},
                'data_budget': 1,
            },
            'contrast': {
                'name': "CONTRAST",
                'skeleton': "The frame is split left/right. The negative side is desaturated, monochrome and "
                            "motion-blurred -- casino noise, roulette wheels, frantic crowds, scattered chips. The "
                            "positive side is still, warm and golden -- composed figures in an Art Deco hall under "
                            "chandelier light, ordered and calm. A clean vertical seam or architectural divide "
                            "separates the two sides.",
                'text_policy': "Headline only, ideally spanning the seam. At most one short label per side if essential.",
                'default_axes': {'environment': 'grand_hall', 'camera': 'eye_level_wide', 'energy': 'dramatic_tension'},
                'data_budget': 2,
            },
            'registry': {
                'name': "REGISTRY",
                'skeleton': "Either (a) a teal holographic board floats above a marble pedestal in a candlelit "
                            "hall, listing 2-4 large values with one row highlighted gold as the winner or record; "
                            "or (b) an open aged ledger lies on marble with 2-3 large handwritten entries, a "
                            "fountain pen, and a wax seal.",
                'text_policy': "Headline plus at most 3 value+label pairs. Values are 1-6 characters (e.g. $85.34, "
                               "$12.4M); labels are 1-2 words. Each value rendered large on its own row or line. "
                               "No timestamps as microtext.",
                'default_axes': {'environment': 'grand_hall', 'camera': 'low_angle_pedestal', 'energy': 'quiet_prestige'},
                'data_budget': 3,
            },
            'doors': {
                'name': "DOORS OF OUTCOME",
                'skeleton': "2-3 grand doors or archways stand in a marble corridor, each with a short engraved "
                            "sign above. A golden light-path on the floor splits and flows toward them; doors may "
                            "glow differently -- warm and open vs dim and closed -- to show outcomes.",
                'text_policy': "Headline plus at most 3 engraved door signs of 1-3 words each, large.",
                'default_axes': {'environment': 'door_corridor', 'camera': 'one_point_symmetry', 'energy': 'quiet_prestige'},
                'data_budget': 3,
            },
            'procession': {
                'name': "HALL PROCESSION",
                'skeleton': "A symmetrical row of 3-5 ornate doors or archways under a chandelier (the five-halls "
                            "shot), or three objects on marble pedestals along a corridor, each step represented "
                            "by an icon-object (door, ledger, trophy) connected by a golden floor inlay.",
                'text_policy': "Headline plus at most 3 short labels (1-2 words) on signs above doors or pedestals. "
                               "For the five-hall establishing shot, use hall names (CAR, JEWELRY, TRIP, "
                               "INDUSTRIAL, REAL ESTATE) but show only 3 visible signs, with the rest implied.",
                'default_axes': {'environment': 'grand_hall', 'camera': 'one_point_symmetry', 'energy': 'quiet_prestige'},
                'data_budget': 3,
            },
            'reveal': {
                'name': "REVEAL",
                'skeleton': "Scale and unveiling: the chateau at night with glowing windows beneath a "
                            "constellation-lined sky, or a trophy cup swelling with golden light at the end of a "
                            "long hall, or curtains drawing back from a prize. A small dim foreground gives way "
                            "to a grand, glowing subject.",
                'text_policy': "Headline plus optionally one value (the prize or pot figure) on a plaque or holo tag.",
                'default_axes': {'environment': 'estate_exterior', 'camera': 'eye_level_wide', 'energy': 'ceremonial_awe'},
                'data_budget': 1,
            },
            'hologram': {
                'name': "HOLOGRAM IN THE HALL",
                'skeleton': "Teal holographic elements materialize inside the classical space -- a holo panel "
                            "hovering above a marble table showing a glowing checkmark or seal, a stream of "
                            "luminous data flowing through a window into a ledger, or ghostly constellation lines "
                            "connecting a chandelier to a verified-price tag. The classical room dominates; the "
                            "hologram accent fills roughly 20% of the frame.",
                'text_policy': "Headline plus at most 2 short holo labels (e.g. 'VERIFIED', one value). Any "
                               "diagrammatic content is abstract and wordless.",
                'default_axes': {'environment': 'study_library', 'camera': 'eye_level_wide', 'energy': 'quiet_prestige'},
                'data_budget': 2,
            },
            'society': {
                'name': "SOCIETY SCENE",
                'skeleton': "Elegant evening-dress figures populate the hall -- a celebrated winner under a "
                            "spotlight, an applauding crowd around a prize, or guests with faint holo "
                            "prediction-tags floating beside them. Cinematic group staging, golden light, marble "
                            "reflections.",
                'text_policy': "Headline plus at most 2 short holo-tag values, or one plaque line (e.g. 'CAR "
                               "HALL'). Never wallet addresses or long strings.",
                'default_axes': {'environment': 'grand_hall', 'camera': 'eye_level_wide', 'energy': 'ceremonial_awe'},
                'data_budget': 2,
            },
        },
        # §3 — Variation axes: each value maps to a fixed sentence used by the assembler.
        'axes': {
            'environment': {
                'grand_hall':      "The setting is a grand Art Deco hall, with crystal chandeliers, columns, and "
                                   "a black marble floor inlaid with gold.",
                'study_library':   "The setting is an intimate wood-paneled study or library, with a desk lamp, "
                                   "a leather-bound ledger, and a glass of whisky.",
                'door_corridor':   "The setting is a marble corridor lined with ornate doors and archways, "
                                   "receding into the depth of the frame.",
                'marble_table':    "The setting is an extreme close-up world: a single object resting on a black "
                                   "marble surface, candlelight reflecting off the stone.",
                'estate_exterior': "The setting is the grand chateau at night, its windows glowing warmly beneath "
                                   "a starlit, constellation-lined sky.",
                'gallery_balcony': "The setting is a mezzanine gallery overlooking the grand hall below, with "
                                   "ornate railings and deep architectural shadow.",
            },
            'camera': {
                'close_up_macro':    "The camera is in extreme close-up, macro focus on the texture and surface "
                                     "detail of the central object.",
                'eye_level_wide':    "The camera is a cinematic eye-level wide establishing shot.",
                'one_point_symmetry':"The camera is positioned frontally with one-point symmetry, looking "
                                     "straight down a corridor or row of doors.",
                'low_angle_pedestal':"The camera looks up at a pedestal or holographic board from a low angle.",
                'over_shoulder':     "The camera looks past a silhouetted guest toward the subject.",
            },
            'energy': {
                'quiet_prestige':   "The lighting is still and confident, candlelit and golden, conveying quiet prestige.",
                'dramatic_tension': "The lighting is high-contrast with deep shadows and a single hard light "
                                    "source, creating dramatic tension.",
                'ceremonial_awe':   "The scene is lit like a ceremonial spotlight moment, with swirling light and "
                                    "a sense of celebration.",
            },
            'hall_theme': {
                'car':         "A sculptural luxury automobile silhouette with brass engine details is woven into "
                               "the scene, evoking the Car Hall.",
                'jewelry':     "A diamond or necklace resting on dark velvet, catching candle glints, is woven "
                               "into the scene, evoking the Jewelry Hall.",
                'trip':        "Vintage travel luggage and a glass horizon traced with golden map lines are woven "
                               "into the scene, evoking the Trip Hall.",
                'industrial':  "Polished brass machinery and gears with a forge-like glow are woven into the "
                               "scene, evoking the Industrial Hall.",
                'real_estate': "A skyline glimpsed beyond arched windows, alongside an architectural model on "
                               "marble, is woven into the scene, evoking the Real Estate Hall.",
            },
            'mood_accent': {
                'gold':       "The dominant accent color throughout the scene is champagne gold and brass.",
                'gold_teal':  "The dominant accent blends champagne gold with the brand's teal-emerald "
                              "holographic glow, for scenes carrying on-chain elements.",
                'gold_vs_mono':"The scene contrasts champagne gold and warm light on the positive side against "
                               "desaturated monochrome on the negative side.",
            },
        },
        # §2 — News-type -> family routing guidance for the Art Director.
        'routing_table': """
News category -> Primary family (fallback):
- Auction results / collectible price records -> registry (fallback: artifact)
- Luxury category news (cars, watches, jewelry, travel, real estate) -> artifact (fallback: society)
- Luxury market trends / wealth reports -> registry (fallback: reveal)
- Oracle / price feeds / Chainlink / Pyth -> hologram (fallback: artifact)
- Smart-contract fairness / transparency / timestamps -> hologram (fallback: doors)
- No-KYC / wallet-based access -> hologram (fallback: contrast)
- Web3 gaming / entertainment market context -> contrast (fallback: society)
- Gambling-vs-skill / positioning / FUD -> contrast (fallback: artifact)
- How-it-works / mechanics explainers -> doors (fallback: procession)
- Platform overview / five halls -> procession (fallback: reveal)
- Winner / prize / pot announcements -> society (fallback: reveal)
- Growth / big numbers / anticipation -> reveal (fallback: registry)
- Anything ambiguous -> artifact

Tie-breakers: prefer the family NOT used in the last 3 posts (see anti-repetition notes below). If still
tied, prefer the lower-risk family -- artifact is the safest universal fallback.
""".strip(),
        # §4 items 1-5 — global text rules for the Art Director (item 6, the legibility line, is
        # appended deterministically by the assembler).
        'text_rules': """
1. Headline: 7 words or fewer, elegant, mixed case or small-caps allowed. Big values are encouraged. Avoid
   hard-to-spell proper nouns; never use real auction-house or luxury-brand names (say THE RECORD SALE, not
   Sotheby's), and never depict real luxury-brand logos or names in the image.
2. In-scene text budget per family: artifact <=1, contrast <=2, registry <=3 value+label pairs, doors <=3
   door signs, procession <=3 labels, reveal <=1 value, hologram <=2 holo labels, society <=2 short tags.
3. Values are 1-6 characters; labels and signs are 1-3 words; render every string large on its own clean
   surface (a plaque, sign, holo panel, or ledger line).
4. Sub-headlines are not generated in-image; thin taglines belong to the overlay layer, not the prompt.
5. Never render wallet addresses, timestamps as microtext, dense lists, or paragraphs.
""".strip(),
        # Safe fallback brief used when the Art Director response is missing/invalid/banned.
        'fallback_brief': {
            'family': 'artifact',
            'headline': 'A Quiet Moment, Recorded',
            'layout': 'art_only',
            'data_elements': [],
            'environment': 'marble_table',
            'camera': 'close_up_macro',
            'energy': 'quiet_prestige',
            'mood_accent': 'gold',
            'hall_theme': 'none',
            'subject_scene': (
                "An antique gold pocket watch lies open on black marble veined with gold, its face catching "
                "warm candlelight, with the dim glow of a grand hall blurred softly behind it."
            ),
        },
        'brief_examples': """
Worked examples (for guidance only -- do not copy headlines or scenes verbatim):

A. Article: "Patek Philippe watch sells for record $12.4M at auction"
{"family": "registry", "headline": "A Record Falls Under the Hammer", "layout": "art_with_data", "data_elements": [{"value": "$12.4M", "label": "HAMMER"}, {"value": "x3", "label": "ESTIMATE"}], "environment": "grand_hall", "camera": "low_angle_pedestal", "energy": "quiet_prestige", "mood_accent": "gold_teal", "hall_theme": "jewelry", "subject_scene": "A teal holographic registry board hovers above a black marble pedestal in a candlelit Art Deco hall, two glowing ledger rows displaying the record figures with the top row haloed in gold; below, a diamond necklace rests on dark velvet catching candlelight, while blurred evening-dress silhouettes watch from the shadows."}

B. Article: "Chainlink launches new low-latency price feeds"
{"family": "hologram", "headline": "The Oracle Just Got Faster", "layout": "art_with_data", "data_elements": [{"value": "VERIFIED", "label": ""}], "environment": "study_library", "camera": "eye_level_wide", "energy": "quiet_prestige", "mood_accent": "gold_teal", "hall_theme": "none", "subject_scene": "A teal stream of luminous data pours through a tall window onto an open ledger on a wood-paneled desk, while a brass scale beside it tips gently into balance, one holographic tag glowing above the ledger."}

C. Article: "Global luxury car market hits new high"
{"family": "artifact", "headline": "Motion Has Never Been Worth More", "layout": "art_with_data", "data_elements": [{"value": "CAR HALL", "label": ""}], "environment": "marble_table", "camera": "close_up_macro", "energy": "quiet_prestige", "mood_accent": "gold_teal", "hall_theme": "car", "subject_scene": "A sculptural brass automobile model rests on black marble, candlelight catching its curves, with faint teal constellation lines tracing its silhouette and a small engraved plaque beside it."}

D. Article: "Survey: users abandoning casino dApps for skill-based games"
{"family": "contrast", "headline": "Luck Fades. Skill Compounds.", "layout": "art_only", "data_elements": [], "environment": "grand_hall", "camera": "eye_level_wide", "energy": "dramatic_tension", "mood_accent": "gold_vs_mono", "hall_theme": "none", "subject_scene": "On the left, monochrome motion-blurred slot machines and frantic figures dissolve into noise; on the right, a still golden Art Deco hall where composed guests in evening wear study a glowing registry board, a clean marble seam dividing the two worlds."}

E. Article: "Car Hall winner announced"
{"family": "society", "headline": "The Pot Found Its Owner", "layout": "art_with_data", "data_elements": [{"value": "CAR HALL", "label": ""}], "environment": "grand_hall", "camera": "eye_level_wide", "energy": "ceremonial_awe", "mood_accent": "gold_teal", "hall_theme": "car", "subject_scene": "A spotlight falls on an applauded winner in evening dress beside a veiled sculptural automobile in a grand Art Deco hall, golden confetti light drifting down, with one holographic plaque glowing softly nearby."}

F. Article: "What happens at the final reveal?"
{"family": "doors", "headline": "Every Pot Finds Its Owner", "layout": "art_with_data", "data_elements": [{"value": "EXACT", "label": ""}, {"value": "FIRST", "label": ""}, {"value": "CLOSEST", "label": ""}], "environment": "door_corridor", "camera": "one_point_symmetry", "energy": "quiet_prestige", "mood_accent": "gold", "hall_theme": "none", "subject_scene": "Three arched marble doors recede down a candlelit corridor, each engraved with a single word above its frame, a golden light-path splitting across the floor toward them with the leftmost door glowing warmly open."}
""".strip(),
        'extra_banned_subject_terms': [
            'rolex', 'patek philippe', "sotheby's", 'sothebys', "christie's", 'christies',
            'rolls-royce', 'rolls royce', 'ferrari', 'lamborghini', 'wallet address',
        ],
    },
    'Meta Coin Guard': {
        'brand_name': 'Meta Coin Guard',
        'brand_tagline': 'a parametric on-chain cover protocol for Web3 -- translucent engineered glass, '
                         'dark steel platforms, and glowing circuit networks define a world where rules '
                         'are written before volatility arrives',
        'headline_max_words': 7,
        'headline_uppercase': True,
        'mood_accent_default': 'teal',
        'mood_accent_restricted': {'teal_vs_red': {'families': ['threat_vs_guard'], 'environments': ['void_storm', 'ruin_contrast']}},
        'environment_restricted': {
            'void_storm': {'energies': ['storm_tension'], 'families': ['threat_vs_guard']},
            'ruin_contrast': {'energies': ['storm_tension'], 'families': ['threat_vs_guard']},
        },
        'data_element_template': 'a glowing panel or glass surface displaying "{value}"{label_part}',
        'data_element_label_template': ' labeled "{label}"',
        'legibility_line': "All text is large, bold, crisp and clearly legible.",
        'anti_repetition_rules': (
            "Hard rules: do not repeat the same family more than 2 times in a row; do not use "
            "'threat_vs_guard' more than 2 times in any 4 consecutive posts; do not use the "
            "'glass_dark' finish more than 4 times in a row; use the 'guardian' family at most "
            "once every 8 posts; use the 'left_block' headline_layout roughly 1 in 3 posts; "
            "the shield motif should appear in some form in every post; include a glass/transparent "
            "structure in at least 3 of every 4 posts."
        ),
        'frozen_style': {
            'format': "vertical 4:5 editorial poster set in a security-infrastructure world of translucent "
                      "engineered glass, dark steel platforms, and glowing circuit networks -- clean 3D product "
                      "visualization aesthetic, NOT photorealistic and NOT cartoon",
            'palette': "near-black charcoal base, with teal/cyan glow as the primary accent (shield outlines, "
                       "conduit traces, protected states) and purple/violet as the secondary accent (brand "
                       "shield icon, energy cores, headline gradients); headline type fades from white to "
                       "purple or from white to sage-green. Red/crimson is permitted only as the threat color "
                       "-- crashes, shattering, ruins -- and never represents the brand itself. Gold/bronze "
                       "appears only on coins, premium badges, or ranking numbers",
            'materials': "translucent engineered glass with visible circuit-board internals (the signature "
                         "material), dark gunmetal steel platforms and pedestals, circuit-board floor surfaces "
                         "with teal trace lines, teal neon conduit tubes, server rack corridors, polished "
                         "dark composite surfaces",
            'rendering': "clean high-contrast stylized 3D product-visualization with cinematic rim-lighting "
                         "in teal and purple; dark dramatic shadows; glass objects are transparent and "
                         "luminous, not frosted or blurry; no humans except the faceless armored Guardian "
                         "figure or anonymous silhouettes in conceptual scenes",
            'background_vocab': "the shield motif is the brand's universal anchor -- a 3D metallic shield, "
                                 "a glowing teal outline, a glass shield frame, or an embossed badge -- "
                                 "alongside circuit-board terrain, teal conduit lines connecting structures, "
                                 "and server-rack corridor environments",
            'headline_zone': "the headline is set in bold geometric sans-serif UPPERCASE type, white or "
                             "fading from white to purple, positioned centered in a top zone or stacked "
                             "in a left-aligned editorial block",
            'never': "no frosted/blurry glassmorphism (glass must be CLEAR and transparent), no gold "
                     "Art Deco or classical luxury, no wireframe-only voids, no daylight or white "
                     "backgrounds, no casual or cartoon style, no recognizable real people, no real "
                     "logos, no paragraphs of text, no micro-labels",
        },
        'metaphors': {
            "protection / the Guard": "a shield -- 3D metallic, glowing teal outline, translucent glass form, or embossed badge",
            "the protocol / rules": "a terminal window with short glowing code, or engraved logic lines on a glass panel",
            "threat / volatility / crashes": "shattering glass objects, falling red candlestick charts, crumbling structures "
                                              "with red embers, or collapsing dominoes",
            "time pressure / missed moment": "a shattering hourglass with glass shards and spilling sand",
            "custody risk / drained funds": "a breached vault or crumbling institutional building leaking red light",
            "user's assets / wallet": "a dark leather-and-metal wallet with a glowing shield emblem, or a sealed case",
            "non-custodial / user control": "the wallet standing untouched outside the vault, with no key held by anyone",
            "on-chain verification / audit": "a glowing green checkmark seal, a verified badge, or teal scan lines",
            "liquidity / capital flows": "a translucent glass wave or flowing teal light streams",
            "oracle / data feeds": "luminous data conduits feeding a console, teal energy streams, or price tickers on dark panels",
            "monitoring / transparency": "a holographic command table, transparent glass structures with visible internals",
            "plans / tiers": "glass-and-steel blocks in ascending steps, or metal shield badges in silver, gold, and platinum",
            "discipline / structure": "a calm figure or shield standing solid while chaos surrounds it",
            "the platform / app": "a dark UI card showing wallet balance and green checkmark, framed by a glass shield",
        },
        'families': {
            'shield_hero': {
                'name': "SHIELD HERO",
                'skeleton': "ONE large shield dominates the frame as the central hero object -- it can be a "
                            "3D metallic shield, a glowing teal shield outline, or a translucent glass shield "
                            "with visible circuitry inside -- sitting on a dark steel pedestal or platform, "
                            "with teal conduit traces converging toward it and a circuit-board floor beneath.",
                'text_policy': "Headline plus at most 1 short label or value displayed on the shield face "
                               "(e.g. 'YOUR GUARD', a percentage, or 1-4 words). Prefer art_only.",
                'default_axes': {'environment': 'steel_platform', 'camera': 'low_angle_hero', 'energy': 'calm_structure', 'finish': 'glass_dark'},
                'data_budget': 1,
            },
            'threat_vs_guard': {
                'name': "THREAT vs GUARD",
                'skeleton': "A two-zone confrontation in flexible geometry (left/right, top/bottom, or "
                            "background/foreground): one zone is the THREAT -- shattering glass objects, "
                            "crashing red candlestick charts, crumbling structures with red embers or "
                            "smoke, collapsing dominoes, or a breached vault; the other zone is the GUARD "
                            "-- an intact shield, a transparent glass structure, or a calm wallet on a "
                            "platform, rendered in teal and purple, always visually heavier and more stable "
                            "than the chaos beside it.",
                'text_policy': "Headline plus at most 2 short zone labels (1-3 words each, e.g. 'MARKET PRICE' / "
                               "'DECLARED VALUE'). Labels on the threat side may name the threat.",
                'default_axes': {'environment': 'void_storm', 'camera': 'dutch_or_split', 'energy': 'storm_tension', 'finish': 'glass_dark'},
                'data_budget': 2,
            },
            'glass_fortress': {
                'name': "GLASS FORTRESS",
                'skeleton': "A large translucent glass-and-steel architectural structure -- a glass cube "
                            "building, a transparent server tower, or a crystal citadel -- with visible "
                            "circuit-board internals and teal energy flowing through its transparent walls. "
                            "The structure may have the MCG shield emblem embedded in or floating above it. "
                            "Often shown at monumental scale from a low angle.",
                'text_policy': "Headline plus at most 2 short labels on glass panels (e.g. 'Transparent', "
                               "'Autonomous'). Labels appear as floating holographic tags.",
                'default_axes': {'environment': 'server_corridor', 'camera': 'low_angle_hero', 'energy': 'calm_structure', 'finish': 'glass_bright'},
                'data_budget': 2,
            },
            'plan_blocks': {
                'name': "PLAN BLOCKS",
                'skeleton': "2-3 engineered glass-and-steel blocks stand on circuit-board terrain, arranged "
                            "in a row or as ascending steps; each block is a translucent glass platform "
                            "with teal or purple internal glow, carrying one large value and one short "
                            "label; a coin badge or shield may hover above the key block.",
                'text_policy': "Headline plus at most 3 value+label pairs. Values are 1-6 characters; "
                               "labels are 1-2 words. Each pair isolated on its own block face, rendered large.",
                'default_axes': {'environment': 'circuit_terrain', 'camera': 'isometric_high', 'energy': 'calm_structure', 'finish': 'glass_dark'},
                'data_budget': 3,
            },
            'protocol_flow': {
                'name': "PROTOCOL FLOW",
                'skeleton': "A horizontal three-node sequence connected by glowing teal arrows or conduit "
                            "lines -- three translucent glass cards, three icons on pedestals, or three "
                            "holographic stages -- each step represented by an icon or UI element "
                            "(wallet, token, smart contract, shield) showing a process left to right.",
                'text_policy': "Headline plus at most 3 step labels of 1-3 words (e.g. 'GUARD ACTIVATED', "
                               "'MARKET MOVES', 'PROTOCOL EXECUTES').",
                'default_axes': {'environment': 'steel_platform', 'camera': 'frontal_wide', 'energy': 'calm_structure', 'finish': 'glass_dark'},
                'data_budget': 3,
            },
            'code_terminal': {
                'name': "CODE TERMINAL",
                'skeleton': "A terminal window or stack of rule-notification panels floats as the hero "
                            "element, framed by the MCG shield outline or embedded in a glass structure; "
                            "the panels have purple neon borders and show short rule text or pseudo-code "
                            "lines; thin data threads connect the terminal to the environment.",
                'text_policy': "Headline plus at most 3 lines of short rule text or pseudo-code (each <=6 "
                               "words). Each rule panel is its own visual element with an icon.",
                'default_axes': {'environment': 'server_corridor', 'camera': 'frontal_terminal', 'energy': 'calm_structure', 'finish': 'glass_dark'},
                'data_budget': 3,
            },
            'dashboard': {
                'name': "DASHBOARD",
                'skeleton': "A dark UI card or app mockup sits centrally, showing a wallet balance or "
                            "Guard status with a green checkmark; the card is framed by a translucent "
                            "glass shield structure; floating badges around it display key parameters "
                            "(token, duration, plan); teal energy waves or conduit lines flow in the "
                            "background.",
                'text_policy': "Headline plus at most 3 floating badge labels (1-3 words each, e.g. "
                               "'Token: INS', 'Guard Plan: X', 'Duration: 4 months').",
                'default_axes': {'environment': 'steel_platform', 'camera': 'frontal_wide', 'energy': 'calm_structure', 'finish': 'glass_bright'},
                'data_budget': 3,
            },
            'guardian': {
                'name': "THE GUARDIAN",
                'skeleton': "The anonymous armored sentinel -- sleek dark armor with teal accent lines "
                            "and a reflective visor, no visible face -- stands calm on a raised platform "
                            "or pedestal; an optional three-node timeline or shield projection appears "
                            "beside or behind the figure; circuit-board floor and dark environment.",
                'text_policy': "Headline plus at most 2 short labels (timeline nodes or one tag).",
                'default_axes': {'environment': 'steel_platform', 'camera': 'low_angle_hero', 'energy': 'calm_structure', 'finish': 'glass_dark'},
                'data_budget': 2,
            },
        },
        'axes': {
            'environment': {
                'steel_platform':  "The setting is a dark polished steel platform or pedestal, with "
                                   "circuit-board traces in the floor and teal conduit lines at the edges.",
                'server_corridor': "The setting is a corridor of glowing server racks receding into the "
                                   "distance, with teal and purple rim-lighting on the rack surfaces.",
                'circuit_terrain': "The setting is a vast landscape of circuit-board terrain stretching "
                                   "to the horizon, with teal trace lines glowing like city grids.",
                'console_deck':    "The setting is a dark operations room centered on a holographic "
                                   "command table or glass platform.",
                'void_storm':      "The setting is dark space with fragments of shattering glass and "
                                   "falling red chart candles, smoke and crimson embers.",
                'ruin_contrast':   "The setting splits: one side shows crumbling institutional buildings "
                                   "or rusted structures with red glow; the other side shows clean glass "
                                   "and teal-lit infrastructure.",
            },
            'camera': {
                'low_angle_hero':   "The camera looks up at the central object or figure from a low angle, "
                                    "making it feel monumental.",
                'isometric_high':   "The camera is a high analytical three-quarter isometric view.",
                'frontal_wide':     "The camera is a flat-on cinematic wide shot, symmetrical.",
                'frontal_terminal': "The camera faces the terminal or panel stack directly, centered.",
                'dutch_or_split':   "The camera uses a tilted angle or a two-zone split framing for "
                                    "confrontation.",
                'close_up_detail':  "The camera is in close-up on the glass surface detail, showing "
                                    "circuit internals and light refractions.",
            },
            'energy': {
                'calm_structure': "The lighting is still, ordered and confident -- clean teal and purple "
                                  "rim-lights on glass and metal.",
                'storm_tension':  "The threat is active -- red light, volumetric haze, shattering glass "
                                  "and falling chart candles charge the scene.",
                'ascendant':      "The light is rising upward, with a sense of scale reveal and growth, "
                                  "teal energy flowing upward through glass structures.",
            },
            'mood_accent': {
                'teal':        "The dominant accent color throughout the scene is teal/cyan.",
                'teal_purple': "The dominant accent blends teal/cyan with purple/violet, for "
                               "brand-core or shield-led scenes.",
                'teal_vs_red': "The scene contrasts teal and purple on the Guard's side against "
                               "red/crimson on the threat side.",
            },
            'finish': {
                'glass_dark':   "The dominant finish is dark gunmetal with translucent glass elements "
                                "glowing from within, deep shadows and neon accents.",
                'glass_bright': "The dominant finish emphasizes the glass transparency -- brighter, "
                                "more luminous, with teal and purple light filling the glass structures.",
            },
            'headline_layout': {
                'centered_top': "the headline is centered in a clean top zone of the frame.",
                'left_block':   "the headline is stacked in a left-aligned editorial block.",
            },
        },
        'routing_table': """
News category -> Primary family (fallback):
- Hacks / exploits / drained protocols -> threat_vs_guard (fallback: shield_hero)
- Market crashes / volatility spikes -> threat_vs_guard (fallback: shield_hero)
- Smart-contract security / audits -> code_terminal (fallback: glass_fortress)
- Rule-based / automated settlement -> code_terminal (fallback: protocol_flow)
- Non-custodial design / user control -> shield_hero (fallback: glass_fortress)
- Wallet monitoring / on-chain visibility -> dashboard (fallback: code_terminal)
- Oracle reliability / price feeds -> dashboard (fallback: code_terminal)
- DeFi metrics / TVL / fees -> plan_blocks (fallback: dashboard)
- Policy / regulation / sanctions -> threat_vs_guard in glass_bright finish (fallback: glass_fortress)
- Institutional Web3 adoption -> glass_fortress in glass_bright finish (fallback: shield_hero)
- Multi-chain / protocol expansion -> glass_fortress (fallback: dashboard)
- How-it-works / plans / mechanics -> protocol_flow (fallback: code_terminal)
- Plan comparisons / tiers / pricing -> plan_blocks (fallback: protocol_flow)
- Psychology / discipline / panic -> guardian (fallback: threat_vs_guard)
- Product / app features / UX -> dashboard (fallback: protocol_flow)
- Anything ambiguous -> shield_hero

Tie-breakers: prefer the family NOT used in the last 3 posts (see anti-repetition notes below). If still
tied, prefer the lower-risk family -- shield_hero is the safest universal fallback. The threat_vs_guard
family will naturally dominate given the security news flow; the anti-repetition rules keep it from
monopolizing the feed.
""".strip(),
        'text_rules': """
1. Headline: 7 words or fewer, bold UPPERCASE sans, white or fading to purple or sage-green.
   Avoid hard-to-spell proper nouns; refer to protocols and companies by concept (e.g. THE BRIDGE EXPLOIT,
   not the protocol's name) -- this also avoids implying accusations on developing incident news. Tickers
   (BTC, ETH, SOL) are safe to use.
2. In-scene text budget per family: shield_hero <=1 label, threat_vs_guard <=2 zone labels, plan_blocks <=3
   value+label pairs, code_terminal <=3 rule lines (<=6 words each), protocol_flow <=3 step labels,
   glass_fortress <=2 holo labels, dashboard <=3 badge labels, guardian <=2 labels.
3. Values are 1-6 characters; labels are 1-3 words; render every string large on its own clean glass or
   steel surface.
4. Sub-headlines are not generated in-image; they belong to the overlay layer, not the prompt.
5. Never render wallet addresses, dense dashboards, readable candlestick charts, or paragraphs of text.
""".strip(),
        'fallback_brief': {
            'family': 'shield_hero',
            'headline': 'THE GUARD HOLDS',
            'layout': 'art_only',
            'data_elements': [],
            'environment': 'steel_platform',
            'camera': 'low_angle_hero',
            'energy': 'calm_structure',
            'mood_accent': 'teal',
            'finish': 'glass_dark',
            'headline_layout': 'centered_top',
            'subject_scene': (
                "A translucent glass shield with visible circuit-board internals stands on a dark "
                "polished steel pedestal, glowing with teal light from within, teal conduit traces "
                "converging toward it across the circuit-board floor, server rack silhouettes fading "
                "into shadow behind it."
            ),
        },
        'brief_examples': """
Worked examples (for guidance only -- do not copy headlines or scenes verbatim):

A. Article: "Bridge protocol exploited for $120M"
{"family": "threat_vs_guard", "headline": "PROTOCOLS FALL, RULES DON'T", "layout": "art_with_data", "data_elements": [{"value": "$120M", "label": "DRAINED"}], "environment": "ruin_contrast", "camera": "dutch_or_split", "energy": "storm_tension", "mood_accent": "teal_vs_red", "finish": "glass_dark", "headline_layout": "centered_top", "subject_scene": "The left side shows crumbling server structures with red ember glow and smoke, labeled panels falling from rusted walls; the right side shows the MCG shield standing intact on a clean glass platform connected by teal conduit lines, transparent glass panels with visible circuitry glowing steadily behind it."}

B. Article: "Major audit firm publishes smart-contract security report"
{"family": "code_terminal", "headline": "CLEAR RULES FAVOR CLEAR CODE", "layout": "art_with_data", "data_elements": [{"value": "verify", "label": ""}, {"value": "execute", "label": ""}, {"value": "settle", "label": ""}], "environment": "server_corridor", "camera": "frontal_terminal", "energy": "calm_structure", "mood_accent": "teal_purple", "finish": "glass_dark", "headline_layout": "left_block", "subject_scene": "A stack of three glass-and-steel rule panels with purple neon borders floats within the outline of the MCG shield, each panel showing a short glowing line of text with a small icon, thin teal data threads anchoring the panels to the server racks behind them."}

C. Article: "DeFi TVL hits $200B milestone"
{"family": "plan_blocks", "headline": "THE FLOOR JUST GOT HIGHER", "layout": "art_with_data", "data_elements": [{"value": "$200B", "label": "TVL"}, {"value": "+40%", "label": "YOY"}], "environment": "circuit_terrain", "camera": "isometric_high", "energy": "ascendant", "mood_accent": "teal_purple", "finish": "glass_dark", "headline_layout": "centered_top", "subject_scene": "Two translucent glass-and-steel blocks stand on circuit-board terrain in ascending steps, each block glowing with teal internal light and carrying a large value on its face, a purple shield badge hovering above the taller block, teal conduit traces connecting the blocks along the ground."}

D. Article: "How the parametric cover protocol works"
{"family": "protocol_flow", "headline": "STRUCTURE BEFORE VOLATILITY", "layout": "art_with_data", "data_elements": [{"value": "ACTIVATE", "label": ""}, {"value": "MONITOR", "label": ""}, {"value": "EXECUTE", "label": ""}], "environment": "steel_platform", "camera": "frontal_wide", "energy": "calm_structure", "mood_accent": "teal", "finish": "glass_dark", "headline_layout": "centered_top", "subject_scene": "Three translucent glass cards sit in a horizontal row on a dark steel platform, connected by glowing teal arrows, the first card showing a wallet icon, the second a pulse monitor, the third a shield with checkmark, each card glowing faintly from within with circuit-board patterns visible through the glass."}

E. Article: "Why panic selling costs more than the drop"
{"family": "guardian", "headline": "PANIC IS THE EXPENSIVE PART", "layout": "art_only", "data_elements": [], "environment": "steel_platform", "camera": "low_angle_hero", "energy": "calm_structure", "mood_accent": "teal_purple", "finish": "glass_dark", "headline_layout": "centered_top", "subject_scene": "The anonymous armored sentinel stands motionless on a raised dark platform, sleek dark armor with teal accent lines and a reflective visor, a faint three-node timeline glowing behind it with teal dots connected by a horizontal line, circuit-board floor beneath and server rack silhouettes in the background."}

F. Article: "New wallet-monitoring dashboard launches"
{"family": "dashboard", "headline": "WHEN MARKETS MOVE FAST, RULES MATTER", "layout": "art_with_data", "data_elements": [{"value": "INS", "label": "Token"}, {"value": "4 mo", "label": "Duration"}], "environment": "steel_platform", "camera": "frontal_wide", "energy": "calm_structure", "mood_accent": "teal_purple", "finish": "glass_bright", "headline_layout": "centered_top", "subject_scene": "A dark UI card showing a wallet balance with a glowing green checkmark sits centrally, framed by a translucent glass shield structure with visible circuitry, floating glass badges around it display parameters, teal energy waves flowing through the background."}
""".strip(),
        'extra_banned_subject_terms': [
            'frosted glass', 'blurry glass', 'art deco', 'chandelier', 'marble', 'gatsby',
            'wallet address', 'gold luxury',
        ],
    },
    'ChainReporter': {
        'brand_name': 'ChainReporter',
        'brand_tagline': "a crypto news media outlet built on ten rotating editorial visual formats -- not "
                         "one house style, but a magazine that picks the cover treatment each story needs",
        'core_axes': ('stage', 'composition', 'energy', 'accent'),
        'headline_max_words': 7,
        'meme_enabled': False,
        'mood_accent_default': 'cr_signal',
        'mood_accent_restricted': {'free': {'families': ['type_led', 'art_drop', 'meme']}},
        'axis_companion_field': {'story_color': 'accent_justification'},
        'passthrough_fields': ['accent_justification', 'art_style'],
        'passthrough_field_schema': {
            'accent_justification': '"" unless accent is "story_color" -- 1 short phrase naming the specific story color and why',
            'art_style': '"" unless family is "art_drop" -- a short description of this post\'s rotating illustration style; must differ from recent art_style values below',
        },
        'no_text_mode': 'art_drop',
        'no_text_line': "No text, no letters, no numbers anywhere in the image.",
        'data_element_template': 'a clean tile or label displaying "{value}"{label_part}',
        'data_element_label_template': ' with the micro-label "{label}"',
        'legibility_line': "All text is large, crisp and clearly legible.",
        'anti_repetition_rules': (
            "Hard rules: do not repeat the same family more than 2 times in a row; 'duotone' may not "
            "exceed 3 of any 5 consecutive posts; 'art_drop' art_style must not repeat within 5 posts; "
            "'meme' at most 1 in 6 posts even when enabled; 'stat_card' at most 1 in 5 posts; the "
            "'cr_signal' accent must appear in at least 1 of every 3 posts."
        ),
        # §0 — Frozen brand layer: never varies, never touches an LLM. Applies to every mode.
        'frozen_style': {
            'format': "vertical 4:5 editorial poster for a crypto news media outlet",
            'palette': "one dominant accent color per post plus neutrals -- the accent can be any color, "
                       "but the image never uses many colors at once",
            'materials': "premium, mode-appropriate materials and surfaces -- glass, metal, paper, paint or "
                         "photographic textures -- never generic stock-photo or default-AI-render textures",
            'rendering': "exchange-marketing-grade craft: controlled lighting, intentional composition, one "
                         "focal idea per image (a single hero object, a single number, a single concept, or "
                         "a single joke)",
            'background_vocab': "clean modern sans-serif typography by default, with deliberate serif or "
                                 "mono type only where the mode calls for it; numbers always render biggest",
            'headline_zone': "the headline sits in a clean, uncluttered zone with no competing detail behind it",
            'never': "generic AI-slop aesthetics (glowing humanoid robots, busy neon collages), dense "
                     "disclaimers or microtext, more than 3 text elements, watermarks, or recognizable real "
                     "people generated by AI",
        },
        # §0 metaphor library — common crypto-news beats mapped to visual choices.
        'metaphors': {
            "price moves / market records": "a single giant accent-colored numeral, or a duotone "
                "chart-and-coin treatment with directional geometry (rising arcs for gains, falling shards "
                "for drops)",
            "hacks / exploits / security incidents": "fractured, cracked or shattering geometry under tense "
                "lighting, with a story-justified accent color for the protocol involved",
            "regulation / enforcement / policy": "a monochrome federal facade, seal, gavel or courthouse, "
                "with sweeping accent-color ring or panel geometry",
            "launches / listings / products": "one premium 3D hero object -- coin medallion, glass device, "
                "rocket, or sculptural logo -- on a clean stage",
            "partnerships / integrations / M&A": "two emblem medallions joined by a connector -- a bridge, "
                "a cross, or a light-spark",
            "protocol mechanics / governance / how-it-works": "a flat or isometric diagram -- stacked "
                "layers, connected nodes, or a simple machine",
            "weekly recaps / multi-stat reports": "a card-grid of stat tiles anchored by one hero 3D object",
            "announcements / statements / deep dives": "typography as the design -- huge type, minimal imagery",
            "person-centric stories (CEOs, regulators, founders)": "route to duotone with an object/scene "
                "metaphor (the gavel, the building, the seal) standing in for the person -- never a "
                "generated face",
            "daily price / mood / evergreen posts": "a standalone artwork in a rotating style with one "
                "crypto motif (a coin, chain link, or Bitcoin glyph) embedded naturally, with zero "
                "in-image text",
        },
        # §1 — Visual modes M1-M10, mapped to snake_case family keys.
        'families': {
            'duotone': {
                'name': "DUOTONE EDITORIAL",
                'skeleton': "A black-and-white photographic or photo-real subject -- an object, building, or "
                            "scene, never a generated face -- fills the frame, with ONE accent-color "
                            "geometric treatment overlaid as a color-split background, duotone wash, or "
                            "large sweeping rings or diagonal panels that interact with the subject.",
                'text_policy': "Headline only, art_only layout.",
                'default_axes': {'stage': 'photo_real', 'composition': 'full_bleed_photo', 'energy': 'newsroom_neutral', 'accent': 'cr_signal'},
                'data_budget': 0,
                'headline_treatment': "set in a clean overlay bar across the lower third, or a left-aligned editorial block",
            },
            'big_number': {
                'name': "BIG NUMBER POSTER",
                'skeleton': "A dark or single-color field holds ONE giant figure rendered in the accent "
                            "color, dominating at least 30% of the frame height, with a short supporting "
                            "line beneath it; abstract geometric or logo-derived shapes decorate the "
                            "corners, and optionally one floating 3D token or object anchors a corner.",
                'text_policy': "One giant value (1-7 characters) plus one short supporting line (<=6 words). "
                               "The value dominates the frame.",
                'default_axes': {'stage': 'studio_dark', 'composition': 'centered_hero', 'energy': 'celebratory', 'accent': 'cr_signal'},
                'data_budget': 1,
                'headline_treatment': "the giant numeral dominates the frame; the headline is set small above or below it",
            },
            'hero_object': {
                'name': "HERO OBJECT 3D",
                'skeleton': "One premium 3D object -- a coin medallion, glass device, vault, rocket, or "
                            "sculptural logo -- sits on a clean stage, rendered in glossy glass or metal "
                            "materials with controlled studio reflections.",
                'text_policy': "Headline plus at most one short label or value near the object.",
                'default_axes': {'stage': 'gradient_sweep', 'composition': 'centered_hero', 'energy': 'celebratory', 'accent': 'cr_signal'},
                'data_budget': 1,
                'headline_treatment': "set in a clean zone above or beside the object, modest scale",
            },
            'concept_photo': {
                'name': "CONCEPT PHOTO / CAMPAIGN",
                'skeleton': "A single striking photo-real scene -- a landmark, sky, or symbolic object in "
                            "the world, never an identifiable generated face -- fills the frame with "
                            "generous negative space, evoking political-ad or brand-campaign energy.",
                'text_policy': "Headline only, short and declarative (5 words or fewer ideal).",
                'default_axes': {'stage': 'photo_real', 'composition': 'full_bleed_photo', 'energy': 'newsroom_neutral', 'accent': 'cr_signal'},
                'data_budget': 0,
                'headline_treatment': "set small in the negative space as a minimal declarative tagline",
                'headline_uppercase': False,
            },
            'flat_explainer': {
                'name': "FLAT EXPLAINER",
                'skeleton': "A flat-vector or isometric illustration in a limited 2-3 color palette renders "
                            "one diagrammatic concept -- stacked layers, connected nodes, or a simple "
                            "machine -- with clean shapes and a friendly but precise tone.",
                'text_policy': "Headline plus at most 2 short labels (1-3 words each) inside the "
                               "illustration; diagram content is otherwise abstract.",
                'default_axes': {'stage': 'flat_field', 'composition': 'isometric', 'energy': 'newsroom_neutral', 'accent': 'story_color'},
                'data_budget': 2,
                'headline_treatment': "set in a clean horizontal band above the illustration",
            },
            'type_led': {
                'name': "TYPE-LED MINIMAL",
                'skeleton': "Typography is the design. Pick one sub-variant and describe it explicitly in "
                            "the subject: brutalist dark (huge white sans on black plus one 3D chrome "
                            "detail), gallery-light (a chrome or silver object on off-white with small "
                            "type), editorial serif (elegant serif over a single macro-photo texture), or "
                            "retro-mono (line art with spaced capitals).",
                'text_policy': "Headline (may render very large) plus at most one sub-element (a kicker "
                               "word or small badge).",
                'default_axes': {'stage': 'studio_dark', 'composition': 'left_type_block', 'energy': 'newsroom_neutral', 'accent': 'free'},
                'data_budget': 1,
                'headline_treatment': "may render very large, filling much of the frame",
            },
            'art_drop': {
                'name': "ART DROP",
                'skeleton': "Standalone artwork in a deliberately rotating style -- painterly illustration, "
                            "dramatic black-and-white portrait-of-an-object, chalk or craft texture, cosmic "
                            "gradient, woodcut, or similar -- with one crypto motif (a coin, chain link, or "
                            "Bitcoin glyph) embedded naturally in the art.",
                'text_policy': "Zero in-image text. The headline and price live in the social copy, not the image.",
                'default_axes': {'stage': 'texture_macro', 'composition': 'full_bleed_photo', 'energy': 'playful', 'accent': 'free'},
                'data_budget': 0,
            },
            'meme': {
                'name': "MEME / PLAYFUL",
                'skeleton': "Whatever the joke needs -- a photoreal parody product shot, an absurdist photo "
                            "composite, or candy-colored cartoon imagery -- staying at a premium craft bar "
                            "while landing the visual joke in a single beat. Never use real brand marks or logos.",
                'text_policy': "At most one short text element if the joke requires it.",
                'default_axes': {'stage': 'photo_real', 'composition': 'centered_hero', 'energy': 'playful', 'accent': 'free'},
                'data_budget': 1,
                'headline_treatment': "a single short caption-style element, if used at all",
            },
            'stat_card': {
                'name': "STAT CARD",
                'skeleton': "A clean card-grid layout holds a title block plus 2-4 rounded stat tiles, each "
                            "carrying one icon, one value and one micro-label, anchored by one hero visual "
                            "element (a 3D object or illustration) in a corner.",
                'text_policy': "Headline plus at most 4 tiles, each a value plus a 1-2 word label. This is "
                               "the text-heaviest mode -- a hard ceiling.",
                'default_axes': {'stage': 'studio_light', 'composition': 'card_grid', 'energy': 'newsroom_neutral', 'accent': 'cr_signal'},
                'data_budget': 4,
                'headline_treatment': "a bold title block spans the top of the grid",
            },
            'lockup': {
                'name': "PARTNERSHIP LOCKUP",
                'skeleton': "Two emblem medallions or badges, each carrying an abstract glyph standing in "
                            "for a real logo, are joined by a connector device -- a bridge, an X-shaped "
                            "crossing, or a light spark -- on a clean stage; alternatively, one cinematic "
                            "backdrop carries both entity names typeset in an acquisition-style layout.",
                'text_policy': "Headline plus the two entity names as short labels (<=8 characters each) -- "
                               "the one place proper nouns appear in-image.",
                'default_axes': {'stage': 'gradient_sweep', 'composition': 'centered_hero', 'energy': 'celebratory', 'accent': 'cr_signal'},
                'data_budget': 2,
                'headline_treatment': "set above the medallions, with the entity names as two short labels beneath or beside them",
                'data_value_max_len': 8,
            },
        },
        # §3 — Variation axes: each value maps to a fixed sentence used by the assembler.
        'axes': {
            'stage': {
                'studio_dark':    "The setting is a dark or single-color studio field, evenly lit and uncluttered.",
                'studio_light':   "The setting is a bright, clean studio field in soft off-white or pale neutral tones.",
                'gradient_sweep': "The setting is a smooth soft-gradient sweep, like a seamless studio backdrop curving from floor to wall.",
                'photo_real':     "The setting is a photo-real environment -- a real-world object, building, or scene rendered with documentary realism.",
                'flat_field':     "The setting is a flat, evenly-lit field of color suited to vector or isometric illustration.",
                'texture_macro':  "The setting is an extreme close-up texture world -- paper, paint, woodgrain, or other tactile material filling the frame.",
            },
            'composition': {
                'centered_hero':    "The composition centers a single hero subject in the frame, symmetrical and commanding.",
                'left_type_block':  "The composition reserves the left portion of the frame for a stacked block of typography, with supporting imagery on the right.",
                'full_bleed_photo': "The composition is a full-bleed photographic frame, the subject filling the entire image with no visible borders.",
                'split_panel':      "The composition divides the frame into two panels -- left/right or top/bottom -- contrasting two halves of the story.",
                'isometric':        "The composition is a three-quarter isometric view, giving an ordered, diagrammatic perspective.",
                'card_grid':        "The composition arranges the frame as a grid of cards or tiles around a title block.",
            },
            'energy': {
                'newsroom_neutral': "The lighting and mood are calm, controlled and editorial -- a neutral newsroom register.",
                'celebratory':      "The lighting is bright and triumphant, with a sense of milestone and momentum.",
                'tension':          "The lighting is high-contrast and charged, with fractured or unstable elements conveying tension.",
                'playful':          "The lighting and mood are light, warm and playful.",
            },
            'accent': {
                'cr_signal':   "The dominant accent color throughout the scene is ChainReporter's signal red-orange.",
                'story_color': "The dominant accent color is justified by the story itself -- green for a "
                               "green protocol's hack, gold for a gold-backed token, blue for an "
                               "ocean-themed chain -- and the reason is named in the brief.",
                'free':        "The dominant accent color is chosen freely to suit this mode's rotating style, not tied to the brand accent.",
            },
        },
        # §2 — News-type -> mode routing guidance for the Art Director.
        'routing_table': """
News category -> Primary family (fallback):
- Regulation / enforcement / policy actions -> duotone (fallback: concept_photo)
- Policy statements / bills / "moment" framing -> concept_photo (fallback: duotone)
- Hacks / exploits / security incidents -> duotone, story-color accent (fallback: big_number)
- Market records / TVL / volumes / raises -> big_number (fallback: stat_card)
- Price moves / daily market posts -> art_drop, price in caption (fallback: big_number)
- Token launches / listings / products -> hero_object (fallback: big_number)
- Partnerships / integrations / M&A -> lockup (fallback: hero_object)
- Protocol upgrades / governance / votes -> flat_explainer (fallback: type_led)
- Explainers / education / guides -> flat_explainer (fallback: duotone)
- Company / people news (CEOs, funds, institutions) -> duotone (fallback: concept_photo)
- Macro / inflation / rates -> duotone or concept_photo (fallback: big_number)
- Weekly recap / report digests -> stat_card (fallback: type_led)
- Announcements / deep-dive promos -> type_led (fallback: hero_object)
- Memecoin / viral / light stories -> meme if enabled (fallback: art_drop)
- Anything ambiguous -> duotone

Tie-breakers: prefer the family NOT used in the last 3 posts; then prefer the lower-risk family --
duotone is the safest universal fallback.
""".strip(),
        # §4 items 1-4 — global text rules for the Art Director (item 5, the legibility line, is
        # appended deterministically by the assembler).
        'text_rules': """
1. Headline: 7 words or fewer. Treatment depends on the family (overlay bar in duotone, giant in
   big_number/type_led, minimal in concept_photo, absent in art_drop). Numbers and tickers are preferred
   over proper nouns; short famous names (BITCOIN, SEC) are fine in headlines, otherwise concept-phrase the
   story instead of naming a protocol.
2. In-image text budget by family: duotone headline only; big_number one giant value plus one short line;
   hero_object at most 1 label; concept_photo headline only; flat_explainer at most 2 labels; type_led
   headline plus 1 sub-element; art_drop ZERO; meme at most 1; stat_card at most 4 tiles; lockup 2 entity names.
3. Every text element sits in its own clean zone; values render large.
4. No real logos or trademarks in-image -- use abstract glyph stand-ins. Never generate the face of a real
   person -- route person-centric stories to duotone with an object/scene metaphor (the gavel, the building,
   the seal) instead of the person.
""".strip(),
        # Safe fallback brief used when the Art Director response is missing/invalid/banned.
        'fallback_brief': {
            'family': 'duotone',
            'headline': 'CRYPTO MARKETS MOVE',
            'layout': 'art_only',
            'data_elements': [],
            'stage': 'photo_real',
            'composition': 'full_bleed_photo',
            'energy': 'newsroom_neutral',
            'accent': 'cr_signal',
            'accent_justification': '',
            'art_style': '',
            'subject_scene': (
                "A black-and-white macro photograph of a chrome coin fills the frame, its surface catching "
                "cold studio light, while two giant signal-orange ring shapes sweep across the composition "
                "from opposite corners."
            ),
        },
        'brief_examples': """
Worked examples (for guidance only -- do not copy headlines or scenes verbatim):

A. Article: "SEC approves first crypto perps framework"
{"family": "duotone", "headline": "THE DOOR OPENS FOR CRYPTO PERPS", "layout": "art_only", "data_elements": [], "stage": "photo_real", "composition": "full_bleed_photo", "energy": "newsroom_neutral", "accent": "cr_signal", "accent_justification": "", "art_style": "", "subject_scene": "A monochrome photographic close-up of a classical federal building facade fills the frame, its columns rendered in cold black-and-white; two giant signal-orange rings sweep across the composition from opposite corners, one passing behind the columns and one in front."}

B. Article: "Uniswap does $100M volume on Polygon in 24h"
{"family": "big_number", "headline": "$100M IN A SINGLE DAY", "layout": "art_with_data", "data_elements": [{"value": "$100M+", "label": "24H VOLUME"}], "stage": "studio_dark", "composition": "centered_hero", "energy": "celebratory", "accent": "story_color", "accent_justification": "Polygon violet, since the volume happened on the Polygon network", "art_style": "", "subject_scene": "A near-black studio field holds one giant violet figure reading $100M+ dominating the upper half of the frame, with a cluster of small violet dots scattered along the bottom edge."}

C. Article: "Daily Bitcoin price post -- $76,940"
{"family": "art_drop", "headline": "BITCOIN AT $76,940", "layout": "art_only", "data_elements": [], "stage": "texture_macro", "composition": "full_bleed_photo", "energy": "playful", "accent": "free", "accent_justification": "", "art_style": "vintage botanical engraving", "subject_scene": "A Bitcoin coin is rendered as the head of a sunflower, its petals radiating outward in fine engraved linework, surrounded by detailed botanical leaves and stems in the style of a 19th-century natural history print."}

D. Article: "Chainlink integrates with major L2"
{"family": "lockup", "headline": "A NEW DATA BRIDGE GOES LIVE", "layout": "art_with_data", "data_elements": [{"value": "LINK", "label": ""}, {"value": "L2NAME", "label": ""}], "stage": "gradient_sweep", "composition": "centered_hero", "energy": "celebratory", "accent": "cr_signal", "accent_justification": "", "art_style": "", "subject_scene": "Two chrome medallions, each engraved with an abstract geometric glyph, sit side by side on a soft gradient stage, joined by a glowing signal-orange light-bridge arcing between them."}

E. Article: "How restaking actually works"
{"family": "flat_explainer", "headline": "RESTAKING, EXPLAINED", "layout": "art_with_data", "data_elements": [{"value": "STAKE", "label": ""}, {"value": "EARN", "label": ""}], "stage": "flat_field", "composition": "isometric", "energy": "newsroom_neutral", "accent": "story_color", "accent_justification": "teal and white, a calm two-color palette suited to a clean technical explainer", "art_style": "", "subject_scene": "Three flat translucent slabs are stacked in isometric perspective, with small coin shapes flowing in a cycle between them via simple arrows, rendered in a clean two-color illustration style."}

F. Article: "Weekly market recap: 4 key numbers"
{"family": "stat_card", "headline": "THE WEEK IN NUMBERS", "layout": "art_with_data", "data_elements": [{"value": "+4.2%", "label": "BTC"}, {"value": "+6.8%", "label": "ETH"}, {"value": "$182B", "label": "TVL"}, {"value": "+38%", "label": "TOP GAINER"}], "stage": "studio_light", "composition": "card_grid", "energy": "newsroom_neutral", "accent": "cr_signal", "accent_justification": "", "art_style": "", "subject_scene": "A bright off-white studio field holds a grid of four rounded stat tiles beneath a bold title block, each tile carrying one icon and one large value, with a small 3D chart-arrow object anchoring the bottom-right corner."}

G. Article: "DOGE pumps 40% on viral moment" (only reachable if meme_enabled is turned on)
{"family": "meme", "headline": "DOGE GOES TO THE MOON, LITERALLY", "layout": "art_only", "data_elements": [], "stage": "photo_real", "composition": "centered_hero", "energy": "playful", "accent": "story_color", "accent_justification": "earthlight green, matching the rising chart in the joke", "art_style": "", "subject_scene": "A photoreal shiba inu in a tiny astronaut suit sits calmly on the lunar surface sipping from a coffee cup, while a glowing green candlestick chart rises across the dark sky behind it, lit by soft earthlight."}
""".strip(),
        'extra_banned_subject_terms': [
            'frosted glass', 'glassmorphism', 'wireframe cube',
            'art deco', 'gold veining', 'chandelier', 'gatsby',
            'gunmetal',
            'real logo', 'real person', 'looks like',
        ],
    },
}
