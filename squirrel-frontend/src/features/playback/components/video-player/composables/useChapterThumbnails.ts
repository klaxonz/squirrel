import { computed, type ComputedRef, type Ref } from 'vue'
import type { Chapter, MediaSource } from '../core'

/**
 * Chapter list normalisation + thumbnail-sprite frame math.
 *
 * Two related concerns that both key off `duration` and the media source:
 *   1. `normalizedChapters` — source chapters flattened into a
 *      `{ ...chapter, startPercent }` shape the progress rail renders.
 *   2. `thumbnailSpriteStyle` — given a sprite-sheet source + the current
 *      scrub preview time, computes the background-position/size to show the
 *      matching frame as a hover/scrub thumbnail.
 *
 * `handleChapterClick` is a thin `seek` passthrough kept here so the chapter
 * surface is one import in VideoPlayer rather than three loose consts.
 */
export interface UseChapterThumbnailsOptions {
  source: ComputedRef<MediaSource | null> | Ref<MediaSource | null>
  duration: ComputedRef<number> | Ref<number>
  /** Current scrub-preview time (null when not hovering the rail). */
  previewTime: ComputedRef<number | null> | Ref<number | null>
  seek: (time: number) => void
}

export interface NormalizedChapter extends Chapter {
  startPercent: number
}

export interface UseChapterThumbnailsReturn {
  sourceChapters: ComputedRef<Chapter[]>
  normalizedChapters: ComputedRef<NormalizedChapter[]>
  thumbnailSpriteUrl: ComputedRef<string | null>
  thumbnailSpriteStyle: ComputedRef<Record<string, string>>
  handleChapterClick: (time: number) => void
}

const DEFAULT_SPRITE_COLUMNS = 10
const DEFAULT_SPRITE_ROWS = 10
const DEFAULT_SPRITE_INTERVAL = 10

export function useChapterThumbnails(options: UseChapterThumbnailsOptions): UseChapterThumbnailsReturn {
  const { source, duration, previewTime, seek } = options

  const sourceChapters = computed(() => source.value?.chapters || [])

  const normalizedChapters = computed<NormalizedChapter[]>(() => {
    if (!duration.value || duration.value <= 0) return []
    return sourceChapters.value.map((chapter) => ({
      ...chapter,
      startPercent: Math.min((chapter.startTime / duration.value) * 100, 100),
    }))
  })

  const thumbnailSpriteUrl = computed(() => source.value?.thumbnailSpriteUrl || null)
  const thumbnailSpriteColumns = computed(() => source.value?.thumbnailSpriteColumns || DEFAULT_SPRITE_COLUMNS)
  const thumbnailSpriteRows = computed(() => source.value?.thumbnailSpriteRows || DEFAULT_SPRITE_ROWS)
  const thumbnailSpriteInterval = computed(() => source.value?.thumbnailSpriteInterval || DEFAULT_SPRITE_INTERVAL)

  const thumbnailSpriteStyle = computed<Record<string, string>>(() => {
    if (!thumbnailSpriteUrl.value || !duration.value) return {} as Record<string, string>
    const totalFrames = thumbnailSpriteColumns.value * thumbnailSpriteRows.value
    const frameIndex = Math.min(
      Math.floor((previewTime.value ?? 0) / thumbnailSpriteInterval.value),
      totalFrames - 1,
    )
    const col = frameIndex % thumbnailSpriteColumns.value
    const row = Math.floor(frameIndex / thumbnailSpriteColumns.value)
    const frameW = 100 * thumbnailSpriteColumns.value
    const frameH = 100 * thumbnailSpriteRows.value
    return {
      backgroundImage: `url(${thumbnailSpriteUrl.value})`,
      backgroundPosition: `-${col * 100}% -${row * 100}%`,
      backgroundSize: `${frameW}% ${frameH}%`,
    }
  })

  const handleChapterClick = (time: number) => {
    seek(time)
  }

  return {
    sourceChapters,
    normalizedChapters,
    thumbnailSpriteUrl,
    thumbnailSpriteStyle,
    handleChapterClick,
  }
}
