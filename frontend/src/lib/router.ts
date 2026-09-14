import type { NavigateFunction } from 'react-router-dom'

/**
 * Bridge that lets non-React code (the API client) navigate the SPA
 * router. `App` registers the router's navigate function on mount; until
 * it does (or after unmount) we fall back to a full-page navigation.
 *
 * Full-page (`window.location.assign`) navigations are what used to make
 * the browser land on the backend's JSON 404 page — used only as a last
 * resort, and the login page is now also servable via the backend's SPA
 * fallback so even that path renders the app.
 */
let navigateFn: NavigateFunction | null = null

export function setAppNavigator(navigate: NavigateFunction): void {
  navigateFn = navigate
}

export function clearAppNavigator(): void {
  navigateFn = null
}

export function navigateApp(to: string, state?: unknown): void {
  if (navigateFn) {
    navigateFn(to, { state, replace: true })
  } else {
    window.location.assign(to)
  }
}