<template>
  <div ref="root" class="space-y-6">
    <div v-if="error" class="app-page-empty app-page-empty--compact">
      <AppEmptyState variant="error" title="加载失败" :copy="error">
        <template #actions>
          <Button variant="outline" size="sm" :disabled="loading" @click="$emit('retry')">重试</Button>
        </template>
      </AppEmptyState>
    </div>

    <div v-if="!items.length && !loading && !error" class="app-page-empty app-page-empty--compact">
      <AppEmptyState variant="plain" icon="inbox" title="暂无远端内容" copy="源站频道暂时没有返回视频。" />
    </div>

    <div v-if="items.length" class="app-video-grid app-video-grid--feed">
      <!-- Native article card — do not use shared Button here; its default h-9
           collapses the media frame and makes remote thumbnails look missing. -->
      <article
        v-for="item in items"
        :key="item.site + ':' + item.url"
        class="remote-channel-video-card group"
        role="button"
        tabindex="0"
        @click="$emit('open', item)"
        @keydown.enter.prevent="$emit('open', item)"
        @keydown.space.prevent="$emit('open', item)"
      >
        <div class="remote-channel-video-thumb group-hover:brightness-110">
          <VideoThumbnail :src="item.thumbnail" :alt="item.title" fit="cover" />
          <span v-if="item.duration" class="app-media-duration-badge app-mono">
            {{ formatDuration(item.duration) }}
          </span>
        </div>

        <div class="flex min-w-0 flex-col gap-1 px-0.5">
          <h3 class="remote-channel-video-title">
            {{ item.title }}
          </h3>
          <div class="text-xs font-medium text-muted-foreground">
            {{ displayDate(item) }}
          </div>
        </div>
      </article>
    </div>

    <div v-if="loading" class="app-video-grid app-video-grid--feed">
      <VideoSkeleton v-for="i in skeletonCount" :key="i" />
    </div>

    <div v-if="items.length && !allLoaded" class="app-page-actions">
      <Button variant="outline" :disabled="loading" @click="$emit('loadMore')">
        {{ loading ? '加载中' : '加载更多' }}
      </Button>
    </div>

    <div ref="loadMoreTrigger" class="h-16 w-full" />
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import { Button } from '@/shared/ui/button'
import VideoSkeleton from '@/features/video/components/feed/VideoSkeleton.vue'
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
import { useSkeletonCount } from '@/features/video/composables/useSkeletonCount'
import { formatDuration } from '@/shared/lib/dateFormat'
import { getMainScrollRoot } from '@/shared/composables/useMainScrollRoot'

type RemoteSearchItem = {
  source: 'remote'
  site: string
  id?: string | number | null
  title: string
  url: string
  thumbnail?: string | null
  duration?: number | null
  publish_date?: string | null
  published_text?: string | null
}

const props = defineProps<{
  items: RemoteSearchItem[]
  loading: boolean
  allLoaded: boolean
  error?: string
  scrollRoot?: HTMLElement | null
}>()

const emit = defineEmits<{
  open: [item: RemoteSearchItem]
  loadMore: []
  retry: []
}>()

const loadMoreTrigger = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

// Skeleton count mirrors the auto-fill grid via the same minCardWidth/gap
// formula — no breakpoint table to keep in sync with the CSS class.
const { count: skeletonCount, attachRef: root } = useSkeletonCount({
  minCardWidth: 280,   // matches --app-video-grid-min
  gap: 32,             // matches --app-video-grid-gap-y (2rem)
  cardHeight: 200,     // thumbnail + 2-line title + date
})

const displayDate = (item: RemoteSearchItem) => {
  if (item.published_text) return item.published_text
  if (!item.publish_date) return ''
  const date = new Date(item.publish_date)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString()
}

const resolveScrollRoot = () => props.scrollRoot || getMainScrollRoot()

const shouldLoadMore = () => {
  return props.items.length > 0 && !props.loading && !props.allLoaded && !props.error
}

const isTriggerVisible = () => {
  if (!loadMoreTrigger.value) return false
  const triggerRect = loadMoreTrigger.value.getBoundingClientRect()
  const root = resolveScrollRoot()
  if (!root) {
    return triggerRect.top <= window.innerHeight + 700
  }

  const rootRect = root.getBoundingClientRect()
  return triggerRect.top <= rootRect.bottom + 700
}

const requestMoreIfVisible = () => {
  if (shouldLoadMore() && isTriggerVisible()) {
    emit('loadMore')
  }
}

const bindObserver = async () => {
  observer?.disconnect()
  await nextTick()
  if (!loadMoreTrigger.value) return

  observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && shouldLoadMore()) {
      emit('loadMore')
    }
  }, {
    root: resolveScrollRoot(),
    rootMargin: '700px',
  })
  observer.observe(loadMoreTrigger.value)
}

watch(() => [props.items.length, props.loading, props.allLoaded, props.error], () => {
  nextTick(() => requestMoreIfVisible())
})

watch(() => props.scrollRoot, () => {
  bindObserver()
})

onMounted(() => {
  bindObserver()
})

onUnmounted(() => {
  observer?.disconnect()
})
</script>

<style scoped>
.remote-channel-video-card {
  display: flex;
  min-width: 0;
  cursor: pointer;
  flex-direction: column;
  gap: 0.625rem;
  border: 0;
  background: transparent;
  text-align: left;
}

.remote-channel-video-card:focus-visible {
  outline: none;
}

.remote-channel-video-thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border: 0;
  border-radius: var(--app-card-radius);
  background: var(--app-media-thumb-placeholder);
  isolation: isolate;
  transition: box-shadow var(--duration-base) var(--ease-default), filter var(--duration-fast) var(--ease-default);
}

.remote-channel-video-card:hover .remote-channel-video-thumb,
.remote-channel-video-card:focus-visible .remote-channel-video-thumb {
  /* Soft lift only — no amber outline ring (matches VideoItem). */
  box-shadow: var(--shadow-card-hover);
}

.remote-channel-video-card:focus-visible .remote-channel-video-thumb {
  box-shadow:
    0 0 0 2px hsl(var(--background)),
    0 0 0 4px hsl(var(--ring) / 0.45),
    var(--shadow-card-hover);
}

.remote-channel-video-title {
  display: -webkit-box;
  overflow: hidden;
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.3;
  transition: color var(--duration-fast) var(--ease-default);
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.group:hover .remote-channel-video-title {
  /* Media craft: title stays foreground — primary is for CTA/play only. */
  color: hsl(var(--foreground));
}

@media (prefers-reduced-motion: reduce) {
  .remote-channel-video-thumb,
  .remote-channel-video-title {
    transition: none;
  }
}
</style>
