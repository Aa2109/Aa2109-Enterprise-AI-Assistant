import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  createConversation,
  deleteConversation,
  getConversationMessages,
  listConversations,
  renameConversation,
} from '@/lib/api/conversations.api'
import { useSessionStore } from '@/stores/useSession'
import type { ConversationResponse } from '@/lib/api/types'

export const conversationKeys = {
  all: ['conversations'] as const,
  messages: (id: string) => ['conversations', id, 'messages'] as const,
}

export function useConversations() {
  return useQuery({
    queryKey: conversationKeys.all,
    queryFn: listConversations,
    staleTime: 30_000,
  })
}

/** Creates a conversation; callers navigate into it. */
export function useCreateConversation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createConversation,
    onSuccess: (created) => {
      // POST /conversations returns only {id, title}; fill in the rest
      // so the sidebar can render the row before the list refetches.
      const now = new Date().toISOString()
      const optimistic: ConversationResponse = {
        id: created.id,
        title: created.title,
        owner_id: useSessionStore.getState().user?.id ?? '',
        created_at: now,
        updated_at: now,
      }

      queryClient.setQueryData<ConversationResponse[]>(
        conversationKeys.all,
        (existing = []) =>
          existing.some((c) => c.id === created.id)
            ? existing
            : [optimistic, ...existing],
      )
      queryClient.invalidateQueries({ queryKey: conversationKeys.all })
    },
  })
}

/** Owner-only at the backend; admins may rename any conversation. */
export function useRenameConversation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      renameConversation(id, title),
    onSuccess: (updated) => {
      queryClient.setQueryData<ConversationResponse[]>(
        conversationKeys.all,
        (existing = []) =>
          existing.map((c) => (c.id === updated.id ? { ...c, ...updated } : c)),
      )
    },
  })
}

/** Owner-only at the backend; admins may delete any conversation. */
export function useDeleteConversation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteConversation,
    onSuccess: (_, conversationId: string) => {
      queryClient.setQueryData<ConversationResponse[]>(
        conversationKeys.all,
        (existing = []) => existing.filter((c) => c.id !== conversationId),
      )
      queryClient.removeQueries({ queryKey: conversationKeys.messages(conversationId) })
    },
  })
}

export function useConversationMessages(conversationId: string | null | undefined) {
  return useQuery({
    queryKey: conversationKeys.messages(conversationId ?? ''),
    queryFn: () => getConversationMessages(conversationId!),
    enabled: Boolean(conversationId),
    staleTime: 15_000,
  })
}
