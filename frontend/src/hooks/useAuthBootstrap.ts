import { useEffect } from 'react'

import { fetchMe } from '@/lib/api/auth.api'
import { useSessionStore } from '@/stores/useSession'

/**
 * Validates a persisted token against `/auth/me` on startup.
 * - No token → nothing to do (unauthenticated).
 * - Valid → refresh the stored profile.
 * - 401 → the API client clears the session and redirects to /login.
 */
export function useAuthBootstrap() {
  const token = useSessionStore((s) => s.token)
  const setUser = useSessionStore((s) => s.setUser)
  const setBootstrapping = useSessionStore((s) => s.setBootstrapping)

  useEffect(() => {
    if (!token) {
      setBootstrapping(false)
      return
    }

    let cancelled = false
    setBootstrapping(true)
    fetchMe()
      .then((user) => {
        if (!cancelled) setUser(user)
      })
      .catch(() => {
        // 401 clears the session via the client; network errors are left alone.
      })
      .finally(() => {
        if (!cancelled) setBootstrapping(false)
      })

    return () => {
      cancelled = true
    }
  }, [token, setUser, setBootstrapping])
}