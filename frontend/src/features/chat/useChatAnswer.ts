import { useMutation, useQueryClient } from '@tanstack/react-query'

import { conversationKeys } from '@/features/conversations/useConversations'
import { askChat } from '@/lib/api/chat.api'
import type {
  ChatResponse,
  MessageHistoryResponse,
  MessageResponse,
} from '@/lib/api/types'

/**
 * Sends a question and keeps the messages query cache in sync:
 * - optimistic user bubble while the agent works,
 * - refetch after success (the server has persisted the real pair),
 * - restore the previous state on failure (nothing was persisted).
 */
export function useChatAnswer(conversationId: string) {
  const queryClient = useQueryClient()
  const messagesKey = conversationKeys.messages(conversationId)

  return useMutation({
    mutationFn: (query: string) =>
      askChat({ query, conversation_id: conversationId }),

    onMutate: async (query) => {
      await queryClient.cancelQueries({ queryKey: messagesKey })
      const previous = queryClient.getQueryData<MessageHistoryResponse>(messagesKey)

      const optimistic: MessageResponse = {
        id: `optimistic-${Date.now()}`,
        role: 'USER',
        content: query,
        message_metadata: {},
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }

      queryClient.setQueryData<MessageHistoryResponse>(messagesKey, (data) =>
        data
          ? { ...data, messages: [...data.messages, optimistic] }
          : {
              conversation_id: conversationId,
              messages: [optimistic],
            },
      )

      return previous
    },

    onError: (_error, _query, previous) => {
      queryClient.setQueryData(messagesKey, previous)
    },

    onSuccess: () => {
      // Server persisted the user/assistant pair — refetch the truth.
      queryClient.invalidateQueries({ queryKey: messagesKey })
      // The first answer also names the conversation server-side, and
      // every answer bumps updated_at (the sidebar orders on it).
      queryClient.invalidateQueries({ queryKey: conversationKeys.all })
    },
  })
}

export type { ChatResponse }