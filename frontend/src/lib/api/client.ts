import { useSessionStore } from '@/stores/useSession'
import { navigateApp } from '@/lib/router'
import type { ApiErrorBody } from '@/lib/api/types'

/**
 * Backend base URL. Empty in dev → Vite proxies the API route prefixes
 * to http://localhost:8000 (see vite.config.ts). Point this at the
 * deployed backend in production.
 */
const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? ''

export class ApiError extends Error {
  status: number
  detail?: string

  constructor(status: number, message: string, detail?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

function resolveUrl(path: string): string {
  // Paths are given with a leading slash ("/auth/login").
  if (path.startsWith('http')) return path
  return `${BASE_URL}${path}`
}

function extractDetail(body: unknown, fallback: string): string {
  if (body && typeof body === 'object') {
    const detail = (body as ApiErrorBody).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
  }
  return fallback
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    if (response.status === 204) return undefined as T
    return (await response.json()) as T
  }

  let message = `Request failed (${response.status})`
  let body: unknown = null
  try {
    body = await response.json()
    message = extractDetail(body, message)
  } catch {
    // Non-JSON error body — keep the generic message.
  }

  // Expired / invalid token: drop the session and send the user to login.
  // Guarded so a 401 from within the /login page doesn't reload the page.
  // The `reason` marker makes the login page show a "session expired"
  // notice (see LoginPage). In-app navigation avoids a full page load, so
  // the browser never hits the server and can't render a raw error body.
  if (response.status === 401) {
    useSessionStore.getState().clear()
    if (window.location.pathname !== '/login') {
      navigateApp('/login?reason=session_expired', { reason: 'session_expired' })
    }
  }

  throw new ApiError(response.status, message)
}

export interface RequestOptions {
  method?: string
  body?: unknown
  headers?: Record<string, string>
  /** Raw FormData body (no Content-Type — the browser sets the boundary). */
  formData?: FormData
  isForm?: boolean
  /** Override the Bearer token (defaults to the persisted session token). */
  token?: string
}

export async function api<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    method = 'GET',
    body,
    headers = {},
    formData,
    isForm = false,
    token,
  } = options

  const requestHeaders: Record<string, string> = {
    ...headers,
  }

  const authToken = token ?? useSessionStore.getState().token
  if (authToken) requestHeaders.Authorization = `Bearer ${authToken}`

  if (formData) {
    requestHeaders.Accept = 'application/json'
  } else if (body !== undefined && !isForm) {
    requestHeaders['Content-Type'] = 'application/json'
  }

  const response = await fetch(resolveUrl(path), {
    method,
    headers: requestHeaders,
    body: formData ?? (body !== undefined ? JSON.stringify(body) : undefined),
  })

  return handleResponse<T>(response)
}

export const GET = <T>(path: string, options?: RequestOptions) => api<T>(path, options)

export const POST = <T>(path: string, body?: unknown, options?: RequestOptions) =>
  api<T>(path, { ...options, method: 'POST', body })

export const DELETE_REQ = <T>(path: string) => api<T>(path, { method: 'DELETE' })