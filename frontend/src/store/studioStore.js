import { create } from 'zustand'
import { API_BASE } from './mmStore'

const STORAGE_KEY = 'chainreporter-studio-workspace-v1'

export const STUDIO_DEFAULT_SETTINGS = {
  duration: 30,
  aspectRatio: '9:16',
  resolution: '720p',
  model: '',
  voice: 'News Anchor',
  music: 'Market Pulse',
  language: 'English',
  visualDirection: 'Original editorial concept video with one clear visual metaphor',
  generateAudio: true,
  audioMode: 'model_native',
}

function settingsForModel(settings, model) {
  if (!model) return settings
  const durations = Array.isArray(model.durations) ? model.durations : []
  const resolutions = Array.isArray(model.resolutions) ? model.resolutions : []
  const duration = durations.includes(settings.duration)
    ? settings.duration
    : (durations.includes(30) ? 30 : (durations[0] || settings.duration))
  const resolution = resolutions.includes(settings.resolution)
    ? settings.resolution
    : (resolutions[0] || settings.resolution)
  return {
    ...settings,
    model: model.id,
    duration,
    resolution,
    generateAudio: model.generateAudio === true,
    audioMode: 'model_native',
  }
}

function normalizeCard(card) {
  return {
    id: String(card?.id || `${card?.media || card?.brand || 'story'}-${card?.headline || card?.title || Date.now()}`),
    media: card?.media || card?.brand || 'ChainReporter',
    headline: card?.headline || card?.title || 'Untitled story',
    copy: card?.copy || card?.desc || card?.summary || '',
    source: card?.source || '',
    link: card?.link || card?.sourceUrl || '',
    publishedAt: card?.publishedAt || card?.pubDate || card?.timeAgo || '',
    timeAgo: card?.timeAgo || '',
    sentiment: card?.sentiment || 'Neutral',
    suitability: card?.suitability ?? null,
    impact: card?.impact ?? null,
    virality: card?.virality ?? null,
    initials: card?.initials || '',
    srcColor: card?.srcColor || '#7a8499',
    imageUrl: card?.imageUrl || '',
  }
}

function readWorkspace() {
  try {
    const raw = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || '{}')
    return {
      importedCards: Array.isArray(raw.importedCards) ? raw.importedCards.map(normalizeCard) : [],
      settings: { ...STUDIO_DEFAULT_SETTINGS, ...(raw.settings || {}) },
      script: raw.script && typeof raw.script === 'object' ? raw.script : null,
      draftId: raw.draftId || null,
      title: raw.title || '',
    }
  } catch {
    return { importedCards: [], settings: { ...STUDIO_DEFAULT_SETTINGS }, script: null, draftId: null, title: '' }
  }
}

function persist(state) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({
      importedCards: state.importedCards,
      settings: state.settings,
      script: state.script,
      draftId: state.draftId,
      title: state.title,
    }))
  } catch { /* local storage is best-effort */ }
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    ...options,
    headers: options.body ? { 'Content-Type': 'application/json', ...(options.headers || {}) } : options.headers,
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.error || `Studio request failed (${response.status})`)
  return data
}

const initial = readWorkspace()

