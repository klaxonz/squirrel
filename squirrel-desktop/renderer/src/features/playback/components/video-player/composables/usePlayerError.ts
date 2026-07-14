import { ref, type Ref } from 'vue'

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
}

export interface UsePlayerErrorOptions {
  t: (key: string, params?: Record<string, string | number>) => string
  onRetry?: () => void
}

export interface UsePlayerErrorReturn {
  errorState: Ref<PlayerErrorState>
  /** Translate an engine error code+message into a localized UI message. */
  resolveErrorMessage: (code: string, fallback: string) => string
  /** Surface an engine-reported error on the overlay. */
  reportError: (code: string, rawMessage: string) => void
  /** Hide the overlay (source swap, recovery, etc.). */
  clear: () => void
  /** Hide the overlay and bubble a retry request to the parent. */
  handleRetry: () => void
}

export function usePlayerError(options: UsePlayerErrorOptions): UsePlayerErrorReturn {
  const { t, onRetry } = options

  const errorState = ref<PlayerErrorState>({
    show: false,
    title: '',
    message: '',
    code: '',
    canRetry: true,
  })

  // 按 code 把引擎/适配器产生的英文错误信息映射为中文。这些 message 来自
  // core/error-recovery.ts、createPlayerEngine.ts、adapters/{Hls,Dash,ShakaDash}Adapter.ts，
  // 在源头改会侵入多个适配器并丢失原始信息，故在 UI 层统一翻译。
  const resolveErrorMessage = (code: string, fallback: string): string => {
    const upper = String(code || '').toUpperCase()
    if (upper.includes('NETWORK') || upper.includes('TIMEOUT')) return t('errorNetwork')
    if (upper.includes('NOT_SUPPORTED') || upper.includes('CAPABILITY')) return t('errorNotSupported')
    if (upper.includes('DECODE')) return t('errorDecode')
    if (upper.includes('MEDIA') || upper.includes('HLS_') || upper.includes('DASH_')) return t('errorMedia')
    if (upper.includes('STALL')) return t('buffering')
    return fallback || t('errorUnknown')
  }

  const reportError = (code: string, rawMessage: string) => {
    errorState.value = {
      show: true,
      title: t('errorTitle'),
      message: resolveErrorMessage(code, rawMessage),
      code,
      canRetry: true,
    }
  }

  const clear = () => {
    errorState.value.show = false
  }

  const handleRetry = () => {
    errorState.value.show = false
    onRetry?.()
  }

  return {
    errorState,
    resolveErrorMessage,
    reportError,
    clear,
    handleRetry,
  }
}
