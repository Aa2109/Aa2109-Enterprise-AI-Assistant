import { useEffect, useRef, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { Check, MessageSquare, Pencil, Trash2, X } from 'lucide-react'

import { Spinner } from '@/components/ui/Spinner'
import { cn } from '@/lib/utils'
import { formatRelativeTime } from '@/lib/format'
import type { ConversationResponse } from '@/lib/api/types'

interface ConversationItemProps {
  conversation: ConversationResponse
  onRename: (title: string) => Promise<void>
  onDelete: () => Promise<void>
  isRenaming?: boolean
  isDeleting?: boolean
}

/**
 * One sidebar row: navigates on click, and reveals rename/delete on
 * hover. Rename edits the title in place (Enter saves, Escape cancels).
 *
 * The actions are plain inline buttons rather than a dropdown because
 * the conversation list is a scroll container, which would clip a
 * popover on the lower rows.
 */
export function ConversationItem({
  conversation,
  onRename,
  onDelete,
  isRenaming = false,
  isDeleting = false,
}: ConversationItemProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(conversation.title)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editing) inputRef.current?.select()
  }, [editing])

  const startEditing = () => {
    setDraft(conversation.title)
    setEditing(true)
  }

  const commit = async () => {
    const title = draft.trim()
    if (!title || title === conversation.title) {
      setEditing(false)
      return
    }
    try {
      await onRename(title)
      setEditing(false)
    } catch {
      // The caller surfaces the toast; keep the draft so it can be retried.
      inputRef.current?.focus()
    }
  }

  if (editing) {
    return (
      <li>
        <div className="flex items-center gap-1 rounded-md bg-overlay px-2 py-1 ring-1 ring-accent/40">
          <input
            ref={inputRef}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault()
                void commit()
              }
              if (event.key === 'Escape') {
                event.preventDefault()
                setEditing(false)
              }
            }}
            aria-label="Conversation title"
            maxLength={255}
            autoFocus
            className="min-w-0 flex-1 bg-transparent text-sm text-fg focus:outline-none"
          />
          <button
            aria-label="Save title"
            onClick={() => void commit()}
            disabled={isRenaming}
            className="rounded p-1 text-fg-faint transition-colors hover:text-accent-strong disabled:opacity-50"
          >
            {isRenaming ? <Spinner className="size-3.5" /> : <Check className="size-3.5" />}
          </button>
          <button
            aria-label="Cancel rename"
            onClick={() => setEditing(false)}
            className="rounded p-1 text-fg-faint transition-colors hover:text-fg"
          >
            <X className="size-3.5" />
          </button>
        </div>
      </li>
    )
  }

  return (
    <li className="group relative">
      <NavLink
        to={`/chat/${conversation.id}`}
        title={conversation.title}
        className={({ isActive }) =>
          cn(
            'flex items-center gap-2 rounded-md px-2.5 py-1.5 pr-16 text-sm transition-colors',
            isActive
              ? 'bg-overlay font-medium text-fg'
              : 'text-fg-muted hover:bg-overlay/60 hover:text-fg',
          )
        }
      >
        <MessageSquare className="size-3.5 shrink-0 text-fg-faint" />
        <span className="min-w-0 flex-1 truncate">{conversation.title}</span>
      </NavLink>

      {/* Timestamp, swapped for the actions on hover/focus. */}
      <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-[10px] text-fg-faint transition-opacity group-focus-within:opacity-0 group-hover:opacity-0">
        {formatRelativeTime(conversation.updated_at)}
      </span>

      <div
        className={cn(
          'absolute right-1 top-1/2 flex -translate-y-1/2 items-center gap-0.5 transition-opacity',
          'opacity-0 group-focus-within:opacity-100 group-hover:opacity-100',
        )}
      >
        <button
          aria-label={`Rename ${conversation.title}`}
          onClick={(event) => {
            event.preventDefault()
            startEditing()
          }}
          className="rounded p-1 text-fg-faint transition-colors hover:bg-elevated hover:text-fg"
        >
          <Pencil className="size-3.5" />
        </button>
        <button
          aria-label={`Delete ${conversation.title}`}
          disabled={isDeleting}
          onClick={(event) => {
            event.preventDefault()
            void onDelete()
          }}
          className="rounded p-1 text-fg-faint transition-colors hover:bg-elevated hover:text-danger disabled:opacity-50"
        >
          {isDeleting ? <Spinner className="size-3.5" /> : <Trash2 className="size-3.5" />}
        </button>
      </div>
    </li>
  )
}
