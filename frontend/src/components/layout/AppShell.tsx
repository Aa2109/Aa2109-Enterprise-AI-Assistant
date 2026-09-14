import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { PanelLeft } from 'lucide-react'

import { Sidebar } from './Sidebar'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'

export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()

  // Close the mobile drawer whenever the route changes.
  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

  return (
    // App-frame shell: locked to the viewport so the *page* never scrolls.
    // Each panel scrolls on its own — the sidebar stays fixed while the
    // chat message area scrolls, and the conversation list only moves
    // when the user scrolls it directly.
    <div className="flex h-dvh overflow-hidden bg-canvas">
      {/* Desktop sidebar */}
      <div className="hidden lg:block">
        <Sidebar />
      </div>

      {/* Mobile drawer */}
      <div
        className={cn(
          'fixed inset-0 z-50 bg-black/60 backdrop-blur-sm transition-opacity lg:hidden',
          sidebarOpen ? 'opacity-100' : 'pointer-events-none opacity-0',
        )}
        onClick={() => setSidebarOpen(false)}
        aria-hidden
      />
      <div
        className={cn(
          'fixed inset-y-0 left-0 z-50 transition-transform duration-200 lg:hidden',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <Sidebar />
      </div>

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-edge bg-surface/70 px-4 backdrop-blur">
          <Button
            variant="ghost"
            size="sm"
            aria-label="Open menu"
            className="lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <PanelLeft className="size-4" />
          </Button>
          <h1 className="truncate text-sm font-medium text-fg-muted">
            Enterprise AI Assistant
          </h1>
        </header>

        <main className="min-h-0 flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}