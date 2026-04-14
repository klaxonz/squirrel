export const CLIP_MARKER_ACTIVE_TOLERANCE = 0.75

const isFiniteNumber = (value) => Number.isFinite(Number(value))

const normalizeVideoId = (value) => {
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

export const resolveClipMarkerVideoId = (videoId, source = null) => {
  const explicitVideoId = normalizeVideoId(videoId)
  if (explicitVideoId !== null) return explicitVideoId

  if (!source || typeof source !== 'object') return null

  return normalizeVideoId(source.id ?? source.videoId ?? source.video_id ?? null)
}

const normalizeClipMarkerTime = (time, duration = 0) => {
  const safeDuration = isFiniteNumber(duration) && Number(duration) > 0 ? Number(duration) : null
  const safeTime = Math.max(Number(time) || 0, 0)
  return safeDuration === null ? safeTime : Math.min(safeTime, safeDuration)
}

export const normalizeClipMarkerBounds = ({
  startTime = 0,
  endTime = 0,
  duration = 0,
} = {}) => {
  const boundedStart = normalizeClipMarkerTime(startTime, duration)
  const boundedEnd = normalizeClipMarkerTime(endTime, duration)
  const rangeStart = Math.min(boundedStart, boundedEnd)
  const rangeEnd = Math.max(boundedStart, boundedEnd)

  return {
    startTime: rangeStart,
    endTime: rangeEnd,
  }
}

export const createPointMarkerDraft = ({
  currentTime = 0,
  duration = 0,
} = {}) => {
  const boundedTime = normalizeClipMarkerTime(currentTime, duration)
  return {
    startTime: boundedTime,
    endTime: boundedTime,
  }
}

export const createSegmentMarkerDraft = ({
  startTime = 0,
  currentTime = 0,
  duration = 0,
} = {}) => normalizeClipMarkerBounds({
  startTime,
  endTime: currentTime,
  duration,
})

export const isPointMarker = (marker) => {
  if (!marker || typeof marker !== 'object') return false
  const startTime = Number(marker.start_time ?? marker.startTime ?? 0)
  const endTime = Number(marker.end_time ?? marker.endTime ?? startTime)
  return Math.abs(endTime - startTime) < 0.001
}

export const isClipMarkerActive = (
  marker,
  currentTime,
  tolerance = CLIP_MARKER_ACTIVE_TOLERANCE
) => {
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
