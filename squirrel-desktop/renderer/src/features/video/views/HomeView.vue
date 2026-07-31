<template>
  <AppPageShell class="home-feed" variant="compact" surface="consume" width="fluid">
    <div class="home-feed__page">
      <main class="home-feed__main" aria-label="首页信息流">
        <div class="home-feed__sort">
          <div class="home-feed__sort-chips" role="tablist" aria-label="排序">
            <button type="button" class="home-feed__chip is-active" role="tab" aria-selected="true">
              最新
            </button>
          </div>
          <Button
            text
            severity="secondary"
            size="sm"
            class="home-feed__sort-refresh"
            title="刷新"
            aria-label="刷新首页"
            @click="refresh"
          >
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
        <section class="home-feed__widget home-feed__widget--nav">
          <header class="home-feed__widget-head">
            <h2>快捷入口</h2>
          </header>
          <div class="home-feed__widget-links">
            <button type="button" class="home-feed__widget-link" @click="goToAllVideos">
              <span class="home-feed__widget-icon" aria-hidden="true">
                <AppIcon name="film" class="size-4" />
              </span>
              <span class="home-feed__widget-copy">
                <strong>视频库</strong>
                <small>全部 / 未读 / 稍后看</small>
              </span>
              <AppIcon name="chevronRight" class="home-feed__widget-chevron size-3.5" />
            </button>
            <button type="button" class="home-feed__widget-link" @click="goToContinueWatching">
              <span class="home-feed__widget-icon" aria-hidden="true">
                <AppIcon name="history" class="size-4" />
              </span>
              <span class="home-feed__widget-copy">
                <strong>继续观看</strong>
                <small>未看完的播放进度</small>
              </span>
              <AppIcon name="chevronRight" class="home-feed__widget-chevron size-3.5" />
            </button>
            <button type="button" class="home-feed__widget-link" @click="goToSubscribed">
              <span class="home-feed__widget-icon" aria-hidden="true">
                <AppIcon name="subscriptions" class="size-4" />
              </span>
              <span class="home-feed__widget-copy">
                <strong>订阅中心</strong>
                <small>管理多站频道</small>
              </span>
              <AppIcon name="chevronRight" class="home-feed__widget-chevron size-3.5" />
            </button>
            <button type="button" class="home-feed__widget-link" @click="goToPlaylists">
              <span class="home-feed__widget-icon" aria-hidden="true">
                <AppIcon name="playlists" class="size-4" />
              </span>
              <span class="home-feed__widget-copy">
                <strong>播放列表</strong>
                <small>整理合集与队列</small>
              </span>
              <AppIcon name="chevronRight" class="home-feed__widget-chevron size-3.5" />
            </button>
          </div>
        </section>

        <section class="home-feed__widget home-feed__widget--tips">
          <header class="home-feed__widget-head">
            <h2>信息流说明</h2>
          </header>
          <ul class="home-feed__tips">
            <li>
              <span class="home-feed__tip-mark" aria-hidden="true">1</span>
              <span>按订阅同步时间排列新内容</span>
            </li>
            <li>
              <span class="home-feed__tip-mark" aria-hidden="true">2</span>
              <span>点卡片进入播放，底栏可喜欢 / 已读 / 稍后看</span>
            </li>
            <li>
              <span class="home-feed__tip-mark" aria-hidden="true">3</span>
              <span>右上搜索支持本地库与远端检索</span>
            </li>
          </ul>
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
const goToPlaylists = () => router.push({ name: 'Playlists' })

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
/*
  Delivery geometry:
  - post column + right rail form one band
  - band is centered in the workspace on wide screens (Reddit-like)
  - posts cap at readable measure; rail fixed
*/
.home-feed__page {
  display: grid;
  width: 100%;
  max-width: none;
  margin-inline: 0;
  grid-template-columns: minmax(0, 1fr);
  gap: 1.25rem;
  padding: 0.85rem var(--app-content-media-gutter) 3rem;
}

@media (min-width: 1100px) {
  .home-feed__page {
    grid-template-columns: minmax(22rem, 42rem) 19.5rem;
    justify-content: center;
    align-items: start;
    column-gap: 1.5rem;
  }
}

