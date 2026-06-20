import { Logger } from '@/shared/lib/logger'

/**
 * Copy text to the system clipboard, resolving to a success boolean.
 *
 * The `navigator.clipboard.writeText(x)` + try/catch + success/failure-feedback
 * pattern was copy-pasted across 6 sites (video share, rss entry/feed copy, log
 * clipboard, youtube oauth code). This helper centralises the clipboard write +
 * error logging and returns whether it succeeded, so each caller owns only its
 * own user feedback (toast / onStatus / copied flag) without re-implementing the
 * write + catch.
 *
 * @returns true on success, false if the clipboard API is unavailable or rejected
 */
export const copyToClipboard = async (text: string): Promise<boolean> => {
  if (typeof navigator === 'undefined' || !navigator.clipboard?.writeText) {
    return false
  }
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (err) {
    Logger.warn('[clipboard] copy failed', err)
    return false
  }
}
