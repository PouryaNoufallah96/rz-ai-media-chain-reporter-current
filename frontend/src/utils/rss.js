import { API_BASE } from '../store/mmStore'

const CORS_PROXIES = [
  u => `${API_BASE}/api/rss?url=${encodeURIComponent(u)}`,
  u => `https://api.allorigins.win/raw?url=${encodeURIComponent(u)}`,
  u => `https://corsproxy.io/?${encodeURIComponent(u)}`,
  u => `https://api.allorigins.win/get?url=${encodeURIComponent(u)}`,
  u => `https://thingproxy.freeboard.io/fetch/${u}`,
]

function fetchWithTimeout(url, ms = 11000) {
  const ctrl = new AbortController()
  const id = setTimeout(() => ctrl.abort(), ms)
  return fetch(url, { signal: ctrl.signal }).finally(() => clearTimeout(id))
}

export async function fetchRSS(url) {
  for (const proxy of CORS_PROXIES) {
    try {
      const r = await fetchWithTimeout(proxy(url))
      if (!r.ok) continue
      let text = await r.text()
      if (text.trim().startsWith('{')) { try { text = JSON.parse(text).contents || text } catch(_){} }
      if (text.includes('<item') || text.includes('<entry') || text.includes('<rss') || text.includes('<feed')) return text
    } catch(_) {}
  }
  throw new Error(`Proxies failed for ${url}`)
}

function stripHTML(h) {
  const d = document.createElement('div'); d.innerHTML = h
  return (d.textContent || d.innerText || '').replace(/\s+/g,' ').trim()
}

export function parseRSS(xml, src) {
  const doc = new DOMParser().parseFromString(xml, 'application/xml')
  if (doc.querySelector('parsererror')) return []
  const entries = [...doc.querySelectorAll('entry')]
  if (entries.length) return entries.map(el => ({
    title:   el.querySelector('title')?.textContent?.trim() || '',
    desc:    stripHTML(el.querySelector('summary,content')?.textContent || '').slice(0,400),
    link:    el.querySelector('link')?.getAttribute('href') || el.querySelector('link')?.textContent?.trim() || '',
    pubDate: el.querySelector('published,updated')?.textContent?.trim() || '',
    source: src,
  }))
  return [...doc.querySelectorAll('item')].map(el => {
    const lk = el.querySelector('link')
    return {
      title:   el.querySelector('title')?.textContent?.trim() || '',
      desc:    stripHTML(el.querySelector('description')?.textContent || '').slice(0,400),
      link:    lk?.textContent?.trim() || lk?.getAttribute('href') || el.querySelector('guid')?.textContent?.trim() || '',
      pubDate: el.querySelector('pubDate')?.textContent?.trim() || '',
      source: src,
    }
  })
}

export function filterByRecency(arts, h) {
  const cut = Date.now() - h * 3600000
  return arts.filter(a => { if (!a.pubDate) return true; const t = Date.parse(a.pubDate); return isNaN(t) ? true : t >= cut })
}

export function timeAgo(pubDate) {
  if (!pubDate) return 'Recent'
  const d = Date.parse(pubDate)
  if (isNaN(d)) return 'Recent'
  const ageMin = (Date.now() - d) / 60000
  if (ageMin < 60) return `${Math.round(ageMin)}m ago`
  if (ageMin < 1440) return `${Math.round(ageMin/60)}h ago`
  return `${Math.round(ageMin/1440)}d ago`
}
