import { onUnmounted, ref, type Ref } from 'vue'

/**
 * Polling-based auto-refresh state machine.
 *
 * Owns the auto-refresh flag + the interval timer, with start/stop/toggle and
 * automatic cleanup on unmount. The refresh callback is injected so this is
 * agnostic to what's being polled (logs, status, queue depth, …). Stopping
 * always clears the timer first, so toggle + unmount can't leak a stray
 * interval.
 *
 * Extracted from LogViewer.vue so the interval-lifecycle invariant (always
 * cleared on stop/unmount, never double-started) lives in one reusable place.
 */
export interface UseLogAutoRefreshOptions {
  /** Invoked on each tick. */
  refresh: () => void | Promise<void>
  /** Poll interval in ms. */
  intervalMs?: number
  /** Whether to start polling immediately on creation. Default true. */
  startImmediately?: boolean
}

export interface UseLogAutoRefreshReturn {
  autoRefresh: Ref<boolean>
  toggleAutoRefresh: () => void
  startAutoRefresh: () => void
  stopAutoRefresh: () => void
}

export function useLogAutoRefresh(options: UseLogAutoRefreshOptions): UseLogAutoRefreshReturn {
  const { refresh, intervalMs = 5000, startImmediately = true } = options

  const autoRefresh = ref(startImmediately)
  let refreshTimer: ReturnType<typeof setInterval> | null = null

  const stopAutoRefresh = () => {
    if (refreshTimer !== null) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }

  const startAutoRefresh = () => {
    // Clear first so a double-start can't stack two intervals.
    stopAutoRefresh()
    refreshTimer = setInterval(() => {
      void refresh()
    }, intervalMs)
  }

  const toggleAutoRefresh = () => {
    autoRefresh.value = !autoRefresh.value
    if (autoRefresh.value) startAutoRefresh()
    else stopAutoRefresh()
  }

  onUnmounted(() => {
    stopAutoRefresh()
  })

  if (startImmediately) startAutoRefresh()

  return {
    autoRefresh,
    toggleAutoRefresh,
    startAutoRefresh,
    stopAutoRefresh,
  }
}
