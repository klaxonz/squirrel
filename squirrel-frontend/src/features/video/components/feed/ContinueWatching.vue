<template>
  <div v-if="historyItems.length > 0 || loading" class="mb-6 pt-4 px-6 overflow-hidden relative group/container">
    <FeedRailHeader
      title="继续观看"
      view-more-label="查看全部"
      :can-scroll-left="canScrollLeft"
      :can-scroll-right="canScrollRight"
      @view-more="$emit('viewMore')"
      @scroll="scroll"
    />

    <div
      ref="scrollContainer"
      class="no-scrollbar flex gap-4 overflow-x-auto pb-4 snap-x"
      @scroll="updateScrollState"
    >
      <RecommendationSkeleton v-if="loading && historyItems.length === 0" :count="6" />
      <VideoItem
        v-for="item in historyItems"
        :key="item.id"
        :video="item as VideoListItem"
        show-avatar
        show-duration
        class="w-[18rem] shrink-0 snap-start"
        @openModal="$emit('openModal', item)"
        @goToSubscription="(id) => $emit('goToSubscription', id)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import FeedRailHeader from '@/features/video/components/feed/FeedRailHeader.vue'
import VideoItem from '@/features/video/components/feed/VideoItem.vue'
import RecommendationSkeleton from '@/features/video/components/feed/RecommendationSkeleton.vue'
import { useVideoHistory } from '@/features/video/composables/useVideoHistory'
import { Logger } from '@/shared/lib/logger'
import type { VideoHistoryEntry, VideoListItem } from '@/features/video/types/video'

const emit = defineEmits<{
  openModal: [video: VideoHistoryEntry]
  viewMore: []
  goToSubscription: [id: number | string | null | undefined]
  heroChange: [video: VideoHistoryEntry | null]
}>()

const { getWatchHistory } = useVideoHistory()
const historyItems = ref<VideoHistoryEntry[]>([])
const loading = ref(false)

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
  })
}

const getProgress = (video: VideoHistoryEntry) => {
  const d = Number(video.duration || 0)
  return d > 0 ? Math.min(1, Number(video.last_position || 0) / d) : 0
}

const HERO_PROGRESS_MIN = 0.3
const HERO_PROGRESS_MAX = 0.9

const pickHeroVideo = (items: VideoHistoryEntry[]): VideoHistoryEntry | null => {
  if (items.length === 0) return null
  const sweet = items.filter((v) => {
    const p = getProgress(v)
    return p >= HERO_PROGRESS_MIN && p <= HERO_PROGRESS_MAX && v.thumbnail
  })
  if (sweet.length > 0) {
    return sweet.reduce((a, b) => (getProgress(a) > getProgress(b) ? a : b))
  }
  const withThumb = items.filter((v) => v.thumbnail)
  return withThumb[0] ?? items[0] ?? null
}

const load = async () => {
  loading.value = true
  try {
    const { items } = await getWatchHistory(1, { pageSize: 30 })
    // Keep anything the user has actually started watching (progress > 0);
    // drop only items that were never played.
    historyItems.value = items.filter((item) => getProgress(item) > 0).slice(0, 12)

    const hero = pickHeroVideo(historyItems.value)
    emit('heroChange', hero)

    // Check scroll state after items are rendered
    await nextTick()
    updateScrollState()
  } catch (e) {
    Logger.error('Failed to load continue watching history:', e)
  } finally {
    loading.value = false
  }
}

onMounted(load)

defineExpose({ refresh: load })
</script>
