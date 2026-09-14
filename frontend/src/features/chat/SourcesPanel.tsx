import { useState } from 'react'
import { ChevronDown, FileSearch } from 'lucide-react'

import type { SourceChunk } from '@/lib/api/types'
import { cn } from '@/lib/utils'

interface SourcesPanelProps {
  sources: SourceChunk[]
  className?: string
}

/**
 * Collapsible panel of structured RAG chunk detail returned on
 * `ChatResponse.sources`: document, chunk index, similarity score and
 * the retrieved text excerpt.
 */
export function SourcesPanel({ sources, className }: SourcesPanelProps) {
  const [open, setOpen] = useState(false)

  if (sources.length === 0) return null

  return (
    <div className={cn('overflow-hidden rounded-xl border border-edge bg-surface', className)}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-2 px-3.5 py-2.5 text-left text-xs font-medium text-fg-muted transition-colors hover:bg-overlay/50"
      >
        <FileSearch className="size-4 text-accent-strong" />
        Evidence used ({sources.length} chunks)
        <ChevronDown
          className={cn(
            'ml-auto size-4 text-fg-faint transition-transform',
            open && 'rotate-180',
          )}
        />
      </button>

      {open && (
        <ul className="divide-y divide-edge border-t border-edge">
          {sources.map((source) => (
            <li key={`${source.chunk_id}-${source.chunk_index}`} className="px-3.5 py-3">
              <div className="mb-1 flex items-center gap-2 text-[11px] text-fg-faint">
                <span className="truncate font-medium">doc {source.document_id.slice(0, 8)}</span>
                <span>·</span>
                <span>chunk {source.chunk_index}</span>
                <span>·</span>
                <span>{source.score.toFixed(3)}</span>
              </div>
              <p className="text-xs leading-relaxed text-fg-muted line-clamp-3">
                {source.content}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}