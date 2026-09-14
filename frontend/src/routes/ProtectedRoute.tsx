import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { useSessionStore } from '@/stores/useSession'
import { Spinner } from '@/components/ui/Spinner'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const token = useSessionStore((s) => s.token)
  const isBootstrapping = useSessionStore((s) => s.isBootstrapping)
  const location = useLocation()

  // Validating a persisted token at startup.
  if (isBootstrapping) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-canvas">
        <Spinner className="size-6" />
      </div>
    )
  }

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <>{children}</>
}