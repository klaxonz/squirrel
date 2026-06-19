import { computed, onUnmounted, ref } from 'vue'
import { createMusicQrLogin, checkMusicQrLogin, type MusicQrLogin, type MusicAuthStatus } from '@/shared/api/music'
import { Logger } from '@/shared/lib/logger'

export function useMusicQrLogin() {
  const isOpen = ref(false)
  const loading = ref(false)
  const qrLogin = ref<MusicQrLogin | null>(null)
  const status = ref(0)
  const authStatus = ref<MusicAuthStatus | null>(null)
  let timer: ReturnType<typeof setInterval> | null = null

  const statusText = computed(() => {
    if (loading.value) return '二维码生成中'
    if (status.value === 4) return '登录成功'
    if (status.value === 2) return '已扫码，请在手机上确认'
    if (status.value === 0 && qrLogin.value) return '二维码已过期，请刷新'
    return '使用酷狗音乐 App 扫码'
  })

  async function open() {
    isOpen.value = true
    loading.value = true
    status.value = 0
    qrLogin.value = null

    const { data, error } = await createMusicQrLogin()
    loading.value = false

    if (error) {
      Logger.error('Failed to create QR login', error)
      return
    }

    qrLogin.value = data
    startPolling()
  }

  function close() {
    isOpen.value = false
    stopPolling()
  }

  function startPolling() {
    stopPolling()
    timer = setInterval(async () => {
      if (!qrLogin.value?.key) return

      const { data, error } = await checkMusicQrLogin(qrLogin.value.key)

      if (error) {
        Logger.error('Failed to check QR login status', error)
        return
      }

      status.value = data?.status ?? 0

      if (data?.logged_in && data.auth) {
        authStatus.value = data.auth
        stopPolling()
        close()
      }

      if (status.value === 0 && qrLogin.value) {
        stopPolling()
      }
    }, 2000)
  }

  function stopPolling() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  onUnmounted(() => {
    stopPolling()
  })

  return {
    isOpen,
    loading,
    qrLogin,
    status,
    statusText,
    authStatus,
    open,
    close,
  }
}
