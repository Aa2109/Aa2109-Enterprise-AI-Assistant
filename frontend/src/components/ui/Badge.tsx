import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

type Tone = 'neutral' | 'accent' | 'success' | 'working' | 'danger'

const toneClasses: Record<Tone, string> = {
  neutral: 'bg-elevated text-fg-muted border-edge',
  accent: 'bg-accent-dim text-accent-strong border-accent/25',
  success: 'bg-success/10 text-success border-success/25',
  working: 'bg-warning/10 text-warning border-warning/25',
  danger: 'bg-danger/10 text-danger border-danger/25',
}

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone
}

export function Badge({ tone = 'neutral', className, ...rest }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium leading-4',
        toneClasses[tone],
        className,
      )}
      {...rest}
    />
  )
}