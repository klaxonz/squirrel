<template>
  <div v-if="historyItems.length > 0" class="mb-6 pt-4 px-6 overflow-hidden relative group/container">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-bold flex items-center gap-2 text-foreground/90">
        <AppIcon name="time" class="size-5 text-primary" />
        继续观看
      </h2>
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

    <div
      ref="scrollContainer"
      class="no-scrollbar flex gap-4 overflow-x-auto pb-4 snap-x scroll-smooth"
      @scroll="updateScrollState"
    >
      <div
        v-for="item in historyItems"
        :key="item.id"
        class="w-64 shrink-0 snap-start group cursor-pointer"
        @click="$emit('openModal', item)"
      >
        <div class="relative aspect-video rounded-lg bg-muted overflow-hidden transition-all duration-300 group-hover:scale-[1.02] group-hover:brightness-110">
          <img
            :src="item.thumbnail"
            loading="lazy"
            class="w-full h-full object-cover"
            :alt="item.title"
          />
          <div v-if="item.duration" class="absolute bottom-1.5 right-1.5 inline-flex h-5 items-center rounded-md bg-black/65 px-1.5 text-[10px] font-medium tabular-nums text-white backdrop-blur-sm">
            {{ formatDuration(item.duration) }}
          </div>
          <div class="absolute bottom-0 left-0 right-0 h-1 bg-black/40">
            <div class="h-full bg-primary transition-all duration-500" :style="{ width: `${getProgress(item) * 100}%` }" />
          </div>
          <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <div class="size-10 rounded-full bg-primary/90 flex items-center justify-center text-white shadow-lg backdrop-blur-sm scale-75 group-hover:scale-100 transition-transform">
              <AppIcon name="play" class="size-5 ml-1" />
            </div>
          </div>
        </div>
        <h3 class="mt-2 text-sm font-medium line-clamp-2 text-foreground/80 group-hover:text-primary transition-colors">
          {{ item.title }}
        </h3>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import useVideoHistory from '@/composables/useVideoHistory'
import { formatDuration } from '@/utils/dateFormat'

const emit = defineEmits(['openModal'])

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

  // Scroll by roughly 2 items worth of width (64 * 4px + 16px gap = 272px per item)
  const scrollAmount = 272 * 2
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

onMounted(async () => {
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
    console.error('Failed to load continue watching history:', e)
  }
})
</script>
