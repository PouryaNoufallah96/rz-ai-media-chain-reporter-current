import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import './AboutPage.css'

function NavBar() {
  return (
    <nav className="glass border-b border-white/[0.06] sticky top-0" style={{zIndex:50}}>
      <div className="flex items-center justify-between px-6 h-14">
        <Link to="/multimedia" className="flex items-center gap-3 flex-shrink-0" style={{textDecoration:'none'}}>
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
               style={{background:'linear-gradient(135deg,#00d4a0,#9b72f5)'}}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#07090e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
            </svg>
          </div>
          <span style={{fontFamily:"'Space Grotesk',sans-serif",fontWeight:700,fontSize:17,letterSpacing:'-0.02em'}}>
            <span style={{color:'#f0f2f8'}}>Chain</span><span style={{color:'#f0a040'}}>Reporter</span>
          </span>
        </Link>
        <div className="hidden md:flex items-center gap-0.5">
          <Link to="/multimedia" className="nav-link">Multi Media</Link>
          <Link to="/about" className="nav-link active">About Us</Link>
        </div>
        <button className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                style={{background:'none',border:'none',cursor:'pointer',color:'#7a8499',transition:'color 0.18s ease,background 0.18s ease'}}
                onMouseEnter={e=>{e.currentTarget.style.color='#f0f2f8';e.currentTarget.style.background='rgba(255,255,255,0.05)'}}
                onMouseLeave={e=>{e.currentTarget.style.color='#7a8499';e.currentTarget.style.background='none'}}>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
          </svg>
        </button>
      </div>
    </nav>
  )
}

