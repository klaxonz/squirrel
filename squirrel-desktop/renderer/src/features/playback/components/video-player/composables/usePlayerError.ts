import { ref, type Ref } from 'vue'
import { classifyPlaybackError } from '../core/playback-error-classifier'

/**
 * Player error-overlay state + i18n message resolution.
 *
 * Owns the single `errorState` ref the ErrorOverlay renders, plus the code→
 * message translation that maps engine/adapter English error codes to localized
 * UI strings. `reportError` is the entry the engine's onError callback calls;
 * `clear` is the recovery/source-swap escape hatch; `handleRetry` hides the
 * overlay and notifies the parent to retry.
 *
 * Why a composable: the original VideoPlayer scattered errorState.value.show =
 * false across four sites (onError, source-change, recovery-on-play, retry).
 * Centralising it here means the "when does the overlay go away" policy lives
 * in one place, and the translation table can't drift from the state it feeds.
 */
export interface PlayerErrorState {
  show: boolean
  title: string
  message: string
  code: string
  canRetry: boolean
  /** Auth-gated failure (YouTube 登录/授权)：overlay 提供「去登录」动作。 */
  requiresAuth: boolean
}

export interface UsePlayerErrorOptions {
  t: (key: string, params?: Record<string, string | number>) => string
  onRetry?: () => void
  onAuthRequired?: () => void
}

export interface UsePlayerErrorReturn {
  errorState: Ref<PlayerErrorState>
  /** Translate an engine error code+message into a localized UI message. */
  resolveErrorMessage: (code: string, fallback: string) => string
  /** Surface an engine-reported error on the overlay. */
  reportError: (code: string, rawMessage: string) => void
  /** Hide the overlay (source swap, recovery, etc.). */
  clear: () => void
  /** Clear the active playback error when a new source operation begins. */
  clearEngineError: () => void
  /** Hide the overlay and bubble a retry request to the parent. */
  handleRetry: () => void
  /** Hide the overlay and bubble a login request to the parent. */
  handleAuthRequired: () => void
}

/** Provider resolve errors that mean "your login state is the problem". */
const AUTH_REQUIRED_CODES: Record<string, true> = {
  YOUTUBE_LOGIN_REQUIRED: true,
  YOUTUBE_AUTH_EXPIRED: true,
  BILIBILI_LOGIN_REQUIRED: true,
}

const isAuthRequiredError = (code: string, message: string): boolean => {
  if (AUTH_REQUIRED_CODES[code]) return true
  return /登录|授权|login|auth/i.test(message)
}

export function usePlayerError(options: UsePlayerErrorOptions): UsePlayerErrorReturn {
  const { t, onRetry, onAuthRequired } = options

  const errorState = ref<PlayerErrorState>({
    show: false,
    title: '',
    message: '',
    code: '',
    canRetry: true,
    requiresAuth: false,
  })

  // 按 code 把引擎/适配器产生的英文错误信息映射为中文。这些 message 来自
  // core/error-recovery.ts、createPlayerEngine.ts、adapters/{Hls,Dash,ShakaDash}Adapter.ts，
  // 在源头改会侵入多个适配器并丢失原始信息，故在 UI 层统一翻译。
  const resolveErrorMessage = (code: string, fallback: string): string => {
    // 提供方已给出可操作的登录提示（如「请在设置中完成 YouTube TV 授权」），
    // 不能被 authorization 分类的通用文案吞掉。
    if (isAuthRequiredError(code, fallback)) return fallback
    const kind = classifyPlaybackError({ code, message: fallback })
    if (kind === 'network') return t('errorNetwork')
    if (kind === 'authorization' || kind === 'source') return t('errorStreamUnavailable')
    if (kind === 'capability') return t('errorNotSupported')
    if (kind === 'decode') return t('errorDecode')
    if (kind === 'buffer') return t('errorPlaybackStalled')
    if (kind === 'media') return t('errorMedia')
    return fallback || t('errorUnknown')
  }

  const reportError = (code: string, rawMessage: string) => {
    errorState.value = {
      show: true,
      title: t('errorTitle'),
      message: resolveErrorMessage(code, rawMessage),
      code,
      canRetry: true,
      requiresAuth: isAuthRequiredError(code, rawMessage),
    }
  }

  const clear = () => {
    errorState.value.show = false
  }

  const clearEngineError = clear

  const handleRetry = () => {
    clear()
    onRetry?.()
  }

  const handleAuthRequired = () => {
    clear()
    onAuthRequired?.()
  }

  return {
    errorState,
    resolveErrorMessage,
    reportError,
    clear,
    clearEngineError,
    handleRetry,
    handleAuthRequired,
  }
}
