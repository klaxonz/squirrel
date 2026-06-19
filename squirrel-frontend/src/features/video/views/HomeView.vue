<template>
  <AppPageShell class="home-view-page" variant="compact" :fill="false">
    <div class="app-page-content">

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
        @goToSubscription="goToChannelDetail"
      />
      <SpecialFollowVideos
        ref="specialFollowRef"
        @openModal="handleOpenModal"
        @goToSubscription="goToChannelDetail"
        @viewMore="goToSpecialFollowVideos"
      />
    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { onActivated, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import SpotlightRow from '@/features/video/components/feed/SpotlightRow.vue'
import ContinueWatching from '@/features/video/components/feed/ContinueWatching.vue'
import SpecialFollowVideos from '@/features/video/components/feed/SpecialFollowVideos.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'

// Home view: recommendation rows only. The full tabbed feed lives in VideosView (/videos).
defineOptions({ name: 'HomeView' })

const router = useRouter()

// ponytail: feed rows share a refresh() surface via defineExpose; minimal interface
// avoids coupling the parent to specific component instances.
const spotlightRef = ref<{ refresh?: () => void } | null>(null)
const continueWatchingRef = ref<{ refresh?: () => void } | null>(null)
const specialFollowRef = ref<{ refresh?: () => void } | null>(null)

let lastRefreshedAt = 0

const handleOpenModal = (video: { id: string | number }) => {
  rememberVideoPlaybackSeed(video)
  router.push(`/video/${video.id}`)
}

const goToChannelDetail = (id: string) => router.push(`/subscription/${id}/all`)
const goToContinueWatching = () => router.push({ name: 'History', query: { mode: 'continue' } })
const goToSpecialFollowVideos = () => router.push({ name: 'AllVideos', query: { special: 'yes' } })

const refresh = () => {
  Promise.allSettled([
    spotlightRef.value?.refresh?.(),
    continueWatchingRef.value?.refresh?.(),
    specialFollowRef.value?.refresh?.(),
  ]).finally(() => {
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