export const useStudioStore = create((set, get) => ({
  ...initial,
  models: [],
  jobs: [],
  modelLoading: false,
  jobsLoading: false,
  draftSaving: false,
  scriptLoading: false,
  directorLoading: false,
  generating: false,
  polling: {},
  error: '',
  notice: '',

  addCards: cards => set(state => {
    const incoming = (Array.isArray(cards) ? cards : [cards]).filter(Boolean).map(normalizeCard)
    const keys = new Set(state.importedCards.map(card => `${card.media}:${card.id}`))
    const additions = incoming.filter(card => {
      const key = `${card.media}:${card.id}`
      if (keys.has(key)) return false
      keys.add(key)
      return true
    })
    const next = { ...state, importedCards: [...state.importedCards, ...additions] }
    persist(next)
    return {
      importedCards: next.importedCards,
      notice: additions.length ? `${additions.length} ${additions.length === 1 ? 'story' : 'stories'} added to Studio` : 'Already in Studio',
      error: '',
    }
  }),

  removeCard: (cardId, media) => set(state => {
    const next = { ...state, importedCards: state.importedCards.filter(card => card.id !== cardId || card.media !== media) }
    persist(next)
    return { importedCards: next.importedCards, script: null, notice: '', error: '' }
  }),

  moveCard: (cardId, media, direction) => set(state => {
    const index = state.importedCards.findIndex(card => card.id === cardId && card.media === media)
    if (index < 0) return {}
    const brand = state.importedCards[index].media
    const candidateIndexes = state.importedCards
      .map((card, cardIndex) => card.media === brand ? cardIndex : -1)
      .filter(cardIndex => cardIndex >= 0)
    const groupPosition = candidateIndexes.indexOf(index)
    const targetPosition = groupPosition + direction
    if (targetPosition < 0 || targetPosition >= candidateIndexes.length) return {}
    const targetIndex = candidateIndexes[targetPosition]
    const importedCards = [...state.importedCards]
    ;[importedCards[index], importedCards[targetIndex]] = [importedCards[targetIndex], importedCards[index]]
    const next = { ...state, importedCards }
    persist(next)
    return { importedCards }
  }),

  clearTray: () => set(state => {
    const next = { ...state, importedCards: [], script: null, draftId: null, title: '' }
    persist(next)
    return { importedCards: [], script: null, draftId: null, title: '', notice: '', error: '' }
  }),

  setTitle: title => set(state => {
    const next = { ...state, title }
    persist(next)
    return { title }
  }),

  setSetting: (key, value) => set(state => {
    const requested = { ...state.settings, [key]: value }
    const selected = key === 'model' ? state.models.find(model => model.id === value) : state.models.find(model => model.id === requested.model)
    const settings = settingsForModel(requested, selected)
    const invalidateDirection = ['model', 'duration', 'resolution', 'language', 'visualDirection'].includes(key)
    const script = invalidateDirection && state.script
      ? { ...state.script, directorBrief: null }
      : state.script
    const next = { ...state, settings, script }
    persist(next)
    return { settings, script, error: '' }
  }),

  setScriptField: (key, value) => set(state => {
    const script = { ...(state.script || {}), [key]: value, directorBrief: null }
    const next = { ...state, script }
    persist(next)
    return { script, error: '' }
  }),

  setCaptions: value => set(state => {
    const script = {
      ...(state.script || {}),
      on_screen_captions: String(value).split('\n').map(line => line.trim()).filter(Boolean),
      directorBrief: null,
    }
    const next = { ...state, script }
    persist(next)
    return { script, error: '' }
  }),

  setDirectorField: (key, value) => set(state => {
    if (!state.script?.directorBrief) return {}
    const script = {
      ...state.script,
      directorBrief: { ...state.script.directorBrief, [key]: value },
    }
    const next = { ...state, script }
    persist(next)
    return { script, error: '' }
  }),

  clearMessages: () => set({ error: '', notice: '' }),

  fetchModels: async () => {
    set({ modelLoading: true, error: '' })
    try {
      const data = await api('/api/studio/models')
      const models = data.models || []
      const current = get().settings.model
      const model = models.some(item => item.id === current) ? current : (models[0]?.id || '')
      const settings = settingsForModel(get().settings, models.find(item => item.id === model))
      const next = { ...get(), settings }
      persist(next)
      set({ models, settings, modelLoading: false })
    } catch (error) {
      set({ modelLoading: false, error: error.message || 'Video models could not be loaded' })
    }
  },

  fetchJobs: async () => {
    set({ jobsLoading: true })
    try {
      const data = await api('/api/studio/jobs')
      set({ jobs: data.jobs || [], jobsLoading: false })
    } catch (error) {
      set({ jobsLoading: false, error: error.message || 'Studio history could not be loaded' })
    }
  },

  saveDraft: async () => {
    const state = get()
    if (!state.importedCards.length) throw new Error('Send at least one story to Studio first')
    set({ draftSaving: true, error: '', notice: '' })
    try {
      const data = await api('/api/studio/draft', {
        method: 'POST',
        body: JSON.stringify({
          draftId: state.draftId,
          title: state.title,
          cards: state.importedCards,
          script: state.script || {},
          settings: state.settings,
        }),
      })
      const next = { ...get(), draftId: data.draft.id, title: data.draft.title }
      persist(next)
      set({ draftId: data.draft.id, title: data.draft.title, draftSaving: false, notice: 'Draft saved' })
      return data.draft
    } catch (error) {
      set({ draftSaving: false, error: error.message || 'Draft could not be saved' })
      throw error
    }
  },

  generateScript: async () => {
    const state = get()
    if (!state.importedCards.length) throw new Error('Send at least one story to Studio first')
    set({ scriptLoading: true, error: '', notice: '' })
    try {
      const data = await api('/api/studio/script', {
        method: 'POST',
        body: JSON.stringify({
          draftId: state.draftId,
          title: state.title,
          cards: state.importedCards,
          settings: state.settings,
        }),
      })
      const next = { ...get(), script: data.script, draftId: data.draft.id, title: data.draft.title }
      persist(next)
      set({
        script: data.script,
        draftId: data.draft.id,
        title: data.draft.title,
        scriptLoading: false,
        notice: 'Script and storyboard ready',
      })
      return data.script
    } catch (error) {
      set({ scriptLoading: false, error: error.message || 'Script could not be generated' })
      throw error
    }
  },

  generateDirection: async () => {
    const state = get()
    if (!state.importedCards.length) throw new Error('Send at least one story to Studio first')
    if (!state.script) throw new Error('Generate and review the script before art direction')
    set({ directorLoading: true, error: '', notice: '' })
    try {
      const data = await api('/api/studio/direct', {
        method: 'POST',
        body: JSON.stringify({
          draftId: state.draftId,
          title: state.title,
          cards: state.importedCards,
          script: state.script,
          settings: state.settings,
        }),
      })
      const next = { ...get(), script: data.script, draftId: data.draft.id, title: data.draft.title }
      persist(next)
      set({
        script: data.script,
        draftId: data.draft.id,
        title: data.draft.title,
        directorLoading: false,
        notice: 'Art direction ready for review',
      })
      return data.directorBrief
    } catch (error) {
      set({ directorLoading: false, error: error.message || 'Art direction could not be generated' })
      throw error
    }
  },

  generateVideo: async () => {
    const state = get()
    if (!state.importedCards.length) throw new Error('Send at least one story to Studio first')
    if (!state.script) throw new Error('Generate the script before creating the reel')
    if (!state.script.directorBrief) throw new Error('Create and review art direction before generating the reel')
    if (!state.settings.model) throw new Error('Choose a video model first')
    set({ generating: true, error: '', notice: '' })
    try {
      const data = await api('/api/studio/generate', {
        method: 'POST',
        body: JSON.stringify({
          draftId: state.draftId,
          title: state.title,
          cards: state.importedCards,
          script: state.script,
          settings: state.settings,
        }),
      })
      const jobs = [data.job, ...get().jobs.filter(job => job.id !== data.job.id)]
      const next = { ...get(), draftId: data.draft.id, jobs }
      persist(next)
      set({
        draftId: data.draft.id,
        jobs,
        generating: false,
        notice: 'Reel submitted. Studio will keep checking its progress.',
      })
      return data.job
    } catch (error) {
      set({ generating: false, error: error.message || 'Reel generation could not be started' })
      throw error
    }
  },

  pollJob: async id => {
    if (get().polling[id]) return null
    set(state => ({ polling: { ...state.polling, [id]: true } }))
    try {
      const data = await api('/api/studio/poll', {
        method: 'POST',
        body: JSON.stringify({ id }),
      })
      set(state => ({
        jobs: state.jobs.map(job => job.id === id ? data.job : job),
        polling: { ...state.polling, [id]: false },
      }))
      return data.job
    } catch (error) {
      set(state => ({
        polling: { ...state.polling, [id]: false },
        error: error.message || 'Reel status could not be refreshed',
      }))
      return null
    }
  },
}))

export const studioDownloadUrl = (id, download = false) => `${API_BASE}/api/studio/download?id=${encodeURIComponent(id)}${download ? '&download=1' : ''}`
