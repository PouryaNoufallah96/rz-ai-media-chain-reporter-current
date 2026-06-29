import { useState, useEffect } from 'react'
import { useMmStore, API_BASE, MM_SOURCES, MEDIA_COLORS, PLAT_COLORS, EDITORIAL_MODEL_META, anyPromoOn } from '../../store/mmStore'

const CHECK_SVG = <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#07090e" strokeWidth="3" strokeLinecap="round"><polyline points="20 6 9 17 4 12"/></svg>
const CHECK_SVG_W = <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round"><polyline points="20 6 9 17 4 12"/></svg>

const LABEL_STYLE = { display:'block', fontSize:11, fontWeight:600, letterSpacing:'.1em', textTransform:'uppercase', color:'#7a8499', marginBottom:8 }

function ToggleRow({ on, color, label, sub, abbr, onClick, checkWhite, filterEngine }) {
  const active = { borderColor: color + '88', background: color + '1a' }
  const inactive = { borderColor:'rgba(255,255,255,.08)', background:'rgba(255,255,255,.03)' }
  return (
    <div onClick={onClick} className="toggle-row" style={on ? active : {}}>
      <div style={{width:22,height:22,borderRadius:6,background:color+'22',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0,fontSize:filterEngine?9:7,fontWeight:800,color}}>{abbr}</div>
      <div style={{flex:1,minWidth:0,textAlign:'left'}}>
        <div style={{fontSize:12,fontWeight:600,color:'#f0f2f8'}}>{label}</div>
        <div style={{fontSize:10,color:'#7a8499'}}>{sub}</div>
      </div>
      <div style={{width:14,height:14,borderRadius:4,flexShrink:0,background:on?color:'rgba(255,255,255,.1)',display:'flex',alignItems:'center',justifyContent:'center'}}>
        {on ? (checkWhite ? CHECK_SVG_W : CHECK_SVG) : null}
      </div>
    </div>
  )
}

