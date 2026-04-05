export const clearAuthStorage = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
}

export const redirectToLogin = () => {
  if (typeof window === 'undefined') return
  if (window.location.pathname === '/login') return
  window.location.href = '/login'
}

export const logoutAndRedirect = async () => {
  clearAuthStorage()
  redirectToLogin()
}
