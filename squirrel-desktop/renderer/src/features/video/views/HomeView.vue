<template>
  <AppPageShell class="home-workbench" variant="compact" surface="consume" width="fluid">
    <div class="home-workbench__page">
      <header class="home-workbench__context-bar">
        <div class="home-workbench__context">
          <time>{{ todayLabel }}</time>
          <span>订阅动态与未完成内容</span>
        </div>
        <div class="home-workbench__actions">
          <RouterLink to="/subscribed">管理订阅</RouterLink>
          <Button text severity="secondary" size="sm" icon-only title="刷新首页" aria-label="刷新首页" @click="refresh">
            <AppIcon name="refresh" class="size-4" />
          </Button>
        </div>
      </header>

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
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { useVideoCardNavigation } from '@/features/video/composables/useVideoCardNavigation'

defineOptions({ name: 'HomeView' })

const router = useRouter()
const { openVideo, openSubscription, openProfile } = useVideoCardNavigation(router)
const todayLabel = new Intl.DateTimeFormat('zh-CN', {
  month: 'long',
  day: 'numeric',
  weekday: 'short',
}).format(new Date())

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

.home-workbench__context-bar,
.home-workbench__context,
.home-workbench__actions {
  display: flex;
  align-items: center;
}

.home-workbench__context-bar {
  min-height: 3rem;
  justify-content: space-between;
  gap: 1.5rem;
  border-bottom: 1px solid var(--app-hairline);
}

.home-workbench__context {
  min-width: 0;
  gap: var(--space-2);
}

.home-workbench__context time {
  color: hsl(var(--foreground));
  font-size: 0.75rem;
  font-weight: 650;
}

.home-workbench__context span {
  border-left: 1px solid var(--app-hairline);
  padding-left: var(--space-2);
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
}

.home-workbench__actions {
  gap: 0.375rem;
}

.home-workbench__actions a {
  border-radius: var(--radius-sm);
  padding: 0.45rem 0.625rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 580;
  text-decoration: none;
}

.home-workbench__actions a:hover {
  background: hsl(var(--accent) / 0.58);
  color: hsl(var(--foreground));
}

.home-workbench__content {
  display: grid;
  gap: 2.5rem;
  padding-top: 0.5rem;
}
</style>
