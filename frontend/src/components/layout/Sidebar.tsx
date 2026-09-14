import { useState } from 'react'
import { NavLink, useNavigate, useParams } from 'react-router-dom'
import {
  Bot,
  FileText,
  LogOut,
  Plus,
} from 'lucide-react'
import { toast } from 'sonner'

import { ConversationItem } from '@/features/conversations/ConversationItem'
import {
  useConversations,
  useCreateConversation,
  useDeleteConversation,
  useRenameConversation,
} from '@/features/conversations/useConversations'
import { useSessionStore } from '@/stores/useSession'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { cn } from '@/lib/utils'
import type { Role } from '@/lib/api/types'

const roleTone: Record<Role, 'neutral' | 'accent' | 'success'> = {
  user: 'neutral',
  analyst: 'accent',
  admin: 'success',
}

export function Sidebar() {
  const navigate = useNavigate()
  const { conversationId: activeId } = useParams()
  const user = useSessionStore((s) => s.user)
  const clear = useSessionStore((s) => s.clear)
  const { data: conversations, isLoading } = useConversations()
  const createMutation = useCreateConversation()
  const renameMutation = useRenameConversation()
  const deleteMutation = useDeleteConversation()
  const [busyId, setBusyId] = useState<string | null>(null)

  const handleNewChat = async () => {
    try {
      const created = await createMutation.mutateAsync()
      navigate(`/chat/${created.id}`)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Could not start a conversation'
      toast.error(message)
    }
  }

  const handleRename = async (conversationId: string, title: string) => {
    setBusyId(conversationId)
    try {
      await renameMutation.mutateAsync({ id: conversationId, title })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Could not rename conversation'
      toast.error(message)
      throw error
    } finally {
      setBusyId(null)
    }
  }

  const handleDelete = async (conversationId: string) => {
    if (!window.confirm('Delete this conversation? This cannot be undone.')) return
    setBusyId(conversationId)
    try {
      await deleteMutation.mutateAsync(conversationId)
      toast.success('Conversation deleted')
      // If it was the active conversation, land on the empty chat home.
      if (activeId === conversationId) {
        navigate('/')
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Could not delete conversation'
      toast.error(message)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <aside className="flex h-dvh w-64 flex-col border-r border-edge bg-surface">
      {/* Brand */}
      <div className="flex h-14 shrink-0 items-center gap-2.5 border-b border-edge px-4">
        <div className="flex size-8 items-center justify-center rounded-lg bg-accent text-[#070a0f]">
          <Bot className="size-4" />
        </div>
        <span className="truncate text-sm font-semibold tracking-tight text-fg">
          Enterprise AI Assistant
        </span>
      </div>

      {/* New chat */}
      <div className="p-3">
        <button
          onClick={handleNewChat}
          disabled={createMutation.isPending}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-edge bg-elevated px-3 py-2 text-sm font-medium text-fg transition-colors hover:border-accent/40 hover:bg-overlay disabled:opacity-50"
        >
          {createMutation.isPending ? (
            <Spinner className="size-4" />
          ) : (
            <Plus className="size-4" />
          )}
          New chat
        </button>
      </div>

      {/* Conversations */}
      <nav className="min-h-0 flex-1 overflow-y-auto px-3 pb-2">
        <p className="px-1 pb-1.5 text-[11px] font-medium uppercase tracking-wider text-fg-faint">
          Conversations
        </p>

        {isLoading && (
          <div className="space-y-1.5 px-1">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-8 animate-pulse rounded-md bg-elevated" />
            ))}
          </div>
        )}

        {!isLoading && conversations?.length === 0 && (
          <p className="px-1 py-2 text-xs text-fg-faint">
            No conversations yet. Start a new chat.
          </p>
        )}

        <ul className="space-y-0.5">
          {conversations?.map((conversation) => (
            <ConversationItem
              key={conversation.id}
              conversation={conversation}
              isRenaming={renameMutation.isPending && busyId === conversation.id}
              isDeleting={deleteMutation.isPending && busyId === conversation.id}
              onRename={(title) => handleRename(conversation.id, title)}
              onDelete={() => handleDelete(conversation.id)}
            />
          ))}
        </ul>
      </nav>

      {/* Footer */}
      <div className="shrink-0 border-t border-edge p-3">
        <NavLink
          to="/documents"
          className={({ isActive }) =>
            cn(
              'mb-2 flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm transition-colors',
              isActive
                ? 'bg-overlay font-medium text-fg'
                : 'text-fg-muted hover:bg-overlay/60 hover:text-fg',
            )
          }
        >
          <FileText className="size-4" />
          Documents
        </NavLink>

        <div className="flex items-center gap-2 rounded-lg bg-elevated px-2.5 py-2">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-accent-dim text-xs font-semibold text-accent-strong">
            {initials(user?.full_name ?? user?.email ?? '?')}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-fg">
              {user?.full_name || user?.email}
            </p>
            <div className="flex items-center gap-1.5">
              <Badge tone={roleTone[(user?.role ?? 'user') as Role]} className="capitalize">
                {user?.role ?? 'user'}
              </Badge>
            </div>
          </div>
          <button
            aria-label="Sign out"
            onClick={() => {
              clear()
              toast.info('Signed out')
              navigate('/login', { replace: true })
            }}
            className="rounded-md p-1.5 text-fg-faint transition-colors hover:bg-overlay hover:text-danger"
          >
            <LogOut className="size-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
  return name.slice(0, 2).toUpperCase()
}