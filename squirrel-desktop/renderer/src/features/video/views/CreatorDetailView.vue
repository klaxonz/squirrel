<template>
  <AppPageShell class="creator-detail-page" variant="compact" surface="consume" width="media">
    <CreatorHeader
      ref="creatorHeaderRef"
      :creator-id="creatorId"
      @loaded="creatorDetail = $event"
    />

    <AppToolbarFrame sticky bordered variant="compact">
      <FeedToolbar
        :active-tab="activeTab"
        :nsfw="nsfw"
        :sort-by="sortBy"
        :special="special"
        :time-range="timeRange"
        :duration="duration"
        :content-type="contentType"
        :tabs="tabs"
        variant="workbench"
        :preference-key="`creator:${creatorId}`"
        :show-tabs="true"
        :show-sort="true"
        :show-filter="true"
        @update:activeTab="activeTab = $event"
        @update:nsfw="nsfw = $event"
        @update:sortBy="sortBy = $event"
        @update:timeRange="timeRange = $event"
        @update:duration="duration = $event"
        @update:content-type="contentType = $event"
        @update:special="setSpecialFilter"
      />
    </AppToolbarFrame>

    <div class="app-page-content app-page-content--media">
      <NewContentBar
        class="creator-detail-page__new-content"
        :visible="newContentVisible"
        :count="newContentCount"
        @apply="applyNewContent"
      />

      <div v-if="feedError">
        <AppEmptyState variant="error" title="创作者内容加载失败" :copy="feedError">
          <template #actions>
            <Button variant="outline" size="sm" @click="refreshContent">重试内容加载</Button>
          </template>
        </AppEmptyState>
      </div>

      <router-view v-slot="{ Component, route: childRoute }">
        <keep-alive :max="10">
          <component
            :is="Component"
            :key="childRoute.name"
            :filters="childFilters"
            presentation="workbench"
            interaction="open"
            ref="videoChildRef"
            @goToProfile="openProfile"
            @goToSubscription="openSubscription"
            @openModal="openVideo"
            @error="feedError = String($event || '')"
            @loaded="feedError = null"
            @loading-change="isRefreshing = !!$event"
          />
        </keep-alive>
      </router-view>
    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRouteTabSync } from '../composables/useRouteTabSync'
import { useFeedFilters } from '../composables/useFeedFilters'
import { useRefreshTriggers } from '../composables/useRefreshTriggers'
import FeedToolbar from '@/features/video/components/feed/FeedToolbar.vue'
import CreatorHeader from '@/features/video/components/feed/CreatorHeader.vue'
import NewContentBar from '@/shared/components/layout/NewContentBar.vue'
import { useNewContentDetector, prependPreservingScroll } from '@/shared/composables/useNewContentDetector'
import { getMainScrollRoot } from '@/shared/composables/useMainScrollRoot'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import type { VideoListItem } from '@/features/video/types/video'
import AppToolbarFrame from '@/shared/components/layout/AppToolbarFrame.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import { Button } from '@/shared/ui/button'
import { VIDEO_TABS } from '@/features/video/constants/videos'
import { useVideoCardNavigation } from '@/features/video/composables/useVideoCardNavigation'
import type { CreatorDetail } from '@/features/video/types/creator'

defineOptions({ name: 'CreatorDetailView' })

const router = useRouter()
const route = useRoute()
const { openVideo, openSubscription, openProfile } = useVideoCardNavigation(router)

const creatorId = computed(() => route.params.id as string)
const { activeTab, nsfw, sortBy, special, timeRange, duration, contentType, filters } = useFeedFilters({
  creatorIdRef: creatorId,
})

const tabs = ref(VIDEO_TABS)
const isRefreshing = ref(false)
const feedError = ref<string | null>(null)
const creatorHeaderRef = ref<{ refresh?: () => Promise<void> } | null>(null)
const videoChildRef = ref<{
  refresh?: () => void
  fetchTop?: (pageSize?: number) => Promise<VideoListItem[]>
  prependVideos?: (items: VideoListItem[]) => void
  getFirstId?: () => number | null
} | null>(null)
const creatorDetail = ref<CreatorDetail | null>(null)

const childFilters = computed(() => filters.value)

const refreshContent = () => {
  feedError.value = null
  return videoChildRef.value?.refresh?.()
}

const setSpecialFilter = (value: string) => {
  special.value = value === 'yes' ? 'yes' : 'all'
  const query = { ...route.query }
  if (special.value === 'yes') query.special = 'yes'
  else delete query.special
  router.replace({ query })
}

// Reddit-style new-content detection: silent probe surfaces the bar instead
// of replacing the list (see useNewContentDetector).
const {
  visible: newContentVisible,
  count: newContentCount,
  check: checkNewContent,
  apply: applyNewContent,
  reset: resetNewContent,
} = useNewContentDetector<VideoListItem>({
  getKnownId: () => videoChildRef.value?.getFirstId?.() ?? null,
  fetchNewest: () => videoChildRef.value?.fetchTop?.() ?? Promise.resolve([]),
  idOf: (item) => item.id,
  onApply: async (newItems) => {
    await prependPreservingScroll(getMainScrollRoot, () => {
      videoChildRef.value?.prependVideos?.(newItems)
    })
  },
  isEnabled: () => !!videoChildRef.value,
})

// R key / window-focus auto-refresh probes silently and surfaces the bar.
useRefreshTriggers({ onRefresh: checkNewContent })
useRouteTabSync(router, route, activeTab, undefined, creatorId)

watch(
  [creatorId, activeTab, nsfw, sortBy, timeRange, duration, contentType, special],
  resetNewContent,
)

watch(() => route.query.special, (value) => {
  special.value = value === 'yes' ? 'yes' : 'all'
}, { immediate: true })
</script>

<style scoped>
.creator-detail-page {
  --app-page-max-width: var(--app-content-media-max);
}

.creator-detail-page__new-content {
  margin-bottom: 0.75rem;
}
</style>
