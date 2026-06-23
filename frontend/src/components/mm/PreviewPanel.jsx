import { useState, useRef, useEffect } from 'react'
import { useMmStore, API_BASE, MEDIA_COLORS, PLAT_COLORS, IMAGE_MODEL_OPTIONS } from '../../store/mmStore'
import { useAccountStore } from '../../store/accountStore'
import { PLAT_ICONS } from '../../utils/platformIcons'
import SchedulePicker from './SchedulePicker'

const STATUS_CLASSES = {ready:'sb-ready',image:'sb-image',approved:'sb-approved',scheduled:'sb-scheduled',published:'sb-published',saved:'sb-saved'}
const STATUS_LABELS  = {ready:'Ready',image:'Needs Image',approved:'Approved',scheduled:'Scheduled',published:'Published',saved:'Saved'}
const SCHEDULABLE_PLATFORMS = ['X', 'Telegram']

async function callAppsScript(payload) {
  const { action, ...rest } = payload
  const pathMap = { approve:'/api/sheets/approve', schedule:'/api/sheets/schedule', uploadImage:'/api/sheets/upload-image', update:'/api/sheets/update' }
  const res = await fetch(`${API_BASE}${pathMap[action]||'/api/sheets/approve'}`, {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(rest)
  })
  if (!res.ok) throw new Error(`Sheets error ${res.status}`)
  return res.json()
}

async function sendToTelegram(card, imageB64) {
  const res = await fetch(`${API_BASE}/api/telegram/post`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({ imageB64:imageB64||'', headline:card.headline||'', copy:card.copy||'', hashtags:card.hashtags||[], link:card.link||'' })
  })
  if (!res.ok) { const e=await res.json().catch(()=>({})); throw new Error(e?.error||`Telegram error ${res.status}`) }
  return res.json()
}

async function sendToX(card, imageB64) {
  const res = await fetch(`${API_BASE}/api/twitter/post`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({ imageB64:imageB64||'', copy:card.copy||'', hashtags:card.hashtags||[], platform:card.platform, mediaBrand:card.media })
  })
  if (!res.ok) { const e=await res.json().catch(()=>({})); throw new Error(e?.error||`X error ${res.status}`) }
  return res.json()
}

async function createScheduledPost(card, mode, copyText, hashtagsState, generatedImg, scheduledAtIso) {
  const res = await fetch(`${API_BASE}/api/schedule/create`, {
    method:'POST', credentials:'include', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      cardId: mode === 'saved' ? card.card_id : card.id,
      savedCardId: mode === 'saved' ? card.id : null,
      brand: card.media, platform: card.platform, modelDisplay: card._modelDisplay||'',
      headline: card.headline, copy: copyText,
      hashtags: hashtagsState.length ? hashtagsState : (card.hashtags||[]),
      sentiment: card.sentiment, suitability: card.suitability, impact: card.impact, virality: card.virality,
      source: card.source, sourceUrl: card.link||'',
      imageB64: generatedImg || card._generatedImageB64 || '',
      imageUrl: card.imageUrl||'',
      scheduledAt: scheduledAtIso,
    })
  })
  if (!res.ok) { const e = await res.json().catch(()=>({})); throw new Error(e?.error || `Schedule failed (${res.status})`) }
}

