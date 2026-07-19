<template>
  <AppPageShell class="home-workbench" variant="compact" surface="consume" width="fluid">
    <div class="home-workbench__page">
      <main class="home-workbench__content" aria-label="首页内容">
        <ContinueWatching
          ref="continueWatchingRef"
          @openModal="openVideo"
          @viewMore="goToContinueWatching"
          @goToProfile="openProfile"
          @goToSubscription="openSubscription"
        />
        <HomeInbox
          ref="homeInboxRef"
          @openModal="openVideo"
          @goToProfile="openProfile"
          @goToSubscription="openSubscription"
          @viewMore="goToAllVideos"
          @refresh="refresh"
        />
      </main>
    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { onActivated, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import ContinueWatching from '@/features/video/components/feed/ContinueWatching.vue'
import HomeInbox from '@/features/video/components/feed/HomeInbox.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import { useVideoCardNavigation } from '@/features/video/composables/useVideoCardNavigation'

defineOptions({ name: 'HomeView' })

const router = useRouter()
const { openVideo, openSubscription, openProfile } = useVideoCardNavigation(router)

const continueWatchingRef = ref<{ refresh?: () => void } | null>(null)
const homeInboxRef = ref<{ refresh?: () => void } | null>(null)
let lastRefreshedAt = 0

const goToContinueWatching = () => router.push({ name: 'History', query: { mode: 'continue' } })
const goToAllVideos = () => router.push({ name: 'AllVideos' })

const refresh = () => {
  Promise.allSettled([
    continueWatchingRef.value?.refresh?.(),
    homeInboxRef.value?.refresh?.(),
  ]).finally(() => {
    lastRefreshedAt = Date.now()
  })
}

onActivated(() => {
  const now = Date.now()
  if (now - lastRefreshedAt < 30_000) return
  refresh()
})

onMounted(() => {
  lastRefreshedAt = Date.now()
})
</script>

<style scoped>
.home-workbench {
  background: hsl(var(--background));
}

.home-workbench__page {
  width: min(100%, 106rem);
  margin-inline: auto;
  padding: 1.5rem clamp(1.25rem, 2.5vw, 2.5rem) 4rem;
}

.home-workbench__content {
  display: grid;
  gap: 2.5rem;
}
</style>
