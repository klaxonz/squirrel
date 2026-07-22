import type { PlayerError } from './types'

export type PlaybackErrorKind =
  | 'network'
  | 'authorization'
  | 'source'
  | 'capability'
  | 'decode'
  | 'buffer'
  | 'media'
  | 'unknown'

const containsAny = (value: string, candidates: readonly string[]): boolean => (
  candidates.some(candidate => value.includes(candidate))
)

/**
 * Stable error taxonomy shared by recovery policy and the UI.
 *
 * Adapters retain their provider/library-specific codes for diagnostics, while
 * lifecycle decisions depend on this small semantic set. Ordering matters:
 * Chromium's MEDIA_ERR_SRC_NOT_SUPPORTED commonly wraps an expired/403 media
 * response, so it is a retryable source failure rather than a codec capability
 * failure.
 */
export function classifyPlaybackError(error: Pick<PlayerError, 'code' | 'message'> | string): PlaybackErrorKind {
  const signature = typeof error === 'string'
    ? error
    : `${error.code || ''} ${error.message || ''}`
  const upper = signature.toUpperCase()

  if (containsAny(upper, ['STALL', 'BUFFER'])) return 'buffer'
  if (containsAny(upper, ['SRC_NOT_SUPPORTED', 'MEDIA_NOT_SUPPORTED', 'EXPIRED_URL'])) return 'source'
  if (containsAny(upper, ['UNAUTHORIZED', 'FORBIDDEN', 'AUTH', 'HTTP_401', 'HTTP_403', ' 401', ' 403'])) {
    return 'authorization'
  }
  if (containsAny(upper, ['NETWORK', 'TIMEOUT', 'CONNECTION', 'OFFLINE'])) return 'network'
  if (containsAny(upper, ['CAPABILITY', 'NOT_SUPPORTED'])) return 'capability'
  if (containsAny(upper, ['DECODE', 'DECODER', 'VIDEO_FROZEN'])) return 'decode'
  if (containsAny(upper, ['MEDIA', 'HLS_', 'DASH_', 'SHAKA_'])) return 'media'
  return 'unknown'
}
