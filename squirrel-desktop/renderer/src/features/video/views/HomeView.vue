<template>
  <AppPageShell class="home-view-page" variant="compact" surface="consume" width="media">
    <div class="app-page-content app-page-content--media home-page-content">
      <header class="home-page-header">
        <div>
          <p class="home-page-header__eyebrow">媒体工作台</p>
          <h1 class="home-page-header__title">首页</h1>
        </div>
        <p>继续上次的播放，浏览订阅源新内容。</p>
      </header>
      <div class="home-dashboard" aria-label="首页内容">
        <div class="home-rails">
          <ContinueWatching
            ref="continueWatchingRef"
            @openModal="openVideo"
            @viewMore="goToContinueWatching"
            @goToProfile="openProfile"
            @goToSubscription="openSubscription"
          />
          <SpecialFollowVideos
            ref="specialFollowRef"
            @openModal="openVideo"
            @goToProfile="openProfile"
            @goToSubscription="openSubscription"
            @viewMore="goToAllVideos"
          />
          <FeaturedVideos
            ref="featuredRef"
            @openModal="openVideo"
            @goToProfile="openProfile"
            @goToSubscription="openSubscription"
            @viewMore="goToAllVideos"
          />
        </div>
      </div>
    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { onActivated, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import ContinueWatching from '@/features/video/components/feed/ContinueWatching.vue'
import SpecialFollowVideos from '@/features/video/components/feed/SpecialFollowVideos.vue'
import FeaturedVideos from '@/features/video/components/feed/FeaturedVideos.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import { useVideoCardNavigation } from '@/features/video/composables/useVideoCardNavigation'

defineOptions({ name: 'HomeView' })

const router = useRouter()
const { openVideo, openSubscription, openProfile } = useVideoCardNavigation(router)

const continueWatchingRef = ref<{ refresh?: () => void } | null>(null)
const specialFollowRef = ref<{ refresh?: () => void } | null>(null)
const featuredRef = ref<{ refresh?: () => void } | null>(null)

let lastRefreshedAt = 0

const goToContinueWatching = () => router.push({ name: 'History', query: { mode: 'continue' } })
const goToAllVideos = () => router.push({ name: 'AllVideos' })

const refresh = () => {
  Promise.allSettled([
    continueWatchingRef.value?.refresh?.(),
    specialFollowRef.value?.refresh?.(),
    featuredRef.value?.refresh?.(),
  ]).finally(() => {
    lastRefreshedAt = Date.now()
  })
}

// keep-alive: refresh rails when returning home, throttled against rapid nav.
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
.home-page-content {
  position: relative;
  padding-top: var(--space-5);
  padding-bottom: var(--space-8);
}

.home-dashboard {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.home-page-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: var(--space-5);
  margin-bottom: var(--space-5);
}

.home-page-header__eyebrow {
  margin: 0 0 0.25rem !important;
  color: hsl(var(--primary)) !important;
  font-size: 0.6875rem !important;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.home-page-header__title {
  margin: 0;
  color: hsl(var(--foreground));
  font-family: var(--app-heading-font);
  font-size: var(--app-h1-size);
  font-weight: var(--app-h1-weight);
  line-height: var(--app-h1-leading);
  letter-spacing: var(--app-h1-tracking);
}

.home-page-header p {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-secondary-size);
}

.home-page-header > p {
  max-width: 24rem;
  padding-bottom: 0.2rem;
  text-align: right;
}

.home-rails {
  display: grid;
  gap: var(--space-6);
  min-width: 0;
}

:deep(.home-feed-rail) {
  min-width: 0;
  margin: 0;
  padding: 0;
  overflow: visible;
}

:deep(.home-feed-rail + .featured-workspace) {
  margin-top: 0;
}

</style>
