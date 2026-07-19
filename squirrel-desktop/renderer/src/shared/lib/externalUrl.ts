import { getDesktopBridge } from '@/shared/composables/useDesktopBridge'

export const normalizeHttpUrl = (value: string | null | undefined): string | null => {
  const candidate = String(value || '').trim()
  if (!candidate) return null
  try {
    const parsed = new URL(candidate)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? parsed.href : null
  } catch {
    return null
  }
}

export const openExternalUrl = async (value: string | null | undefined): Promise<boolean> => {
  const url = normalizeHttpUrl(value)
  if (!url) return false
  try {
    const bridge = getDesktopBridge()
    if (bridge?.isDesktop && bridge.openExternal) return await bridge.openExternal(url)
    return window.open(url, '_blank', 'noopener,noreferrer') !== null
  } catch {
    return false
  }
}