export default function Sidebar({ topics, setTopics, onAnalyze }) {
  const { selectedMedia, selectedPlatforms, selectedSources, recencyHours, filterMode,
          selectedModels, analyzing, progress, errorMsg, promoMode, promoPrompts,
          toggleMedia, togglePlatform, toggleSource, toggleModel, setRecencyHours, setFilterMode,
          togglePromoMode, setPromoPrompt } = useMmStore()

  // When any brand has Promo Copy ON, the whole run is promo-only — sources and filtering
  // are irrelevant (no news is fetched), so those controls are disabled here.
  const promoActive = anyPromoOn(useMmStore.getState())

  const [topicInput, setTopicInput] = useState('')
  const [topicChips, setTopicChips] = useState([])

  useEffect(() => {
    if (!selectedMedia.length) return
    fetch(`${API_BASE}/api/account/brand-keywords?brands=${selectedMedia.map(encodeURIComponent).join(',')}`, { credentials:'include' })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.keywords?.length) {
          setTopicChips(data.keywords)
          setTopics(data.keywords.join(', '))
        }
      })
      .catch(() => {})
  }, [selectedMedia.join(',')])

  function addChip(word) {
    const w = word.trim()
    if (w && !topicChips.includes(w)) { setTopicChips(c=>[...c,w]); setTopics([...topicChips,w].join(', ')) }
  }
  function removeChip(w) { const nc=topicChips.filter(c=>c!==w); setTopicChips(nc); setTopics(nc.join(', ')) }

  function handleTopicKey(e) {
    if (e.key !== 'Enter') return
    e.preventDefault()
    const v = e.target.value.trim()
    if (v) { addChip(v); setTopicInput('') }
  }
  function handleTopicInput(e) {
    const v = e.target.value
    if (!v.includes(',')) { setTopicInput(v); return }
    v.split(',').forEach((p,i,a) => { if(i<a.length-1 && p.trim()) addChip(p) })
    setTopicInput(v.split(',').pop().replace(/^\s+/,''))
  }

  // Filter engine options
  const filterOptions = [
    { key:'preprocess',         color:'#00d4a0', abbr:'PP', label:'Pre-Process',         sub:'Local ML model · no API cost' },
    { key:'openai_embedding',   color:'#10a37f', abbr:'OA', label:'OpenAI Embedding',    sub:'text-embedding-3-small · backend' },
    { key:'deepseek_preprocess',color:'#22d3ee', abbr:'DS', label:'DeepSeek Pre-Process',sub:'DeepSeek V4 Flash · routing AI' },
    { key:'test',               color:'#f0a040', abbr:'⚡', label:'Test Version',         sub:'Verify API + models · minimal tokens' },
  ]

  const modelOptions = [
    { key:'gpt',      color:'#10a37f', abbr:'OP', label:'GPT-5.5',              badge:'OpenAI',    sub:'Best general-purpose editorial AI' },
    { key:'gemini',   color:'#4285f4', abbr:'GE', label:'Gemini 3.1 Pro Preview',badge:'Google',    sub:'Strong reasoning · multimodal' },
    { key:'claude',   color:'#d97706', abbr:'AN', label:'Claude Opus 4.7',       badge:'Anthropic', sub:'Top reasoning benchmark score' },
    { key:'deepseek', color:'#22d3ee', abbr:'DS', label:'DeepSeek V4 Flash',     badge:'DeepSeek',  sub:'Fast · cost-efficient · strong reasoning' },
  ]

  return (
    <aside id="mm-sidebar" className="glass" style={{textAlign:'left'}}>
      <div className="p-4" style={{display:'flex',flexDirection:'column',gap:14}}>

        {/* Title */}
        <div>
          <h1 style={{fontFamily:"'Space Grotesk',sans-serif",fontWeight:700,fontSize:17,color:'#f0f2f8',letterSpacing:'-.02em',marginBottom:4}}>
            <span style={{color:'#00d4a0'}}>Multi</span> Media
          </h1>
          <p style={{fontSize:11,color:'#7a8499',lineHeight:1.55}}>Route the right news to the right media brand and platform.</p>
        </div>

        {/* ① Media */}
        <div>
          <label style={LABEL_STYLE}>① Select Media</label>
          <div style={{display:'flex',flexDirection:'column',gap:6}}>
            {[
              {m:'RZ Prime',      color:'#f0a040',abbr:'RZ', sub:'Token Access · BNB Chain · Retail'},
              {m:'Coin Hall',     color:'#00d4ff',abbr:'CH', sub:'Luxury · Web3 · Aspirational'},
              {m:'ChainReporter', color:'#9b72f5',abbr:'CR', sub:'General Crypto News · Full Spectrum'},
              {m:'Meta Coin Guard',color:'#4ade80',abbr:'MCG',sub:'Security · DeFi Protection · Risk'},
            ].map(({m,color,abbr,sub}) => (
              <div key={m}>
                <ToggleRow on={selectedMedia.includes(m)} color={color} label={m} sub={sub} abbr={abbr} onClick={()=>toggleMedia(m)} />
                {selectedMedia.includes(m) && m !== 'ChainReporter' && (
                  <div
                    onClick={e => { e.stopPropagation(); togglePromoMode(m) }}
                    style={{marginLeft:12,marginTop:4,display:'flex',alignItems:'center',gap:7,cursor:'pointer',userSelect:'none'}}
                  >
                    <span style={{fontSize:9,fontWeight:700,letterSpacing:'.08em',textTransform:'uppercase',color:promoMode[m]?'#f0a040':'#4a5568',transition:'color .2s'}}>Promo Copy</span>
                    <div style={{width:28,height:15,borderRadius:8,flexShrink:0,background:promoMode[m]?'rgba(240,160,64,.3)':'rgba(255,255,255,.07)',border:`1px solid ${promoMode[m]?'rgba(240,160,64,.55)':'rgba(255,255,255,.11)'}`,position:'relative',transition:'background .2s, border-color .2s'}}>
                      <div style={{position:'absolute',top:2,left:promoMode[m]?13:2,width:9,height:9,borderRadius:'50%',background:promoMode[m]?'#f0a040':'#4a5568',transition:'left .18s ease, background .2s'}}/>
                    </div>
                  </div>
                )}
                {selectedMedia.includes(m) && promoMode[m] && (
                  <textarea
                    value={promoPrompts[m] || ''}
                    onChange={e => setPromoPrompt(m, e.target.value)}
                    onClick={e => e.stopPropagation()}
                    placeholder={`What post do you want for ${m}?`}
                    rows={2}
                    className="cr-input"
                    style={{width:'calc(100% - 12px)',marginLeft:12,marginTop:4,padding:'6px 8px',fontSize:10,resize:'vertical',minHeight:32,borderColor:'rgba(240,160,64,.25)',color:'#f0f2f8'}}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* ② Platforms */}
        <div>
          <label style={{...LABEL_STYLE,marginBottom:4}}>② Destination Platforms</label>
          <p style={{fontSize:10,color:'#4a5568',marginBottom:8}}>Creates columns. Drag news cards into them after analysis.</p>
          <div style={{display:'flex',flexDirection:'column',gap:6}}>
            <ToggleRow on={selectedPlatforms.includes('X')} color='#00d4ff' label='X (Twitter)' sub='Short viral · 280 chars' abbr={
              <svg width="11" height="11" viewBox="0 0 24 24" fill="#00d4ff"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.81l7.73-8.835L1.254 2.25H8.08l4.253 5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
            } onClick={()=>togglePlatform('X')} />
            <ToggleRow on={selectedPlatforms.includes('Telegram')} color='#00d4a0' label='Telegram' sub='Summaries · takeaways' abbr={
              <svg width="13" height="13" viewBox="0 0 24 24" fill="#00d4a0"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8l-1.7 8c-.12.56-.45.7-.9.44l-2.5-1.84-1.2 1.16c-.13.13-.24.24-.5.24l.18-2.52 4.56-4.12c.2-.18-.04-.27-.3-.1L7.56 15.4l-2.46-.77c-.53-.17-.54-.53.12-.78l9.62-3.72c.44-.16.83.1.8.67z"/></svg>
            } onClick={()=>togglePlatform('Telegram')} />
            <ToggleRow on={selectedPlatforms.includes('Instagram')} color='#e1306c' label='Instagram' sub='Visual captions · carousel' checkWhite abbr={
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#e1306c" strokeWidth="1.8" strokeLinecap="round"><rect x="2" y="2" width="20" height="20" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r=".7" fill="#e1306c" stroke="none"/></svg>
            } onClick={()=>togglePlatform('Instagram')} />
          </div>
        </div>

        {/* ③ Sources */}
        <div style={promoActive ? {opacity:.4, pointerEvents:'none'} : undefined}>
          <label style={LABEL_STYLE}>③ Select Source{promoActive ? '  ·  Promo mode' : ''}</label>
          {promoActive && (
            <p style={{fontSize:10,color:'#f0a040',marginBottom:8}}>Promo mode — sources not used.</p>
          )}
          <div style={{display:'flex',flexWrap:'wrap',gap:4}}>
            {Object.keys(MM_SOURCES).map(src => (
              <button key={src} className={`src-chip${selectedSources.includes(src)?' on':''}`} onClick={()=>toggleSource(src)}>{src}</button>
            ))}
          </div>
        </div>

        {/* ④ Topics */}
        <div>
          <label style={{...LABEL_STYLE,marginBottom:6}}>④ Topics / Keywords</label>
          <div style={{background:'rgba(255,255,255,.04)',border:'1px solid rgba(255,255,255,.10)',borderRadius:10,padding:'8px 10px',marginBottom:8,cursor:'text'}}>
            <input type="text" placeholder="Type keyword, press Enter…" value={topicInput}
              onChange={handleTopicInput} onKeyDown={handleTopicKey}
              style={{background:'none',border:'none',outline:'none',width:'100%',fontSize:11.5,color:'#f0f2f8',caretColor:'#00d4a0',padding:0}} />
          </div>
          <div style={{display:'flex',flexWrap:'wrap',gap:5,marginBottom:6}}>
            {topicChips.map(w => (
              <span key={w} className="tc-chip" data-word={w}>{w}<button className="tc-x" onClick={()=>removeChip(w)}>×</button></span>
            ))}
          </div>
        </div>

        {/* ⑤ Time Range */}
        <div>
          <label style={{...LABEL_STYLE,marginBottom:6}}>⑤ Time Range</label>
          <div style={{display:'flex',flexWrap:'wrap',gap:5}}>
            {[6,12,24,48].map(h => (
              <button key={h} className={`time-chip${recencyHours===h?' on':''}`} onClick={()=>setRecencyHours(h)}>Last {h}h</button>
            ))}
          </div>
        </div>

        {/* ⑥ Filter Engine */}
        <div style={promoActive ? {opacity:.4, pointerEvents:'none'} : undefined}>
          <label style={{...LABEL_STYLE,marginBottom:6}}>⑥ Filter Engine</label>
          {promoActive && (
            <p style={{fontSize:10,color:'#f0a040',marginBottom:8}}>Promo mode — no filtering needed.</p>
          )}
          <div style={{display:'flex',flexDirection:'column',gap:6}}>
            {filterOptions.map(f => (
              <ToggleRow key={f.key} on={filterMode===f.key} color={f.color} abbr={f.abbr} label={f.label} sub={f.sub} onClick={()=>setFilterMode(f.key)} filterEngine />
            ))}
          </div>
        </div>

        {/* AI Editorial Models */}
        <div>
          <label style={{...LABEL_STYLE,marginBottom:4}}>⑦ AI Editorial Models</label>
          <p style={{fontSize:10,color:'#4a5568',marginBottom:8}}>Choose 1–5 models. Each picks 5 articles per brand independently.</p>
          <div style={{display:'flex',flexDirection:'column',gap:6}}>
            {modelOptions.map(m => (
              <ToggleRow key={m.key} on={selectedModels.includes(m.key)} color={m.color} abbr={m.abbr}
                label={<>{m.label} <span style={{fontSize:9,fontWeight:700,padding:'1px 5px',borderRadius:3,background:m.color+'22',color:m.color,marginLeft:3}}>{m.badge}</span></>}
                sub={m.sub} onClick={()=>toggleModel(m.key)} />
            ))}
          </div>
        </div>

        {/* Error */}
        {errorMsg && (
          <div style={{background:'rgba(239,68,85,.08)',border:'1px solid rgba(239,68,85,.22)',borderRadius:10,padding:10,fontSize:11,color:'#f08090',lineHeight:1.5}}>
            {errorMsg}
          </div>
        )}

        {/* Analyze button */}
        <button className="btn-analyze" disabled={analyzing} onClick={onAnalyze}>
          {analyzing ? (
            <><span className="spinner" style={{borderColor:'rgba(7,9,14,.3)',borderTopColor:'#07090e'}}></span>&nbsp;{progress.label||'Analyzing…'}</>
          ) : (
            <><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg> Analyze &amp; Route News</>
          )}
        </button>

        {/* Progress bar */}
        {analyzing && (
          <div>
            <div style={{height:2,background:'rgba(255,255,255,.06)',borderRadius:1,overflow:'hidden'}}>
              <div style={{height:'100%',width:`${progress.pct}%`,background:'linear-gradient(to right,#00d4a0,#9b72f5)',borderRadius:1,transition:'width .4s ease'}}></div>
            </div>
            <p style={{fontSize:10,color:'#7a8499',marginTop:4,textAlign:'center'}}>{progress.label}</p>
          </div>
        )}

        {/* Legend */}
        <div style={{borderTop:'1px solid rgba(255,255,255,.06)',paddingTop:12}}>
          <p style={{fontSize:10,fontWeight:700,letterSpacing:'.08em',textTransform:'uppercase',color:'#4a5568',marginBottom:8}}>Legend</p>
          <div style={{display:'flex',flexDirection:'column',gap:5}}>
            {[{c:'#00d4a0',l:'Ready',d:'Ready to review'},{c:'#f0a040',l:'Needs Image',d:'Image required'},{c:'#9b72f5',l:'Approved',d:'Ready to publish'},{c:'#3d8ef0',l:'Scheduled',d:'Queued to publish'}].map(({c,l,d})=>(
              <div key={l} style={{display:'flex',alignItems:'center',gap:7}}>
                <div style={{width:8,height:8,borderRadius:'50%',background:c,flexShrink:0}}></div>
                <span style={{fontSize:10.5,fontWeight:600,color:c,width:72}}>{l}</span>
                <span style={{fontSize:10,color:'#7a8499'}}>{d}</span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </aside>
  )
}
