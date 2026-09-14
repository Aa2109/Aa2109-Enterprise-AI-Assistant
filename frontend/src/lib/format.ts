import type { DocumentStatus } from './api/types'

/** "2026-09-12T14:24:38" → "12 Sep, 14:24" · "Just now" under 60s. */
export function formatDateTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  const diff = Date.now() - date.getTime()
  if (diff > -30_000 && diff < 60_000) return 'Just now'
  return new Intl.DateTimeFormat(undefined, {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

/** Short relative time for the sidebar: "2h", "3d", "12 Sep". */
export function formatRelativeTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  const diff = Date.now() - date.getTime()
  const minutes = Math.floor(diff / 60_000)
  if (minutes < 1) return 'now'
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d`
  return new Intl.DateTimeFormat(undefined, {
    day: 'numeric',
    month: 'short',
  }).format(date)
}

/** Default from a user message: first 6 words (or 8 chars), truncated. */
export function deriveTitle(query: string): string {
  const trimmed = query.trim()
  if (!trimmed) return 'New Conversation'
  const words = trimmed.split(/\s+/)
  const title = words.slice(0, 6).join(' ')
  return title.length > 40 ? `${title.slice(0, 40)}…` : title
}

/** Human label + tone for a document processing status. */
export const DOCUMENT_STATUS_LABEL: Record<DocumentStatus, string> = {
  UPLOADED: 'Uploaded',
  EXTRACTING: 'Extracting text',
  EXTRACTED: 'Extracted',
  CHUNKING: 'Chunking',
  READY: 'Ready',
  FAILED: 'Failed',
}

export const DOCUMENT_STATUS_TONE: Record<
  DocumentStatus,
  'neutral' | 'working' | 'success' | 'danger'
> = {
  UPLOADED: 'neutral',
  EXTRACTING: 'working',
  EXTRACTED: 'working',
  CHUNKING: 'working',
  READY: 'success',
  FAILED: 'danger',
}