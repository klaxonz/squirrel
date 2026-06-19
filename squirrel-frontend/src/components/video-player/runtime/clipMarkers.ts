export const CLIP_MARKER_ACTIVE_TOLERANCE = 0.75

type VideoId = string | number

/**
 * Source object that may carry a video id under one of several known keys.
 * Typed as unknown because call sites pass heterogeneous shapes (e.g. the
 * player's MediaSource, which carries the id under `metadata`); the body
 * probes defensively and returns null when none of the keys match.
 */
type VideoIdSource = unknown

/** Marker shape with either snake_case (persisted) or camelCase (normalized) keys. */
type ClipMarkerLike = {
  start_time?: number
  end_time?: number
  startTime?: number
  endTime?: number
} | null

type MarkerTimeInput = number | string | null | undefined

const isFiniteNumber = (value: MarkerTimeInput): value is number => Number.isFinite(Number(value))

const normalizeVideoId = (value: unknown): VideoId | null => {
  if (value === null || value === undefined) return null

  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed ? trimmed : null
  }

  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null
  }

  return null
}

export const resolveClipMarkerVideoId = (videoId: VideoId | null | undefined, source: VideoIdSource = null): VideoId | null => {
  const explicitVideoId = normalizeVideoId(videoId)
  if (explicitVideoId !== null) return explicitVideoId

  if (!source || typeof source !== 'object') return null

  const probe = source as { id?: unknown; videoId?: unknown; video_id?: unknown }
  return normalizeVideoId(probe.id ?? probe.videoId ?? probe.video_id ?? null)
}

const normalizeClipMarkerTime = (time: MarkerTimeInput, duration: MarkerTimeInput): number => {
  const safeDuration = isFiniteNumber(duration) && Number(duration) > 0 ? Number(duration) : null
  const safeTime = Math.max(Number(time) || 0, 0)
  return safeDuration === null ? safeTime : Math.min(safeTime, safeDuration)
}

type ClipMarkerBoundsInput = {
  startTime?: MarkerTimeInput
  endTime?: MarkerTimeInput
  duration?: MarkerTimeInput
}

export const normalizeClipMarkerBounds = ({
  startTime = 0,
  endTime = 0,
  duration = 0,
}: ClipMarkerBoundsInput = {}): { startTime: number; endTime: number } => {
  const boundedStart = normalizeClipMarkerTime(startTime, duration)
  const boundedEnd = normalizeClipMarkerTime(endTime, duration)
  const rangeStart = Math.min(boundedStart, boundedEnd)
  const rangeEnd = Math.max(boundedStart, boundedEnd)

  return {
    startTime: rangeStart,
    endTime: rangeEnd,
  }
}

type PointMarkerDraftInput = {
  currentTime?: MarkerTimeInput
  duration?: MarkerTimeInput
}

export const createPointMarkerDraft = ({
  currentTime = 0,
  duration = 0,
}: PointMarkerDraftInput = {}): { startTime: number; endTime: number } => {
  const boundedTime = normalizeClipMarkerTime(currentTime, duration)
  return {
    startTime: boundedTime,
    endTime: boundedTime,
  }
}

type SegmentMarkerDraftInput = {
  startTime?: MarkerTimeInput
  currentTime?: MarkerTimeInput
  duration?: MarkerTimeInput
}

export const createSegmentMarkerDraft = ({
  startTime = 0,
  currentTime = 0,
  duration = 0,
}: SegmentMarkerDraftInput = {}): { startTime: number; endTime: number } => normalizeClipMarkerBounds({
  startTime,
  endTime: currentTime,
  duration,
})

export const isPointMarker = (marker: ClipMarkerLike): boolean => {
  if (!marker || typeof marker !== 'object') return false
  const startTime = Number(marker.start_time ?? marker.startTime ?? 0)
  const endTime = Number(marker.end_time ?? marker.endTime ?? startTime)
  return Math.abs(endTime - startTime) < 0.001
}

export const isClipMarkerActive = (
  marker: ClipMarkerLike,
  currentTime: MarkerTimeInput,
  tolerance: number = CLIP_MARKER_ACTIVE_TOLERANCE,
): boolean => {
  if (!marker || typeof marker !== 'object') return false

  const time = Number(currentTime)
  if (!Number.isFinite(time)) return false

  const startTime = Number(marker.start_time ?? marker.startTime ?? 0)
  const endTime = Number(marker.end_time ?? marker.endTime ?? startTime)
  if (!Number.isFinite(startTime) || !Number.isFinite(endTime)) return false

  if (isPointMarker({ startTime, endTime })) {
    return Math.abs(time - startTime) <= tolerance
  }

  return time >= startTime && time <= endTime
}
