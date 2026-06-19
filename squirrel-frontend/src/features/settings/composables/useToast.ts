import { ref, type Ref } from 'vue'

export interface ToastState {
  visible: boolean
  message: string
  error: boolean
}

export interface UseToastOptions {
  /** How long the toast stays visible before auto-hiding. Default 3000ms. */
  duration?: number
}

export interface UseToastReturn {
  /** Reactive toast state; templates bind to `toast.value.{visible,message,error}`. */
  toast: Ref<ToastState>
  /** Show a toast. Replaces any in-flight toast and resets the hide timer. */
  show: (message: string, isError?: boolean) => void
  /** Hide immediately (e.g. on unmount). */
  hide: () => void
}

/**
 * A transient toast message. Owns the clear/reset timer dance that every view
 * was hand-rolling; the visual markup stays in each view (three visual variants
 * exist, so a shared component would need a variant prop and risk visual
 * regression). The shared part is the logic: `show()` clears any pending hide,
 * sets the state, and arms a fresh timer.
 *
 * Lifecycle is left to the caller (most views want the toast to outlive
 * specific handlers but not the unmount; `hide()` is exposed for cleanup if
 * needed — the timers are short-lived enough that leaking one across unmount is
 * harmless, matching the prior hand-rolled behavior).
 */
export function useToast(options: UseToastOptions = {}): UseToastReturn {
  const duration = options.duration ?? 3000
  const toast = ref<ToastState>({ visible: false, message: '', error: false })
  let timer: ReturnType<typeof setTimeout> | null = null

  const hide = () => {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    toast.value.visible = false
  }

  const show = (message: string, isError = false) => {
    if (timer) clearTimeout(timer)
    toast.value = { visible: true, message, error: isError }
    timer = setTimeout(() => {
      toast.value.visible = false
      timer = null
    }, duration)
  }

  return { toast, show, hide }
}
