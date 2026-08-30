<template>
  <section class="home-inbox" aria-labelledby="home-inbox-title">
    <!-- Flat filter row on canvas — not a second card chrome -->
    <header class="home-inbox__header">
      <div class="home-inbox__heading">
        <h2 id="home-inbox-title">最新入库</h2>
      </div>

      <div class="home-inbox__tools">
        <AppSegmentedControl
          :model-value="activeFilter"
          :options="filterOptions"
          size="sm"
          aria-label="首页内容范围"
          @update:model-value="setFilter"
        />
        <Button variant="secondary" size="sm" @click="emit('viewMore')">
          全部
          <AppIcon name="chevronRight" class="size-3.5" />
        </Button>
      </div>
    </header>

    <div v-if="loadError && !loading && items.length === 0" class="home-inbox__state">
      <AppEmptyState variant="error" title="内容同步失败" :copy="loadError">
        <template #actions>
          <Button size="sm" @click="load">重试</Button>
        </template>
      </AppEmptyState>
    </div>

    <div v-else-if="loading && items.length === 0" class="home-inbox__posts" aria-label="正在加载最新内容">
      <VideoSkeleton
        v-for="index in 4"
        :key="index"
        :delay="(index - 1) * 35"
        layout="list"
        appearance="default"
      />
    </div>

    <div v-else-if="videoGroups.length" class="home-inbox__timeline">
      <section v-for="group in videoGroups" :key="group.title" class="home-inbox__group">
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
import { ref, watch } from 'vue'
import { getVideoList } from '@/shared/api'
import type { VideoListItem, VideoProfile } from '@/features/video/types/video'
import { useFeedGrouping } from '@/features/video/composables/useFeedGrouping'
import { errorMessage } from '@/shared/lib/errorMessage'
import { Logger } from '@/shared/lib/logger'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import VideoItem from './VideoItem.vue'
import VideoSkeleton from './VideoSkeleton.vue'

type InboxFilter = 'all' | 'unread' | 'special'

const emit = defineEmits<{
  openModal: [video: VideoListItem]
  goToProfile: [profile: VideoProfile]
  goToSubscription: [id: number | string | null | undefined]
  viewMore: []
}>()

const filterOptions = [
  { value: 'all', label: '全部' },
  { value: 'unread', label: '未看' },
  { value: 'special', label: '特别关注' },
] as const

const items = ref<VideoListItem[]>([])
const activeFilter = ref<InboxFilter>('all')
const loading = ref(false)
const loadError = ref('')
const { videoGroups } = useFeedGrouping({ feedItems: items })
let requestToken = 0
let abortController: AbortController | null = null

const setFilter = (value: string | number) => {
  if (value === 'all' || value === 'unread' || value === 'special') activeFilter.value = value
}

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
      category: activeFilter.value === 'unread' ? 'unread' : 'all',
      sort_by: 'publish_date',
      nsfw: 'all',
      special: activeFilter.value === 'special' ? 'yes' : 'all',
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
      category: activeFilter.value === 'unread' ? 'unread' : 'all',
      sort_by: 'publish_date',
      nsfw: 'all',
      special: activeFilter.value === 'special' ? 'yes' : 'all',
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

watch(activeFilter, load, { immediate: true })
defineExpose({
  refresh: load,
  loadTop,
  prepend,
  activeFilter,
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

.home-inbox__header,
.home-inbox__tools,
.home-inbox__group-header {
  display: flex;
  align-items: center;
}

.home-inbox__header {
  min-height: 2.35rem;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.15rem 0.1rem;
  background: transparent;
}

.home-inbox__heading {
  min-width: 0;
}

.home-inbox__header h2,
.home-inbox__group-header h3 {
  margin: 0;
}

.home-inbox__header h2 {
  font-family: var(--font-sans);
  font-size: var(--app-text-lg);
  font-weight: 700;
  letter-spacing: 0;
}

.home-inbox__tools {
  gap: 0.4rem;
  flex: 0 0 auto;
}

.home-inbox__timeline {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.home-inbox__group {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.home-inbox__group-header {
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0 0.2rem;
}

.home-inbox__group-header h3 {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-xs);
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.home-inbox__group-header span {
  display: inline-flex;
  min-width: 1.25rem;
  height: 1.15rem;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: hsl(var(--foreground) / 0.06);
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-xs);
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  padding-inline: 0.35rem;
}

.home-inbox__posts {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.home-inbox__state {
  min-height: 14rem;
  border: 1px solid hsl(var(--border) / 0.9);
  border-radius: var(--radius-lg);
  background: hsl(var(--card));
  padding: 1rem;
}

@media (max-width: 760px) {
  .home-inbox__header {
    align-items: flex-start;
    flex-direction: column;
    padding-block: 0.75rem;
  }

  .home-inbox__tools {
    width: 100%;
    justify-content: space-between;
  }
}
 </style>
