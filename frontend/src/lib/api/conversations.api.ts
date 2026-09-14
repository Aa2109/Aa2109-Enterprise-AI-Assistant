import { api } from './client'
import type {
  ConversationCreateResponse,
  ConversationResponse,
  MessageHistoryResponse,
} from './types'

export function listConversations(): Promise<ConversationResponse[]> {
  return api<ConversationResponse[]>('/conversations')
}

export function createConversation(): Promise<ConversationCreateResponse> {
  return api<ConversationCreateResponse>('/conversations', { method: 'POST' })
}

export function getConversation(id: string): Promise<ConversationResponse> {
  return api<ConversationResponse>(`/conversations/${id}`)
}

export function getConversationMessages(
  id: string,
): Promise<MessageHistoryResponse> {
  return api<MessageHistoryResponse>(`/conversations/${id}/messages`)
}

/** Owner-only at the backend; admins may rename any conversation. */
export function renameConversation(
  id: string,
  title: string,
): Promise<ConversationResponse> {
  return api<ConversationResponse>(`/conversations/${id}`, {
    method: 'PATCH',
    body: { title },
  })
}

/** Owner-only at the backend; admins may delete any conversation. */
export function deleteConversation(id: string): Promise<{ message: string }> {
  return api<{ message: string }>(`/conversations/${id}`, { method: 'DELETE' })
}