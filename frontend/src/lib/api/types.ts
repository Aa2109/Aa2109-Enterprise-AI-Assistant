/**
 * Type mirrors of the backend FastAPI/Pydantic schemas.
 * Keep these in sync with `app/schemas/*.py` in the backend.
 */

// ── Auth ──────────────────────────────────────────────────────────────

export interface SignupRequest {
  email: string
  password: string
  full_name: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user_id: string
  role: string
}

export interface UserResponse {
  id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
}

export type Role = 'user' | 'analyst' | 'admin'

// ── Conversations & messages ──────────────────────────────────────────

export interface ConversationCreateResponse {
  id: string
  title: string
}

export interface ConversationResponse {
  id: string
  owner_id: string
  title: string
  created_at: string
  updated_at: string
}

export type MessageRole = 'SYSTEM' | 'USER' | 'ASSISTANT' | 'TOOL'

export interface MessageResponse {
  id: string
  role: MessageRole
  content: string
  message_metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface MessageHistoryResponse {
  conversation_id: string
  messages: MessageResponse[]
}

// ── Documents ─────────────────────────────────────────────────────────

export type DocumentStatus =
  | 'UPLOADED'
  | 'EXTRACTING'
  | 'EXTRACTED'
  | 'CHUNKING'
  | 'READY'
  | 'FAILED'

export interface DocumentResponse {
  id: string
  original_filename: string
  status: DocumentStatus
  created_at: string
}

// ── Chat ──────────────────────────────────────────────────────────────

export interface ChatRequest {
  query: string
  conversation_id: string
  /** 1–10, default 5. */
  limit?: number
  owner_id?: string
  document_id?: string
}

export interface SourceChunk {
  chunk_id: string
  document_id: string
  chunk_index: number
  content: string
  score: number
}

export interface ChatResponse {
  answer: string | null
  sources: SourceChunk[]
  /** Human-readable citation list, e.g. "employee_leave_policy.pdf". */
  citations: string[]
  status: string
  approval_id: string | null
}

export const CHAT_STATUS = {
  completed: 'completed',
  approvalRequired: 'approval_required',
} as const

// ── Shared errors ─────────────────────────────────────────────────────

export interface ApiErrorBody {
  detail?: string | { msg?: string }[]
}