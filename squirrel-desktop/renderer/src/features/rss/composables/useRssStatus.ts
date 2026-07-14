import { ref } from 'vue'

/**
 * Cross-cutting RSS status-message layer.
 *
 * Owns the transient status banner state that every RSS composable reports
 * through (accounts / feeds / entries / reader / sync all take an `onStatus`
 * callback). Two responsibilities:
 *   1. surface the latest message + its error flag to the view header,
 *   2. auto-clear the message after a timeout — but only for terminal messages;
 *      progress messages (those containing "同步中") stay visible until the next
 *      status update replaces them.
 *
 * Extracted from RssSources.vue so the timer lifecycle + the "don't auto-dismiss
 * progress messages" policy live in one place instead of being inlined in the
 * view next to six composable wiring blocks.
 */
export interface UseRssStatusReturn {
  statusMessage: ReturnType<typeof ref<string>>
  statusError: ReturnType<typeof ref<boolean>>
  /** Report a status update. Progress messages (containing "同步中") are sticky. */
  onStatus: (message: string, isError?: boolean) => void
  /** Clear the timer + message. Call on unmount to avoid a pending clear firing post-teardown. */
  dispose: () => void
}

const DISMISS_DELAY_MS = 6000
// Messages containing this substring denote in-progress syncs and must remain
// visible until the operation completes and reports a terminal status.
const PROGRESS_MARKER = '同步中'

export function useRssStatus(): UseRssStatusReturn {
  const statusMessage = ref('')
  const statusError = ref(false)

  let statusTimeout: ReturnType<typeof setTimeout> | null = null

  const clearTimer = () => {
    if (statusTimeout === null) return
    clearTimeout(statusTimeout)
    statusTimeout = null
  }

  const onStatus = (message: string, isError = false) => {
    statusMessage.value = message
    statusError.value = isError
    clearTimer()
    if (message && !message.includes(PROGRESS_MARKER)) {
      statusTimeout = setTimeout(() => {
        statusMessage.value = ''
        statusError.value = false
      }, DISMISS_DELAY_MS)
    }
  }

  const dispose = () => {
    clearTimer()
  }

  return {
    statusMessage,
    statusError,
    onStatus,
    dispose,
  }
}
