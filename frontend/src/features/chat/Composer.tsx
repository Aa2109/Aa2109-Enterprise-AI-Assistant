import { useLayoutEffect, useRef, useState, type KeyboardEvent } from 'react'
import { ArrowUp } from 'lucide-react'

import { cn } from '@/lib/utils'

interface ComposerProps {
  onSend: (query: string) => void
  disabled?: boolean
}

/** Grow the box up to ~8 lines, then scroll inside it. */
const MAX_HEIGHT = 200

export function Composer({ onSend, disabled }: ComposerProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const canSend = value.trim().length > 0 && !disabled

  // Auto-resize: reset to `auto` first so the box shrinks back when
  // text is deleted, then grow to fit the content.
  useLayoutEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`
  }, [value])

  const handleSubmit = () => {
    if (!canSend) return
    onSend(value.trim())
    setValue('')
    textareaRef.current?.focus()
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="border-t border-edge bg-surface px-4 py-3">
      <div
        className={cn(
          'mx-auto flex w-full max-w-3xl items-end gap-2 rounded-xl border bg-elevated p-2 transition-colors',
          'border-edge focus-within:border-accent/50 focus-within:ring-2 focus-within:ring-accent/20',
        )}
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything…  (Shift+Enter for a new line)"
          rows={1}
          aria-label="Message"
          className={cn(
            'min-w-0 flex-1 resize-none bg-transparent px-2 py-2 text-sm leading-6 text-fg',
            'placeholder:text-fg-faint focus:outline-none',
          )}
          style={{ maxHeight: MAX_HEIGHT }}
        />
        <button
          type="button"
          aria-label="Send message"
          onClick={handleSubmit}
          disabled={!canSend}
          className={cn(
            'flex size-9 shrink-0 items-center justify-center rounded-lg transition-colors',
            'bg-accent text-[#070a0f] shadow-glow hover:bg-accent-strong',
            'disabled:cursor-not-allowed disabled:bg-overlay disabled:text-fg-faint disabled:shadow-none',
          )}
        >
          <ArrowUp className="size-4" />
        </button>
      </div>
      <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-fg-faint">
        Answers are grounded in your documents and reviewed by a supervisor
        agent. Always verify critical facts.
      </p>
    </div>
  )
}
