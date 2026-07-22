export interface PostSeekVideoHealthSample {
  hasActiveVideoTrack: boolean
  paused: boolean
  ended: boolean
  targetTime: number
  currentTime: number
  frameCallbackSupported: boolean
  lastPresentedFrameMediaTime: number | null
  baselineDecodedFrames: number | null
  decodedFrames: number | null
}

const MIN_PLAYHEAD_ADVANCE_SECONDS = 0.5
const TARGET_FRAME_TOLERANCE_SECONDS = 0.35
const MAX_FRAME_CLOCK_DRIFT_SECONDS = 1

/**
 * A seek is visually healthy only after a video frame from the destination is
 * presented. requestVideoFrameCallback is authoritative when available: a
 * decoded-frame counter can otherwise advance once for the stale pre-seek frame.
 */
export function hasPresentedVideoFrameAfterSeek(sample: PostSeekVideoHealthSample): boolean {
  if (
    sample.lastPresentedFrameMediaTime !== null
    && Number.isFinite(sample.lastPresentedFrameMediaTime)
  ) {
    return (
      sample.lastPresentedFrameMediaTime >= sample.targetTime - TARGET_FRAME_TOLERANCE_SECONDS
      && Math.abs(sample.lastPresentedFrameMediaTime - sample.currentTime) <= MAX_FRAME_CLOCK_DRIFT_SECONDS
    )
  }

  if (sample.frameCallbackSupported) return false

  return (
    sample.baselineDecodedFrames !== null
    && sample.decodedFrames !== null
    && Number.isFinite(sample.baselineDecodedFrames)
    && Number.isFinite(sample.decodedFrames)
    && sample.decodedFrames > sample.baselineDecodedFrames
  )
}

/**
 * Detect the otherwise invisible failure where the audio clock advances after
 * a seek but Chromium never presents a video frame at the destination.
 */
export function shouldRecoverVideoAfterSeek(sample: PostSeekVideoHealthSample): boolean {
  if (!sample.hasActiveVideoTrack || sample.paused || sample.ended) return false
  if (!Number.isFinite(sample.currentTime) || !Number.isFinite(sample.targetTime)) return false
  if (sample.currentTime < sample.targetTime + MIN_PLAYHEAD_ADVANCE_SECONDS) return false
  return !hasPresentedVideoFrameAfterSeek(sample)
}
