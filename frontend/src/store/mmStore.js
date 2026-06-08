import { create } from 'zustand'

// ── Constants ─────────────────────────────────────────────────────────────────
export const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'http://localhost:3001'
  : `http://${window.location.hostname}:3001`

export const MM_SOURCES = {
  'CoinDesk':      'https://www.coindesk.com/arc/outboundfeeds/rss/',
  'Cointelegraph': 'https://cointelegraph.com/rss',
  'Decrypt':       'https://decrypt.co/feed',
  'CryptoSlate':   'https://cryptoslate.com/feed/',
  'The Block':     'https://www.theblock.co/rss.xml',
  'Blockworks':    'https://blockworks.co/feed/',
  'Bitcoin Mag':   'https://bitcoinmagazine.com/.rss/full/',
  'BeInCrypto':    'https://beincrypto.com/feed/',
  'Crypto.News':   'https://crypto.news/feed/',
  'U.Today':       'https://u.today/rss',
  'NewsBTC':       'https://www.newsbtc.com/feed/',
  'CryptoPotato':  'https://cryptopotato.com/feed/',
  'The Defiant':   'https://thedefiant.io/feed',
  'AMBCrypto':     'https://ambcrypto.com/feed/',
  'Chainlink Blog':'https://blog.chain.link/rss/',
  'DL News':       'https://dlnews.com/arc/outboundfeeds/rss/',
  'Chainalysis Blog':'https://blog.chainalysis.com/feed/',
}

export const SRC_COLORS = {
  'CoinDesk':'#3d8ef0','Cointelegraph':'#f0a040','Decrypt':'#ef4455',
  'CryptoSlate':'#9b72f5','The Block':'#3d8ef0','Blockworks':'#00d4a0',
  'Bitcoin Mag':'#f0a040','BeInCrypto':'#9b72f5','Crypto.News':'#3d8ef0',
  'U.Today':'#00d4a0','NewsBTC':'#ef4455','CryptoPotato':'#f0a040',
  'The Defiant':'#00d4a0','AMBCrypto':'#9b72f5',
  'Chainlink Blog':'#375bd2','DL News':'#ef4455','Chainalysis Blog':'#00d4a0',
}

export const MEDIA_LIST      = ['RZ Prime','Coin Hall','ChainReporter','Meta Coin Guard']
export const PLAT_LIST       = ['X','Telegram','Instagram']
export const MEDIA_COLORS    = {'RZ Prime':'#f0a040','Coin Hall':'#00d4ff','ChainReporter':'#9b72f5','Meta Coin Guard':'#4ade80'}
export const PLAT_COLORS     = {X:'#00d4ff',Telegram:'#00d4a0',Instagram:'#e1306c'}

export const EDITORIAL_MODEL_META = {
  gpt:      { display:'GPT-5.5',              color:'#10a37f', badge:'OpenAI',    desc:'Best general-purpose editorial AI' },
  gemini:   { display:'Gemini 3.1 Pro Preview',color:'#4285f4', badge:'Google',    desc:'Strong reasoning · multimodal' },
  claude:   { display:'Claude Opus 4.7',       color:'#d97706', badge:'Anthropic', desc:'Top reasoning benchmark score' },
  deepseek: { display:'DeepSeek V4 Flash',     color:'#22d3ee', badge:'DeepSeek',  desc:'Fast · cost-efficient · strong reasoning' },
  grok:     { display:'Grok 4.3',              color:'#ef4455', badge:'xAI',       desc:'xAI · real-time knowledge' },
}

export const mkey = m => m.toLowerCase().replace(/\s+/g,'-')
export const cacheKey = (articleId, platform, modelKey) => `${articleId}|${platform}|${modelKey}`

function buildEmptyRouted() {
  const r = {}
  MEDIA_LIST.forEach(m => {
    r[m] = { suggested: [] }
    PLAT_LIST.forEach(p => { r[m][p] = [] })
  })
  return r
}

