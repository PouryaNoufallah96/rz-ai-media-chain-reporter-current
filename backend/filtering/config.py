# ── Tunables ───────────────────────────────────────────────────────────────────
DEDUP_COSINE        = 0.92   # cosine ≥ this → same event
DEFAULT_THRESHOLD   = 0.32   # min routing cosine for normal brands
CATCHALL_THRESHOLD  = 0.24   # lower threshold for ChainReporter catch-all
TOP_N_PER_BRAND     = 10     # survivors sent to the AI stage per brand
EMBED_BATCH         = 128    # texts per OpenAI embeddings API request

# ── Source authority scores (0-100; unknown → 55) ──────────────────────────────
SOURCE_AUTHORITY = {
    'The Block':       92,
    'CoinDesk':        90,
    'Cointelegraph':   88,
    'Blockworks':      86,
    'Decrypt':         84,
    'Bitcoin Mag':     82,
    'The Defiant':     80,
    'BeInCrypto':      74,
    'Crypto.News':     70,
    'CryptoPotato':    66,
    'NewsBTC':         64,
    'U.Today':         60,
    'AMBCrypto':       52,
    'Chainlink Blog':  80,
    'DL News':         74,
    'Chainalysis Blog':82,
}
DEFAULT_AUTHORITY = 55

# ── Brand configurations ───────────────────────────────────────────────────────
BRAND_CONFIGS = {
    'rz_prime': {
        'name':       'RZ Prime',
        'threshold':  DEFAULT_THRESHOLD,
        'value_gate': False,
        'source_bias': {'BeInCrypto', 'Crypto.News', 'CryptoPotato', 'NewsBTC', 'U.Today'},
        'anchor_phrases': [
            'presale', 'IDO', 'BNB Chain', 'non-custodial', 'no KYC',
            'token reservation', 'launchpad', 'smart contract audit',
            'DEX listing', 'PancakeSwap', 'early investor', 'vesting',
            'BEP20', 'token distribution', 'fair launch', 'TGE',
        ],
    },
    'coin_hall': {
        'name':       'Coin Hall',
        'threshold':  DEFAULT_THRESHOLD,
        'value_gate': True,   # requires a number / price / forecast signal
        'source_bias': {'Decrypt', 'Cointelegraph', 'CoinDesk', 'BeInCrypto', 'The Block'},
        'anchor_phrases': [
            'prediction market', 'luxury prize', 'oracle-confirmed outcome',
            'blockchain entertainment', 'NFT auction', "Sotheby's", 'Rolex',
            'Ferrari', 'tokenized real estate', 'play-to-earn',
            'DeFi TVL', 'price prediction',
        ],
    },
    'chain_reporter': {
        'name':       'ChainReporter',
        'threshold':  CATCHALL_THRESHOLD,
        'value_gate': False,
        'source_bias': {'CoinDesk', 'Cointelegraph', 'The Block', 'Blockworks', 'Bitcoin Mag'},
        'anchor_phrases': [
            'Bitcoin ETF approval', 'Ethereum SEC regulation',
            'institutional crypto investment', 'BlackRock Bitcoin fund',
            'stablecoin', 'Federal Reserve rate decision',
            'crypto regulation policy', 'altcoin market',
            'Binance Coinbase exchange news', 'halving',
        ],
    },
    'meta_coin_guard': {
        'name':       'Meta Coin Guard',
        'threshold':  DEFAULT_THRESHOLD,
        'value_gate': False,
        'source_bias': {'The Block', 'Blockworks', 'The Defiant', 'CoinDesk'},
        'anchor_phrases': [
            'crypto security', 'DeFi exploit', 'protocol hack', 'wallet drainer',
            'rug pull', 'smart contract vulnerability', 'phishing attack',
            'flash loan attack', 'on-chain forensics', 'security audit',
            'exit scam', 'private key compromise', 'bridge exploit',
            'ZachXBT', 'PeckShield', 'Certik',
        ],
    },
}

# Ordered list used for consistent iteration
BRAND_KEYS = ['rz_prime', 'coin_hall', 'chain_reporter', 'meta_coin_guard']

# Brand display-name → key lookup (for incoming selectedMedia strings)
BRAND_NAME_TO_KEY = {cfg['name']: key for key, cfg in BRAND_CONFIGS.items()}

# ── Virality power words ───────────────────────────────────────────────────────
VIRALITY_POWER_WORDS = [
    'breaking', 'urgent', 'alert', 'crash', 'surges', 'explodes', 'collapses',
    'massive', 'historic', 'record', 'first ever', 'all-time high', 'ath',
    'all-time low', 'atl', 'billions', 'trillion', 'emergency', 'warning',
    'critical', 'shocking', 'unprecedented', 'exclusive', 'leaked', 'confirmed',
    'just in', 'developing', 'soars', 'plunges', 'skyrockets', 'rallies', 'dumps',
    'hack', 'exploit', 'rug', 'sec', 'etf', 'approval', 'halving', 'listing',
]

VIRALITY_ENTITIES = [
    'bitcoin', 'blackrock', 'sec', 'trump', 'binance', 'coinbase',
    'federal reserve', 'elon musk', 'michael saylor', 'vitalik',
]

