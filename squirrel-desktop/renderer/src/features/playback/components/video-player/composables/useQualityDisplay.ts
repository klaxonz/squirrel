import { computed } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import { getCodecFamily } from '../core/codec'
import type { QualityLevel } from '../core'

export interface UseQualityDisplayOptions {
  qualities: Ref<QualityLevel[]>
  selectedCodecFamily: Ref<string>
  currentCodecFamily: Ref<string | null>
  currentQualityId: Ref<string | number | null>
  currentQualityLabel: Ref<string | null>
  // ponytail: loose t signature; the caller casts its i18n t to this shape
  // (matches the useSleepTimer convention) so this composable stays decoupled
  // from the LocaleMessages key union.
  t: (key: string, params?: Record<string, string | number>) => string
}

export interface UseQualityDisplayReturn {
  visibleCodecFamily: ComputedRef<string | null>
  resolvedCurrentQuality: ComputedRef<QualityLevel | null>
  displayedQualities: ComputedRef<QualityLevel[]>
  currentQualityText: ComputedRef<string>
  qualityTagLabel: ComputedRef<string>
  qualityMenuLabel: ComputedRef<string>
  isQualityActive: (quality: { id: string | number }) => boolean
}

// Quality-menu helpers. Empty / whitespace labels must NOT count as displayable
// — otherwise the chip falls through to t('quality') ("画质") even when the
// ladder is present, and empty rows appear in the popup.
const isInternalQualityLabel = (label: string | null | undefined) => /^level[_\s-]?\d+$/i.test(String(label || '').trim().toLowerCase())
const isAutoQualityLabel = (label: string | null | undefined) => {
  const normalized = String(label || '').trim().toLowerCase()
  // '自动' is the zh-CN auto token; '??' is legacy mojibake for the same.
  return ['auto', '自动', '??'].includes(normalized)
}
const isDisplayableQualityLabel = (label: string | null | undefined) => {
  const text = String(label || '').trim()
  if (!text) return false
  return !isInternalQualityLabel(text) && !isAutoQualityLabel(text)
}

const formatHeightLabel = (height?: number | null) => {
  const value = Number(height || 0)
  return Number.isFinite(value) && value > 0 ? `${value}p` : ''
}

/** Prefer a human rung label; never return blank for a known height/id. */
const resolveQualityLabel = (quality: { label?: string | null; height?: number | null; id?: string | number | null }) => {
  if (isDisplayableQualityLabel(quality.label)) return String(quality.label).trim()
  const fromHeight = formatHeightLabel(quality.height)
  if (fromHeight) return fromHeight
  const idText = quality.id === undefined || quality.id === null ? '' : String(quality.id).trim()
  return idText
}

