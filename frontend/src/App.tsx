import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom'

import { AppShell } from '@/components/layout/AppShell'
import { ProtectedRoute } from '@/routes/ProtectedRoute'
import { LoginPage } from '@/features/auth/LoginPage'
import { SignupPage } from '@/features/auth/SignupPage'
import { ChatPage, ChatHome } from '@/features/chat/ChatPage'
import { DocumentsPage } from '@/features/documents/DocumentsPage'
import { clearAppNavigator, setAppNavigator } from '@/lib/router'

/**
 * Hands the router's navigate function to the API client (non-React code)
 * so session-expiry can redirect without a full page load.
 */
function RouterBridge() {
  const navigate = useNavigate()

  useEffect(() => {
    setAppNavigator(navigate)
    return () => clearAppNavigator()
  }, [navigate])

  return null
}

export function App() {
  return (
    <BrowserRouter>
      <RouterBridge />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />

        <Route
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<ChatHome />} />
          <Route path="/chat/:conversationId" element={<ChatPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}