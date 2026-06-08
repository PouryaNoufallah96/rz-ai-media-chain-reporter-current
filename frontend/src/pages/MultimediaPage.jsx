import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useMmStore, API_BASE } from '../store/mmStore'
import { useAnalyzeAndRoute } from '../hooks/useAnalyzeAndRoute'
import Sidebar from '../components/mm/Sidebar'
import MainArea from '../components/mm/LaneBoard'
import PreviewPanel from '../components/mm/PreviewPanel'
import './MultimediaPage.css'

// Load the HuggingFace semantic router as a module script (same as original)
let _semLoaded = false
function loadSemRouter() {
  if (_semLoaded) return
  _semLoaded = true
  const s = document.createElement('script')
  s.type = 'module'
  s.textContent = `
import { pipeline } from 'https://cdn.jsdelivr.net/npm/@huggingface/transformers@3';
const PROFILES = {
  'RZ Prime': 'Crypto token presale, token sale, IDO, BNB Chain, non-custodial wallet, no KYC access, token reservation, reserve-now-pay-later, token launch, launchpad, smart contract audit, DEX listing, pancakeswap, early investor, token allocation, vesting, EVM, BEP20, token distribution, presale platform, fair launch, token generation event, soft cap hard cap fundraise, RZ Prime.',
  'Coin Hall': 'Web3 prediction game, luxury prize prediction competition, price prediction, oracle-confirmed outcome, blockchain entertainment, NFT auction, Sotheby\\'s, Christie\\'s, Rolex Patek Philippe luxury watch, Ferrari Lamborghini supercar, tokenized real estate fractional ownership, play-to-earn blockchain gaming, DeFi TVL on-chain activity, NFT marketplace collectible, luxury lifestyle Web3, skill-based contest, smart contract resolution, Coin Hall.',
  'Meta Coin Guard': 'Crypto security, DeFi exploit, protocol hack, wallet drainer, rug pull, smart contract vulnerability, phishing attack, flash loan attack, reentrancy bug, on-chain forensics blockchain forensics, security audit, exit scam, private key compromise, bridge exploit, stolen funds, malware, ZachXBT PeckShield Certik, address poisoning, crypto fraud, Meta Coin Guard.',
  'ChainReporter': 'Bitcoin ETF approval, Ethereum SEC regulation, institutional crypto investment, BlackRock Bitcoin fund, crypto market news, stablecoin USDT USDC, macro finance, Federal Reserve rate decision, Bitcoin price, crypto regulation policy, altcoin market, Binance Coinbase exchange news, blockchain mainstream adoption, corporate Bitcoin treasury, halving, ChainReporter.',
};
let _extractor = null, _brandVecs = null, _initPromise = null;
async function _load() {
  _extractor = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2');
  _brandVecs = {};
  for (const [brand, text] of Object.entries(PROFILES)) {
    const out = await _extractor(text, { pooling:'mean', normalize:true });
    _brandVecs[brand] = Array.from(out.data);
  }
}
function _cosine(a,b) { let d=0; for(let i=0;i<a.length;i++) d+=a[i]*b[i]; return d; }
const EMBED_CHUNK = 12;
async function embedArticles(articles) {
  if (!_initPromise) _initPromise = _load();
  await _initPromise;
  for (let c = 0; c < articles.length; c += EMBED_CHUNK) {
    const chunk = articles.slice(c, c + EMBED_CHUNK);
    const texts = chunk.map(art => (art.title+' '+art.desc).slice(0,512));
    const out = await _extractor(texts,{pooling:'mean',normalize:true});
    const dim = out.dims[out.dims.length-1];
    const flat = out.data;
    chunk.forEach((art,k) => {
      const vec = flat.slice(k*dim, (k+1)*dim);
      art._semScores = {};
      for (const [brand,bv] of Object.entries(_brandVecs)) {
        art._semScores[brand] = Math.max(0,_cosine(vec,bv))*100;
      }
    });
  }
}
_initPromise = _load().catch(err => { window._semRouterError = err.message; });
window._semRouter = { embedArticles, _initPromise };
  `
  document.head.appendChild(s)
}

