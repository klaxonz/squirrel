import { computed, nextTick, ref, watch, type ComputedRef, type Ref } from 'vue'

/**
 * Expand/collapse overflow detection for the video description block.
 *
 * Owns the "is the description taller than its collapsed clamp?" detection that
 * gates the 展开/收起 toggle, plus the ResizeObserver that re-measures when the
 * description element resizes. Resets the expanded state whenever the video id
 * or description text changes.
 *
 * Extracted from VideoPlay.vue so the measurement lifecycle (ResizeObserver
 * connect/disconnect, nextTick re-measure, the two reset watchers) lives in one
 * place instead of interleaved with subscription / playback wiring.
 */
export interface UseVideoDescriptionOverflowOptions {
  videoId: ComputedRef<string | number | null | undefined> | Ref<string | number | null | undefined>
  description: ComputedRef<string> | Ref<string>
}

export interface UseVideoDescriptionOverflowReturn {
  /** Template ref: attach to the clamped description element. */
  descriptionTextRef: Ref<HTMLElement | null>
  descriptionExpanded: Ref<boolean>
  hasLongDescription: ComputedRef<boolean>
}

export function useVideoDescriptionOverflow(
  options: UseVideoDescriptionOverflowOptions,
): UseVideoDescriptionOverflowReturn {
  const { videoId, description } = options

  const descriptionTextRef = ref<HTMLElement | null>(null)
  const descriptionExpanded = ref(false)
  const hasDescriptionOverflow = ref(false)
  let descriptionResizeObserver: ResizeObserver | null = null

  const hasLongDescription = computed(() => hasDescriptionOverflow.value)

  const syncDescriptionOverflow = async () => {
    await nextTick()
    const el = descriptionTextRef.value
    hasDescriptionOverflow.value = !!el && el.scrollHeight > el.clientHeight + 1
  }

  // Reset expanded state when the video or its description changes, then re-measure.
  watch(videoId, () => {
    descriptionExpanded.value = false
    void syncDescriptionOverflow()
  })

  watch(description, () => {
    descriptionExpanded.value = false
    void syncDescriptionOverflow()
  })

  // Measure on mount and on resize. Re-observing when the ref rebinds (video
  // swap) disconnects the prior observer to avoid leaks; only re-measures while
  // collapsed (expanded shows the full height, so overflow is meaningless).
  watch(descriptionTextRef, (el) => {
    descriptionResizeObserver?.disconnect()
    descriptionResizeObserver = null

    if (el) {
      descriptionResizeObserver = new ResizeObserver(() => {
        if (!descriptionExpanded.value) void syncDescriptionOverflow()
      })
      descriptionResizeObserver.observe(el)
    }

    void syncDescriptionOverflow()
  })

  return {
    descriptionTextRef,
    descriptionExpanded,
    hasLongDescription,
  }
}
