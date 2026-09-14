import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
}

const variantClasses: Record<Variant, string> = {
  primary:
    'bg-accent text-[#070a0f] hover:bg-accent-strong focus-visible:ring-accent/40 shadow-glow',
  secondary:
    'bg-elevated border border-edge hover:bg-overlay text-fg hover:text-fg focus-visible:ring-accent/40',
  ghost: 'bg-transparent text-fg-muted hover:text-fg hover:bg-overlay focus-visible:ring-accent/40',
  danger:
    'bg-danger/10 text-danger border border-danger/20 hover:bg-danger/20 focus-visible:ring-danger/40',
}

const sizeClasses: Record<Size, string> = {
  sm: 'h-8 text-xs px-3 gap-1.5 rounded-md',
  md: 'h-9 text-sm px-4 gap-2 rounded-lg',
  lg: 'h-11 text-sm px-5 gap-2 rounded-lg',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading = false, className, disabled, children, ...rest }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center justify-center font-medium transition-colors cursor-pointer',
        'disabled:opacity-50 disabled:pointer-events-none',
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...rest}
    >
      {loading && (
        <svg className="size-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden>
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12z" />
        </svg>
      )}
      {children}
    </button>
  ),
)
Button.displayName = 'Button'