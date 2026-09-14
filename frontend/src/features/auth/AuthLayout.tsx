import type { ReactNode } from 'react'
import { Bot, Database, FileText, Globe, ShieldCheck } from 'lucide-react'
import { cn } from '@/lib/utils'

interface AuthLayoutProps {
  title: string
  subtitle: string
  children: ReactNode
}

const capabilities = [
  { icon: FileText, label: 'Internal knowledge', text: 'RAG over your documents' },
  { icon: Globe, label: 'Web research', text: 'Fresh external sources' },
  { icon: Database, label: 'Structured data', text: 'Read-only SQL answers' },
  { icon: ShieldCheck, label: 'Guardrails', text: 'RBAC, audit, no fabrication' },
]

export function AuthLayout({ title, subtitle, children }: AuthLayoutProps) {
  return (
    <div className="flex min-h-dvh">
      {/* Brand panel */}
      <aside className="relative hidden w-1/2 flex-col justify-between overflow-hidden border-r border-edge bg-gradient-to-br from-[#0b1020] via-surface to-[#110c24] p-10 lg:flex">
        <div className="pointer-events-none absolute -top-32 -right-32 size-96 rounded-full bg-accent/10 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-40 -left-24 size-96 rounded-full bg-agent-research/10 blur-3xl" />

        <div className="relative flex items-center gap-2.5">
          <div className="flex size-9 items-center justify-center rounded-lg bg-accent text-[#070a0f] shadow-glow">
            <Bot className="size-5" />
          </div>
          <span className="text-base font-semibold tracking-tight text-fg">
            Enterprise AI Assistant
          </span>
        </div>

        <div className="relative max-w-md">
          <h1 className="text-3xl font-semibold tracking-tight text-fg">
            An assistant that shows its work.
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-fg-muted">
            One conversation, three specialist agents — internal documents,
            live web research, and your data — supervised and synthesized
            into a single source-attributed answer.
          </p>

          <ul className="mt-8 space-y-3">
            {capabilities.map((cap) => (
              <li key={cap.label} className="flex items-start gap-3">
                <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md border border-edge bg-elevated text-accent-strong">
                  <cap.icon className="size-4" />
                </span>
                <div>
                  <p className="text-sm font-medium text-fg">{cap.label}</p>
                  <p className="text-xs text-fg-faint">{cap.text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-fg-faint">
          LangGraph supervisor + specialists · FastAPI · Qdrant · PostgreSQL
        </p>
      </aside>

      {/* Form panel */}
      <main className="flex flex-1 items-center justify-center bg-canvas px-6 py-12">
        <div className="w-full max-w-sm">
          <div className={cn('mb-8 flex items-center gap-2.5 lg:hidden')}>
            <div className="flex size-9 items-center justify-center rounded-lg bg-accent text-[#070a0f]">
              <Bot className="size-5" />
            </div>
            <span className="text-base font-semibold tracking-tight text-fg">
              Enterprise AI Assistant
            </span>
          </div>

          <h2 className="text-xl font-semibold tracking-tight text-fg">{title}</h2>
          <p className="mt-1 text-sm text-fg-muted">{subtitle}</p>

          <div className="mt-6">{children}</div>
        </div>
      </main>
    </div>
  )
}