<template>
  <section v-if="items.length > 0 || loading" class="group/container mb-6 px-6 pt-2">
    <FeedRailHeader
      title="特别关注"
      view-more-label="查看更多"
      :can-scroll-left="canScrollLeft"
      :can-scroll-right="canScrollRight"
      @view-more="emit('viewMore')"
      @scroll="scroll"
    />

    <div
      ref="scrollContainer"
      class="no-scrollbar flex gap-4 overflow-x-auto pb-4 snap-x"
      @scroll="updateScrollState"
    >
      <RecommendationSkeleton v-if="loading && items.length === 0" :count="6" />
      <VideoItem
        v-for="item in items"
        :key="item.id"
        :video="item"
        show-avatar
        show-duration
        class="w-[18rem] shrink-0 snap-start"
        @openModal="emit('openModal', item)"
        @goToSubscription="(id) => emit('goToSubscription', id)"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { getVideoList } from '@/shared/api'
import type { VideoListItem } from '@/features/video/types/video'
import FeedRailHeader from '@/features/video/components/feed/FeedRailHeader.vue'
import VideoItem from '@/features/video/components/feed/VideoItem.vue'
import RecommendationSkeleton from '@/features/video/components/feed/RecommendationSkeleton.vue'

const emit = defineEmits(['openModal', 'goToSubscription', 'viewMore'])

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

  const scrollAmount = 304 * 2
  scrollContainer.value.scrollTo({
    left: scrollContainer.value.scrollLeft + (direction === 'left' ? -scrollAmount : scrollAmount),
  })
}

const load = async () => {
  loading.value = true
  try {
    const data = await getVideoList({
      pageSize: 12,
      page_size: 12,
      category: 'all',
      sort_by: 'publish_date',
      nsfw: 'all',
      special: 'yes',
    })

    items.value = (data?.data || []).slice(0, 12)
    await nextTick()
    updateScrollState()
  } catch {
    // silent — row stays empty
  } finally {
    loading.value = false
  }
}

onMounted(load)

defineExpose({ refresh: load })
</script>