@media (min-width: 1400px) {
  .home-feed__page {
    grid-template-columns: minmax(28rem, 48rem) 20rem;
  }
}

@media (min-width: 1800px) {
  .home-feed__page {
    grid-template-columns: minmax(32rem, 52rem) 20.5rem;
  }
}

.home-feed__main {
  display: flex;
  min-width: 0;
  width: 100%;
  max-width: none;
  flex-direction: column;
  gap: 0.9rem;
}

.home-feed__sort {
  display: flex;
  min-height: 2.35rem;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.15rem 0.15rem 0.1rem;
}

.home-feed__sort-chips {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.15rem;
  border-radius: 999px;
  background: hsl(var(--foreground) / 0.04);
}

.home-feed__chip {
  height: 1.85rem;
  border: 0;
  border-radius: 999px;
  padding: 0 0.9rem;
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    box-shadow var(--duration-fast) var(--ease-default);
}

.home-feed__chip.is-active {
  background: hsl(var(--card));
  color: hsl(var(--foreground));
  box-shadow: var(--shadow-xs), 0 0 0 1px hsl(var(--border) / 0.55);
}

.home-feed__chip:hover:not(.is-active) {
  color: hsl(var(--foreground));
}

.home-feed__sort-refresh {
  color: hsl(var(--muted-foreground));
}

.home-feed__rail {
  display: none;
  min-width: 0;
  flex-direction: column;
  gap: 0.85rem;
}

@media (min-width: 1100px) {
  .home-feed__rail {
    display: flex;
    position: sticky;
    top: 0.85rem;
  }
}

.home-feed__widget {
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.9);
  border-radius: var(--radius-lg);
  background: hsl(var(--card));
  box-shadow: var(--app-surface-shadow);
  padding: 0.8rem 0.75rem;
}

.home-feed__widget-head h2 {
  margin: 0 0 0.55rem;
  font-size: 0.8125rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.home-feed__widget-links {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.home-feed__widget-link {
  display: grid;
  min-height: 2.85rem;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.7rem;
  border: 0;
  border-radius: var(--radius-md);
  padding: 0.4rem 0.45rem;
  background: transparent;
  color: hsl(var(--foreground));
  text-align: left;
  cursor: pointer;
  transition: background-color var(--duration-fast) var(--ease-default);
}

.home-feed__widget-link:hover {
  background: hsl(var(--foreground) / 0.05);
}

.home-feed__widget-link:hover .home-feed__widget-chevron {
  color: hsl(var(--foreground));
  transform: translateX(1px);
}

.home-feed__widget-icon {
  display: inline-flex;
  width: 2.05rem;
  height: 2.05rem;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: hsl(var(--secondary));
  color: hsl(var(--foreground));
  box-shadow: inset 0 0 0 1px hsl(var(--border) / 0.55);
}

.home-feed__widget-copy {
  display: grid;
  min-width: 0;
  gap: 0.12rem;
}

.home-feed__widget-copy strong {
  font-size: 0.8125rem;
  font-weight: 700;
  line-height: 1.2;
}

.home-feed__widget-copy small {
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 500;
  line-height: 1.3;
}

.home-feed__widget-chevron {
  color: hsl(var(--muted-foreground) / 0.75);
  transition:
    color var(--duration-fast) var(--ease-default),
    transform var(--duration-fast) var(--ease-default);
}

.home-feed__tips {
  display: grid;
  gap: 0.55rem;
  margin: 0;
  padding: 0;
  list-style: none;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  line-height: 1.45;
}

.home-feed__tips li {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.55rem;
  align-items: start;
}

.home-feed__tip-mark {
  display: inline-flex;
  width: 1.15rem;
  height: 1.15rem;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: hsl(var(--foreground) / 0.06);
  color: hsl(var(--foreground) / 0.72);
  font-size: 0.625rem;
  font-weight: 700;
  line-height: 1;
}

@media (prefers-reduced-motion: reduce) {
  .home-feed__chip,
  .home-feed__widget-link,
  .home-feed__widget-chevron {
    transition: none;
  }
}
</style>
