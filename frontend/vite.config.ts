import path from 'node:path'
import type { IncomingMessage } from 'node:http'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// API routers in the backend are mounted at the root (no /api/v1 prefix),
// so in dev we proxy those prefixes straight to the FastAPI server.
// Set VITE_API_BASE_URL to an absolute URL for a production deployment.
const API_TARGET = process.env.VITE_API_TARGET ?? 'http://localhost:8000'

const API_ROUTE_PREFIXES = [
  '/auth',
  '/chat',
  '/conversations',
  '/documents',
  '/search',
  '/memories',
  '/approvals',
  '/health',
  '/metrics',
]

/**
 * A full-page navigation (hard refresh on a client route like
 * `/chat/<id>`) is a document request — the browser sends
 * `Accept: text/html`. Those must stay on Vite's own SPA fallback so the
 * dev server serves its index.html: proxying them to the backend would
 * return the *production* build's index.html, which references hashed
 * `/assets/*` bundles the dev asset pipeline can't serve (broken JS, app
 * never boots). API calls (an `Accept` header that is not `text/html`,
 * e.g. the catch-all for fetch or `application/json`) and streams
 * (`text/event-stream`) carry no `text/html` and still forward upstream.
 */
const isDocumentRequest = (req: IncomingMessage): boolean =>
  (req.headers.accept ?? '').includes('text/html')

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: Object.fromEntries(
      API_ROUTE_PREFIXES.map((prefix) => [
        prefix,
        {
          target: API_TARGET,
          changeOrigin: true,
          bypass: (req) => (isDocumentRequest(req) ? '/index.html' : undefined),
        },
      ]),
    ),
  },
})