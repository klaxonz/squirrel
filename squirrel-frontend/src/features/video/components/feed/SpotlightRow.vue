<template>
  <section v-if="items.length > 0 || loading" class="group/container app-reveal mb-10 px-6 pt-8">
    <FeedRailHeader
      title="精选推荐"
      :can-scroll-left="canScrollLeft"
      :can-scroll-right="canScrollRight"
      @scroll="scroll"
    />

    <div
      ref="scrollContainer"
      class="no-scrollbar flex gap-4 overflow-x-auto pb-4 snap-x scroll-smooth"
      @scroll="updateScrollState"
    >
      <RecommendationSkeleton v-if="loading && items.length === 0" :count="6" />
      <VideoItem
        v-for="(video, i) in items"
        :key="video.id"
        :video="video"
        show-avatar
        show-duration
        class="app-reveal w-[18rem] shrink-0 snap-start"
        :style="{ '--reveal-index': i }"
        @openModal="$emit('openModal', video)"
        @goToSubscription="(id) => $emit('goToSubscription', id)"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { getVideoList } from '@/shared/api'
import type { VideoListItem } from '@/features/video/types/video'
import { Logger } from '@/shared/lib/logger'
import FeedRailHeader from '@/features/video/components/feed/FeedRailHeader.vue'
import VideoItem from '@/features/video/components/feed/VideoItem.vue'
import RecommendationSkeleton from '@/features/video/components/feed/RecommendationSkeleton.vue'

defineEmits(['openModal', 'goToSubscription'])

const items = ref<VideoListItem[]>([])
const loading = ref(false)
const scrollContainer = ref<HTMLElement | null>(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)

const updateScrollState = () => {
  if (!scrollContainer.value) return
  const { scrollLeft, scrollWidth, clientWidth } = scrollContainer.value
  canScrollLeft.value = scrollLeft > 0
  canScrollRight.value = scrollLeft < scrollWidth - clientWidth - 2
}

const scroll = (direction: 'left' | 'right') => {
  if (!scrollContainer.value) return
  // 288px card + 16px gap = 304px per item, scroll 2 items
  const scrollAmount = 304 * 2
  scrollContainer.value.scrollTo({
    left: scrollContainer.value.scrollLeft + (direction === 'left' ? -scrollAmount : scrollAmount),
    behavior: 'smooth',
  })
}

const load = async () => {
  loading.value = true
  try {
    const data = await getVideoList({
      pageSize: 10,
      page_size: 10,
      category: 'all',
      sort_by: 'publish_date',
      nsfw: 'all',
    })
    items.value = (data?.data || []).slice(0, 10)
    await nextTick()
    updateScrollState()
  } catch (e) {
    Logger.error('Failed to load spotlight videos:', e)
  } finally {
    loading.value = false
  }
}

// Re-check scroll state whenever videos change (data loads async)
watch(() => scrollContainer.value?.scrollWidth, () => nextTick(updateScrollState))

onMounted(load)

defineExpose({ refresh: load })
</script>
