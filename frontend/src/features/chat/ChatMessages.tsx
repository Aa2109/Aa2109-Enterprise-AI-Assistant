import { useEffect, useRef } from 'react'
import { Bot } from 'lucide-react'

import { MessageBubble } from './MessageBubble'
import { ThinkingIndicator } from './ThinkingIndicator'
import { Citations } from './Citations'
import { SourcesPanel } from './SourcesPanel'
import { EmptyState } from '@/components/ui/EmptyState'
import type { ChatResponse, MessageResponse } from '@/lib/api/types'
import { CHAT_STATUS } from '@/lib/api/types'

interface ChatMessagesProps {
  messages: MessageResponse[]
  pending: boolean
  /** Latest agent response for citations/evidence rendering. */
  latestResponse?: ChatResponse | null
  isLoading?: boolean
}

export function ChatMessages({
  messages,
  pending,
  latestResponse,
  isLoading,
}: ChatMessagesProps) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length, pending])

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <ThinkingIndicator label="Loading conversation…" />
      </div>
    )
  }

  if (messages.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <EmptyState
          icon={<Bot className="size-6" />}
          title="What would you like to know?"
          description="Ask about your internal documents, the latest web research, or your data — the assistant's agents will work through it."
        />
      </div>
    )
  }

  const lastIndex = messages.length - 1

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5 px-4 py-6">
      {messages.map((message, index) => (
        <MessageBubble key={message.id} message={message}>
          {/* Attach citations + evidence to the last assistant answer. */}
          {message.role === 'ASSISTANT' &&
            !pending &&
            latestResponse &&
            index === lastIndex && (
              <>
                {pendingApproval(latestResponse) && (
                  <div className="rounded-lg border border-warning/25 bg-warning/10 px-3.5 py-2.5 text-xs text-warning">
                    This request requires an administrator approval and is
                    waiting for one.
                  </div>
                )}
                <Citations citations={latestResponse.citations} />
                <SourcesPanel sources={latestResponse.sources} />
              </>
            )}
        </MessageBubble>
      ))}

      {pending && (
        <MessageBubble
          message={{
            id: 'pending',
            role: 'ASSISTANT',
            content: '',
            message_metadata: {},
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }}
        >
          <ThinkingIndicator className="py-1" />
        </MessageBubble>
      )}

      <div ref={endRef} />
    </div>
  )
}

function pendingApproval(response: ChatResponse): boolean {
  return response.status === CHAT_STATUS.approvalRequired
}