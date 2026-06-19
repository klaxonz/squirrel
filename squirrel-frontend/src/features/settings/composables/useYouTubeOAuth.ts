import { onUnmounted, ref } from 'vue'
import {
  getYouTubeOAuthStatus,
  revokeYouTubeOAuth,
  setupYouTubeOAuth,
} from '@/shared/api'
import { getDesktopBridge } from '@/shared/composables/useDesktopBridge'

/** Shape of the YouTube OAuth UI prompt (verification code + dismiss tracking). */
export interface YouTubeOAuthPromptState {
  visible: boolean
  verificationUrl: string
  userCode: string
  copied: boolean
  /** Last code the user dismissed; re-showing the same code is suppressed. */
  dismissedCode: string
}

export interface UseYouTubeOAuthOptions {
  /** Persist + merge a login-status result (owned by the login-status cluster). */
  upsertLoginStatus: (siteName: string, payload: unknown) => void
  /** Re-fetch site runtimes after a state change (owned by the runtimes cluster). */
  refreshSiteRuntimes: () => void | Promise<void>
  /** Open a URL via the desktop bridge, falling back to window.open. */
  openExternalUrl: (url: string | null | undefined) => void | Promise<void>
}

/**
 * Owns the YouTube TV-code OAuth flow: starting/revoke, the verification-code
 * prompt UI (show/hide/copy + dismiss suppression), and the 3s status poll
 * while authorization is pending. The login-status upsert and the runtime
 * refresh are injected so this composable doesn't reach into other clusters.
 */
