<template>
  <AppPageShell class="home-view-page" variant="compact" :fill="false">
    <div class="app-page-content">

      <!-- Page header -->
      <div class="flex items-center justify-between px-6 pt-6 pb-2">
        <h1 class="text-2xl font-bold tracking-tight text-foreground/90">首页</h1>
        <button
          type="button"
          class="flex size-9 items-center justify-center rounded-full bg-muted/40 text-muted-foreground transition-colors hover:bg-muted/70 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          :class="{ 'animate-spin': isRefreshing }"
          title="刷新推荐"
          @click="refresh"
        >
          <AppIcon name="refresh" class="size-4" />
        </button>
      </div>

      <!-- Recommendation rows -->
      <SpotlightRow
        ref="spotlightRef"
        @openModal="handleOpenModal"
        @goToSubscription="goToChannelDetail"
      />
      <ContinueWatching
        ref="continueWatchingRef"
        @openModal="handleOpenModal"
        @viewMore="goToContinueWatching"
      />
      <SpecialFollowVideos
        ref="specialFollowRef"
        @openModal="handleOpenModal"
        @goToSubscription="goToChannelDetail"
        @viewMore="goToSpecialFollowVideos"
      />

      <!-- Empty state: all recommendation rows hide themselves when empty,
           so if nothing has rendered we offer a path to the full list. -->
      <div class="px-6 pb-10 pt-2 text-center">
        <button
          type="button"
          class="inline-flex h-9 items-center gap-1.5 rounded-full bg-primary/10 px-4 text-sm font-semibold text-primary transition-colors hover:bg-primary/20"
          @click="goToAllVideos"
        >
          浏览全部视频
          <AppIcon name="chevronRight" class="size-4" />
        </button>
      </div>
    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { onActivated, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import SpotlightRow from '@/components/feed/SpotlightRow.vue'
import ContinueWatching from '@/components/feed/ContinueWatching.vue'
import SpecialFollowVideos from '@/components/feed/SpecialFollowVideos.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import { rememberVideoPlaybackSeed } from '@/composables/videoPlaybackSeed'

// Home view: recommendation rows only. The full tabbed feed lives in VideosView (/videos).
defineOptions({ name: 'HomeView' })

const router = useRouter()

const spotlightRef = ref<any>(null)
const continueWatchingRef = ref<any>(null)
const specialFollowRef = ref<any>(null)
const isRefreshing = ref(false)

let lastRefreshedAt = 0

const handleOpenModal = (video: any) => {
  rememberVideoPlaybackSeed(video)
  router.push(`/video/${video.id}`)
}

const goToChannelDetail = (id: string) => router.push(`/subscription/${id}/all`)
const goToContinueWatching = () => router.push({ name: 'History', query: { mode: 'continue' } })
const goToSpecialFollowVideos = () => router.push({ name: 'AllVideos', query: { special: 'yes' } })
const goToAllVideos = () => router.push({ name: 'AllVideos' })

const refresh = () => {
  isRefreshing.value = true
  Promise.allSettled([
    spotlightRef.value?.refresh?.(),
    continueWatchingRef.value?.refresh?.(),
    specialFollowRef.value?.refresh?.(),
  ]).finally(() => {
    isRefreshing.value = false
    lastRefreshedAt = Date.now()
  })
}

// HomeView is kept-alive at the app root; refresh recommendation rows when
// returning to the home page, throttled to avoid hammering the API on rapid nav.
onActivated(() => {
  const now = Date.now()
  if (now - lastRefreshedAt < 30_000) return
  refresh()
})

onMounted(() => {
  // Initial load is handled by each row's onMounted; just stamp the timestamp.
  lastRefreshedAt = Date.now()
})
</script>

<style scoped>
.home-view-page {
  --app-page-max-width: 2400px;
}
</style>
