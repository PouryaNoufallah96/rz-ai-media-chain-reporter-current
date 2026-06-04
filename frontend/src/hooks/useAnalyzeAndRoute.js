import { useCallback } from 'react'
import { useMmStore, API_BASE, MM_SOURCES, SRC_COLORS, EDITORIAL_MODEL_META, mkey } from '../store/mmStore'
import { fetchRSS, parseRSS, filterByRecency, timeAgo } from '../utils/rss'
import { preScore } from '../utils/scoring'

export function useAnalyzeAndRoute() {
  const store = useMmStore()

  const run = useCallback(async (topics) => {
    const { selectedSources, selectedMedia, selectedPlatforms, selectedModels,
            recencyHours, filterMode, testMode, setProgress, setAnalyzing,
            setErrorMsg, setModelLanes, setPlatformLanes, setLastShortlist,
            setEditorial, setMmReport } = useMmStore.getState()

    if (!selectedSources.length) { setErrorMsg('Select at least one source.'); return }
    if (!selectedMedia.length)   { setErrorMsg('Select at least one media brand.'); return }

    setAnalyzing(true)
    setErrorMsg('')

    try {
      // ── Phase 1: RSS Fetch ──
      const allArticles = []
      const sourceCounts = {}
      selectedSources.forEach(s => { sourceCounts[s] = 0 })
      for (let i = 0; i < selectedSources.length; i++) {
        const name = selectedSources[i], url = MM_SOURCES[name]
        if (!url) continue
        setProgress(5 + Math.round((i / selectedSources.length) * 35), `Fetching ${name}…`)
        try {
          const xml  = await fetchRSS(url)
          const arts = parseRSS(xml, name)
          allArticles.push(...arts.slice(0, 15))
          sourceCounts[name] = arts.length
        } catch(e) { console.warn(`Skip ${name}:`, e.message) }
      }
      if (!allArticles.length) throw new Error('Could not load any feeds. Check your connection.')

      const tooOldCount = allArticles.length - allArticles.filter(a => {
        if (!a.pubDate) return true
        const t = Date.parse(a.pubDate)
        return isNaN(t) ? true : t >= Date.now() - recencyHours * 3600000
      }).length

      const recent = filterByRecency(allArticles, recencyHours)
      if (!recent.length) throw new Error(`No articles in the last ${recencyHours}h. Try a wider time range.`)

      const tooOldArticles = allArticles
        .filter(a => a.pubDate && (() => { const t = Date.parse(a.pubDate); return !isNaN(t) && t < Date.now() - recencyHours*3600000 })())
        .map(a => ({ ...a, _pipelineStatus:'too_old', _scores:null, _keywords:null, _routing:null }))

      // ── Phase 2: Filter ──
      let shortlistPayload, allTracked, preResult = null

      if (filterMode === 'openai_embedding') {
        setProgress(48, `Running OpenAI Embedding pipeline on ${recent.length} articles…`)
        const r = await fetch(`${API_BASE}/api/filter/pipeline`, {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ articles:recent, selectedMedia, topics, recencyHours }),
        })
        if (!r.ok) { const e = await r.json().catch(()=>({})); throw new Error(e?.error||`Filter failed (${r.status})`) }
        const fd = await r.json()
        if (!fd.shortlist?.length) throw new Error('OpenAI Embedding: no articles passed. Try wider range.')
        shortlistPayload = fd.shortlist; allTracked = fd.all_tracked||[]
        setLastShortlist(shortlistPayload)
        preResult = { rejected:{duplicate:(fd.stats?.dropped_dup_cheap||0)+(fd.stats?.dropped_clustered||0),noMediaFit:fd.stats?.no_media_fit||0,lowScore:fd.stats?.cap_exceeded||0}, passed:fd.stats?.embedded||0, shortlisted:shortlistPayload, allTracked }

      } else if (filterMode === 'deepseek_preprocess') {
        setProgress(48, `Sending ${recent.length} articles to DeepSeek V4 Flash…`)
        const r = await fetch(`${API_BASE}/api/filter/deepseek`, {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ articles:recent, selectedMedia, topics, recencyHours }),
        })
        if (!r.ok) { const e = await r.json().catch(()=>({})); throw new Error(e?.error||`DeepSeek filter failed (${r.status})`) }
        const fd = await r.json()
        if (!fd.shortlist?.length) throw new Error('DeepSeek Pre-Process: no articles passed.')
        shortlistPayload = fd.shortlist; allTracked = fd.all_tracked||[]
        setLastShortlist(shortlistPayload)
        preResult = { rejected:{duplicate:fd.stats?.dropped_dup_cheap||0,noMediaFit:0,lowScore:0}, passed:fd.stats?.sent_to_deepseek||0, shortlisted:shortlistPayload, allTracked }

      } else {
        // Pre-Process / Test path
        if (filterMode !== 'test') {
          setProgress(45, 'Loading semantic model…')
          if (window._semRouter?._initPromise) await window._semRouter._initPromise
          setProgress(50, `Embedding ${recent.length} articles…`)
          if (window._semRouter?.embedArticles) await window._semRouter.embedArticles(recent)
        }
        setProgress(58, `Pre-scoring ${recent.length} articles…`)
        await new Promise(r => setTimeout(r, 20))
        preResult = preScore(recent, selectedMedia, topics)
        allTracked = preResult.allTracked
        const { shortlisted } = preResult
        if (!shortlisted.length) throw new Error('All articles filtered. Try wider range or more sources.')

        const isTest = testMode
        let articlesForAI = shortlisted
        if (isTest) {
          const seen=new Set(), picked=[]
          for (const brand of selectedMedia) {
            shortlisted.filter(a=>a._routing?.primary_media===brand).slice(0,3)
              .forEach(a=>{ if(!seen.has(a.title)){seen.add(a.title);picked.push(a)} })
          }
          articlesForAI = picked.length ? picked : shortlisted.slice(0, 3)
        }
        shortlistPayload = articlesForAI.map((a,i) => ({
          input_index: i,
          title:   isTest ? a.title.split(' ').slice(0,6).join(' ') : a.title,
          source:  a.source, link: a.link||'',
          desc:    isTest ? (a.desc||'').split(' ').slice(0,10).join(' ') : (a.desc||'').slice(0,220),
          pubDate: a.pubDate||'',
          scores: {
            final:      Math.round(a._scores?.final||0),  virality: Math.round(a._scores?.virality||0),
            freshness:  Math.round(a._scores?.freshness||0), authority: Math.round(a._scores?.authority||0),
            userTopic:  Math.round(a._scores?.userTopic||0), confidence: Math.round(a._scores?.confidence||0),
          },
          routing: { primary_media:a._routing?.primary_media||'', secondary_media:a._routing?.secondary_media||'' },
        }))
        setLastShortlist(preResult.shortlisted)
      }

      // Mobile cap
      if (window.innerWidth <= 768) {
        const bc = {}
        shortlistPayload = shortlistPayload.filter(a => { const b=a.routing?.primary_media||'_'; bc[b]=(bc[b]||0)+1; return bc[b]<=10 })
      }

      setProgress(62, `Sending ${shortlistPayload.length} articles to ${selectedModels.length} AI editor${selectedModels.length===1?'':'s'}…`)

      // ── Phase 3: Editorial AI ──
      const editRes = await fetch(`${API_BASE}/api/ai/editorial-select`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ shortlist:shortlistPayload, selectedMedia, selectedPlatforms, selectedModels, topics, testMode }),
      })
      if (!editRes.ok) { const e = await editRes.json().catch(()=>({})); throw new Error(e?.error||`Editorial AI failed (${editRes.status})`) }
      const editorial = await editRes.json()
      setEditorial(editorial)

      // ── Phase 4: Build lanes ──
      const lastShortlist = useMmStore.getState().lastShortlist
      const modelLanes = {}
      selectedModels.forEach(key => {
        const data = editorial?.[key], meta = EDITORIAL_MODEL_META[key], brands = data?.brands||{}
        modelLanes[key] = {}
        selectedMedia.forEach(brand => {
          modelLanes[key][brand] = [];
          (brands[brand]||[]).forEach((a,rank) => {
            const src = lastShortlist[a.input_index]||{}, srcCol=SRC_COLORS[a.source]||'#7a8499'
            const init=(a.source||'').split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase()
            modelLanes[key][brand].push({
              id:`${key}-${mkey(brand)}-${a.input_index}-${rank}`,
              _modelKey:key, _modelDisplay:meta?.display, _modelColor:meta?.color,
              media:brand, platform:'suggested', source:a.source||'', initials:init, srcColor:srcCol,
              headline:a.title||'', copy:a.copy||'', selectionReason:a.selection_reason||'',
              mediaReason:a.selection_reason||'', platReason:'', hashtags:a.hashtags||[],
              suitability:Math.round((a.suitability_score||70)/10), impact:Math.round((a.impact_score||70)/10),
              virality:Math.round((a.virality_score||60)/10), sentiment:'Neutral',
              link:a.source_url||src.link||'#', status:'ready',
              timeAgo:src.pubDate?timeAgo(src.pubDate):src.pub_date?timeAgo(src.pub_date):'Recent',
              lowConfidence:false, lowConfidenceReason:'',
            })
          })
        })
      })
      setModelLanes(modelLanes)

      const platformLanes = {}
      selectedMedia.forEach(brand => { platformLanes[brand]={}; selectedPlatforms.forEach(p=>{platformLanes[brand][p]=[]}) })
      setPlatformLanes(platformLanes)

      // Build report
      const perMedia = {}
      selectedMedia.forEach(m=>{perMedia[m]=0})
      Object.values(editorial).forEach(md => { const bm=md.brands||{}; Object.entries(bm).forEach(([brand,arts]) => { if(perMedia.hasOwnProperty(brand)) perMedia[brand]+=(arts?.length||0) }) })
      const shortlisted = preResult?.shortlisted || shortlistPayload
      setMmReport({
        runAt:Date.now(), selectedSources:[...selectedSources], selectedMedia:[...selectedMedia],
        recencyHours, sourceCounts, fetchedTotal:allArticles.length, tooOld:tooOldCount,
        afterRecency:recent.length, rejected:preResult?.rejected||{duplicate:0,noMediaFit:0,lowScore:0},
        shortlistedCount:shortlistPayload.length, perMedia, filterMode,
        allArticles:[...tooOldArticles,...allTracked],
      })

      setProgress(100, 'Done!')
      setTimeout(() => useMmStore.getState().setProgress(0,''), 1800)

    } catch(err) {
      setErrorMsg(err.message)
      useMmStore.getState().setProgress(0,'')
    } finally {
      setAnalyzing(false)
    }
  }, [])

  return run
}