// ── Zustand store ─────────────────────────────────────────────────────────────
export const useMmStore = create((set, get) => ({
  selectedMedia:     [...MEDIA_LIST],
  selectedPlatforms: [...PLAT_LIST],
  selectedSources:   ['CoinDesk','Cointelegraph','The Block'],
  recencyHours:      24,
  filterMode:        'preprocess',   // 'preprocess' | 'openai_embedding' | 'deepseek_preprocess' | 'test'
  testMode:          false,
  routed:            buildEmptyRouted(),
  activeCard:        null,
  editorial:         null,
  lastShortlist:     [],
  selectedModels:    ['gpt','gemini','claude','deepseek','grok'],
  modelLanes:        { gpt:{}, gemini:{}, claude:{}, deepseek:{}, grok:{} },
  platformLanes:     {},
  copyCache:         {},
  progress:          { pct: 0, label: '' },
  analyzing:         false,
  errorMsg:          '',
  mmReport:          null,

  // ── Setters ──
  setSelectedMedia:     v  => set({ selectedMedia: v }),
  setSelectedPlatforms: v  => set({ selectedPlatforms: v }),
  setSelectedSources:   v  => set({ selectedSources: v }),
  setRecencyHours:      h  => set({ recencyHours: h }),
  setFilterMode:        (mode) => set({ filterMode: mode, testMode: mode === 'test' }),
  setSelectedModels:    v  => set({ selectedModels: v }),
  setActiveCard:        c  => set({ activeCard: c }),
  setEditorial:         e  => set({ editorial: e }),
  setLastShortlist:     s  => set({ lastShortlist: s }),
  setModelLanes:        v  => set({ modelLanes: v }),
  setPlatformLanes:     v  => set({ platformLanes: v }),
  setProgress:          (pct, label) => set({ progress: { pct, label } }),
  setAnalyzing:         v  => set({ analyzing: v }),
  setErrorMsg:          v  => set({ errorMsg: v }),
  setMmReport:          v  => set({ mmReport: v }),

  toggleMedia: (m) => set(s => {
    const arr = s.selectedMedia.includes(m)
      ? s.selectedMedia.filter(x => x !== m)
      : [...s.selectedMedia, m]
    return { selectedMedia: arr }
  }),
  togglePlatform: (p) => set(s => {
    const arr = s.selectedPlatforms.includes(p)
      ? s.selectedPlatforms.filter(x => x !== p)
      : [...s.selectedPlatforms, p]
    return { selectedPlatforms: arr }
  }),
  toggleSource: (src) => set(s => {
    const arr = s.selectedSources.includes(src)
      ? s.selectedSources.filter(x => x !== src)
      : [...s.selectedSources, src]
    return { selectedSources: arr }
  }),
  initPlatformLanes: () => set(s => {
    const pl = {}
    s.selectedMedia.forEach(brand => {
      pl[brand] = {}
      s.selectedPlatforms.forEach(p => { pl[brand][p] = [] })
    })
    return { platformLanes: pl }
  }),

  toggleModel: (key) => set(s => {
    if (s.selectedModels.includes(key)) {
      if (s.selectedModels.length === 1) return {}
      return { selectedModels: s.selectedModels.filter(k => k !== key) }
    }
    return { selectedModels: [...s.selectedModels, key] }
  }),

  updateCardStatus: (cardId, status, extra = {}) => set(s => {
    const activeCard = s.activeCard?.id === cardId ? { ...s.activeCard, status, ...extra } : s.activeCard
    // Update in modelLanes
    const modelLanes = { ...s.modelLanes }
    Object.keys(modelLanes).forEach(mk => {
      const lanes = { ...modelLanes[mk] }
      Object.keys(lanes).forEach(brand => {
        lanes[brand] = lanes[brand].map(c => c.id === cardId ? { ...c, status, ...extra } : c)
      })
      modelLanes[mk] = lanes
    })
    // Update in platformLanes
    const platformLanes = { ...s.platformLanes }
    Object.keys(platformLanes).forEach(brand => {
      const lanes = { ...platformLanes[brand] }
      Object.keys(lanes).forEach(plat => {
        lanes[plat] = lanes[plat].map(c => c.id === cardId ? { ...c, status, ...extra } : c)
      })
      platformLanes[brand] = lanes
    })
    return { activeCard, modelLanes, platformLanes }
  }),

  updateCard: (cardId, extra = {}) => set(s => {
    const activeCard = s.activeCard?.id === cardId ? { ...s.activeCard, ...extra } : s.activeCard
    const modelLanes = { ...s.modelLanes }
    Object.keys(modelLanes).forEach(mk => {
      const lanes = { ...modelLanes[mk] }
      Object.keys(lanes).forEach(brand => {
        lanes[brand] = lanes[brand].map(c => c.id === cardId ? { ...c, ...extra } : c)
      })
      modelLanes[mk] = lanes
    })
    const platformLanes = { ...s.platformLanes }
    Object.keys(platformLanes).forEach(brand => {
      const lanes = { ...platformLanes[brand] }
      Object.keys(lanes).forEach(plat => {
        lanes[plat] = lanes[plat].map(c => c.id === cardId ? { ...c, ...extra } : c)
      })
      platformLanes[brand] = lanes
    })
    return { activeCard, modelLanes, platformLanes }
  }),

  getCachedCopy: (articleId, platform, modelKey) => get().copyCache[cacheKey(articleId, platform, modelKey)] || null,
  setCachedCopy: (articleId, platform, modelKey, payload) => set(s => ({
    copyCache: { ...s.copyCache, [cacheKey(articleId, platform, modelKey)]: payload }
  })),
}))
