import { cn } from '@/lib/utils'

interface ThinkingIndicatorProps {
  label?: string
  className?: string
}

/** Animated "the supervisor is working…" placeholder. */
export function ThinkingIndicator({
  label = 'Thinking…',
  className,
}: ThinkingIndicatorProps) {
  return (
    <div className={cn('flex items-center gap-2 text-sm text-fg-muted', className)}>
      <span className="flex items-center gap-1">
        {[0, 1, 2].map((dot) => (
          <span
            key={dot}
            className="size-1.5 animate-bounce rounded-full bg-accent"
            style={{ animationDelay: `${dot * 150}ms` }}
          />
        ))}
      </span>
      <span>{label}</span>
    </div>
  )
}