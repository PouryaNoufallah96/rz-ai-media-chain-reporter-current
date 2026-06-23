import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import './NavBar.css'

export default function NavBar({ onToggleNav, navOpen: navOpenProp }) {
  const [internalOpen, setInternalOpen] = useState(false)
  const navOpen = onToggleNav ? navOpenProp : internalOpen
  const toggle  = onToggleNav || (() => setInternalOpen(o => !o))
  const { pathname } = useLocation()
  const { user } = useAuthStore()
  const linkClass = (path) => `nav-link${pathname.startsWith(path) ? ' active' : ''}`
  const initial = user?.username ? user.username[0].toUpperCase() : '?'

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
          <Link to="/multimedia" className={linkClass('/multimedia')}>Multi Media</Link>
          <Link to="/about" className={linkClass('/about')}>About Us</Link>
          <Link to="/account" className={linkClass('/account')}>Account</Link>
        </div>

        <div style={{display:'flex',alignItems:'center',gap:8}}>
          <button id="mob-menu-btn" onClick={toggle}
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
          <Link to="/account" title={user?.username || 'Account'} style={{width:32,height:32,borderRadius:'50%',background:'linear-gradient(135deg,#00d4a0,#9b72f5)',display:'flex',alignItems:'center',justifyContent:'center',color:'#07090e',fontWeight:700,fontSize:13,fontFamily:"'Space Grotesk',sans-serif",textDecoration:'none',flexShrink:0}}>
            {initial}
          </Link>
        </div>
      </div>
    </nav>
  )
}
