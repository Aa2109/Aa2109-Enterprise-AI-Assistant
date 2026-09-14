import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { Bot, Sparkles } from 'lucide-react'

import { ChatMessages } from './ChatMessages'
import { Composer } from './Composer'
import { useChatAnswer } from './useChatAnswer'
import { useConversationMessages, useCreateConversation } from '@/features/conversations/useConversations'
import { Button } from '@/components/ui/Button'
import type { ChatResponse } from '@/lib/api/types'

export function ChatHome() {
  const navigate = useNavigate()
  const createMutation = useCreateConversation()

  const startChat = async () => {
    try {
      const created = await createMutation.mutateAsync()
      navigate(`/chat/${created.id}`)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Could not start a conversation'
      toast.error(message)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 text-center">
        <div className="flex size-14 items-center justify-center rounded-2xl bg-accent text-[#070a0f] shadow-glow">
          <Bot className="size-7" />
        </div>
        <h2 className="max-w-md text-2xl font-semibold tracking-tight text-fg">
          Your enterprise assistant awaits
        </h2>
        <p className="max-w-md text-sm leading-relaxed text-fg-muted">
          Start a conversation to ask about your internal documents, the
          latest industry research, or your own data — supervisors route each
          question to the right specialist agent.
        </p>
        <Button size="lg" onClick={startChat} loading={createMutation.isPending}>
          <Sparkles className="size-4" />
          New conversation
        </Button>
      </div>
      <p className="pb-4 text-center text-xs text-fg-faint">
        Supports RAG over your documents, live web research, and read-only
        structured data queries.
      </p>
    </div>
  )
}

export function ChatPage() {
  const { conversationId = '' } = useParams()
  const { data, isLoading } = useConversationMessages(conversationId)
  const answerMutation = useChatAnswer(conversationId)
  const [latestResponse, setLatestResponse] = useState<ChatResponse | null>(null)

  const messages = data?.messages ?? []

  const handleSend = async (query: string) => {
    try {
      const response = await answerMutation.mutateAsync(query)
      setLatestResponse(response)
      if (response.status === 'approval_required') {
        toast.info('This request needs an approval before it can continue.')
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'The assistant could not answer'
      toast.error(message)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto">
        <ChatMessages
          messages={messages}
          pending={answerMutation.isPending}
          latestResponse={latestResponse}
          isLoading={isLoading}
        />
      </div>
      <Composer onSend={handleSend} disabled={answerMutation.isPending} />
    </div>
  )
}