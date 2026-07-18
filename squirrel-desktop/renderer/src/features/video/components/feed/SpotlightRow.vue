<template>
  <section v-if="items.length > 0 || loading || loadError" class="home-feed-rail group/container">
    <FeedRailHeader
      title="最新更新"
      view-more
      :can-scroll-left="canScrollLeft"
      :can-scroll-right="canScrollRight"
      @view-more="$emit('viewMore')"
      @scroll="onScroll"
    />

    <div v-if="loadError && !loading && items.length === 0" class="app-page-empty app-page-empty--compact">
      <AppEmptyState variant="error" title="最新更新加载失败" :copy="loadError">
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
        v-for="video in items"
        :key="video.id"
        :video="video"
        show-duration
        thumbnail-status="none"
        class="app-video-rail-card"
        @openModal="$emit('openModal', video)"
        @goToProfile="(profile) => $emit('goToProfile', profile)"
        @goToSubscription="(id) => $emit('goToSubscription', id)"
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

defineEmits(['openModal', 'goToProfile', 'goToSubscription', 'viewMore'])

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
      pageSize: 10,
      page_size: 10,
      category: 'all',
      sort_by: 'publish_date',
      nsfw: 'all',
    })
    items.value = (data?.data || []).slice(0, 10)
  } catch (e) {
    Logger.error('Failed to load spotlight videos:', e)
    items.value = []
    loadError.value = errorMessage(e, '无法加载最新更新，请稍后重试。')
  } finally {
    loading.value = false
  }
}

onMounted(load)

defineExpose({ refresh: load })
</script>
