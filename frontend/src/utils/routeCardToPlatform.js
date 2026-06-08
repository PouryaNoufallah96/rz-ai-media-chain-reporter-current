import { API_BASE } from '../store/mmStore'

const PLAT_REASONS = {
  X:         '≤ 280 chars · punchy hook · 2–3 hashtags',
  Telegram:  'Full context · 2–4 paragraphs · brand-voice',
  Instagram: 'Strong opening hook · 5–10 hashtags',
}

export async function generatePlatformCopy(card, platform, { updatePlatformCard, getCachedCopy, setCachedCopy, siblingCopy }) {
  const modelKey = card._modelKey || 'gpt'
  const cached = getCachedCopy(card.id, platform, modelKey)
  if (cached) { updatePlatformCard(card.id, platform, cached); return }

  try {
    const body = { article:{title:card.headline,source:card.source,desc:card.copy,matchedKeywords:card.hashtags||[]}, platform, mediaBrand:card.media, sentiment:card.sentiment||'Neutral', modelKey }
    if (siblingCopy) body.siblingCopy = siblingCopy
    const r = await fetch(`${API_BASE}/api/copy/generate`, {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)
    })
    if (!r.ok) return
    const result = await r.json()
    const payload = {
      copy: result.copy || card.copy,
      hashtags: result.hashtags?.length ? result.hashtags : card.hashtags,
      charCount: platform === 'X' ? (result.copy || '').length : null,
      variants: result.variants || null,
      platReason: PLAT_REASONS[platform] || `Formatted for ${platform}`,
    }
    setCachedCopy(card.id, platform, modelKey, payload)
    updatePlatformCard(card.id, platform, payload)
  } catch (e) { console.warn('Platform copy failed:', e.message) }
}

export function routeCardToPlatform(cardId, targetPlatform, targetBrand, storeBag) {
  const { modelLanes, platformLanes, setPlatformLanes, updatePlatformCard, getCachedCopy, setCachedCopy } = storeBag
  if ((platformLanes[targetBrand]?.[targetPlatform] || []).some(c => c.id === cardId)) return   // already routed here — no-op

  let siblingCopy = null
  if (targetPlatform !== 'X') {
    const xCard = (platformLanes[targetBrand]?.X || []).find(c => c.id === cardId)
    if (xCard) siblingCopy = xCard.copy
  }

  // Look for the card in model lanes first — those are cloned (card stays put)
  for (const mk of Object.keys(modelLanes)) {
    for (const brand of Object.keys(modelLanes[mk])) {
      const found = modelLanes[mk][brand].find(c => c.id === cardId)
      if (found) {
        const routed = { ...found, platform: targetPlatform, media: brand }
        const newPl = JSON.parse(JSON.stringify(platformLanes))
        if (!newPl[brand]) newPl[brand] = {}
        if (!newPl[brand][targetPlatform]) newPl[brand][targetPlatform] = []
        newPl[brand][targetPlatform].push(routed)
        setPlatformLanes(newPl)
        generatePlatformCopy(routed, targetPlatform, { updatePlatformCard, getCachedCopy, setCachedCopy, siblingCopy })
        return
      }
    }
  }

  // Otherwise the card is already in a platform lane — move it (remove from old lane)
  const pl = JSON.parse(JSON.stringify(platformLanes))
  let card = null
  for (const brand of Object.keys(pl)) {
    for (const plat of Object.keys(pl[brand])) {
      const idx = pl[brand][plat].findIndex(c => c.id === cardId)
      if (idx !== -1) {
        card = { ...pl[brand][plat][idx], platform: targetPlatform }
        pl[brand][plat].splice(idx, 1)
        break
      }
    }
    if (card) break
  }
  if (!card) return
  if (!pl[targetBrand]) pl[targetBrand] = {}
  if (!pl[targetBrand][targetPlatform]) pl[targetBrand][targetPlatform] = []
  pl[targetBrand][targetPlatform].push(card)
  setPlatformLanes(pl)
  generatePlatformCopy(card, targetPlatform, { updatePlatformCard, getCachedCopy, setCachedCopy, siblingCopy })
}
