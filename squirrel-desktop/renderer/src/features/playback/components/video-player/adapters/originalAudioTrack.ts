export interface AudioTrackCandidate {
  active?: boolean
  language?: string
  label?: string | null
  primary?: boolean
  roles?: string[]
  codecs?: string | null
  mimeType?: string | null
}

const ORIGINAL_LABEL_PATTERN = /\boriginal\b|原声|原聲|原始|オリジナル|원본/i
const NON_ORIGINAL_ROLES = new Set(['alternate', 'dub', 'description', 'secondary'])
const ENHANCED_AUDIO_ROLES = new Set(['enhanced-audio-intelligibility'])

const normalizedRoles = (track: AudioTrackCandidate): string[] => (
  Array.isArray(track.roles)
    ? track.roles.map((role) => String(role || '').trim().toLowerCase()).filter(Boolean)
    : []
)

const isOriginalTrack = (track: AudioTrackCandidate): boolean => {
  const roles = normalizedRoles(track)
  if (roles.some((role) => NON_ORIGINAL_ROLES.has(role))) return false
  return Boolean(
    track.primary
    || roles.includes('main')
    || ORIGINAL_LABEL_PATTERN.test(String(track.label || ''))
  )
}

const isEnhancedTrack = (track: AudioTrackCandidate): boolean => {
  const roles = normalizedRoles(track)
  return roles.some((role) => ENHANCED_AUDIO_ROLES.has(role))
    || /stable volume|voice boost|\bdrc\b/i.test(String(track.label || ''))
}

/**
 * Pick the creator's original mix, not a localized dub or accessibility mix.
 * youtubei.js marks original audio with role=main and dubbed audio with
 * alternate+dub; DRC/Stable Volume adds enhanced-audio-intelligibility.
 */
export const chooseOriginalAudioTrack = <T extends AudioTrackCandidate>(tracks: readonly T[]): T | null => {
  if (tracks.length <= 1) return null

  const originals = tracks.filter(isOriginalTrack)
  if (originals.length === 0) return null

  const active = tracks.find((track) => track.active)
  const score = (track: T): number => {
    const roles = normalizedRoles(track)
    let value = 0
    if (!isEnhancedTrack(track)) value += 10_000
    if (roles.includes('main')) value += 1_000
    if (track.primary) value += 500
    if (ORIGINAL_LABEL_PATTERN.test(String(track.label || ''))) value += 250
    if (active?.codecs && track.codecs === active.codecs) value += 100
    if (active?.mimeType && track.mimeType === active.mimeType) value += 50
    if (track.active) value += 10
    return value
  }

  return [...originals].sort((left, right) => score(right) - score(left))[0] || null
}