export function useYouTubeOAuth(options: UseYouTubeOAuthOptions) {
  const { upsertLoginStatus, refreshSiteRuntimes, openExternalUrl } = options

  const youtubeOAuthPrompt = ref<YouTubeOAuthPromptState>({
    visible: false,
    verificationUrl: '',
    userCode: '',
    copied: false,
    dismissedCode: '',
  })

  let ytOAuthPollTimer: ReturnType<typeof setInterval> | null = null
  let youtubeOAuthCopyTimer: ReturnType<typeof setTimeout> | null = null

  const showYouTubeOAuthPrompt = ({ verificationUrl = '', userCode = '' }: { verificationUrl?: string | null; userCode?: string | null } = {}) => {
    const code = String(userCode || '').trim()
    if (!code) {
      hideYouTubeOAuthPrompt()
      return
    }
    if (!youtubeOAuthPrompt.value.visible && youtubeOAuthPrompt.value.dismissedCode === code) {
      return
    }
    youtubeOAuthPrompt.value = {
      visible: true,
      verificationUrl: String(verificationUrl || '').trim(),
      userCode: code,
      copied: false,
      dismissedCode: '',
    }
  }

  const hideYouTubeOAuthPrompt = () => {
    youtubeOAuthPrompt.value.dismissedCode = youtubeOAuthPrompt.value.userCode
    youtubeOAuthPrompt.value.visible = false
  }

  const copyYouTubeOAuthCode = async () => {
    const code = String(youtubeOAuthPrompt.value.userCode || '').trim()
    if (!code) return
    await navigator.clipboard.writeText(code)
    youtubeOAuthPrompt.value.copied = true
    if (youtubeOAuthCopyTimer) clearTimeout(youtubeOAuthCopyTimer)
    youtubeOAuthCopyTimer = setTimeout(() => {
      youtubeOAuthPrompt.value.copied = false
    }, 2000)
  }

  const startYouTubeOAuthPolling = () => {
    stopYouTubeOAuthPolling()
    ytOAuthPollTimer = setInterval(async () => {
      const bridge = getDesktopBridge()
      if (bridge?.isDesktop === true && typeof bridge.getSiteLoginStatus === 'function') {
        const result = await bridge.getSiteLoginStatus('youtube')
        if (result) upsertLoginStatus('youtube', result)
        if (result?.oauth_status === 'pending') {
          showYouTubeOAuthPrompt({
            verificationUrl: result.verification_url,
            userCode: result.user_code,
          })
        } else {
          hideYouTubeOAuthPrompt()
          stopYouTubeOAuthPolling()
        }
        return
      }

      try {
        const data = await getYouTubeOAuthStatus()
        if (data) {
          if (data.status === 'pending') {
            showYouTubeOAuthPrompt({
              verificationUrl: data.verification_url || '',
              userCode: data.user_code || '',
            })
          } else {
            hideYouTubeOAuthPrompt()
          }
          upsertLoginStatus('youtube', {
            site_name: 'youtube',
            supported: true,
            logged_in: data.status === 'authenticated',
            message: data.status === 'pending' ? 'TV 授权中' : (data.status === 'authenticated' ? 'TV 授权有效' : '未配置 TV 授权'),
            checked_at: new Date().toISOString(),
            oauth_status: data.status,
            oauth_account: data.account || null,
            verification_url: data.verification_url || null,
            user_code: data.user_code || null,
          })
        }
        if (data?.status !== 'pending') stopYouTubeOAuthPolling()
      } catch {
        // polling failure — keep the current prompt state, retry next tick
      }
    }, 3000)
  }

  const stopYouTubeOAuthPolling = () => {
    if (ytOAuthPollTimer) clearInterval(ytOAuthPollTimer)
    ytOAuthPollTimer = null
  }

  const handleStartYouTubeOAuth = async () => {
    youtubeOAuthPrompt.value.dismissedCode = ''
    const bridge = getDesktopBridge()
    if (bridge?.isDesktop === true && typeof bridge.openSiteLogin === 'function') {
      const result = await bridge.openSiteLogin('youtube')
      if (result) {
        upsertLoginStatus('youtube', result)
        await openExternalUrl(result.verification_url)
        showYouTubeOAuthPrompt({
          verificationUrl: result.verification_url,
          userCode: result.user_code,
        })
        if (result.oauth_status === 'pending') startYouTubeOAuthPolling()
      }
      return
    }

    try {
      const data = await setupYouTubeOAuth()
      if (data.verification_url) await openExternalUrl(data.verification_url)
      showYouTubeOAuthPrompt({
        verificationUrl: data.verification_url || '',
        userCode: data.user_code || '',
      })
      upsertLoginStatus('youtube', {
        site_name: 'youtube',
        supported: true,
        logged_in: data.status === 'authenticated',
        message: data.status === 'pending' ? 'TV 授权中' : (data.status === 'authenticated' ? 'TV 授权有效' : '未配置 TV 授权'),
        checked_at: new Date().toISOString(),
        oauth_status: data.status,
        oauth_account: data.account || null,
        verification_url: data.verification_url || null,
        user_code: data.user_code || null,
      })
      if (data.status === 'pending') startYouTubeOAuthPolling()
    } catch {
      // setup failure — prompt stays hidden; user can retry
    }
  }

  const handleRevokeYouTubeOAuth = async () => {
    hideYouTubeOAuthPrompt()
    const bridge = getDesktopBridge()
    if (bridge?.isDesktop === true && typeof bridge.clearSiteSession === 'function') {
      const result = await bridge.clearSiteSession('youtube')
      if (result) upsertLoginStatus('youtube', result)
    } else {
      await revokeYouTubeOAuth()
    }
    stopYouTubeOAuthPolling()
    await refreshSiteRuntimes()
  }

  onUnmounted(() => {
    stopYouTubeOAuthPolling()
    if (youtubeOAuthCopyTimer) clearTimeout(youtubeOAuthCopyTimer)
    youtubeOAuthCopyTimer = null
  })

  return {
    youtubeOAuthPrompt,
    showYouTubeOAuthPrompt,
    hideYouTubeOAuthPrompt,
    copyYouTubeOAuthCode,
    handleStartYouTubeOAuth,
    handleRevokeYouTubeOAuth,
  }
}
