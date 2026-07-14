import { ref } from 'vue'

export type ToastVariant = 'success' | 'error' | 'info'

export interface ToastItem {
  id: number
  variant: ToastVariant
  message: string
}

export interface ShowOptions {
  variant?: ToastVariant
  /** Override the default auto-hide delay (ms). */
  duration?: number
}

/**
 * Global toast singleton. The whole app shares one toast stack — call
 * `useToast()` anywhere and call `.success() / .error() / .info()` to push.
 * `<ToastProvider>` (mounted once in AppLayout) reads `toasts` and renders the
 * stack; it owns the per-item clear timers.
 *
 * Replaces the old per-component `useToast` (which returned a component-scoped
 * `toast` ref that each view had to render itself, leading to three divergent
 * visual variants across four files).
 */

let nextId = 1

const DEFAULT_DURATION = 3000

/** Single shared reactive queue — the source of truth for ToastProvider. */
export const toasts = ref<ToastItem[]>([])

const timers = new Map<number, ReturnType<typeof setTimeout>>()

function clearTimer(id: number) {
  const timer = timers.get(id)
  if (timer) {
    clearTimeout(timer)
    timers.delete(id)
  }
}

function dismiss(id: number) {
  clearTimer(id)
  toasts.value = toasts.value.filter((t) => t.id !== id)
}

function show(message: string, options: ShowOptions = {}) {
  const variant = options.variant ?? 'info'
  const duration = options.duration ?? DEFAULT_DURATION
  const id = nextId++
  toasts.value = [...toasts.value, { id, variant, message }]
  if (duration > 0) {
    const timer = setTimeout(() => dismiss(id), duration)
    timers.set(id, timer)
  }
  return id
}

export interface UseToastReturn {
  toasts: typeof toasts
  show: (message: string, options?: ShowOptions) => number
  success: (message: string, options?: Omit<ShowOptions, 'variant'>) => number
  error: (message: string, options?: Omit<ShowOptions, 'variant'>) => number
  info: (message: string, options?: Omit<ShowOptions, 'variant'>) => number
  dismiss: (id: number) => void
}

export function useToast(): UseToastReturn {
  return {
    toasts,
    show,
    success: (message, options) => show(message, { ...options, variant: 'success' }),
    error: (message, options) => show(message, { ...options, variant: 'error' }),
    info: (message, options) => show(message, { ...options, variant: 'info' }),
    dismiss,
  }
}
