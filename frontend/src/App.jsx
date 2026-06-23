import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import MultimediaPage from './pages/MultimediaPage'
import AboutPage from './pages/AboutPage'
import LoginPage from './pages/LoginPage'
import AccountPage from './pages/AccountPage'
import { RequireAuth, GuestOnly } from './components/RequireAuth'
import { useAuthStore } from './store/authStore'

export default function App() {
  useEffect(() => {
    useAuthStore.getState().checkAuth()
  }, [])

  return (
    <Routes>
      <Route path="/login" element={<GuestOnly><LoginPage /></GuestOnly>} />
      <Route path="/" element={<RequireAuth><Navigate to="/multimedia" replace /></RequireAuth>} />
      <Route path="/multimedia" element={<RequireAuth><MultimediaPage /></RequireAuth>} />
      <Route path="/about" element={<RequireAuth><AboutPage /></RequireAuth>} />
      <Route path="/account" element={<RequireAuth><AccountPage /></RequireAuth>} />
    </Routes>
  )
}
