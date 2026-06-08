import { useEffect, useRef, useState } from 'react'
import { useMmStore, MEDIA_COLORS, PLAT_COLORS, PLAT_LIST } from '../../store/mmStore'
import { routeCardToPlatform } from '../../utils/routeCardToPlatform'

const STATUS_BADGE = {
  ready:     <span className="sbadge sb-ready"     style={{fontSize:8.5}}>● Ready</span>,
  image:     <span className="sbadge sb-image"     style={{fontSize:8.5}}>● Needs Image</span>,
  approved:  <span className="sbadge sb-approved"  style={{fontSize:8.5}}>● Approved</span>,
  scheduled: <span className="sbadge sb-scheduled" style={{fontSize:8.5}}>● Scheduled</span>,
  published: <span className="sbadge sb-published" style={{fontSize:8.5}}>● Published</span>,
}
const MK_LABEL = {'RZ Prime':'RZ','Coin Hall':'CH','ChainReporter':'CR','Meta Coin Guard':'MCG'}

export default function EditorialCard({ card, onDragStart }) {
  const setActiveCard = useMmStore(s => s.setActiveCard)
  const selectedPlatforms = useMmStore(s => s.selectedPlatforms)
  const platformLanes = useMmStore(s => s.platformLanes)
  const modelLanes = useMmStore(s => s.modelLanes)
  const setPlatformLanes = useMmStore(s => s.setPlatformLanes)
  const updateCard = useMmStore(s => s.updateCard)
  const getCachedCopy = useMmStore(s => s.getCachedCopy)
  const setCachedCopy = useMmStore(s => s.setCachedCopy)

  const [popoverOpen, setPopoverOpen] = useState(false)
  const popoverRef = useRef(null)

  const isSuggested = !card.platform || card.platform === 'suggested'
  const mc = MEDIA_COLORS[card.media] || '#7a8499'
  const pc = isSuggested ? null : (PLAT_COLORS[card.platform] || '#7a8499')
  const sentColor = card.sentiment === 'Bullish' ? '#00d4a0' : card.sentiment === 'Bearish' ? '#ef4455' : '#7a8499'
  const mkLabel = MK_LABEL[card.media] || (card.media||'').slice(0,2)

  const routedPlatforms = PLAT_LIST.filter(p => (platformLanes[card.media]?.[p] || []).some(c => c.id === card.id))

  useEffect(() => {
    if (!popoverOpen) return
    function onDown(e) { if (popoverRef.current && !popoverRef.current.contains(e.target)) setPopoverOpen(false) }
    function onKey(e) { if (e.key === 'Escape') setPopoverOpen(false) }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('mousedown', onDown); document.removeEventListener('keydown', onKey) }
  }, [popoverOpen])

  function sendTo(plat) {
    if (routedPlatforms.includes(plat)) return
    routeCardToPlatform(card.id, plat, card.media, { modelLanes, platformLanes, setPlatformLanes, updateCard, getCachedCopy, setCachedCopy })
  }

  return (
    <div
      ref={popoverRef}
      className={`mm-card fade-up${card === useMmStore.getState().activeCard ? ' active' : ''}`}
      id={`card-${card.id}`}
      draggable
      onDragStart={e => { e.dataTransfer.setData('text/plain', card.id); if (onDragStart) onDragStart(card.id); e.currentTarget.classList.add('dragging') }}
      onDragEnd={e => e.currentTarget.classList.remove('dragging')}
      onClick={() => setActiveCard(card)}
    >
      <button className="qs-btn" title="Quick send to platform"
        onClick={e => { e.stopPropagation(); setPopoverOpen(o => !o) }}>⋯</button>

      {popoverOpen && (
        <div className="qs-popover" onClick={e => e.stopPropagation()}>
          <span className="qs-label">Send to</span>
          {selectedPlatforms.map(p => {
            const routed = routedPlatforms.includes(p)
            return (
              <button key={p} className={`qs-plat-btn${routed ? ' routed' : ''}`}
                onClick={() => { sendTo(p); setPopoverOpen(false) }}>
                <span>{p}</span>
                {routed && <span>✓</span>}
              </button>
            )
          })}
        </div>
      )}

      {/* Row 1: media badge + platform + time */}
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:7,gap:4}}>
        <div style={{display:'flex',alignItems:'center',gap:4}}>
          <span style={{fontSize:8,fontWeight:700,padding:'1.5px 5px',borderRadius:3,background:mc+'20',color:mc,border:`1px solid ${mc}35`}}>{mkLabel}</span>
          {isSuggested
            ? <span style={{fontSize:8,fontWeight:600,padding:'1.5px 5px',borderRadius:3,background:'rgba(255,255,255,.04)',color:'#4a5568',border:'1px solid rgba(255,255,255,.08)'}}>drag to platform →</span>
            : <span style={{fontSize:8,fontWeight:700,padding:'1.5px 5px',borderRadius:3,background:pc+'20',color:pc,border:`1px solid ${pc}35`}}>{card.platform}</span>
          }
          {isSuggested && routedPlatforms.length > 0 && <span className="routed-badge">→ {routedPlatforms.join(', ')}</span>}
        </div>
        <span style={{fontSize:9,color:'#4a5568'}}>{card.timeAgo}</span>
      </div>

      {/* Row 2: source */}
      <div style={{display:'flex',alignItems:'center',gap:5,marginBottom:6}}>
        <div style={{width:16,height:16,borderRadius:4,flexShrink:0,display:'flex',alignItems:'center',justifyContent:'center',fontSize:6,fontWeight:700,background:card.srcColor+'1a',color:card.srcColor,border:`1px solid ${card.srcColor}30`}}>{card.initials}</div>
        <span style={{fontSize:10,color:'#7a8499'}}>{card.source}</span>
      </div>

      {/* Headline */}
      <h4 style={{fontFamily:"'Space Grotesk',sans-serif",fontWeight:700,fontSize:11,color:'#f0f2f8',lineHeight:1.35,letterSpacing:'-.01em',marginBottom:6,display:'-webkit-box',WebkitLineClamp:2,WebkitBoxOrient:'vertical',overflow:'hidden'}}>{card.headline}</h4>

      {/* Copy preview */}
      <p style={{fontSize:10,color:'#7a8499',lineHeight:1.5,marginBottom:8,display:'-webkit-box',WebkitLineClamp:2,WebkitBoxOrient:'vertical',overflow:'hidden'}}>{card.copy}</p>

      {/* Status + scores */}
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between'}}>
        {STATUS_BADGE[card.status] || STATUS_BADGE.ready}
        <div style={{display:'flex',alignItems:'center',gap:5,flexWrap:'wrap'}}>
          <span style={{fontSize:9,color:sentColor,fontWeight:600}}>{card.sentiment}</span>
          <span style={{fontSize:9,color:'#f0a040',fontWeight:700}}>⚡{card.suitability}/10</span>
          {card.lowConfidence && <span style={{fontSize:7.5,padding:'1px 4px',borderRadius:3,background:'rgba(240,160,64,.12)',color:'#f0a040',border:'1px solid rgba(240,160,64,.3)'}}>⚠ Low Conf</span>}
        </div>
      </div>
    </div>
  )
}
