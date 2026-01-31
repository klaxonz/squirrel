import { ref, watch } from 'vue'

type EmitFn = (event: 'error', payload: unknown) => void
type ExternalErrorInfo = {
  code?: string
  title?: string
  message?: string
  canRetry?: boolean
}
type PropsLike = { externalError?: ExternalErrorInfo | null }
type PlayerStateLike = {
  media?: {
    playing: boolean
    loading: boolean
    loadingStage: string
    canPlay: { video: boolean; audio: boolean }
  }
}

type ErrorState = {
  show: boolean
  title: string
  message: string
  code: string
  detail: string
  retryable: boolean
}

type UiError = Omit<ErrorState, 'show'>

const toRecord = (value: unknown): Record<string, any> => {
  if (value && typeof value === 'object') return value as Record<string, any>
  return {}
}

export default function useMediaError(emit: EmitFn, props: PropsLike) {
  const AUTO_HIDE_DELAY = 6000

  const errorState = ref<ErrorState>({
    show: false,
    title: '',
    message: '',
    code: '',
    detail: '',
    retryable: true,
  })

  let hideTimer: number | null = null

  const scheduleAutoHide = () => {
    if (hideTimer) {
      clearTimeout(hideTimer)
      hideTimer = null
    }
    hideTimer = window.setTimeout(() => {
      errorState.value.show = false
    }, AUTO_HIDE_DELAY)
  }

  const mapErrorToUi = (err: unknown): UiError => {
    const e = toRecord(err)
    const type = String(e.type || e.name || '').toLowerCase()

    if (type === 'network') {
      return {
        title: '网络连接错误',
        message: '无法连接到服务器，请检查网络或稍后重试。',
        code: String(e.code || 'NETWORK'),
        detail: String(e.message || ''),
        retryable: true,
      }
    }
    if (type === 'media') {
      return {
        title: '媒体播放错误',
        message: '视频无法播放，可能是格式不支持或文件损坏。',
        code: String(e.code || 'MEDIA'),
        detail: String(e.message || ''),
        retryable: true,
      }
    }
    if (type === 'fatal') {
      return {
        title: '播放失败',
        message: '发生致命错误，暂时无法播放。',
        code: String(e.code || 'FATAL'),
        detail: String(e.message || ''),
        retryable: true,
      }
    }

    const mediaErr = toRecord(e?.target?.error || e.error)
    switch (mediaErr.code) {
      case 1:
        return {
          title: '已中止',
          message: '播放被中止。',
          code: 'MEDIA_ERR_ABORTED',
          detail: '',
          retryable: false,
        }
      case 2:
        return {
          title: '网络错误',
          message: '网络连接异常，请检查网络。',
          code: 'MEDIA_ERR_NETWORK',
          detail: '',
          retryable: true,
        }
      case 3:
        return {
          title: '解码错误',
          message: '媒体解码失败。',
          code: 'MEDIA_ERR_DECODE',
          detail: '',
          retryable: true,
        }
      case 4:
        return {
          title: '不支持的资源',
          message: '当前媒体资源不受支持。',
          code: 'MEDIA_ERR_SRC_NOT_SUPPORTED',
          detail: '',
          retryable: false,
        }
      default:
        return {
          title: '播放出现问题',
          message: '请稍后重试。',
          code: String(e.code || 'UNKNOWN'),
          detail: String(e.message || ''),
          retryable: true,
        }
    }
  }

  const showInlineError = (err: unknown) => {
    const ui = mapErrorToUi(err)
    errorState.value = { show: true, ...ui }
    scheduleAutoHide()
    emit('error', err)
  }

  const clearError = () => {
    errorState.value.show = false
    if (hideTimer) {
      clearTimeout(hideTimer)
      hideTimer = null
    }
  }

  const EXTERNAL_ERROR_CODES: Record<string, { title: string; message: string }> = {
    EXTRACT_FAILED: { title: '播放失败', message: '播放链接提取失败，请重试' },
    NO_STREAM_URL: { title: '无法播放', message: '没有获取到播放链接' },
    URL_FETCH_TIMEOUT: { title: '获取超时', message: '获取播放链接超时' },
  }

  const watchExternalError = (playerState?: PlayerStateLike) => {
    watch(
      () => props?.externalError,
      (info) => {
        if (!info) return
        try {
          const mappedCode =
            info.code && EXTERNAL_ERROR_CODES[info.code] ? EXTERNAL_ERROR_CODES[info.code] : null
          const mapped: UiError = {
            title: mappedCode?.title || info.title || '播放失败',
            message: mappedCode?.message || info.message || '',
            code: info.code || '',
            detail: '',
            retryable: info.canRetry !== false,
          }
          errorState.value = { show: true, ...mapped }
          scheduleAutoHide()

          if (playerState?.media) {
            playerState.media.playing = false
            playerState.media.loading = false
            playerState.media.loadingStage = 'idle'
            playerState.media.canPlay.video = false
            playerState.media.canPlay.audio = false
          }
        } catch (_) {}
      }
    )
  }

  const cleanup = () => {
    if (hideTimer) {
      clearTimeout(hideTimer)
      hideTimer = null
    }
  }

  return {
    errorState,
    showInlineError,
    clearError,
    watchExternalError,
    cleanup,
  }
}
