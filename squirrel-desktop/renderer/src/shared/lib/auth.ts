export const clearAuthStorage = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
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
  redirectToLogin()
}
