<template>
  <section v-if="railItems.length > 0 || loading" class="home-feed-rail group/container">
    <FeedRailHeader
      title="继续观看"
      view-more
      :can-scroll-left="canScrollLeft"
      :can-scroll-right="canScrollRight"
      @view-more="$emit('viewMore')"
      @scroll="onScroll"
    />

    <FeedRailTrack
      ref="track"
      :content-key="railItems.length"
      @scroll-state="onScrollState"
    >
      <RecommendationSkeleton v-if="loading && railItems.length === 0" :count="6" />
      <VideoItem
        v-for="item in railItems"
        :key="item.id"
        :video="item as VideoListItem"
        show-avatar
        show-duration
        class="w-[18rem] shrink-0 snap-start"
        @openModal="$emit('openModal', item)"
        @goToSubscription="(id) => $emit('goToSubscription', id)"
      />
    </FeedRailTrack>
  </section>
</template>

<script lang="ts">
// Module-level record of recently shown hero video IDs.
// Persists across component mount/unmount within the same page session
// to prevent the same video from dominating the hero spot.
import type { VideoHistoryEntry } from '@/features/video/types/video'

const recentHeroIds: number[] = []
const MAX_RECENT_HERO = 5

export function pushRecentHero(video: VideoHistoryEntry) {
  if (video.id == null) return
  recentHeroIds.push(video.id)
  if (recentHeroIds.length > MAX_RECENT_HERO) recentHeroIds.shift()
}

export function getRecentHeroIds(): readonly number[] {
  return recentHeroIds
}
</script>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import FeedRailHeader from '@/features/video/components/feed/FeedRailHeader.vue'
import FeedRailTrack from '@/features/video/components/feed/FeedRailTrack.vue'
import VideoItem from '@/features/video/components/feed/VideoItem.vue'
import RecommendationSkeleton from '@/features/video/components/feed/RecommendationSkeleton.vue'
import { useVideoHistory } from '@/features/video/composables/useVideoHistory'
import { Logger } from '@/shared/lib/logger'
import type { VideoListItem } from '@/features/video/types/video'

const props = withDefaults(defineProps<{
  /** Video already featured in the home hero — omit from this rail to avoid adjacent duplicates. */
  excludeVideoId?: number | null
}>(), {
  excludeVideoId: null,
})

const emit = defineEmits<{
  openModal: [video: VideoHistoryEntry]
  viewMore: []
  goToSubscription: [id: number | string | null | undefined]
  heroChange: [video: VideoHistoryEntry | null]
}>()

const { getWatchHistory } = useVideoHistory()
const historyItems = ref<VideoHistoryEntry[]>([])
const loading = ref(false)
const track = ref<InstanceType<typeof FeedRailTrack> | null>(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)

/** Full history minus the hero item currently owned by HomeView. */
const railItems = computed(() => {
  const excludeId = props.excludeVideoId
  if (excludeId == null) return historyItems.value
  return historyItems.value.filter((item) => item.id !== excludeId)
})

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

const HERO_PROGRESS_MIN = 0.3
const HERO_PROGRESS_MAX = 0.9

function weightedRandomPick<T>(items: T[], weightFn: (item: T) => number): T | null {
  if (items.length === 0) return null
  const weights = items.map(weightFn)
  const totalWeight = weights.reduce((sum, w) => sum + w, 0)
  if (totalWeight <= 0) return items[Math.floor(Math.random() * items.length)]
  let rand = Math.random() * totalWeight
  for (let i = 0; i < items.length; i++) {
    rand -= weights[i]
    if (rand <= 0) return items[i]
  }
  return items[items.length - 1]
}

const pickHeroVideo = (items: VideoHistoryEntry[]): VideoHistoryEntry | null => {
  if (items.length === 0) return null

  const sweet = items.filter((v) => {
    const p = getProgress(v)
    return p >= HERO_PROGRESS_MIN && p <= HERO_PROGRESS_MAX && v.thumbnail
  })

  let pool: VideoHistoryEntry[]
  if (sweet.length > 0) {
    pool = sweet
  } else {
    const withThumb = items.filter((v) => v.thumbnail)
    pool = withThumb.length > 0 ? withThumb : items
  }

  if (pool.length === 1) {
    pushRecentHero(pool[0])
    return pool[0]
  }

  const freshCandidates = pool.filter((v) => !recentHeroIds.includes(v.id))
  const candidates = freshCandidates.length > 0 ? freshCandidates : pool

  const weightFn = (item: VideoHistoryEntry): number => {
    const p = getProgress(item)
    const progressWeight = p > 0 ? Math.min(9, Math.max(1, p * 10)) : 1
    const originalIdx = items.findIndex((v) => v.id === item.id)
    const recencyWeight =
      originalIdx >= 0 ? Math.max(0, 5 - (originalIdx / Math.max(1, items.length - 1)) * 5) : 0
    return progressWeight + recencyWeight
  }

  const hero = weightedRandomPick(candidates, weightFn) ?? candidates[0]!
  pushRecentHero(hero)
  return hero
}

const load = async () => {
  loading.value = true
  try {
    const { items } = await getWatchHistory(1, { pageSize: 30 })
    historyItems.value = items.filter((item) => getProgress(item) > 0).slice(0, 12)

    const hero = pickHeroVideo(historyItems.value)
    emit('heroChange', hero)
  } catch (e) {
    Logger.error('Failed to load continue watching history:', e)
  } finally {
    loading.value = false
  }
}

watch(railItems, () => {
  track.value?.updateScrollState()
})

onMounted(load)

defineExpose({ refresh: load })
</script>
