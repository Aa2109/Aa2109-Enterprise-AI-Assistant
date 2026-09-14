import { api } from './client'
import type { ChatRequest, ChatResponse } from './types'

/**
 * Non-streaming agentic answer. The backend persists the user + assistant
 * message pair server-side, so the returned bubble and the future
 * `GET /conversations/{id}/messages` stay consistent.
 */
export async function askChat(request: ChatRequest): Promise<ChatResponse> {
  return api<ChatResponse>('/chat/answer', {
    method: 'POST',
    body: {
      query: request.query,
      conversation_id: request.conversation_id,
      limit: request.limit ?? 5,
      ...(request.document_id ? { document_id: request.document_id } : {}),
    },
  })
}