export default function AboutPage() {
  const videoRef   = useRef(null)
  const sectionRef = useRef(null)

  useEffect(() => {
    const video   = videoRef.current
    const section = sectionRef.current
    if (!video || !section) return
    let started = false

    function initVideo() { video.currentTime = 0; video.pause() }
    video.addEventListener('loadeddata', initVideo)
    video.addEventListener('canplay', initVideo)
    if (video.readyState >= 2) initVideo()

    function onScroll() {
      const maxScroll = section.offsetHeight - window.innerHeight
      const progress  = Math.min(Math.max(window.scrollY / maxScroll, 0), 1)
      video.style.opacity   = 0.25 + progress * 0.75
      video.style.filter    = `blur(${(8 * (1 - progress)).toFixed(2)}px)`
      video.style.transform = `scale(${(1.08 - progress * 0.08).toFixed(4)}) translateZ(0)`
      if (progress > 0.15 && !started) { started = true; video.play().catch(()=>{}) }
      if (progress < 0.05 && started && !video.paused) { video.pause(); video.currentTime = 0; started = false }
    }

    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <>
      <NavBar />

      {/* Hero */}
      <section id="hero-section" ref={sectionRef}>
        <div id="hero-sticky">
          <video id="hero-video" ref={videoRef} muted playsInline preload="auto" loop>
            <source src="/cosmic_bigbang.mp4" type="video/mp4" />
          </video>
          <div id="hero-vignette"></div>
          <div id="hero-glow"></div>
          <div id="hero-content">
            <div className="hero-eyebrow">
              <svg width="9" height="9" viewBox="0 0 24 24" fill="var(--mint)"><circle cx="12" cy="12" r="12"/></svg>
              AI-Powered Crypto Journalism
            </div>
            <h1 className="hero-title">The Universe<br/>of <span>Crypto News</span></h1>
            <p className="hero-sub">ChainReporter harnesses artificial intelligence to scan, analyze, and amplify the stories that move markets — delivering cinematic editorial workflows from signal to tweet in seconds.</p>
            <Link to="/multimedia"
              style={{display:'inline-flex',alignItems:'center',gap:8,padding:'12px 28px',borderRadius:12,background:'linear-gradient(135deg,#00d4a0,#00a878)',color:'#07090e',fontWeight:700,fontSize:13,letterSpacing:'0.04em',textDecoration:'none',transition:'opacity 0.2s ease,transform 0.2s ease'}}
              onMouseEnter={e=>{e.currentTarget.style.opacity='0.88';e.currentTarget.style.transform='translateY(-1px)'}}
              onMouseLeave={e=>{e.currentTarget.style.opacity='1';e.currentTarget.style.transform='translateY(0)'}}>
              Open Dashboard
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </Link>
          </div>
          <div className="hero-scroll-hint">
            <span>Scroll to explore</span>
            <div className="scroll-arrow"><div className="scroll-dot"></div></div>
          </div>
        </div>
      </section>

      {/* What We Do */}
      <section className="section py-28 px-6" style={{borderTop:'1px solid rgba(255,255,255,0.05)'}}>
        <div style={{position:'relative',maxWidth:1100,margin:'0 auto'}}>
          <div className="section-aurora">
            <div style={{position:'absolute',top:-200,left:'50%',transform:'translateX(-50%)',width:700,height:500,borderRadius:'50%',background:'radial-gradient(circle,rgba(0,212,160,0.07) 0%,transparent 65%)',filter:'blur(40px)',pointerEvents:'none'}}></div>
          </div>
          <div className="text-center mb-20" style={{position:'relative'}}>
            <span className="step-num" style={{fontSize:10}}>What We Do</span>
            <h2 style={{fontFamily:"'Space Grotesk',sans-serif",fontSize:'clamp(32px,5vw,56px)',fontWeight:800,letterSpacing:'-0.03em',color:'#f0f2f8',marginTop:18,marginBottom:16,lineHeight:1.1}}>
              From Raw Feed<br/>to <span style={{color:'var(--gold)'}}>Viral Story</span>
            </h2>
            <p style={{color:'#7a8499',fontSize:17,maxWidth:520,margin:'0 auto',lineHeight:1.65}}>We built ChainReporter so crypto journalists and content teams could move at the speed of the market — without sacrificing quality.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6" style={{position:'relative'}}>
            {[
              {color:'#00d4a0',bg:'rgba(0,212,160,0.1)',border:'rgba(0,212,160,0.2)',icon:<><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></>,title:'Smart Aggregation',desc:'Pulls live RSS feeds from 15 of the most trusted crypto publications simultaneously, filtering by recency and relevance.'},
              {color:'#9b72f5',bg:'rgba(155,114,245,0.1)',border:'rgba(155,114,245,0.2)',icon:<><path d="M12 2a10 10 0 1 0 10 10"/><path d="M12 6v6l4 2"/><path d="M22 2 12 12"/></>,title:'AI Virality Engine',desc:'GPT-4o-mini ranks every article by viral potential, impact score, and sentiment — surfacing the stories most likely to drive engagement.'},
              {color:'#f0a040',bg:'rgba(240,160,64,0.1)',border:'rgba(240,160,64,0.2)',icon:<><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></>,title:'Cinematic Imagery',desc:'Generates hyper-realistic editorial images using the latest OpenAI image models, matched to tone, sentiment, and market mood.'},
            ].map(c => (
              <div className="glass-card p-7" key={c.title}>
                <div className="icon-box mb-5" style={{background:c.bg,border:`1px solid ${c.border}`}}>
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={c.color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">{c.icon}</svg>
                </div>
                <h3 style={{fontFamily:"'Space Grotesk',sans-serif",fontWeight:700,fontSize:18,color:'#f0f2f8',marginBottom:10,letterSpacing:'-0.02em'}}>{c.title}</h3>
                <p style={{color:'#7a8499',fontSize:14,lineHeight:1.7}}>{c.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="section py-28 px-6" style={{background:'rgba(12,15,24,0.6)'}}>
        <div style={{maxWidth:1100,margin:'0 auto'}}>
          <div className="text-center mb-20">
            <span className="step-num" style={{fontSize:10}}>Workflow</span>
            <h2 style={{fontFamily:"'Space Grotesk',sans-serif",fontSize:'clamp(32px,5vw,56px)',fontWeight:800,letterSpacing:'-0.03em',color:'#f0f2f8',marginTop:18,marginBottom:16,lineHeight:1.1}}>
              Five Steps to<br/><span style={{color:'var(--mint)'}}>Publish-Ready Content</span>
            </h2>
          </div>
          <div style={{display:'flex',flexDirection:'column',gap:0}}>
            {[
              {n:'1',c:'#00d4a0',bg:'rgba(0,212,160,0.1)',border:'rgba(0,212,160,0.25)',title:'Select Your Sources',desc:'Choose from 15 curated crypto news outlets. Filter by recency — last 6h, 12h, 24h, or 48h. Add your own topic keywords to focus the analysis.'},
              {n:'2',c:'#9b72f5',bg:'rgba(155,114,245,0.1)',border:'rgba(155,114,245,0.25)',title:'AI Analyzes the Feed',desc:'ChainReporter fetches live RSS data, pools the freshest articles, and sends them to GPT-4o-mini for virality scoring, impact assessment, and tweet generation.'},
              {n:'3',c:'#f0a040',bg:'rgba(240,160,64,0.1)',border:'rgba(240,160,64,0.25)',title:'Choose the Best Story',desc:'Ranked cards appear in the center panel. Tap any card to promote it to the Chosen One panel, review key takeaways, sentiment analysis, and the pre-written tweet.'},
              {n:'4',c:'#3d8ef0',bg:'rgba(61,142,240,0.1)',border:'rgba(61,142,240,0.25)',title:'Generate the Image',desc:'Select an image model and generate a cinematic editorial image. Regenerate until it matches your vision.'},
              {n:'5',c:'#00d4a0',bg:'rgba(0,212,160,0.1)',border:'rgba(0,212,160,0.25)',title:'Approve & Archive',desc:'Approve the image and tweet. ChainReporter saves the image to Google Drive and logs the story — headline, tweet, source, score, and image link — to your Google Sheet automatically.',last:true},
            ].map(s => (
              <div key={s.n} style={{display:'flex',gap:32,padding:'28px 0',borderBottom:s.last?'none':'1px solid rgba(255,255,255,0.05)'}}>
                <div style={{flexShrink:0,width:52,height:52,borderRadius:'50%',background:s.bg,border:`1px solid ${s.border}`,display:'flex',alignItems:'center',justifyContent:'center',fontFamily:"'Space Grotesk',sans-serif",fontWeight:800,fontSize:18,color:s.c}}>{s.n}</div>
                <div>
                  <h3 style={{fontFamily:"'Space Grotesk',sans-serif",fontWeight:700,fontSize:17,color:'#f0f2f8',marginBottom:6,letterSpacing:'-0.02em'}}>{s.title}</h3>
                  <p style={{color:'#7a8499',fontSize:14,lineHeight:1.7,maxWidth:620}}>{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="section py-28 px-6">
        <div style={{maxWidth:1100,margin:'0 auto'}}>
          <div className="text-center mb-16">
            <span className="step-num" style={{fontSize:10}}>Technology</span>
            <h2 style={{fontFamily:"'Space Grotesk',sans-serif",fontSize:'clamp(32px,5vw,52px)',fontWeight:800,letterSpacing:'-0.03em',color:'#f0f2f8',marginTop:18,marginBottom:16,lineHeight:1.1}}>
              Built on <span style={{color:'var(--violet)'}}>Frontier AI</span>
            </h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              {emoji:'🧠',name:'GPT-4o mini',desc:'News analysis & tweet generation'},
              {emoji:'🎨',name:'gpt-image-2',desc:'Cinematic editorial images'},
              {emoji:'📡',name:'15 RSS Feeds',desc:'Live crypto news aggregation'},
              {emoji:'☁️',name:'Google Cloud',desc:'Drive + Sheets archiving'},
            ].map(t => (
              <div className="glass-card p-6 text-center" key={t.name}>
                <div style={{fontSize:28,marginBottom:10}}>{t.emoji}</div>
                <div style={{fontFamily:"'Space Grotesk',sans-serif",fontWeight:700,fontSize:14,color:'#f0f2f8',marginBottom:4}}>{t.name}</div>
                <div style={{fontSize:12,color:'#7a8499'}}>{t.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="section py-28 px-6" style={{background:'rgba(12,15,24,0.5)'}}>
        <div style={{maxWidth:700,margin:'0 auto',textAlign:'center'}}>
          <h2 style={{fontFamily:"'Space Grotesk',sans-serif",fontSize:'clamp(32px,5vw,52px)',fontWeight:800,letterSpacing:'-0.03em',color:'#f0f2f8',marginBottom:18,lineHeight:1.1}}>
            Ready to <span style={{color:'var(--gold)'}}>Break the Story?</span>
          </h2>
          <p style={{color:'#7a8499',fontSize:17,lineHeight:1.65,marginBottom:36}}>Open the dashboard, select your sources, and let the AI do the heavy lifting.</p>
          <Link to="/multimedia"
            style={{display:'inline-flex',alignItems:'center',gap:10,padding:'15px 36px',borderRadius:14,background:'linear-gradient(135deg,#f0a040,#d07820)',color:'#07090e',fontWeight:800,fontSize:15,letterSpacing:'0.03em',textDecoration:'none',transition:'opacity 0.2s ease,transform 0.2s ease'}}
            onMouseEnter={e=>{e.currentTarget.style.opacity='0.88';e.currentTarget.style.transform='translateY(-2px)'}}
            onMouseLeave={e=>{e.currentTarget.style.opacity='1';e.currentTarget.style.transform='translateY(0)'}}>
            Launch ChainReporter
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="section py-10 px-6">
        <div className="footer-divider mb-8"></div>
        <div style={{maxWidth:1100,margin:'0 auto',display:'flex',alignItems:'center',justifyContent:'space-between',flexWrap:'wrap',gap:12}}>
          <div style={{display:'flex',alignItems:'center',gap:10}}>
            <div style={{width:28,height:28,borderRadius:8,flexShrink:0,background:'linear-gradient(135deg,#00d4a0,#9b72f5)',display:'flex',alignItems:'center',justifyContent:'center'}}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#07090e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
              </svg>
            </div>
            <span style={{fontFamily:"'Space Grotesk',sans-serif",fontWeight:700,fontSize:15,letterSpacing:'-0.02em'}}>
              <span style={{color:'#f0f2f8'}}>Chain</span><span style={{color:'#f0a040'}}>Reporter</span>
            </span>
          </div>
          <p style={{color:'#4a5568',fontSize:12}}>© 2026 ChainReporter. AI-powered crypto journalism.</p>
        </div>
      </footer>
    </>
  )
}
