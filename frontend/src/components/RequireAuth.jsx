import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

function LoadingScreen() {
  return (
    <div style={{ display:'flex', alignItems:'center', justifyContent:'center', width:'100%', height:'100vh', background:'#07090e' }}>
      <style>{'@keyframes cr-spin{to{transform:rotate(360deg)}}'}</style>
      <div style={{ width:28, height:28, border:'2.5px solid rgba(255,255,255,.1)', borderTopColor:'#00d4a0', borderRadius:'50%', animation:'cr-spin .7s linear infinite' }} />
    </div>
  )
}

export function RequireAuth({ children }) {
  const { user, authChecked } = useAuthStore()
  if (!authChecked) return <LoadingScreen />
  if (!user) return <Navigate to="/login" replace />
  return children
}

export function GuestOnly({ children }) {
  const { user, authChecked } = useAuthStore()
  if (!authChecked) return <LoadingScreen />
  if (user) return <Navigate to="/multimedia" replace />
  return children
}
