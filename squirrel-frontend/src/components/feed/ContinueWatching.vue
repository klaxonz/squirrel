<template>
  <div v-if="historyItems.length > 0" class="mb-6 pt-4 px-6 overflow-hidden relative group/container">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xl font-bold tracking-tight flex items-center gap-2 text-foreground/90">
        <AppIcon name="time" class="size-5 text-primary" />
        继续观看
      </h2>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="flex h-8 items-center gap-1.5 rounded-md px-2.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
          @click="$emit('viewMore')"
        >
          查看更多
          <AppIcon name="chevronRight" class="size-3.5" />
        </button>
        <div class="flex gap-1 opacity-0 transition-opacity duration-200" :class="{ 'opacity-100': canScrollLeft || canScrollRight, 'group-hover/container:opacity-100': true }">
        <button
          class="size-8 flex items-center justify-center rounded-full bg-background/80 hover:bg-muted border border-border shadow-sm disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          :disabled="!canScrollLeft"
          @click="scroll('left')"
        >
          <AppIcon name="chevronLeft" class="size-4 text-foreground/70" />
        </button>
        <button
          class="size-8 flex items-center justify-center rounded-full bg-background/80 hover:bg-muted border border-border shadow-sm disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          :disabled="!canScrollRight"
          @click="scroll('right')"
        >
          <AppIcon name="chevronRight" class="size-4 text-foreground/70" />
        </button>
        </div>
      </div>
    </div>

    <div
      ref="scrollContainer"
      class="no-scrollbar flex gap-4 overflow-x-auto pb-4 snap-x scroll-smooth"
      @scroll="updateScrollState"
    >
      <RecommendationCard
        v-for="item in historyItems"
        :key="item.id"
        :video="item"
        show-duration
        show-play-overlay
        show-progress
        :show-subscription="false"
        @openModal="$emit('openModal', item)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import RecommendationCard from '@/components/feed/RecommendationCard.vue'
import useVideoHistory from '@/composables/useVideoHistory'
import { Logger } from '@/utils/logger'

const emit = defineEmits(['openModal', 'viewMore'])

const { getWatchHistory } = useVideoHistory()
const historyItems = ref<any[]>([])

const scrollContainer = ref<HTMLElement | null>(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)

const updateScrollState = () => {
  if (!scrollContainer.value) return
  const { scrollLeft, scrollWidth, clientWidth } = scrollContainer.value
  canScrollLeft.value = scrollLeft > 0
  // Use a small threshold (e.g., 2px) to account for fractional pixel rounding errors
  canScrollRight.value = scrollLeft < scrollWidth - clientWidth - 2
}

const scroll = (direction: 'left' | 'right') => {
  if (!scrollContainer.value) return

  // Scroll by roughly 2 items worth of width (288px card + 16px gap = 304px per item)
  const scrollAmount = 304 * 2
  const targetScroll = scrollContainer.value.scrollLeft + (direction === 'left' ? -scrollAmount : scrollAmount)

  scrollContainer.value.scrollTo({
    left: targetScroll,
    behavior: 'smooth'
  })
}

const getProgress = (video: any) => {
  const d = Number(video.duration || 0)
  return d > 0 ? Math.min(1, Number(video.last_position || 0) / d) : 0
}

const load = async () => {
  try {
    const { items } = await getWatchHistory(1, { pageSize: 15 })
    // Filter out items that are completed or barely started
    historyItems.value = items.filter((item: any) => {
      const progress = getProgress(item)
      return progress > 0.01 && progress < 0.95
    }).slice(0, 8) // Limit to 8 items

    // Check scroll state after items are rendered
    await nextTick()
    updateScrollState()
  } catch (e) {
    Logger.error('Failed to load continue watching history:', e)
  }
}

onMounted(load)

defineExpose({ refresh: load })
</script>
