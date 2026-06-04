import { Routes, Route, Navigate } from 'react-router-dom'
import MultimediaPage from './pages/MultimediaPage'
import AboutPage from './pages/AboutPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/multimedia" replace />} />
      <Route path="/multimedia" element={<MultimediaPage />} />
      <Route path="/about" element={<AboutPage />} />
    </Routes>
  )
}
