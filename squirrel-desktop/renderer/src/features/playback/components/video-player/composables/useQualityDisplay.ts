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

// ponytail: pure scoring/dedup helpers for the quality menu. Lifted verbatim
// from VideoPlayer.vue so the displayed list, active check, and labels stay
// byte-identical to the pre-extraction behavior. NOTE: the '??' literals below
// are mojibake carried over from the original source (not real CJK); kept as-is
// to preserve behavior — fixing them is a separate task.
const isInternalQualityLabel = (label: string | null | undefined) => /^level[_\s-]?\d+$/i.test(String(label || '').trim().toLowerCase())
const isAutoQualityLabel = (label: string | null | undefined) => ['auto', '??', '??'].includes(String(label || '').trim().toLowerCase())
const isDisplayableQualityLabel = (label: string | null | undefined) => !isInternalQualityLabel(label) && !isAutoQualityLabel(label)

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
    const codecMatchedQualities = visibleCodecFamily.value
      ? qualities.value.filter((quality) => getCodecFamily(quality.codec) === visibleCodecFamily.value)
      : qualities.value
    const sourceQualities = codecMatchedQualities.length > 0 ? codecMatchedQualities : qualities.value
    const dedupedQualities = new Map<string, QualityLevel>()

    sourceQualities.forEach((quality) => {
      const bucketKey = getQualityBucketKey(quality)
      const existing = dedupedQualities.get(bucketKey)
      if (!existing || scoreQualityForDisplay(quality) > scoreQualityForDisplay(existing)) {
        dedupedQualities.set(bucketKey, quality)
      }
    })

    return [...dedupedQualities.values()].sort((left, right) => {
      const heightDelta = (Number(right.height || 0) - Number(left.height || 0))
      if (heightDelta !== 0) return heightDelta
      return Number(right.bitrate || 0) - Number(left.bitrate || 0)
    })
  })

  const currentQualityText = computed(() => (
    resolvedCurrentQuality.value?.label
      || (isDisplayableQualityLabel(currentQualityLabel.value) ? (currentQualityLabel.value || '') : '')
  ))
  const qualityTagLabel = computed(() => currentQualityText.value)
  const qualityMenuLabel = computed(() => currentQualityText.value || t('quality'))

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
