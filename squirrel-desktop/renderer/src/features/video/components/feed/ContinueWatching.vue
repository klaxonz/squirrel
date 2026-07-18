<template>
  <section v-if="historyItems.length > 0 || loading || loadError" class="home-feed-rail group/container">
    <FeedRailHeader
      title="继续观看"
      view-more
      :can-scroll-left="canScrollLeft"
      :can-scroll-right="canScrollRight"
      @view-more="$emit('viewMore')"
      @scroll="onScroll"
    />

    <div v-if="loadError && !loading && historyItems.length === 0" class="app-page-empty app-page-empty--compact">
      <AppEmptyState variant="error" title="继续观看加载失败" :copy="loadError">
        <template #actions>
          <Button size="sm" @click="load">重试</Button>
        </template>
      </AppEmptyState>
    </div>

    <FeedRailTrack
      v-else
      ref="track"
      :content-key="historyItems.length"
      @scroll-state="onScrollState"
    >
      <RecommendationSkeleton v-if="loading && historyItems.length === 0" :count="6" />
      <VideoItem
        v-for="item in historyItems"
        :key="item.id"
        :video="item as VideoListItem"
        show-duration
        thumbnail-status="progress-only"
        class="app-video-rail-card"
        @openModal="$emit('openModal', item)"
        @goToProfile="(profile) => $emit('goToProfile', profile)"
        @goToSubscription="(id) => $emit('goToSubscription', id)"
      />
    </FeedRailTrack>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import FeedRailHeader from '@/features/video/components/feed/FeedRailHeader.vue'
import FeedRailTrack from '@/features/video/components/feed/FeedRailTrack.vue'
import VideoItem from '@/features/video/components/feed/VideoItem.vue'
import RecommendationSkeleton from '@/features/video/components/feed/RecommendationSkeleton.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import { Button } from '@/shared/ui/button'
import { useVideoHistory } from '@/features/video/composables/useVideoHistory'
import { errorMessage } from '@/shared/lib/errorMessage'
import { Logger } from '@/shared/lib/logger'
import type { VideoHistoryEntry, VideoListItem, VideoProfile } from '@/features/video/types/video'

defineEmits<{
  openModal: [video: VideoHistoryEntry]
  viewMore: []
  goToProfile: [profile: VideoProfile]
  goToSubscription: [id: number | string | null | undefined]
}>()

const { getWatchHistory } = useVideoHistory()
const historyItems = ref<VideoHistoryEntry[]>([])
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

const getProgress = (video: VideoHistoryEntry) => {
  const d = Number(video.duration || 0)
  return d > 0 ? Math.min(1, Number(video.last_position || 0) / d) : 0
}

const load = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const { items } = await getWatchHistory(1, { pageSize: 30 })
    historyItems.value = items.filter((item) => getProgress(item) > 0).slice(0, 12)
  } catch (e) {
    Logger.error('Failed to load continue watching history:', e)
    historyItems.value = []
    loadError.value = errorMessage(e, '无法加载继续观看，请稍后重试。')
  } finally {
    loading.value = false
  }
}

watch(historyItems, () => {
  track.value?.updateScrollState()
})

onMounted(load)

defineExpose({ refresh: load })
</script>
