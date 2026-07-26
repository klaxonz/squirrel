<template>
  <AppPageShell class="home-feed" variant="compact" surface="consume" width="fluid">
    <div class="home-feed__page">
      <main class="home-feed__main" aria-label="首页信息流">
        <div class="home-feed__sort">
          <span class="home-feed__sort-label">最新</span>
          <Button text severity="secondary" size="sm" class="home-feed__sort-refresh" @click="refresh">
            <AppIcon name="refresh" class="size-3.5" />
            刷新
          </Button>
        </div>

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

      <aside class="home-feed__rail" aria-label="辅助信息">
        <section class="home-feed__widget">
          <header class="home-feed__widget-head">
            <h2>快捷入口</h2>
          </header>
          <div class="home-feed__widget-links">
            <button type="button" class="home-feed__widget-link" @click="goToAllVideos">全部视频</button>
            <button type="button" class="home-feed__widget-link" @click="goToContinueWatching">继续观看</button>
            <button type="button" class="home-feed__widget-link" @click="goToSubscribed">订阅中心</button>
          </div>
        </section>
        <section class="home-feed__widget home-feed__widget--muted">
          <p>信息流按订阅同步时间排列。点开卡片即可播放；喜欢 / 稍后看在帖子底部。</p>
        </section>
      </aside>
    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { onActivated, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import ContinueWatching from '@/features/video/components/feed/ContinueWatching.vue'
import HomeInbox from '@/features/video/components/feed/HomeInbox.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { useVideoCardNavigation } from '@/features/video/composables/useVideoCardNavigation'

defineOptions({ name: 'HomeView' })

const router = useRouter()
const { openVideo, openSubscription, openProfile } = useVideoCardNavigation(router)

const continueWatchingRef = ref<{ refresh?: () => void } | null>(null)
const homeInboxRef = ref<{ refresh?: () => void } | null>(null)
let lastRefreshedAt = 0

const goToContinueWatching = () => router.push({ name: 'History', query: { mode: 'continue' } })
const goToAllVideos = () => router.push({ name: 'AllVideos' })
const goToSubscribed = () => router.push({ name: 'Subscribed' })

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
.home-feed {
  background: hsl(var(--background));
}

/* Reddit home: main post column + right widgets on gray canvas. */
.home-feed__page {
  display: grid;
  width: 100%;
  max-width: 72rem;
  margin-inline: auto;
  grid-template-columns: minmax(0, 1fr);
  gap: 1.5rem;
  padding: 1rem var(--app-content-media-gutter) 3rem;
}

@media (min-width: 1100px) {
  .home-feed__page {
    grid-template-columns: minmax(0, 1fr) 20rem;
    align-items: start;
  }
}

.home-feed__main {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.75rem;
}

.home-feed__sort {
  display: flex;
  min-height: 2.5rem;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  background: hsl(var(--card));
  padding: 0.375rem 0.75rem;
}

.home-feed__sort-label {
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  font-weight: 700;
}

.home-feed__rail {
  display: none;
  min-width: 0;
  flex-direction: column;
  gap: 0.75rem;
}

@media (min-width: 1100px) {
  .home-feed__rail {
    display: flex;
    position: sticky;
    top: 0.75rem;
  }
}

.home-feed__widget {
  overflow: hidden;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  background: hsl(var(--card));
  padding: 0.875rem;
}

.home-feed__widget-head h2 {
  margin: 0 0 0.625rem;
  font-size: 0.875rem;
  font-weight: 700;
}

.home-feed__widget-links {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.home-feed__widget-link {
  display: flex;
  min-height: 2rem;
  align-items: center;
  border: 0;
  border-radius: var(--radius-md);
  padding: 0 0.5rem;
  background: transparent;
  color: hsl(var(--foreground));
  font-size: 0.8125rem;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
}

.home-feed__widget-link:hover {
  background: hsl(var(--foreground) / 0.06);
}

.home-feed__widget--muted p {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  line-height: 1.5;
}
</style>
