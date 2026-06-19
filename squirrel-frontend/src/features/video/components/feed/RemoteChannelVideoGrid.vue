<template>
  <div ref="root" class="space-y-6">
    <div v-if="error" class="rounded-lg border border-destructive/20 bg-destructive/5 p-4">
      <p class="text-sm font-medium text-destructive">{{ error }}</p>
    </div>

    <div v-if="!items.length && !loading && !error" class="min-h-[24rem]">
      <AppEmptyState variant="plain" icon="inbox" title="暂无远端内容" copy="源站频道暂时没有返回视频。" />
    </div>

    <div v-if="items.length" class="grid grid-cols-1 gap-x-5 gap-y-8 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 3xl:grid-cols-5">
      <button
        v-for="item in items"
        :key="item.site + ':' + item.url"
        type="button"
        class="group flex min-w-0 cursor-pointer flex-col gap-2.5 text-left"
        @click="$emit('open', item)"
      >
        <div class="relative aspect-video overflow-hidden rounded-sm bg-muted transition-colors group-hover:brightness-110">
          <VideoThumbnail :src="item.thumbnail" :alt="item.title" />
          <span v-if="item.duration" class="absolute bottom-1.5 right-1.5 inline-flex h-5 items-center rounded-md bg-black/65 px-1.5 text-[10px] font-medium tabular-nums text-white backdrop-blur-sm">
            {{ formatDuration(item.duration) }}
          </span>
        </div>

        <div class="flex min-w-0 flex-col gap-1 px-0.5">
          <h3 class="line-clamp-2 text-[14px] font-semibold leading-[1.3] tracking-tight text-foreground/90 transition-colors group-hover:text-primary">
            {{ item.title }}
          </h3>
          <div class="text-[11px] font-medium text-muted-foreground/50">
            {{ displayDate(item) }}
          </div>
        </div>
      </button>
    </div>

    <div v-if="loading" class="grid grid-cols-1 gap-x-5 gap-y-8 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 3xl:grid-cols-5">
      <VideoSkeleton v-for="i in skeletonCount" :key="i" />
    </div>

    <div v-if="items.length && !allLoaded" class="flex justify-center py-4">
      <Button variant="outline" class="h-9 rounded-md" :disabled="loading" @click="$emit('loadMore')">
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
import { useSkeletonCount, type GridBreakpoint } from '@/features/video/composables/useSkeletonCount'
import { formatDuration } from '@/shared/lib/dateFormat'

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
}>()

const loadMoreTrigger = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

// --- Adaptive skeleton count ----------------------------------------------
// Mirrors `grid-cols-1 sm:2 xl:3 2xl:4 3xl:5` on the grid container.
const GRID_BREAKPOINTS: GridBreakpoint[] = [
  [1920, 5], // 3xl
  [1536, 4], // 2xl
  [1280, 3], // xl
  [640, 2],  // sm
  [0, 1],    // base
]
const { count: skeletonCount, attachRef: root } = useSkeletonCount({
  breakpoints: GRID_BREAKPOINTS,
  cardHeight: 200, // thumbnail + 2-line title + date
  rowGap: 32,      // matches `gap-y-8` (2rem ≈ 32px)
})

const displayDate = (item: RemoteSearchItem) => {
  if (item.published_text) return item.published_text
  if (!item.publish_date) return ''
  const date = new Date(item.publish_date)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString()
}

const resolveScrollRoot = () => {
  return props.scrollRoot || document.getElementById('app-main-scroll') || null
}

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
