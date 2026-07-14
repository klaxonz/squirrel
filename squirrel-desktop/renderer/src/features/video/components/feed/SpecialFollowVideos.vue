<template>
  <section v-if="items.length > 0 || loading || loadError" class="home-feed-rail group/container">
    <FeedRailHeader
      title="特别关注"
      view-more
      view-more-label="查看更多"
      :can-scroll-left="canScrollLeft"
      :can-scroll-right="canScrollRight"
      @view-more="emit('viewMore')"
      @scroll="onScroll"
    />

    <div v-if="loadError && !loading && items.length === 0" class="app-page-empty app-page-empty--compact">
      <AppEmptyState variant="error" title="特别关注加载失败" :copy="loadError">
        <template #actions>
          <Button size="sm" @click="load">重试</Button>
        </template>
      </AppEmptyState>
    </div>

    <FeedRailTrack
      v-else
      ref="track"
      :content-key="items.length"
      @scroll-state="onScrollState"
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
        @goToProfile="(profile) => emit('goToProfile', profile)"
        @goToSubscription="(id) => emit('goToSubscription', id)"
      />
    </FeedRailTrack>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getVideoList } from '@/shared/api'
import type { VideoListItem } from '@/features/video/types/video'
import { errorMessage } from '@/shared/lib/errorMessage'
import { Logger } from '@/shared/lib/logger'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import { Button } from '@/shared/ui/button'
import FeedRailHeader from '@/features/video/components/feed/FeedRailHeader.vue'
import FeedRailTrack from '@/features/video/components/feed/FeedRailTrack.vue'
import VideoItem from '@/features/video/components/feed/VideoItem.vue'
import RecommendationSkeleton from '@/features/video/components/feed/RecommendationSkeleton.vue'

const emit = defineEmits(['openModal', 'goToProfile', 'goToSubscription', 'viewMore'])

const items = ref<VideoListItem[]>([])
const loading = ref(false)
const loadError = ref('')
const track = ref<InstanceType<typeof FeedRailTrack> | null>(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)

const onScrollState = (state: { canScrollLeft: boolean; canScrollRight: boolean }) => {
  canScrollLeft.value = state.canScrollLeft
  canScrollRight.value = state.canScrollRight
}

const onScroll = (direction: 'left' | 'right') => {
  track.value?.scroll(direction)
}

const load = async () => {
  loading.value = true
  loadError.value = ''
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
  } catch (error) {
    Logger.error('Failed to load special follow videos:', error)
    items.value = []
    loadError.value = errorMessage(error, '无法加载特别关注，请稍后重试。')
  } finally {
    loading.value = false
  }
}

onMounted(load)

defineExpose({ refresh: load })
</script>
