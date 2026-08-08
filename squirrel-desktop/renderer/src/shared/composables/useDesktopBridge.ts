export const getDesktopBridge = (): DesktopAppBridge | null => {
  if (typeof window === 'undefined') return null
  return window.desktopApp || null
}

export const useDesktopBridge = () => {
  const isDesktop = (): boolean => getDesktopBridge()?.isDesktop === true

  const getServerUrl = (): Promise<string> | undefined => {
    const b = getDesktopBridge()
    return b?.getServerUrl?.()
  }

  const setServerUrl = (url: string): Promise<string | false> | undefined => {
    const b = getDesktopBridge()
    return b?.setServerUrl?.(url)
  }

  const clearServerUrl = (): Promise<boolean> | undefined => {
    const b = getDesktopBridge()
    return b?.clearServerUrl?.()
  }

  const onServerUrlChange = (listener: (url: string) => void): (() => void) | undefined => {
    const b = getDesktopBridge()
    return b?.onServerUrlChange?.(listener)
  }

  const onNavigate = (listener: (direction: 'back' | 'forward') => void): (() => void) | undefined => {
    return getDesktopBridge()?.onNavigate?.(listener)
  }

  const getRemoteChannel = (params: Parameters<NonNullable<DesktopAppBridge['getRemoteChannel']>>[0]) => {
    const b = getDesktopBridge()
    return b?.getRemoteChannel?.(params)
  }

  const resolveYouTubeSubtitles = (url: string, opts?: { lang?: string; format?: 'vtt' }) => {
    const b = getDesktopBridge()
    return b?.resolveYouTubeSubtitles?.(url, opts)
  }

  const resolveBilibiliSubtitles = (url: string, opts?: { lang?: string; format?: 'vtt' }) => {
    const b = getDesktopBridge()
    return b?.resolveBilibiliSubtitles?.(url, opts)
  }

  const mintYouTubePoToken = (videoId: string) => {
    const b = getDesktopBridge()
    return b?.mintYouTubePoToken?.(videoId)
  }

  const openExternal = (url: string) => {
    const b = getDesktopBridge()
    return b?.openExternal?.(url)
  }

  return {
    isDesktop,
    getServerUrl,
    setServerUrl,
    clearServerUrl,
    onServerUrlChange,
    onNavigate,
    getRemoteChannel,
    resolveYouTubeSubtitles,
    resolveBilibiliSubtitles,
    mintYouTubePoToken,
    openExternal,
    getDesktopBridge,
  }
}
