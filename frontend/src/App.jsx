import { useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import MultimediaPage from './pages/MultimediaPage'
import AboutPage from './pages/AboutPage'
import LoginPage from './pages/LoginPage'
import AccountPage from './pages/AccountPage'
import { RequireAuth, GuestOnly } from './components/RequireAuth'
import { useAuthStore } from './store/authStore'
import { useLanguageStore, localizeDocument } from './store/languageStore'

export default function App() {
  const language = useLanguageStore(s => s.language)
  const { pathname } = useLocation()
  const interfaceLanguage = pathname === '/login' ? 'en' : language

  useEffect(() => {
    useAuthStore.getState().checkAuth()
  }, [])

  useEffect(() => {
    document.documentElement.lang = interfaceLanguage === 'fa' ? 'fa' : 'en'
    document.documentElement.dir = interfaceLanguage === 'fa' ? 'rtl' : 'ltr'
    return localizeDocument(interfaceLanguage)
  }, [interfaceLanguage])

  return (
    <div className={interfaceLanguage === 'fa' ? 'app-fa' : 'app-en'}>
    <Routes>
      <Route path="/login" element={<GuestOnly><LoginPage /></GuestOnly>} />
      <Route path="/" element={<RequireAuth><Navigate to="/multimedia" replace /></RequireAuth>} />
      <Route path="/multimedia" element={<RequireAuth><MultimediaPage /></RequireAuth>} />
      <Route path="/about" element={<RequireAuth><AboutPage /></RequireAuth>} />
      <Route path="/account" element={<RequireAuth><AccountPage /></RequireAuth>} />
    </Routes>
    </div>
  )
}
