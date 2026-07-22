const normalizeAbsoluteUrl = (value) => {
  const normalized = String(value || '').trim()
  if (!normalized) return ''

  try {
    return new URL(normalized).toString()
  } catch {
    return ''
  }
}

/**
 * Resolve the renderer entry without letting a stale local build shadow Vite.
 *
 * `electron .` is a development entrypoint. Loading renderer/dist there makes
 * the page run under file:// even when Vite is healthy, which changes cookie
 * same-site semantics and also serves stale assets. Only a packaged Electron
 * build should use the shipped file URL.
 */
export const resolveDesktopRendererUrl = ({
  configuredUrl,
  isPackaged,
  packagedRendererUrl,
  devRendererUrl,
}) => {
  const configured = normalizeAbsoluteUrl(configuredUrl)
  if (configured) return configured

  const fallback = normalizeAbsoluteUrl(isPackaged ? packagedRendererUrl : devRendererUrl)
  if (!fallback) {
    throw new Error('Unable to resolve desktop renderer URL')
  }
  return fallback
}