function NavBar({ onToggleNav, navOpen }) {
  return (
    <nav style={{background:'rgba(12,15,24,0.82)',backdropFilter:'blur(18px)',WebkitBackdropFilter:'blur(18px)',borderBottom:'1px solid rgba(255,255,255,.06)',position:'sticky',top:0,zIndex:50,width:'100%'}}>
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',padding:'0 24px',height:56}}>
        <Link to="/multimedia" style={{textDecoration:'none',display:'flex',alignItems:'center',gap:12,flexShrink:0}}>
          <div style={{width:32,height:32,borderRadius:9,background:'linear-gradient(135deg,#00d4a0,#9b72f5)',display:'flex',alignItems:'center',justifyContent:'center'}}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#07090e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
            </svg>
          </div>
          <span style={{fontFamily:"'Space Grotesk',sans-serif",fontWeight:700,fontSize:17,letterSpacing:'-.02em'}}>
            <span style={{color:'#f0f2f8'}}>Chain</span><span style={{color:'#f0a040'}}>Reporter</span>
          </span>
          <div style={{display:'flex',alignItems:'center',gap:5,padding:'3px 9px',borderRadius:100,background:'rgba(0,212,160,.1)',border:'1px solid rgba(0,212,160,.28)'}}>
            <svg width="9" height="9" viewBox="0 0 24 24" fill="#00d4a0"><circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12" stroke="#00d4a0" strokeWidth="1.5" strokeLinecap="round" fill="none"/></svg>
            <span style={{fontSize:11,fontWeight:700,color:'#00d4a0',letterSpacing:'.04em'}}>AI</span>
          </div>
        </Link>

        <div id="mob-nav-links" style={{display:'flex',alignItems:'center',gap:2}} className={navOpen?'open':''}>
          <Link to="/multimedia" className="nav-link active">Multi Media</Link>
          <Link to="/about" className="nav-link">About Us</Link>
        </div>

        <div style={{display:'flex',alignItems:'center',gap:4}}>
          <button id="mob-menu-btn" onClick={onToggleNav}
            style={{display:'none',width:36,height:36,borderRadius:8,background:'none',border:'none',cursor:'pointer',color:'#7a8499',alignItems:'center',justifyContent:'center',transition:'color .18s,background .18s'}}
            onMouseEnter={e=>{e.currentTarget.style.color='#f0f2f8';e.currentTarget.style.background='rgba(255,255,255,.05)'}}
            onMouseLeave={e=>{e.currentTarget.style.color='#7a8499';e.currentTarget.style.background='none'}}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
          <button style={{width:32,height:32,borderRadius:8,background:'none',border:'none',cursor:'pointer',color:'#7a8499',display:'flex',alignItems:'center',justifyContent:'center',transition:'color .18s,background .18s'}}
            onMouseEnter={e=>{e.currentTarget.style.color='#f0f2f8';e.currentTarget.style.background='rgba(255,255,255,.05)'}}
            onMouseLeave={e=>{e.currentTarget.style.color='#7a8499';e.currentTarget.style.background='none'}}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
            </svg>
          </button>
        </div>
      </div>
    </nav>
  )
}

export default function MultimediaPage() {
  const { mmReport, initPlatformLanes } = useMmStore()
  const analyzeAndRoute = useAnalyzeAndRoute()
  const [topics, setTopics] = useState('Bitcoin ETF, Regulation')
  const [navOpen, setNavOpen] = useState(false)

  useEffect(() => {
    loadSemRouter()
    initPlatformLanes()
  }, [])

  function handleAnalyze() {
    analyzeAndRoute(topics)
  }

  return (
    <>
      <div aria-hidden="true" style={{position:'fixed',inset:0,zIndex:0,pointerEvents:'none',background:'radial-gradient(ellipse 60% 40% at 50% 0%,rgba(0,212,160,.07) 0%,transparent 70%),radial-gradient(ellipse 50% 50% at 80% 80%,rgba(155,114,245,.07) 0%,transparent 70%),radial-gradient(ellipse 40% 30% at 20% 70%,rgba(240,160,64,.05) 0%,transparent 70%)'}}></div>
      <div id="mob-backdrop" className={navOpen?'open':''} onClick={()=>setNavOpen(false)}></div>
      <NavBar onToggleNav={()=>setNavOpen(o=>!o)} navOpen={navOpen} />
      <div id="mm-layout" style={{position:'relative',zIndex:10}}>
        <Sidebar topics={topics} setTopics={setTopics} onAnalyze={handleAnalyze} />
        <MainArea mmReport={mmReport} onOpenReport={()=>{}} />
      </div>
      <PreviewPanel />
    </>
  )
}
