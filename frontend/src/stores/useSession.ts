import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

import type { UserResponse } from '@/lib/api/types'

interface SessionState {
  /** JWT access token (Persisted in localStorage). */
  token: string | null
  /** Authenticated user profile (persisted; refreshed from /auth/me). */
  user: UserResponse | null
  /** True while /auth/me is validating a persisted token at startup. */
  isBootstrapping: boolean
  setSession: (token: string, user: UserResponse) => void
  setUser: (user: UserResponse) => void
  setBootstrapping: (value: boolean) => void
  clear: () => void
}

/**
 * Client-side session. The token and profile are persisted so a page
 * reload keeps the session; `isBootstrapping` covers the startup window
 * where we re-validate the token against `/auth/me` (see `useBootstrap`).
 */
export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isBootstrapping: false,

      setSession: (token, user) =>
        set({ token, user, isBootstrapping: false }),
      setUser: (user) => set({ user }),
      setBootstrapping: (isBootstrapping) => set({ isBootstrapping }),
      clear: () => set({ token: null, user: null, isBootstrapping: false }),
    }),
    {
      name: 'eia.session',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        token: state.token,
        user: state.user,
      }),
    },
  ),
)

/** Reads the current token outside React (API client uses this). */
export const getSessionToken = (): string | null =>
  useSessionStore.getState().token