export default function PreviewPanel({ mode = 'multimedia', card: cardProp, onClose }) {
  const { activeCard, setActiveCard, updateCardStatus, updatePlatformCard } = useMmStore()
  const { confirmScheduleSaved, discardSaved } = useAccountStore()
  const card = mode === 'saved' ? cardProp : activeCard
  const isOpen = !!card

  function _approveLabel(plat) {
    const p = (plat || '').trim().toLowerCase()
    if (p === 'telegram') return 'Post to Telegram'
    if (p === 'x' || p === 'twitter') return 'Post to X'
    return 'Approve Image'
  }

  const [editing, setEditing]         = useState(false)
  const [copyText, setCopyText]       = useState('')
  const [showImage, setShowImage]     = useState(false)
  const [showSchedule, setShowSchedule] = useState(false)
  const [imageModel, setImageModel]   = useState('openai/gpt-5.4-image-2')
  const [imagePrompt, setImagePrompt] = useState('')
  const [refImages, setRefImages]     = useState([])
  const [generatedImg, setGeneratedImg] = useState('')
  const [imgLoading, setImgLoading]   = useState(false)
  const [aiBrief, setAiBrief]         = useState(null)
  const [showAiBrief, setShowAiBrief] = useState(false)
  const [approveLabel, setApproveLabel] = useState('✓ Approve')
  const [approveImgLabel, setApproveImgLabel] = useState(() => _approveLabel(cardProp?.platform))
  const [saveLabel, setSaveLabel] = useState('Save for Later')
  const [schedDate, setSchedDate] = useState('')
  const [schedTime, setSchedTime] = useState('09:00')
  const [selectedVariant, setSelectedVariant] = useState(0)
  const [genPct, setGenPct] = useState(0)
  const [hashtagsState, setHashtagsState] = useState([])
  const [discardLabel, setDiscardLabel] = useState('Discard')
  const [confirmLabel, setConfirmLabel] = useState('✓ Confirm')
  const [savedStatus, setSavedStatus] = useState(null)
  const [scheduleSavedLabel, setScheduleSavedLabel] = useState('Confirm Schedule')
  const copyRef = useRef(null)

  const ESTIMATE_MS = 18000
  useEffect(() => {
    if (!card?.isGenerating) return
    setGenPct(0)
    const started = card.genStartedAt || Date.now()
    const tick = () => setGenPct(Math.min(92, Math.round(100 * (1 - Math.exp(-(Date.now() - started) / ESTIMATE_MS)))))
    tick()
    const id = setInterval(tick, 250)
    return () => { clearInterval(id); setGenPct(100) }
  }, [card?.id, card?.platform, card?.isGenerating, card?.genStartedAt])

  useEffect(() => {
    if (card) {
      setCopyText(card.copy || '')
      setEditing(false)
      setShowImage(false)
      setShowSchedule(false)
      setGeneratedImg('')
      setApproveLabel('✓ Approve')
      setApproveImgLabel(_approveLabel(card?.platform))
      setSaveLabel('Save for Later')
      setSelectedVariant(0)
      setHashtagsState(card.hashtags || [])
      setDiscardLabel('Discard')
      setScheduleSavedLabel('Confirm Schedule')
      setConfirmLabel('✓ Confirm')
      setSavedStatus(null)
    }
  }, [card?.id])

  if (!card) return null

  const mc = MEDIA_COLORS[card.media] || '#7a8499'
  const pc = PLAT_COLORS[card.platform] || '#7a8499'
  const sentColor = card.sentiment==='Bullish'?'#00d4a0':card.sentiment==='Bearish'?'#ef4455':'#7a8499'
  const displayStatus = mode === 'saved' ? (savedStatus || card.status) : card.status

  function markApproved() {
    if (mode === 'multimedia') updateCardStatus(card.id, 'approved')
    else setSavedStatus('approved')
  }

  async function handleApprove() {
    setApproveLabel('Saving…')
    try {
      await callAppsScript({ action:'approve', id:card.id, title:card.headline, source:card.source, sourceUrl:card.link||'', mediaBrand:card.media, platform:card.platform, copy:copyText, hashtags:card.hashtags||[], sentiment:card.sentiment, fitScore:card.suitability, impactScore:card.impact, viralityScore:card.virality, imageStatus:card.imageUrl?'Image Approved':'No Image', imageUrl:card.imageUrl||'' })
      markApproved()
      fetch(`${API_BASE}/api/account/log-action`, {
        method:'POST', credentials:'include', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ brand: card.media, platform: card.platform, modelDisplay: card._modelDisplay||'', headline: card.headline, action: 'approved' })
      }).catch(()=>{})
      if (card.platform==='X') setApproveLabel('✓ Saved — Approve Image below to post to X')
      else if (card.platform==='Telegram') setApproveLabel('✓ Saved — Approve Image to post to Telegram')
      else if (card.platform==='Instagram') setApproveLabel('✓ Saved to Sheets — post manually on Instagram')
      else setApproveLabel('✓ Approved')
    } catch(e) { markApproved(); setApproveLabel('✓ Approve') }
  }

  async function handleGenerateImage() {
    setImgLoading(true); setGeneratedImg(''); setAiBrief(null)
    try {
      const res = await fetch(`${API_BASE}/api/image/generate`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({ article:{title:card.headline}, platform:card.platform||'X', mediaBrand:card.media||'ChainReporter', sentiment:card.sentiment||'Neutral', model:imageModel, copy:copyText, ...(imagePrompt.trim() && {imageDirection:imagePrompt.trim()}), ...(refImages.length && {referenceImages:refImages.map(r=>r.b64)}) })
      })
      if (!res.ok) { const e=await res.json().catch(()=>({})); throw new Error(e?.error||res.statusText) }
      const data = await res.json()
      if (!data.imageB64) throw new Error('No image data returned')
      setGeneratedImg(data.imageB64)
      if (mode === 'multimedia') useMmStore.getState().activeCard._generatedImageB64 = data.imageB64
      if (data.brief) setAiBrief({ brief: data.brief, prompt: data.prompt })
    } catch(e) { alert('Image generation failed: '+e.message) }
    finally { setImgLoading(false) }
  }

  async function handleApproveImage() {
    const b64 = generatedImg || card._generatedImageB64
    if (!b64) { alert('No image to approve. Generate an image first.'); return }
    setApproveImgLabel('Uploading to Drive…')
    try {
      const up = await callAppsScript({ action:'uploadImage', imageB64:b64, mediaBrand:card.media, platform:card.platform||'X' })
      const driveUrl = up?.driveUrl || ''
      if (mode === 'multimedia') useMmStore.getState().activeCard.imageUrl = driveUrl
      try {
        await callAppsScript({ action:'approve', id:card.id, title:card.headline, source:card.source, sourceUrl:card.link||'', mediaBrand:card.media, platform:card.platform, copy:copyText, hashtags:card.hashtags||[], sentiment:card.sentiment, fitScore:card.suitability, impactScore:card.impact, viralityScore:card.virality, imageStatus:'Image Approved', imageUrl:driveUrl })
      } catch(_) {}
      const plat = (card.platform || '').trim().toLowerCase()
      if (plat === 'x' || plat === 'twitter') {
        setApproveImgLabel('Posting to X…')
        try { await sendToX(card, b64); markApproved(); setApproveImgLabel('✓ Posted to X') }
        catch(e) { markApproved(); setApproveImgLabel('✗ X failed: '+e.message.slice(0,40)) }
      } else if (plat === 'telegram') {
        setApproveImgLabel('Posting to Telegram…')
        try { await sendToTelegram(card, b64); markApproved(); setApproveImgLabel('✓ Posted to Telegram') }
        catch(e) { markApproved(); setApproveImgLabel('✗ Telegram: '+e.message.slice(0,40)) }
      } else if (plat === 'instagram') {
        markApproved(); setApproveImgLabel('✓ Image saved — post manually on Instagram')
      } else {
        markApproved(); setApproveImgLabel('✓ Image saved to Drive — route card to a platform to post')
      }
    } catch(e) { setApproveImgLabel('Error: '+e.message.slice(0,50)) }
  }

  async function handleSchedule() {
    if (!schedDate||!schedTime) { alert('Select date and time'); return }
    const scheduledAtIso = new Date(`${schedDate}T${schedTime}`).toISOString()
    if (new Date(scheduledAtIso) <= new Date()) { alert('Please pick a time in the future'); return }
    try {
      await callAppsScript({ action:'schedule', id:card.id, title:card.headline, source:card.source, sourceUrl:card.link||'', mediaBrand:card.media, platform:card.platform, copy:copyText, hashtags:card.hashtags||[], sentiment:card.sentiment, fitScore:card.suitability, impactScore:card.impact, viralityScore:card.virality, scheduledDate:schedDate, scheduledTime:schedTime })
      if (SCHEDULABLE_PLATFORMS.includes(card.platform)) {
        await createScheduledPost(card, mode, copyText, hashtagsState, generatedImg, scheduledAtIso)
        useAccountStore.getState().fetchScheduled()
      }
      updateCardStatus(card.id,'scheduled')
      fetch(`${API_BASE}/api/account/log-action`, {
        method:'POST', credentials:'include', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ brand: card.media, platform: card.platform, modelDisplay: card._modelDisplay||'', headline: card.headline, action: 'scheduled' })
      }).catch(()=>{})
      setShowSchedule(false)
    } catch(e) { alert('Schedule error: '+e.message) }
  }

  async function handleSaveForLater() {
    setSaveLabel('Saving…')
    try {
      const res = await fetch(`${API_BASE}/api/account/save`, {
        method:'POST', credentials:'include', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          id: card.id, media: card.media, platform: card.platform,
          modelDisplay: card._modelDisplay, modelColor: card._modelColor,
          headline: card.headline, copy: copyText, hashtags: hashtagsState,
          sentiment: card.sentiment, suitability: card.suitability, impact: card.impact, virality: card.virality,
          source: card.source, link: card.link||'', initials: card.initials, srcColor: card.srcColor,
          variants: card.variants||[],
        })
      })
      if (!res.ok) { const e = await res.json().catch(()=>({})); throw new Error(e?.error || `Save failed (${res.status})`) }
      setSaveLabel('✓ Saved for Later')
    } catch(e) { setSaveLabel('Save for Later'); alert('Save failed: '+e.message) }
  }

  async function handleConfirmScheduleSaved() {
    if (!schedDate||!schedTime) { alert('Select date and time'); return }
    const scheduledAtIso = new Date(`${schedDate}T${schedTime}`).toISOString()
    if (new Date(scheduledAtIso) <= new Date()) { alert('Please pick a time in the future'); return }
    setScheduleSavedLabel('Scheduling…')
    try {
      if (SCHEDULABLE_PLATFORMS.includes(card.platform)) {
        await createScheduledPost(card, mode, copyText, hashtagsState, generatedImg, scheduledAtIso)
        useAccountStore.getState().fetchScheduled()
      }
      const ok = await confirmScheduleSaved(card.id, schedDate, schedTime, copyText, hashtagsState)
      if (ok) onClose?.()
      else setScheduleSavedLabel('Confirm Schedule')
    } catch(e) { setScheduleSavedLabel('Confirm Schedule'); alert('Schedule error: '+e.message) }
  }

  async function handleDiscard() {
    setDiscardLabel('Discarding…')
    const ok = await discardSaved(card.id)
    if (ok) onClose?.()
    else setDiscardLabel('Discard')
  }

  async function handleConfirmSaved() {
    setConfirmLabel('Saving…')
    try {
      await callAppsScript({ action:'approve', id:card.id, title:card.headline, source:card.source, sourceUrl:card.link||'', mediaBrand:card.media, platform:card.platform, copy:copyText, hashtags:card.hashtags||[], sentiment:card.sentiment, fitScore:card.suitability, impactScore:card.impact, viralityScore:card.virality, imageStatus:card.imageUrl?'Image Approved':'No Image', imageUrl:card.imageUrl||'' })
      markApproved()
      fetch(`${API_BASE}/api/account/log-action`, {
        method:'POST', credentials:'include', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ brand: card.media, platform: card.platform, modelDisplay: card._modelDisplay||'', headline: card.headline, action: 'approved' })
      }).catch(()=>{})
      if (card.platform==='X') setConfirmLabel('✓ Saved — Approve Image below to post to X')
      else if (card.platform==='Telegram') setConfirmLabel('✓ Saved — Approve Image to post to Telegram')
      else if (card.platform==='Instagram') setConfirmLabel('✓ Saved to Sheets — post manually on Instagram')
      else setConfirmLabel('✓ Approved')
    } catch(e) { markApproved(); setConfirmLabel('✓ Confirm') }
  }

  function openSchedule() {
    setShowImage(false)
    setShowSchedule(s => {
      if (!s) {
        const d = new Date(); d.setDate(d.getDate()+1)
        setSchedDate(d.toISOString().split('T')[0])
        setSchedTime('09:00')
      }
      return !s
    })
  }

  function handleClose() {
    if (mode === 'saved') onClose?.()
    else setActiveCard(null)
  }

  const panelId = mode === 'saved' ? 'saved-detail-panel' : 'preview-panel'
  const overlayId = mode === 'saved' ? 'saved-detail-overlay' : 'preview-overlay'

  return (
    <>
      {/* Overlay */}
      <div id={overlayId} className={isOpen?'open':''}></div>

      {/* Panel */}
      <div id={panelId} className={isOpen?'open':''}>
        {/* Header */}
        <div style={{padding:'14px 16px',borderBottom:'1px solid rgba(255,255,255,.07)',display:'flex',alignItems:'center',justifyContent:'space-between',flexShrink:0}}>
          <div style={{display:'flex',alignItems:'center',gap:6,flexWrap:'wrap'}}>
            <div style={{padding:'2px 8px',borderRadius:5,fontSize:9,fontWeight:700,letterSpacing:'.05em',background:mc+'20',color:mc,border:`1px solid ${mc}35`}}>{card.media}</div>
            <div style={{width:22,height:22,borderRadius:6,display:'flex',alignItems:'center',justifyContent:'center',background:pc+'1a',color:pc}}>{PLAT_ICONS[card.platform]}</div>
            <span style={{fontFamily:"'Space Grotesk',sans-serif",fontWeight:700,fontSize:13,color:'#f0f2f8'}}>{card.platform}</span>
            <span className={`sbadge`} style={{fontSize:9,background:sentColor+'15',color:sentColor,border:`1px solid ${sentColor}35`}}>{card.sentiment}</span>
          </div>
          <button onClick={handleClose} style={{background:'none',border:'none',cursor:'pointer',color:'#7a8499',padding:4,borderRadius:6,transition:'color .18s,background .18s'}}
            onMouseEnter={e=>{e.currentTarget.style.color='#f0f2f8';e.currentTarget.style.background='rgba(255,255,255,.07)'}}
            onMouseLeave={e=>{e.currentTarget.style.color='#7a8499';e.currentTarget.style.background='none'}}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
          </button>
        </div>

        {/* Body */}
        <div style={{padding:16,display:'flex',flexDirection:'column',gap:14}}>
          {/* Source */}
          <div style={{display:'flex',alignItems:'center',gap:8}}>
            <div style={{width:20,height:20,borderRadius:5,flexShrink:0,display:'flex',alignItems:'center',justifyContent:'center',fontSize:7,fontWeight:700,background:card.srcColor+'1a',color:card.srcColor,border:`1px solid ${card.srcColor}30`}}>{card.initials}</div>
            <span style={{fontSize:11,color:'#7a8499'}}>{card.source}</span>
            <span style={{fontSize:10,color:'#4a5568',marginLeft:'auto'}}>{card.timeAgo}</span>
          </div>

          {/* Headline */}
          <h3 style={{fontFamily:"'Space Grotesk',sans-serif",fontWeight:700,fontSize:14,color:'#f0f2f8',lineHeight:1.4,letterSpacing:'-.02em'}}>{card.headline}</h3>

          {/* Scores */}
          <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
            <span className="sbadge sb-ready" style={{fontSize:9.5}}>⚡ Fit {card.suitability}/10</span>
            <span className="sbadge sb-image" style={{fontSize:9.5}}>Impact {card.impact}/10</span>
            <span className="sbadge sb-scheduled" style={{fontSize:9.5}}>Virality {card.virality}/10</span>
          </div>

          {/* Why boxes */}
          {mode === 'multimedia' && (
            <div style={{background:'rgba(255,255,255,.04)',border:'1px solid rgba(255,255,255,.08)',borderRadius:10,padding:'10px 12px',display:'flex',flexDirection:'column',gap:9}}>
              <div>
                <p style={{fontSize:10,fontWeight:600,color:'#7a8499',marginBottom:4,letterSpacing:'.06em',textTransform:'uppercase'}}>Why this media brand?</p>
                <p style={{fontSize:12,color:'#c8cdd8',lineHeight:1.55}}>{card.mediaReason||'—'}</p>
              </div>
              <div style={{borderTop:'1px solid rgba(255,255,255,.06)',paddingTop:9}}>
                <p style={{fontSize:10,fontWeight:600,color:'#7a8499',marginBottom:4,letterSpacing:'.06em',textTransform:'uppercase'}}>Why this platform?</p>
                <p style={{fontSize:12,color:'#c8cdd8',lineHeight:1.55}}>{card.platReason||'—'}</p>
              </div>
            </div>
          )}

          {/* Copy */}
          <div>
            <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:6}}>
              <p style={{fontSize:10,fontWeight:600,color:'#7a8499',letterSpacing:'.06em',textTransform:'uppercase'}}>Generated Copy</p>
              <button onClick={()=>{ setEditing(e=>!e) }} style={{fontSize:10,fontWeight:600,color:'#00d4a0',background:'none',border:'none',cursor:'pointer',padding:'2px 6px',borderRadius:5,transition:'background .18s'}}
                onMouseEnter={e=>e.currentTarget.style.background='rgba(0,212,160,.1)'} onMouseLeave={e=>e.currentTarget.style.background='none'}>
                {editing ? 'Done' : 'Edit'}
              </button>
            </div>
            {card.isGenerating
              ? (
                <div style={{background:'rgba(155,114,245,.06)',border:'1px solid rgba(155,114,245,.22)',borderRadius:8,padding:'14px 14px'}}>
                  <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:10}}>
                    <span className="spinner" style={{width:13,height:13,border:'1.5px solid rgba(155,114,245,.25)',borderTopColor:'#9b72f5'}}/>
                    <span style={{fontSize:12,color:'#c8cdd8'}}>Generating 3 platform-specific variants — please wait…</span>
                  </div>
                  <div style={{height:6,borderRadius:4,background:'rgba(255,255,255,.06)',overflow:'hidden'}}>
                    <div style={{height:'100%',width:`${genPct}%`,borderRadius:4,background:'linear-gradient(90deg,#9b72f5,#00d4a0)',transition:'width .25s ease-out'}}/>
                  </div>
                  <div style={{marginTop:6,fontSize:10.5,color:'#7a8499',textAlign:'right'}}>{genPct}%</div>
                </div>
              )
              : editing
              ? <textarea value={copyText} onChange={e=>setCopyText(e.target.value)} style={{width:'100%',minHeight:80,background:'rgba(0,212,160,.05)',border:'1px solid rgba(0,212,160,.45)',borderRadius:8,padding:'8px 10px',fontSize:13,color:'#f0f2f8',lineHeight:1.65,fontFamily:'Inter,sans-serif',resize:'vertical',boxShadow:'0 0 0 3px rgba(0,212,160,.08)',outline:'none'}}/>
              : <div id="preview-copy" style={{fontSize:13,color:'#c8cdd8',lineHeight:1.65}}>{copyText}</div>
            }
          </div>

          {/* Variant picker */}
          {(card.variants||[]).length > 1 && (
            <div>
              <p style={{fontSize:10,fontWeight:600,color:'#7a8499',letterSpacing:'.06em',textTransform:'uppercase',marginBottom:6}}>Variants — pick one</p>
              <div style={{display:'flex',flexDirection:'column',gap:6}}>
                {card.variants.map((v,i)=>(
                  <div key={i} onClick={()=>{
                      setSelectedVariant(i); setCopyText(v.copy); setHashtagsState(v.hashtags||[])
                      if (mode === 'multimedia') updatePlatformCard(card.id, card.platform, { copy:v.copy, hashtags:v.hashtags, charCount:v.copy.length })
                    }}
                    style={{cursor:'pointer',padding:'7px 10px',borderRadius:7,
                      border:`1px solid ${i===selectedVariant?pc+'70':'rgba(255,255,255,.08)'}`,
                      background:i===selectedVariant?pc+'14':'rgba(255,255,255,.03)'}}>
                    {v.label && (
                      <span style={{display:'inline-block',fontSize:8.5,fontWeight:700,letterSpacing:'.07em',textTransform:'uppercase',
                        padding:'1.5px 6px',borderRadius:4,marginBottom:4,
                        background:(i===selectedVariant?pc:'#7a8499')+'1f',
                        color:i===selectedVariant?pc:'#7a8499',
                        border:`1px solid ${(i===selectedVariant?pc:'#7a8499')}40`}}>{v.label}</span>
                    )}
                    <div style={{fontSize:11,lineHeight:1.5,color:i===selectedVariant?'#f0f2f8':'#7a8499',
                      display:'-webkit-box',WebkitLineClamp:2,WebkitBoxOrient:'vertical',overflow:'hidden'}}>
                      {v.copy}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Hashtags */}
          <div style={{display:'flex',flexWrap:'wrap',gap:5}}>
            {hashtagsState.map(h=>(
              <span key={h} style={{fontSize:10.5,fontWeight:600,color:pc}}>{h}</span>
            ))}
          </div>

          {/* Source link */}
          <div style={{display:'flex',alignItems:'center',gap:6}}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#7a8499" strokeWidth="1.8" strokeLinecap="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
            <a href={card.link||'#'} target="_blank" rel="noreferrer" style={{fontSize:11,color:'#3d8ef0',textDecoration:'none',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{card.link&&card.link!=='#'?'View source article →':'No link available'}</a>
          </div>

          {/* Status */}
          <div style={{display:'flex',alignItems:'center',justifyContent:'space-between'}}>
            <span style={{fontSize:11,color:'#7a8499'}}>Status:</span>
            <span className={`sbadge ${STATUS_CLASSES[displayStatus]||'sb-ready'}`}>{STATUS_LABELS[displayStatus]||'Ready'}</span>
          </div>
        </div>

        {/* Footer actions */}
        <div style={{padding:'14px 16px',borderTop:'1px solid rgba(255,255,255,.07)',display:'flex',flexDirection:'column',gap:8,flexShrink:0}}>
          {mode === 'multimedia' ? (
            <>
              <div style={{display:'flex',gap:8}}>
                <button className="btn-mint" style={{flex:1,padding:9,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase',fontWeight:700}} onClick={handleApprove}>{approveLabel}</button>
                <button className="btn-ghost" style={{flex:1,padding:9,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase'}} onClick={()=>{setShowImage(s=>!s);setShowSchedule(false)}}>Needs Image</button>
              </div>
              <div style={{display:'flex',gap:8}}>
                <button className="btn-ghost" style={{flex:1,padding:8,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase'}} onClick={openSchedule}>Schedule</button>
                <button className="btn-ghost" style={{flex:1,padding:8,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase'}} onClick={handleSaveForLater} disabled={saveLabel!=='Save for Later'}>{saveLabel}</button>
              </div>
            </>
          ) : (
            <>
              <div style={{display:'flex',gap:8}}>
                <button className="btn-mint" style={{flex:1,padding:9,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase',fontWeight:700}} onClick={handleConfirmSaved}>{confirmLabel}</button>
                <button className="btn-ghost" style={{flex:1,padding:9,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase'}} onClick={()=>{setShowImage(s=>!s);setShowSchedule(false)}}>Generate Image</button>
              </div>
              <div style={{display:'flex',gap:8}}>
                <button className="btn-ghost" style={{flex:1,padding:8,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase'}} onClick={openSchedule}>Schedule</button>
                <button className="btn-ghost" style={{flex:1,padding:8,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase'}} onClick={handleDiscard} disabled={discardLabel!=='Discard'}>{discardLabel}</button>
              </div>
            </>
          )}

          {/* Image section */}
          {showImage && (
            <div style={{display:'flex',flexDirection:'column',gap:8,borderTop:'1px solid rgba(255,255,255,.06)',paddingTop:10}}>
              <p style={{fontSize:10,fontWeight:600,color:'#7a8499',marginBottom:4,letterSpacing:'.06em',textTransform:'uppercase'}}>Image Direction <span style={{fontWeight:400,textTransform:'none',letterSpacing:0}}>(optional)</span></p>
              <textarea value={imagePrompt} onChange={e=>setImagePrompt(e.target.value)} placeholder="Describe what you want in the image… e.g. show the wolf mascot, use a comparison table layout" rows={2} className="cr-input" style={{width:'100%',padding:'7px 10px',fontSize:11,resize:'vertical',minHeight:36}} />
              <p style={{fontSize:10,fontWeight:600,color:'#7a8499',marginBottom:4,letterSpacing:'.06em',textTransform:'uppercase',marginTop:4}}>Reference Images <span style={{fontWeight:400,textTransform:'none',letterSpacing:0}}>(optional, max 3)</span></p>
              <label style={{display:'inline-flex',alignItems:'center',gap:5,padding:'6px 12px',fontSize:10,fontWeight:600,borderRadius:8,border:'1px solid rgba(155,114,245,.35)',background:'rgba(155,114,245,.08)',color:'#9b72f5',cursor:'pointer',letterSpacing:'.04em'}}>
                + Add Images
                <input type="file" accept="image/*" multiple style={{display:'none'}} onChange={e=>{
                  const files = Array.from(e.target.files).slice(0, 3 - refImages.length)
                  if (!files.length) return
                  Promise.all(files.map(f=>new Promise(res=>{const r=new FileReader();r.onload=()=>res({name:f.name,b64:r.result,preview:r.result});r.readAsDataURL(f)}))).then(imgs=>setRefImages(prev=>[...prev,...imgs].slice(0,3)))
                  e.target.value = ''
                }} />
              </label>
              {refImages.length > 0 && (
                <div style={{display:'flex',gap:6,flexWrap:'wrap'}}>
                  {refImages.map((img,i) => (
                    <div key={i} style={{position:'relative',width:52,height:52}}>
                      <img src={img.preview} alt={img.name} style={{width:52,height:52,objectFit:'cover',borderRadius:6,border:'1px solid rgba(255,255,255,.1)'}} />
                      <button onClick={()=>setRefImages(prev=>prev.filter((_,j)=>j!==i))} style={{position:'absolute',top:-4,right:-4,width:16,height:16,borderRadius:'50%',border:'none',background:'#ef4455',color:'#fff',fontSize:9,cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'center',lineHeight:1,padding:0}}>×</button>
                    </div>
                  ))}
                </div>
              )}
              <p style={{fontSize:10,fontWeight:600,color:'#7a8499',marginBottom:7,letterSpacing:'.06em',textTransform:'uppercase',marginTop:4}}>Image Generation Model</p>
              <select value={imageModel} onChange={e=>setImageModel(e.target.value)} className="cr-input" style={{width:'100%',padding:'7px 10px',fontSize:11}}>
                {IMAGE_MODEL_OPTIONS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
              <button onClick={handleGenerateImage} disabled={imgLoading}
                style={{width:'100%',padding:9,fontSize:11,fontWeight:700,letterSpacing:'.06em',textTransform:'uppercase',border:'none',borderRadius:9,cursor:'pointer',background:'linear-gradient(135deg,#f0a040,#e08030)',color:'#07090e',opacity:imgLoading?0.6:1,transition:'opacity .18s'}}>
                {imgLoading ? 'Generating…' : 'Create Image'}
              </button>
              {generatedImg && (
                <div style={{display:'flex',flexDirection:'column',gap:8}}>
                  <img src={`data:image/png;base64,${generatedImg}`} alt="Generated" style={{width:'100%',borderRadius:9,border:'1px solid rgba(255,255,255,.1)',display:'block'}} />
                  <div style={{display:'flex',gap:6}}>
                    <button className="btn-mint" style={{flex:1,padding:8,fontSize:10,letterSpacing:'.06em',textTransform:'uppercase',fontWeight:700}} onClick={handleApproveImage}>{approveImgLabel}</button>
                    <button className="btn-ghost" style={{flex:1,padding:8,fontSize:10,letterSpacing:'.06em',textTransform:'uppercase'}} onClick={handleGenerateImage}>Regenerate</button>
                  </div>
                </div>
              )}
              {aiBrief && (
                <div style={{display:'flex',flexDirection:'column',gap:6}}>
                  <button onClick={()=>setShowAiBrief(s=>!s)} className="btn-ghost"
                    style={{width:'100%',padding:7,fontSize:10,letterSpacing:'.06em',textTransform:'uppercase'}}>
                    {showAiBrief ? 'Hide AI Brief ▴' : 'Show AI Brief ▾'}
                  </button>
                  {showAiBrief && (
                    <div style={{display:'flex',flexDirection:'column',gap:8}}>
                      <div>
                        <p style={{fontSize:10,fontWeight:600,color:'#7a8499',marginBottom:5,letterSpacing:'.06em',textTransform:'uppercase'}}>Visual Brief (JSON)</p>
                        <pre style={{margin:0,padding:'8px 10px',fontSize:10,lineHeight:1.5,color:'#c8cdd8',background:'rgba(0,0,0,.3)',border:'1px solid rgba(255,255,255,.08)',borderRadius:8,overflowX:'auto',whiteSpace:'pre-wrap',wordBreak:'break-word'}}>{JSON.stringify(aiBrief.brief, null, 2)}</pre>
                      </div>
                      <div>
                        <p style={{fontSize:10,fontWeight:600,color:'#7a8499',marginBottom:5,letterSpacing:'.06em',textTransform:'uppercase'}}>Assembled Prompt</p>
                        <pre style={{margin:0,padding:'8px 10px',fontSize:10,lineHeight:1.5,color:'#c8cdd8',background:'rgba(0,0,0,.3)',border:'1px solid rgba(255,255,255,.08)',borderRadius:8,overflowX:'auto',whiteSpace:'pre-wrap',wordBreak:'break-word'}}>{aiBrief.prompt}</pre>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Schedule section */}
          {showSchedule && (
            <div style={{display:'flex',flexDirection:'column',gap:8,borderTop:'1px solid rgba(255,255,255,.06)',paddingTop:10}}>
              <p style={{fontSize:10,fontWeight:600,color:'#7a8499',marginBottom:7,letterSpacing:'.06em',textTransform:'uppercase'}}>Schedule Post</p>
              {generatedImg && (
                <div style={{display:'flex',alignItems:'center',gap:8,padding:'6px 8px',borderRadius:8,background:'rgba(0,212,160,.06)',border:'1px solid rgba(0,212,160,.2)'}}>
                  <img src={`data:image/png;base64,${generatedImg}`} alt="Generated" style={{width:44,height:44,borderRadius:6,objectFit:'cover',flexShrink:0}} />
                  <span style={{fontSize:11,color:'#00d4a0'}}>Image will be attached to this post</span>
                </div>
              )}
              <SchedulePicker date={schedDate} time={schedTime} onDateChange={setSchedDate} onTimeChange={setSchedTime}
                onConfirm={mode === 'multimedia' ? handleSchedule : handleConfirmScheduleSaved}
                confirmLabel={mode === 'multimedia' ? 'Confirm Schedule' : scheduleSavedLabel} />
            </div>
          )}
        </div>
      </div>
    </>
  )
}
