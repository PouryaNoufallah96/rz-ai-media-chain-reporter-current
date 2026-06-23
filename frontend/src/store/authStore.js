import { create } from 'zustand'
import { API_BASE } from './mmStore'

export const useAuthStore = create((set) => ({
  user: null,
  authChecked: false,
  authError: '',

  checkAuth: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/me`, { credentials: 'include' })
      if (res.ok) {
        const data = await res.json()
        set({ user: data.user, authChecked: true })
      } else {
        set({ user: null, authChecked: true })
      }
    } catch {
      set({ user: null, authChecked: true })
    }
  },

  login: async (identifier, password, rememberMe = false) => {
    set({ authError: '' })
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier, password, rememberMe }),
      })
      const data = await res.json()
      if (!res.ok) {
        set({ authError: data.error || 'Login failed' })
        return false
      }
      set({ user: data.user, authChecked: true, authError: '' })
      return true
    } catch (e) {
      set({ authError: e.message || 'Login failed' })
      return false
    }
  },

  logout: async () => {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, { method: 'POST', credentials: 'include' })
    } catch { /* ignore */ }
    set({ user: null })
  },
}))
