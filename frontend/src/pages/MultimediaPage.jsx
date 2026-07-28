import { useState, useEffect } from 'react'
import { useMmStore, API_BASE } from '../store/mmStore'
import { useAnalyzeAndRoute } from '../hooks/useAnalyzeAndRoute'
import Sidebar from '../components/mm/Sidebar'
import MainArea from '../components/mm/LaneBoard'
import PreviewPanel from '../components/mm/PreviewPanel'
import NavBar from '../components/NavBar'
import FilteringReportModal from '../components/mm/FilteringReportModal'
import ChatWidget from '../components/chat/ChatWidget'
import { useLanguageStore } from '../store/languageStore'
import './MultimediaPage.css'

const SIDEBAR_MIN_WIDTH = 262
const SIDEBAR_MAX_WIDTH = 560

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

export default function MultimediaPage() {
  const { mmReport, setReportOpen, initPlatformLanes, activeCard } = useMmStore()
  const language = useLanguageStore(state => state.language)
  const previewSessionKey = activeCard
    ? `${activeCard.id || ''}|${activeCard.platform || ''}|${activeCard.headline || ''}`
    : 'closed'
  const analyzeAndRoute = useAnalyzeAndRoute()
  const [topics, setTopics] = useState('')
  const [navOpen, setNavOpen] = useState(false)
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = Number(window.localStorage.getItem('chainreporter-sidebar-width'))
    return Number.isFinite(saved) ? Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, saved)) : SIDEBAR_MIN_WIDTH
  })

  useEffect(() => {
    loadSemRouter()
    initPlatformLanes()
  }, [])

  useEffect(() => {
    window.localStorage.setItem('chainreporter-sidebar-width', String(sidebarWidth))
  }, [sidebarWidth])

  function handleAnalyze() {
    analyzeAndRoute(topics)
  }

  function startSidebarResize(event) {
    if (window.innerWidth <= 768) return
    event.preventDefault()
    const startX = event.clientX
    const startWidth = sidebarWidth
    const previousUserSelect = document.body.style.userSelect
    document.body.style.userSelect = 'none'

    const onMove = moveEvent => {
      const dragDistance = moveEvent.clientX - startX
      const width = startWidth + (language === 'fa' ? -dragDistance : dragDistance)
      setSidebarWidth(Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, width)))
    }
    const onUp = () => {
      document.body.style.userSelect = previousUserSelect
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }

  return (
    <>
      <div aria-hidden="true" style={{position:'fixed',inset:0,zIndex:0,pointerEvents:'none',background:'radial-gradient(ellipse 60% 40% at 50% 0%,rgba(0,212,160,.07) 0%,transparent 70%),radial-gradient(ellipse 50% 50% at 80% 80%,rgba(155,114,245,.07) 0%,transparent 70%),radial-gradient(ellipse 40% 30% at 20% 70%,rgba(240,160,64,.05) 0%,transparent 70%)'}}></div>
      <div id="mob-backdrop" className={navOpen?'open':''} onClick={()=>setNavOpen(false)}></div>
      <NavBar onToggleNav={()=>setNavOpen(o=>!o)} navOpen={navOpen} />
      <div id="mm-layout" style={{position:'relative',zIndex:10}}>
        <Sidebar topics={topics} setTopics={setTopics} onAnalyze={handleAnalyze} width={sidebarWidth} />
        <div id="mm-sidebar-resizer" role="separator" aria-orientation="vertical" aria-label="Resize control panel" onMouseDown={startSidebarResize} />
        <MainArea mmReport={mmReport} onOpenReport={() => setReportOpen(true)} />
      </div>
      <PreviewPanel key={previewSessionKey} />
      <FilteringReportModal />
      <ChatWidget activeCard={activeCard} />
    </>
  )
}
