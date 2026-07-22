export const AUTH_INVALIDATED_EVENT = 'squirrel:auth-invalidated'

export const clearAuthStorage = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
}

export const subscribeToAuthInvalidation = (listener: () => void): (() => void) => {
  if (typeof window === 'undefined') return () => {}
  window.addEventListener(AUTH_INVALIDATED_EVENT, listener)
  return () => window.removeEventListener(AUTH_INVALIDATED_EVENT, listener)
}

const notifyAuthInvalidated = () => {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new Event(AUTH_INVALIDATED_EVENT))
}

/**
 * App routes use Vue hash history (`#/login`), so pathname is usually `/`.
 * Read the SPA path from the hash first; fall back to pathname for non-SPA contexts.
 */
export function getAppRoutePath(
  locationLike: Pick<Location, 'hash' | 'pathname'> = window.location,
): string {
  const hash = locationLike.hash || ''
  if (hash.startsWith('#')) {
    const route = hash.slice(1)
    const pathOnly = route.split('?')[0] || '/'
    return pathOnly.startsWith('/') ? pathOnly : `/${pathOnly}`
  }
  return locationLike.pathname || '/'
}

export function isAuthShellRoute(path: string): boolean {
  return (
    path === '/login'
    || path.startsWith('/login/')
    || path === '/register'
    || path.startsWith('/register/')
    || path === '/server-config'
    || path.startsWith('/server-config/')
  )
}

const redirectToLogin = () => {
  if (typeof window === 'undefined') return
  if (isAuthShellRoute(getAppRoutePath())) return

  // Keep the Vite/Electron origin intact; only switch the hash route.
  // A pathname replace('/login') leaves hash history apps on a broken URL like
  // `/login#/server-config` and breaks visual/login navigation.
  const nextHash = '#/login'
  if (window.location.hash !== nextHash) {
    window.location.hash = nextHash
  }
}

export const logoutAndRedirect = async () => {
  clearAuthStorage()
  // Keep Pinia and the router in the same state before changing the hash. The
  // event is synchronous, so a 401 can never leave a stale authenticated user
  // that immediately bounces /login back to the protected home route.
  notifyAuthInvalidated()
  redirectToLogin()
}
