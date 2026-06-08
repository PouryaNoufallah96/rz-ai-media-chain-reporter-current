import { useState, useRef, useEffect } from 'react'
import { useMmStore, API_BASE, MEDIA_COLORS, PLAT_COLORS } from '../../store/mmStore'

const PLAT_ICONS = {
  X:        <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.81l7.73-8.835L1.254 2.25H8.08l4.253 5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>,
  Telegram: <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8l-1.7 8c-.12.56-.45.7-.9.44l-2.5-1.84-1.2 1.16c-.13.13-.24.24-.5.24l.18-2.52 4.56-4.12c.2-.18-.04-.27-.3-.1L7.56 15.4l-2.46-.77c-.53-.17-.54-.53.12-.78l9.62-3.72c.44-.16.83.1.8.67z"/></svg>,
  Instagram:<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><rect x="2" y="2" width="20" height="20" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r=".7" fill="currentColor" stroke="none"/></svg>,
}
const STATUS_CLASSES = {ready:'sb-ready',image:'sb-image',approved:'sb-approved',scheduled:'sb-scheduled',published:'sb-published'}
const STATUS_LABELS  = {ready:'Ready',image:'Needs Image',approved:'Approved',scheduled:'Scheduled',published:'Published'}

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

export default function PreviewPanel() {
  const { activeCard, setActiveCard, updateCardStatus, updatePlatformCard } = useMmStore()
  const card = activeCard
  const isOpen = !!card

  const [editing, setEditing]         = useState(false)
  const [copyText, setCopyText]       = useState('')
  const [showImage, setShowImage]     = useState(false)
  const [showSchedule, setShowSchedule] = useState(false)
  const [imageModel, setImageModel]   = useState('openai/gpt-5.4-image-2')
  const [generatedImg, setGeneratedImg] = useState('')
  const [imgLoading, setImgLoading]   = useState(false)
  const [approveLabel, setApproveLabel] = useState('✓ Approve')
  const [approveImgLabel, setApproveImgLabel] = useState('✓ Approve Image')
  const [schedDate, setSchedDate] = useState('')
  const [schedTime, setSchedTime] = useState('09:00')
  const [selectedVariant, setSelectedVariant] = useState(0)
  const copyRef = useRef(null)

  useEffect(() => {
    if (card) {
      setCopyText(card.copy || '')
      setEditing(false)
      setShowImage(false)
      setShowSchedule(false)
      setGeneratedImg('')
      setApproveLabel('✓ Approve')
      setApproveImgLabel('✓ Approve Image')
      setSelectedVariant(0)
    }
  }, [card?.id])

  if (!card) return null

  const mc = MEDIA_COLORS[card.media] || '#7a8499'
  const pc = PLAT_COLORS[card.platform] || '#7a8499'
  const sentColor = card.sentiment==='Bullish'?'#00d4a0':card.sentiment==='Bearish'?'#ef4455':'#7a8499'

  async function handleApprove() {
    setApproveLabel('Saving…')
    try {
      await callAppsScript({ action:'approve', id:card.id, title:card.headline, source:card.source, sourceUrl:card.link||'', mediaBrand:card.media, platform:card.platform, copy:copyText, hashtags:card.hashtags||[], sentiment:card.sentiment, fitScore:card.suitability, impactScore:card.impact, viralityScore:card.virality, imageStatus:card.imageUrl?'Image Approved':'No Image', imageUrl:card.imageUrl||'' })
      updateCardStatus(card.id, 'approved')
      if (card.platform==='X') setApproveLabel('✓ Saved — Approve Image below to post to X')
      else if (card.platform==='Telegram') setApproveLabel('✓ Saved — Approve Image to post to Telegram')
      else if (card.platform==='Instagram') setApproveLabel('✓ Saved to Sheets — post manually on Instagram')
      else setApproveLabel('✓ Approved')
    } catch(e) { updateCardStatus(card.id,'approved'); setApproveLabel('✓ Approve') }
  }

  async function handleGenerateImage() {
    setImgLoading(true); setGeneratedImg('')
    try {
      const res = await fetch(`${API_BASE}/api/image/generate`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({ article:{title:card.headline}, platform:card.platform||'X', mediaBrand:card.media||'ChainReporter', sentiment:card.sentiment||'Neutral', model:imageModel })
      })
      if (!res.ok) { const e=await res.json().catch(()=>({})); throw new Error(e?.error||res.statusText) }
      const data = await res.json()
      if (!data.imageB64) throw new Error('No image data returned')
      setGeneratedImg(data.imageB64)
      useMmStore.getState().activeCard._generatedImageB64 = data.imageB64
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
      useMmStore.getState().activeCard.imageUrl = driveUrl
      try {
        await callAppsScript({ action:'approve', id:card.id, title:card.headline, source:card.source, sourceUrl:card.link||'', mediaBrand:card.media, platform:card.platform, copy:copyText, hashtags:card.hashtags||[], sentiment:card.sentiment, fitScore:card.suitability, impactScore:card.impact, viralityScore:card.virality, imageStatus:'Image Approved', imageUrl:driveUrl })
      } catch(_) {}
      if (card.platform==='X') {
        setApproveImgLabel('Posting to X…')
        try { await sendToX(card, b64); updateCardStatus(card.id,'approved'); setApproveImgLabel('✓ Posted to X') }
        catch(e) { updateCardStatus(card.id,'approved'); setApproveImgLabel('✗ X failed: '+e.message.slice(0,40)) }
      } else if (card.platform==='Telegram') {
        setApproveImgLabel('Posting to Telegram…')
        try { await sendToTelegram(card, b64); updateCardStatus(card.id,'approved'); setApproveImgLabel('✓ Posted to Telegram') }
        catch(e) { updateCardStatus(card.id,'approved'); setApproveImgLabel('✗ Telegram: '+e.message.slice(0,40)) }
      } else if (card.platform==='Instagram') {
        updateCardStatus(card.id,'approved'); setApproveImgLabel('✓ Image saved — post manually on Instagram')
      } else {
        updateCardStatus(card.id,'approved'); setApproveImgLabel('✓ Image Approved')
      }
    } catch(e) { setApproveImgLabel('Error: '+e.message.slice(0,50)) }
  }

  async function handleSchedule() {
    if (!schedDate||!schedTime) { alert('Select date and time'); return }
    try {
      await callAppsScript({ action:'schedule', id:card.id, title:card.headline, source:card.source, sourceUrl:card.link||'', mediaBrand:card.media, platform:card.platform, copy:copyText, hashtags:card.hashtags||[], sentiment:card.sentiment, fitScore:card.suitability, impactScore:card.impact, viralityScore:card.virality, scheduledDate:schedDate, scheduledTime:schedTime })
      updateCardStatus(card.id,'scheduled')
      setShowSchedule(false)
    } catch(e) { alert('Schedule error: '+e.message) }
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

  return (
    <>
      {/* Overlay */}
      <div id="preview-overlay" className={isOpen?'open':''} onClick={()=>setActiveCard(null)}></div>

      {/* Panel */}
      <div id="preview-panel" className={isOpen?'open':''}>
        {/* Header */}
        <div style={{padding:'14px 16px',borderBottom:'1px solid rgba(255,255,255,.07)',display:'flex',alignItems:'center',justifyContent:'space-between',flexShrink:0}}>
          <div style={{display:'flex',alignItems:'center',gap:6,flexWrap:'wrap'}}>
            <div style={{padding:'2px 8px',borderRadius:5,fontSize:9,fontWeight:700,letterSpacing:'.05em',background:mc+'20',color:mc,border:`1px solid ${mc}35`}}>{card.media}</div>
            <div style={{width:22,height:22,borderRadius:6,display:'flex',alignItems:'center',justifyContent:'center',background:pc+'1a',color:pc}}>{PLAT_ICONS[card.platform]}</div>
            <span style={{fontFamily:"'Space Grotesk',sans-serif",fontWeight:700,fontSize:13,color:'#f0f2f8'}}>{card.platform}</span>
            <span className={`sbadge`} style={{fontSize:9,background:sentColor+'15',color:sentColor,border:`1px solid ${sentColor}35`}}>{card.sentiment}</span>
          </div>
          <button onClick={()=>setActiveCard(null)} style={{background:'none',border:'none',cursor:'pointer',color:'#7a8499',padding:4,borderRadius:6,transition:'color .18s,background .18s'}}
            onMouseEnter={e=>{e.currentTarget.style.color='#f0f2f8';e.currentTarget.style.background='rgba(255,255,255,.07)'}}
            onMouseLeave={e=>{e.currentTarget.style.color='#7a8499';e.currentTarget.style.background='none'}}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
          </button>
        </div>

        {/* Body */}
        <div style={{flex:1,overflowY:'auto',padding:16,display:'flex',flexDirection:'column',gap:14}}>
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

          {/* Copy */}
          <div>
            <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:6}}>
              <p style={{fontSize:10,fontWeight:600,color:'#7a8499',letterSpacing:'.06em',textTransform:'uppercase'}}>Generated Copy</p>
              <button onClick={()=>{ setEditing(e=>!e) }} style={{fontSize:10,fontWeight:600,color:'#00d4a0',background:'none',border:'none',cursor:'pointer',padding:'2px 6px',borderRadius:5,transition:'background .18s'}}
                onMouseEnter={e=>e.currentTarget.style.background='rgba(0,212,160,.1)'} onMouseLeave={e=>e.currentTarget.style.background='none'}>
                {editing ? 'Done' : 'Edit'}
              </button>
            </div>
            {editing
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
                      setSelectedVariant(i); setCopyText(v.copy)
                      updatePlatformCard(card.id, card.platform, { copy:v.copy, hashtags:v.hashtags, charCount:v.copy.length })
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
            {(card.hashtags||[]).map(h=>(
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
            <span className={`sbadge ${STATUS_CLASSES[card.status]||'sb-ready'}`}>{STATUS_LABELS[card.status]||'Ready'}</span>
          </div>
        </div>

        {/* Footer actions */}
        <div style={{padding:'14px 16px',borderTop:'1px solid rgba(255,255,255,.07)',display:'flex',flexDirection:'column',gap:8,flexShrink:0}}>
          <div style={{display:'flex',gap:8}}>
            <button className="btn-mint" style={{flex:1,padding:9,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase',fontWeight:700}} onClick={handleApprove}>{approveLabel}</button>
            <button className="btn-ghost" style={{flex:1,padding:9,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase'}} onClick={()=>{setShowImage(s=>!s);setShowSchedule(false)}}>Needs Image</button>
          </div>
          <button className="btn-ghost" style={{width:'100%',padding:8,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase'}} onClick={openSchedule}>Schedule</button>

          {/* Image section */}
          {showImage && (
            <div style={{display:'flex',flexDirection:'column',gap:8,borderTop:'1px solid rgba(255,255,255,.06)',paddingTop:10}}>
              <p style={{fontSize:10,fontWeight:600,color:'#7a8499',marginBottom:7,letterSpacing:'.06em',textTransform:'uppercase'}}>Image Generation Model</p>
              <select value={imageModel} onChange={e=>setImageModel(e.target.value)} className="cr-input" style={{width:'100%',padding:'7px 10px',fontSize:11}}>
                <option value="openai/gpt-5.4-image-2">GPT-5.4 Image 2 (OpenAI)</option>
                <option value="google/gemini-3.1-flash-image-preview">Gemini 3.1 Flash Image (Google)</option>
                <option value="google/gemini-3-pro-image-preview">Gemini 3 Pro Image (Google)</option>
                <option value="x-ai/grok-imagine-image-quality">Grok Imagine Quality (xAI)</option>
                <option value="recraft/recraft-v4-pro">Recraft V4 Pro</option>
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
            </div>
          )}

          {/* Schedule section */}
          {showSchedule && (
            <div style={{display:'flex',flexDirection:'column',gap:8,borderTop:'1px solid rgba(255,255,255,.06)',paddingTop:10}}>
              <p style={{fontSize:10,fontWeight:600,color:'#7a8499',marginBottom:7,letterSpacing:'.06em',textTransform:'uppercase'}}>Schedule Post</p>
              <div style={{display:'flex',gap:6}}>
                <input type="date" value={schedDate} onChange={e=>setSchedDate(e.target.value)} className="cr-input" style={{flex:1,padding:'7px 8px',fontSize:11}} />
                <input type="time" value={schedTime} onChange={e=>setSchedTime(e.target.value)} className="cr-input" style={{flex:1,padding:'7px 8px',fontSize:11}} />
              </div>
              <button onClick={handleSchedule}
                style={{width:'100%',padding:9,fontSize:11,fontWeight:700,letterSpacing:'.06em',textTransform:'uppercase',border:'none',borderRadius:9,cursor:'pointer',background:'linear-gradient(135deg,#f0a040,#e08030)',color:'#07090e',transition:'opacity .18s'}}
                onMouseEnter={e=>e.currentTarget.style.opacity='.85'} onMouseLeave={e=>e.currentTarget.style.opacity='1'}>
                Confirm Schedule
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
