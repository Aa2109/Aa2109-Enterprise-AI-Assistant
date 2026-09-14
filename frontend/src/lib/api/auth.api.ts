import { api } from './client'
import type {
  LoginRequest,
  SignupRequest,
  TokenResponse,
  UserResponse,
} from './types'

export async function signup(request: SignupRequest): Promise<TokenResponse> {
  return api<TokenResponse>('/auth/signup', {
    method: 'POST',
    body: request,
  })
}

export async function login(request: LoginRequest): Promise<TokenResponse> {
  return api<TokenResponse>('/auth/login', {
    method: 'POST',
    body: request,
  })
}

/** Fetch the current user. Pass `token` to use a fresh token (e.g. right
 * after login) instead of the persisted session token. */
export async function fetchMe(token?: string): Promise<UserResponse> {
  return api<UserResponse>('/auth/me', { token })
}