export function useQualityDisplay(options: UseQualityDisplayOptions): UseQualityDisplayReturn {
  const {
    qualities,
    selectedCodecFamily,
    currentCodecFamily,
    currentQualityId,
    currentQualityLabel,
    t,
  } = options

  const visibleCodecFamily = computed(() => (
    selectedCodecFamily.value !== 'auto'
      ? selectedCodecFamily.value
      : currentCodecFamily.value
  ))

  const resolvedCurrentQuality = computed(() => {
    if (currentQualityId.value === null || currentQualityId.value === undefined) return null
    return qualities.value.find((quality) => String(quality.id) === String(currentQualityId.value)) || null
  })

  const getQualityBucketKey = (quality: { height?: number | null; label?: string | null; id?: string | number | null }) => {
    const height = Number(quality.height || 0)
    if (Number.isFinite(height) && height > 0) {
      return `height:${height}`
    }
    const label = String(quality.label || quality.id || '').trim().toLowerCase()
    return `label:${label}`
  }

  const scoreQualityForDisplay = (quality: { id?: string | number | null; codec?: string | null; height?: number | null; bitrate?: number | null }) => {
    let score = 0
    if (resolvedCurrentQuality.value && String(quality.id) === String(resolvedCurrentQuality.value.id)) {
      score += 1_000_000_000_000
    }

    const preferredCodecFamily = visibleCodecFamily.value
      || getCodecFamily(resolvedCurrentQuality.value?.codec)
      || currentCodecFamily.value
    if (preferredCodecFamily && getCodecFamily(quality.codec) === preferredCodecFamily) {
      score += 1_000_000_000
    }

    score += Math.max(0, Number(quality.height || 0)) * 1_000_000
    score += Math.max(0, Number(quality.bitrate || 0))
    return score
  }

  const displayedQualities = computed(() => {
    // Always consider every codec family. Filtering to the active codec only
    // hid entire ladders (e.g. AVC 1080/720/480 when playing VP9 2160p left
    // just 2160/1440/144). Per-height scoring still prefers the active codec.
    const sourceQualities = qualities.value
    const dedupedQualities = new Map<string, QualityLevel>()

    sourceQualities.forEach((quality) => {
      // Normalize missing labels so the menu never renders blank rows.
      const normalized: QualityLevel = {
        ...quality,
        label: resolveQualityLabel(quality) || String(quality.id ?? ''),
      }
      if (!normalized.label) return

      const bucketKey = getQualityBucketKey(normalized)
      const existing = dedupedQualities.get(bucketKey)
      if (!existing || scoreQualityForDisplay(normalized) > scoreQualityForDisplay(existing)) {
        dedupedQualities.set(bucketKey, normalized)
      }
    })

    return [...dedupedQualities.values()].sort((left, right) => {
      const heightDelta = (Number(right.height || 0) - Number(left.height || 0))
      if (heightDelta !== 0) return heightDelta
      return Number(right.bitrate || 0) - Number(left.bitrate || 0)
    })
  })

  const currentQualityText = computed(() => {
    // Always show an explicit rung (1080p / 720p…). Never "自动" / "Auto" —
    // users pick a concrete height; ABR may still run under the hood until a
    // manual selection locks the ladder.
    const resolved = resolvedCurrentQuality.value
    if (resolved) {
      const label = resolveQualityLabel(resolved)
      if (label) return label
    }

    if (isDisplayableQualityLabel(currentQualityLabel.value)) {
      return String(currentQualityLabel.value || '').trim()
    }

    // Engine sometimes reports height-only tokens ("720") without a trailing p.
    const rawLabel = String(currentQualityLabel.value || '').trim()
    if (rawLabel && !isAutoQualityLabel(rawLabel) && !isInternalQualityLabel(rawLabel)) {
      const asHeight = Number.parseInt(rawLabel.replace(/[^0-9]/g, ''), 10)
      if (Number.isFinite(asHeight) && asHeight > 0) return `${asHeight}p`
      return rawLabel
    }

    // Provisional: prefer a mid-ladder ~720p-class rung (matches Shaka's default
    // bandwidth seed) so the chip is concrete before adaptation settles; then
    // fall back to the highest available height.
    const ladder = displayedQualities.value
    if (ladder.length === 0) return ''
    const preferred = ladder.find((quality) => Number(quality.height || 0) <= 720)
      || ladder[ladder.length - 1]
      || ladder[0]
    return resolveQualityLabel(preferred)
  })
  const qualityTagLabel = computed(() => currentQualityText.value)
  // Popup header mirrors the chip: concrete height only, never bare "画质".
  const qualityMenuLabel = computed(() => (
    currentQualityText.value || t('quality')
  ))

  const isQualityActive = (quality: { id: string | number }) => (
    resolvedCurrentQuality.value !== null
      && String(resolvedCurrentQuality.value.id) === String(quality.id)
  )

  return {
    visibleCodecFamily,
    resolvedCurrentQuality,
    displayedQualities,
    currentQualityText,
    qualityTagLabel,
    qualityMenuLabel,
    isQualityActive,
  }
}

export default useQualityDisplay