# ── Brand editorial descriptions (passed verbatim to DeepSeek) ────────────────
# Each string covers: identity, audience, what it covers, what it rejects.
BRAND_EDITORIAL_DESCS = {
    'RZ Prime': (
        'IDENTITY: RZ Prime is a crypto token access platform built on BNB Chain. It enables '
        'non-custodial, no-KYC token reservation and decentralised launch participation.\n'
        'AUDIENCE: First-time token investors, retail users who want transparency, people '
        'interested in decentralised launch mechanics, BEP-20/DEX ecosystems, and early '
        'access to token projects.\n'
        'COVERS: Token presales, IDOs, launchpad platforms (PinkSale, DAO Maker, Binance '
        'Launchpad), smart contract audits, wallet-based access, BNB Chain ecosystem news, '
        'vesting schedules, tokenomics, DEX listings, regulatory developments that affect '
        'token availability, DeFi metrics that show market health.\n'
        'REJECTS: Luxury lifestyle, gaming culture, security incidents unrelated to token '
        'access mechanics, pure DeFi exploits with no access angle, content requiring '
        'heavy technical knowledge with no user-facing angle.'
    ),
    'Coin Hall': (
        'IDENTITY: Coin Hall is a Web3 prediction and entertainment platform. Users predict '
        'crypto prices and outcomes across five themed Halls (Jewelry, Trip, Car, Industrial, '
        'Real Estate), with outcomes settled by oracle-confirmed data.\n'
        'AUDIENCE: Crypto-native users who follow markets daily and want to turn that knowledge '
        'into a skill-based competition. They value prestige, aesthetics, and proving foresight.\n'
        'COVERS: Almost any crypto news that contains a price, number, percentage, forecast, '
        'or uncertain outcome. Price movements and analyst targets (Industrial Hall). Token '
        'launches, mints, listings, NFTs, rare collectibles (Jewelry/Industrial Hall). '
        'Oracle/data-feed news — Chainlink, Pyth (all halls). Luxury cars, EVs, tokenized '
        'vehicles (Car Hall). Travel, hospitality, VIP access, event tokens (Trip Hall). '
        'Tokenized real estate, RWA (Real Estate Hall). Play-to-earn, Web3 gaming (theme hall).\n'
        'REJECTS: Stories with NO number, price, value, forecast, or uncertain outcome at all. '
        'Pure legal or regulatory text with no market angle. Security/hack reporting with no '
        'value or entertainment hook. Deep technical infrastructure with no user-facing narrative.\n'
        'VALUE GATE: Every article routed to Coin Hall MUST contain at least one of: a price, '
        'a number, a percentage, a dollar/euro/pound sign, or a word such as forecast, predict, '
        'target, or value. If none of these are present, do NOT route to Coin Hall.'
    ),
    'ChainReporter': (
        'IDENTITY: ChainReporter is the general-purpose crypto newsroom. Full-spectrum coverage '
        '— markets, regulation, technology, culture. The default brand when a story matters to '
        'the crypto world but does not fit a niche.\n'
        'AUDIENCE: Anyone who follows crypto seriously: traders, builders, investors, policy '
        'watchers, DeFi users, crypto-curious people. They want to be informed, not sold to.\n'
        'COVERS: Everything that matters in crypto. Bitcoin/Ethereum price and ETF news. '
        'Exchange news (Binance, Coinbase, Kraken). DeFi protocol updates. Global regulatory '
        'actions (SEC, CFTC, MiCA, FATF). Government crypto policy. Macro economics affecting '
        'crypto (Fed rate decisions, CPI). Institutional adoption (BlackRock, Fidelity, '
        'MicroStrategy). Legal cases, on-chain data, security incidents, geopolitical events '
        'moving crypto markets. Halving. Stablecoin legislation.\n'
        'REJECTS: Pure luxury lifestyle with no crypto connection. Token reservation mechanics '
        'with no broader market relevance. Content with no meaningful connection to crypto.\n'
        'NOTE: ChainReporter is the catch-all. Any clearly-crypto story that does not fit '
        'another brand strongly belongs here.'
    ),
    'Meta Coin Guard': (
        'IDENTITY: Meta Coin Guard is a security-focused crypto protection platform. '
        'Non-custodial, rule-based, automated asset protection. Appeals to users who trust '
        'code over people.\n'
        'AUDIENCE: Security-conscious DeFi users, people who have been exploited or rug-pulled, '
        'users who distrust custodial platforms. They want verifiable, automated protection.\n'
        'COVERS: DeFi exploits and post-mortems. Smart contract vulnerabilities. Rug pulls and '
        'exit scams. Wallet drainer malware. Phishing campaigns. Centralised exchange '
        'insolvencies (showing why non-custodial matters). Sanctions enforcement. Oracle '
        'reliability. Bridge exploits. Address poisoning. SIM swaps. On-chain forensics '
        '(ZachXBT, PeckShield, Certik). Regulatory pressure on custodial platforms. Bug '
        'bounties. Emergency protocol pauses.\n'
        'REJECTS: Luxury lifestyle. Token presale mechanics. Pure market price commentary '
        'with no risk or security angle. Gaming culture stories with no wallet safety relevance.'
    ),
}
