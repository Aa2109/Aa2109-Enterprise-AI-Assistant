import type { MessageResponse } from '@/lib/api/types'
import { cn } from '@/lib/utils'

interface MessageBubbleProps {
  message: MessageResponse
  /** Set for the last assistant message: renders under the bubble. */
  children?: React.ReactNode
}

export function MessageBubble({ message, children }: MessageBubbleProps) {
  const isUser = message.role === 'USER'

  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[85%] sm:max-w-[75%]',
          isUser ? 'items-end' : 'items-start',
        )}
      >
        <div
          className={cn(
            'rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap',
            isUser
              ? 'rounded-br-md bg-accent text-[#070a0f]'
              : 'rounded-bl-md border border-edge bg-elevated text-fg',
          )}
        >
          {message.content}
        </div>
        {children && !isUser && <div className="mt-2">{children}</div>}
      </div>
    </div>
  )
}