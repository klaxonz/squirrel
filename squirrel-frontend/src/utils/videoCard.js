export const formatVideoCardId = (videoId, options = {}) => {
  const { length = 4, placeholder = '-'.repeat(Math.max(1, length)) } = options
  const normalized = String(videoId ?? '').trim()

  if (!normalized) {
    return placeholder
  }

  return normalized.slice(-length).toUpperCase()
}
