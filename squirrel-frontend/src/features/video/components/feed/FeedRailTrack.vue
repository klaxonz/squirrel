<template>
  <div
    ref="scrollContainer"
    class="feed-rail-track no-scrollbar flex gap-4 overflow-x-auto pb-4 snap-x"
    @scroll="updateScrollState"
  >
    <slot />
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  /** Approximate width of one snap item (card + gap). Used for page scroll distance. */
  itemExtent?: number
  /** How many items to advance per click. */
  pageSize?: number
  /**
   * Optional signal that content length changed (e.g. items.length).
   * Triggers a scroll-state remeasure after paint.
   */
  contentKey?: string | number
}>(), {
  itemExtent: 304,
  pageSize: 2,
  contentKey: undefined,
})

const emit = defineEmits<{
  scrollState: [state: { canScrollLeft: boolean; canScrollRight: boolean }]
}>()

const scrollContainer = ref<HTMLElement | null>(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)

let resizeObserver: ResizeObserver | null = null
let mutationObserver: MutationObserver | null = null

const publish = () => {
  emit('scrollState', {
    canScrollLeft: canScrollLeft.value,
    canScrollRight: canScrollRight.value,
  })
}

const updateScrollState = () => {
  const el = scrollContainer.value
  if (!el) return
  const { scrollLeft, scrollWidth, clientWidth } = el
  const nextLeft = scrollLeft > 0
  // 2px slack for fractional pixel rounding
  const nextRight = scrollLeft < scrollWidth - clientWidth - 2
  if (nextLeft !== canScrollLeft.value || nextRight !== canScrollRight.value) {
    canScrollLeft.value = nextLeft
    canScrollRight.value = nextRight
    publish()
  } else {
    // Still publish once after mount/remeasure so parents stay in sync
    publish()
  }
}

const scroll = (direction: 'left' | 'right') => {
  const el = scrollContainer.value
  if (!el) return
  const delta = props.itemExtent * props.pageSize
  const prefersReduce =
    typeof window !== 'undefined'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches

  el.scrollTo({
    left: el.scrollLeft + (direction === 'left' ? -delta : delta),
    behavior: prefersReduce ? 'auto' : 'smooth',
  })
  // scroll event will remeasure; also remeasure after smooth scroll settles
  window.setTimeout(updateScrollState, prefersReduce ? 0 : 320)
}

const remeasure = async () => {
  await nextTick()
  // Double rAF: wait for flex children (cards / skeletons) to lay out
  await new Promise<void>((resolve) => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => resolve())
    })
  })
  updateScrollState()
}

watch(() => props.contentKey, () => {
  void remeasure()
})

onMounted(() => {
  void remeasure()
  const el = scrollContainer.value
  if (!el) return

  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => updateScrollState())
    resizeObserver.observe(el)
  }

  if (typeof MutationObserver !== 'undefined') {
    mutationObserver = new MutationObserver(() => {
      void remeasure()
    })
    mutationObserver.observe(el, { childList: true, subtree: true })
  }
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
  mutationObserver?.disconnect()
  mutationObserver = null
})

defineExpose({
  updateScrollState,
  scroll,
  scrollContainer,
  canScrollLeft,
  canScrollRight,
})
</script>
