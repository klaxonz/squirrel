import { getDesktopBridge } from '@/shared/composables/useDesktopBridge'
import { Logger } from '@/shared/lib/logger'
import { useToast } from '@/shared/components/toast/useToast'
import type { SiteLoginStatus } from '@/shared/lib/site-runtime-login-status'

/**
 * Desktop-app site login / session management.
 *
 * Owns the site-name normalisation that maps hostnames/aliases onto the set of
 * sites the desktop bridge can log into, plus the two desktop-only session
 * handlers (open login window, clear session). The handlers toggle the
 * per-site "testing" flag, drive the desktop bridge, upsert the merged login
 * status, and persist — exactly the behaviour they had inline in
 * SiteRuntimeManager.vue, now co-located with the normalisation table they
 * share.
 *
 * Extracted from SiteRuntimeManager.vue: the view also had a duplicate
 * `getDesktopBridge` (the shared one in useDesktopBridge is the source of
 * truth); this composable uses the shared helper, killing the duplication.
 */
const DESKTOP_LOGIN_SITES = new Set(['bilibili', 'javdb', 'pornhub', 'youporn'])
const DESKTOP_LOGIN_SITE_ALIASES: Record<string, string> = {
  'b23.tv': 'bilibili',
  'bilibili.com': 'bilibili',
  'javdb.com': 'javdb',
  'pornhub.com': 'pornhub',
  'youporn.com': 'youporn',
}

/** Login-status payload shape the desktop handlers emit. Broader than the
 * typed SiteLoginStatus (the backend/error payloads carry site_name, checked_at,
 * source, etc.); those extra fields round-trip through the cache untouched. */
type DesktopLoginStatusPayload = SiteLoginStatus & Record<string, unknown>

export interface UseSiteDesktopLoginOptions {
  loginStatusTesting: { value: Record<string, boolean> }
  upsertLoginStatus: (siteName: string, payload: SiteLoginStatus | null | undefined) => void
  saveResultsToCache: () => void
}

export interface UseSiteDesktopLoginReturn {
  normalizeDesktopLoginSite: (siteName: string) => string
  supportsDesktopLoginSite: (siteName: string) => boolean
  handleDesktopSiteLogin: (siteName: string) => Promise<void>
  handleClearDesktopSiteSession: (siteName: string) => Promise<void>
}

export function useSiteDesktopLogin(options: UseSiteDesktopLoginOptions): UseSiteDesktopLoginReturn {
  const { loginStatusTesting, upsertLoginStatus, saveResultsToCache } = options
  const toast = useToast()

  const normalizeDesktopLoginSite = (siteName: string): string => {
    const rawValue = String(siteName || '').trim().toLowerCase()
    if (!rawValue) return ''
    let normalizedSite = rawValue.replace(/^\./, '')
    try {
      normalizedSite = new URL(rawValue.includes('://') ? rawValue : `https://${rawValue}`).hostname
        .toLowerCase()
        .replace(/^www\./, '')
        .replace(/^\./, '')
    } catch {
      normalizedSite = normalizedSite.replace(/^www\./, '')
    }
    return DESKTOP_LOGIN_SITE_ALIASES[normalizedSite] || normalizedSite
  }

  const supportsDesktopLoginSite = (siteName: string): boolean =>
    DESKTOP_LOGIN_SITES.has(normalizeDesktopLoginSite(siteName))

  const handleDesktopSiteLogin = async (siteName: string) => {
    if (!siteName) return
    const bridge = getDesktopBridge()
    if (bridge?.isDesktop !== true || typeof bridge.openSiteLogin !== 'function') return

    loginStatusTesting.value[siteName] = true
    try {
      toast.success('桌面登录窗口已打开，手机确认后会自动完成')
      const result = await bridge.openSiteLogin(siteName)
      if (result) {
        upsertLoginStatus(siteName, result as SiteLoginStatus)
        if (result.logged_in) {
          toast.success('桌面登录成功')
        } else {
          toast.error(result.message || '未检测到桌面登录态')
        }
      }
    } catch (error) {
      Logger.error('Failed to open desktop site login', error)
      upsertLoginStatus(siteName, {
        site_name: siteName,
        supported: true,
        logged_in: false,
        message: '桌面登录窗口打开失败',
        checked_at: new Date().toISOString(),
        source: 'desktop',
      } as DesktopLoginStatusPayload)
      toast.error('桌面登录窗口打开失败')
    } finally {
      loginStatusTesting.value[siteName] = false
      saveResultsToCache()
    }
  }

  const handleClearDesktopSiteSession = async (siteName: string) => {
    if (!siteName) return
    const bridge = getDesktopBridge()
    if (bridge?.isDesktop !== true || typeof bridge.clearSiteSession !== 'function') return

    loginStatusTesting.value[siteName] = true
    try {
      const result = await bridge.clearSiteSession(siteName)
      if (result) {
        upsertLoginStatus(siteName, result as SiteLoginStatus)
        toast.success('桌面会话已清除')
      }
    } catch (error) {
      Logger.error('Failed to clear desktop site session', error)
      upsertLoginStatus(siteName, {
        site_name: siteName,
        supported: true,
        logged_in: false,
        message: '清除桌面会话失败',
        checked_at: new Date().toISOString(),
        source: 'desktop',
      } as DesktopLoginStatusPayload)
      toast.error('清除桌面会话失败')
    } finally {
      loginStatusTesting.value[siteName] = false
      saveResultsToCache()
    }
  }

  return {
    normalizeDesktopLoginSite,
    supportsDesktopLoginSite,
    handleDesktopSiteLogin,
    handleClearDesktopSiteSession,
  }
}
