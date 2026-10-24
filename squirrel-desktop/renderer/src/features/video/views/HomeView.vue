<template>
  <AppPageShell class="home-feed" variant="compact" surface="consume" width="browse">
    <header class="app-page-heading">
      <AppOperatePageHeader title="首页" summary="订阅收件箱" size="lg" />
    </header>

    <AppToolbarFrame bordered compact boundary="browse" divider="content" sticky>
      <div class="home-feed__toolbar">
        <AppSectionNav
          :model-value="activeFilter"
          :options="HOME_INBOX_FILTER_OPTIONS"
          aria-label="首页内容范围"
          @change="setFilter"
        />
        <Button variant="ghost" size="sm" class="home-feed__view-all" @click="goToAllVideos">
          全部视频
          <AppIcon name="chevronRight" class="size-3.5" />
        </Button>
      </div>
    </AppToolbarFrame>

    <main class="home-feed__main" aria-label="首页信息流">
      <NewContentBar
        class="home-feed__new-content"
        :visible="newContentVisible"
        :count="newContentCount"
        @apply="applyNewContent"
      />

      <ContinueWatching
        ref="continueWatchingRef"
        compact
        @openModal="openVideo"
        @viewMore="goToContinueWatching"
        @goToProfile="openProfile"
        @goToSubscription="openSubscription"
      />

      <HomeInbox
        ref="homeInboxRef"
        :filter="activeFilter"
        @openModal="openVideo"
        @goToProfile="openProfile"
        @goToSubscription="openSubscription"
      />
    </main>
  </AppPageShell>
</template>

<script setup lang="ts">
import { onActivated, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ContinueWatching from '@/features/video/components/feed/ContinueWatching.vue'
import HomeInbox from '@/features/video/components/feed/HomeInbox.vue'
import NewContentBar from '@/shared/components/layout/NewContentBar.vue'
import { useNewContentDetector, prependPreservingScroll } from '@/shared/composables/useNewContentDetector'
import { getMainScrollRoot } from '@/shared/composables/useMainScrollRoot'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppToolbarFrame from '@/shared/components/layout/AppToolbarFrame.vue'
import AppOperatePageHeader from '@/shared/components/layout/AppOperatePageHeader.vue'
import AppSectionNav from '@/shared/components/layout/AppSectionNav.vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { HOME_INBOX_FILTER_OPTIONS, type HomeInboxFilter } from '@/features/video/constants/homeInbox'
import { useVideoCardNavigation } from '@/features/video/composables/useVideoCardNavigation'
import type { VideoListItem } from '@/features/video/types/video'

defineOptions({ name: 'HomeView' })

const router = useRouter()
const { openVideo, openSubscription, openProfile } = useVideoCardNavigation(router)

const activeFilter = ref<HomeInboxFilter>('all')
const setFilter = (value: string | number) => {
  if (value === 'all' || value === 'unread' || value === 'special') activeFilter.value = value
}

const continueWatchingRef = ref<{ refresh?: () => void } | null>(null)
const homeInboxRef = ref<{
  refresh?: () => void
  loadTop?: () => Promise<VideoListItem[]>
  prepend?: (items: VideoListItem[]) => void
  getFirstId?: () => number | null
} | null>(null)
let lastRefreshedAt = 0

const goToContinueWatching = () => router.push({ name: 'History', query: { mode: 'continue' } })
const goToAllVideos = () => router.push({ name: 'AllVideos' })

// A quiet probe compares the newest page against what is displayed and surfaces
// a bar; applying prepends new items without reloading the page.
const {
  visible: newContentVisible,
  count: newContentCount,
  check: checkNewContent,
  apply: applyNewContent,
  reset: resetNewContent,
} = useNewContentDetector<VideoListItem>({
  getKnownId: () => homeInboxRef.value?.getFirstId?.() ?? null,
  fetchNewest: () => homeInboxRef.value?.loadTop?.() ?? Promise.resolve([]),
  idOf: (item) => item.id,
  onApply: async (newItems) => {
    await prependPreservingScroll(getMainScrollRoot, () => {
      homeInboxRef.value?.prepend?.(newItems)
    })
    // Keep the continue-watching rail in step with the newly surfaced content.
    void continueWatchingRef.value?.refresh?.()
  },
})

onActivated(() => {
  const now = Date.now()
  if (now - lastRefreshedAt < 30_000) return
  lastRefreshedAt = now
  checkNewContent()
})

onMounted(() => {
  lastRefreshedAt = Date.now()
})

// The inbox filter switch rebuilds the list — pending detection is stale then.
watch(activeFilter, () => resetNewContent())
</script>

<style scoped>
.home-feed { background: hsl(var(--background)); }

.home-feed__toolbar {
  display: flex;
  min-width: 0;
  min-height: 2.75rem;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.home-feed__view-all {
  flex: 0 0 auto;
  gap: 0.2rem;
  padding-inline: 0.25rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  font-weight: 500;
}

.home-feed__view-all:hover {
  background: transparent;
  color: hsl(var(--foreground));
}

.home-feed__main {
  display: flex;
  width: 100%;
  max-width: var(--app-content-browse-max);
  min-width: 0;
  margin-inline: auto;
  flex-direction: column;
  gap: var(--app-section-gap);
  padding: var(--space-5) var(--app-page-gutter) var(--space-9);
}

.home-feed__new-content { margin-bottom: calc(var(--space-3) * -1); }

@media (max-width: 640px) {
  .home-feed__main {
    gap: var(--space-5);
    padding: var(--space-3) var(--space-3) var(--space-8);
  }
}
</style>
