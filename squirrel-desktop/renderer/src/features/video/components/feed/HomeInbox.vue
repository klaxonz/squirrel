<template>
  <section class="home-inbox" aria-label="最新入库">

    <div v-if="loadError && !loading && items.length === 0" class="home-inbox__state">
      <AppEmptyState variant="error" title="内容同步失败" :copy="loadError">
        <template #actions>
          <Button size="sm" @click="load">重试</Button>
        </template>
      </AppEmptyState>
    </div>

    <div v-else-if="loading && items.length === 0" class="home-inbox__posts" aria-label="正在加载最新内容">
      <VideoSkeleton
        v-for="index in 8"
        :key="index"
        :delay="(index - 1) * 35"
        layout="list"
        appearance="default"
      />
    </div>

    <div v-else-if="videoGroups.length" class="home-inbox__timeline">
      <VideoItem
        v-if="leadVideo"
        :video="leadVideo"
        layout="lead"
        show-avatar
        show-duration
        class="home-inbox__lead"
        @openModal="emit('openModal', $event)"
        @goToProfile="(profile) => emit('goToProfile', profile)"
        @goToSubscription="(id) => emit('goToSubscription', id)"
        @lead-image-error="handleLeadImageError"
      />

      <section v-for="group in timelineGroups" :key="group.title" class="home-inbox__group">
        <header class="home-inbox__group-header">
          <h3>{{ group.title }}</h3>
          <span>{{ group.videos.length }}</span>
        </header>
        <div class="home-inbox__posts">
          <VideoItem
            v-for="video in group.videos"
            :key="video.id"
            :video="video"
            layout="list"
            show-avatar
            show-duration
            appearance="default"
            @openModal="emit('openModal', video)"
            @goToProfile="(profile) => emit('goToProfile', profile)"
            @goToSubscription="(id) => emit('goToSubscription', id)"
          />
        </div>
      </section>
    </div>

    <div v-else class="home-inbox__state">
      <AppEmptyState variant="plain" icon="inbox" title="暂时没有新内容" copy="换一个范围，或等待下一次订阅同步。" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { getVideoList } from '@/shared/api'
import type { VideoListItem, VideoProfile } from '@/features/video/types/video'
import { useFeedGrouping } from '@/features/video/composables/useFeedGrouping'
import { errorMessage } from '@/shared/lib/errorMessage'
import { Logger } from '@/shared/lib/logger'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import { Button } from '@/shared/ui/button'
import VideoItem from './VideoItem.vue'
import VideoSkeleton from './VideoSkeleton.vue'
import type { HomeInboxFilter } from '@/features/video/constants/homeInbox'

const props = withDefaults(defineProps<{
  filter?: HomeInboxFilter
}>(), {
  filter: 'all',
})

const emit = defineEmits<{
  openModal: [video: VideoListItem]
  goToProfile: [profile: VideoProfile]
  goToSubscription: [id: number | string | null | undefined]
}>()

const items = ref<VideoListItem[]>([])
const loading = ref(false)
const loadError = ref('')
const failedLeadIds = ref<Set<number>>(new Set())
const { videoGroups } = useFeedGrouping({ feedItems: items })

const handleLeadImageError = (videoId: number) => {
  if (failedLeadIds.value.has(videoId)) return
  const next = new Set(failedLeadIds.value)
  next.add(videoId)
  failedLeadIds.value = next
}

// The lead must earn its size: unread, carrying a real cover, and not one
// whose image already failed to load at runtime.
const leadVideo = computed<VideoListItem | null>(() => {
  const failed = failedLeadIds.value
  for (const group of videoGroups.value) {
    const candidate = group.videos.find((video) => (
      !video.is_read
      && !failed.has(video.id)
      && String(video.thumbnail || '').trim()
    ))
    if (candidate) return candidate
  }
  return null
})

const timelineGroups = computed(() => {
  const lead = leadVideo.value
  if (!lead) return videoGroups.value
  return videoGroups.value
    .map((group) => ({
      ...group,
      videos: group.videos.filter((video) => video.id !== lead.id),
    }))
    .filter((group) => group.videos.length > 0)
})
let requestToken = 0
let abortController: AbortController | null = null

const load = async () => {
  const currentToken = ++requestToken
  abortController?.abort()
  abortController = new AbortController()
  loading.value = true
  loadError.value = ''

  try {
    const data = await getVideoList({
      pageSize: 24,
      page_size: 24,
      category: props.filter === 'unread' ? 'unread' : 'all',
      sort_by: 'publish_date',
      nsfw: 'all',
      special: props.filter === 'special' ? 'yes' : 'all',
    }, { signal: abortController.signal })
    if (currentToken !== requestToken) return
    items.value = Array.isArray(data?.data) ? data.data : []
  } catch (error) {
    if (currentToken !== requestToken) return
    Logger.error('Failed to load home inbox:', error)
    loadError.value = errorMessage(error, '无法同步最新内容，请稍后重试。')
  } finally {
    if (currentToken === requestToken) loading.value = false
  }
}

// Silent probe for the newest page — same params as load() but does NOT touch
// visible state. The caller (HomeView) decides whether to surface a
// "view new posts" bar (see useNewContentDetector).
const loadTop = async (): Promise<VideoListItem[]> => {
  try {
    const data = await getVideoList({
      pageSize: 24,
      page_size: 24,
      category: props.filter === 'unread' ? 'unread' : 'all',
      sort_by: 'publish_date',
      nsfw: 'all',
      special: props.filter === 'special' ? 'yes' : 'all',
    })
    return Array.isArray(data?.data) ? data.data : []
  } catch {
    return []
  }
}

// Prepend newly fetched items at the top of the current inbox, keeping the
// existing items (and their local UI state) untouched.
const prepend = (newItems: VideoListItem[]) => {
  if (!newItems.length) return
  const seen = new Set(items.value.map((item) => item.id))
  const fresh = newItems.filter((item) => !seen.has(item.id))
  if (fresh.length) items.value = [...fresh, ...items.value]
}

watch(() => props.filter, load, { immediate: true })
defineExpose({
  refresh: load,
  loadTop,
  prepend,
  getFirstId: () => items.value[0]?.id ?? null,
})
</script>

<style scoped>
/* Flat stream: filters on canvas, posts are the only cards. */
.home-inbox {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  background: transparent;
}

.home-inbox__group-header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 0.5rem;
  padding: 0;
}

.home-inbox__group-header h3 {
  margin: 0;
  color: hsl(var(--foreground));
  font-size: var(--app-text-base);
  font-weight: 600;
  letter-spacing: -0.01em;
}

.home-inbox__timeline {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.home-inbox__lead {
  margin-bottom: 0.25rem;
}

.home-inbox__group {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.home-inbox__group-header span {
  display: inline-flex;
  min-width: 1.25rem;
  height: 1.15rem;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  background: hsl(var(--foreground) / 0.06);
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-xs);
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  padding-inline: 0.35rem;
}

.home-inbox__posts {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 17.5rem), 1fr));
  align-items: start;
  gap: var(--space-6) var(--space-5);
}

.home-inbox__state {
  min-height: 14rem;
  border: 1px solid hsl(var(--border) / 0.9);
  border-radius: var(--radius-lg);
  background: hsl(var(--card));
  padding: 1rem;
}
 </style>
