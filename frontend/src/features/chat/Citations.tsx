import { FileText, Globe } from 'lucide-react'
import { cn } from '@/lib/utils'

interface CitationsProps {
  citations: string[]
  className?: string
}

/**
 * Renders the human-readable citation list from `ChatResponse.citations`.
 * Strings typically look like "employee_leave_policy.pdf" (internal, RAG)
 * or "Java 24 Release Notes — https://openjdk.org/..." (external, research).
 */
export function Citations({ citations, className }: CitationsProps) {
  if (citations.length === 0) return null

  return (
    <div className={cn('space-y-1.5', className)}>
      <p className="text-[11px] font-medium uppercase tracking-wider text-fg-faint">
        Sources
      </p>
      <div className="flex flex-wrap gap-1.5">
        {citations.map((citation, index) => {
          const isExternal = /https?:\/\//i.test(citation)
          const link = citation.match(/https?:\/\/[^\s]+/)?.[0]
          const Icon = isExternal ? Globe : FileText

          return (
            <span
              key={`${index}-${citation}`}
              className={cn(
                'inline-flex max-w-full items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs',
                isExternal
                  ? 'border-agent-research/30 bg-agent-research/10 text-agent-research'
                  : 'border-accent/30 bg-accent-dim text-accent-strong',
              )}
            >
              <Icon className="size-3.5 shrink-0" />
              {link ? (
                <a
                  href={link}
                  target="_blank"
                  rel="noreferrer"
                  className="truncate underline-offset-2 hover:underline"
                >
                  {citation.replace(link, '').replace(/\s*[-—]\s*$/, '') || link}
                </a>
              ) : (
                <span className="truncate">{citation}</span>
              )}
            </span>
          )
        })}
      </div>
    </div>
  )
}