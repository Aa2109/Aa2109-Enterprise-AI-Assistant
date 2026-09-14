import { cn } from '@/lib/utils'

interface SpinnerProps {
  className?: string
  /** Tailwind text color class, e.g. "text-fg-muted". */
  color?: string
}

export function Spinner({ className, color = 'text-accent' }: SpinnerProps) {
  return (
    <svg
      className={cn('size-4 animate-spin', color, className)}
      viewBox="0 0 24 24"
      fill="none"
      aria-label="Loading"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12z"
      />
    </svg>
  )
}