<template>
  <AppPageShell class="channel-detail-page" variant="compact" surface="consume" width="media">
    <!-- Channel Header -->
    <ChannelHeader
      ref="channelHeaderRef"
      :subscription-id="subscriptionId"
      :mode="channelDataMode"
      @update:mode="handleChannelModeChange"
      @loaded="channelDetail = $event"
      @synced="handleChannelSynced"
    />

    <!-- Local-only toolbar: remote feed ignores sort/filter/tabs -->
    <AppToolbarFrame v-if="channelDataMode === 'local'" sticky bordered variant="compact">
      <FeedToolbar
        :active-tab="activeTab"
        :nsfw="nsfw"
        :sort-by="sortBy"
        :special="special"
        :time-range="timeRange"
        :duration="duration"
        :content-type="contentType"
        :subscription-id="subscriptionId"
        :tabs="tabs"
        variant="workbench"
        :preference-key="`subscription:${subscriptionId}`"
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
    <AppToolbarFrame v-else sticky bordered variant="compact">
      <div class="channel-remote-toolbar">
        <span class="channel-remote-toolbar__label">远端内容</span>
        <Button
          type="button"
          text variant="secondary"
          size="sm"
          :disabled="isRefreshing"
          @click="refreshCurrentList"
        >
          {{ isRefreshing ? '加载中' : '刷新' }}
        </Button>
      </div>
    </AppToolbarFrame>

    <!-- Main Content Area -->
    <div class="app-page-content app-page-content--media">

      <!-- Reddit-style new-content bar (local feed only; remote has its own
           operational re-fetch button in the toolbar above). -->
      <NewContentBar
        v-if="channelDataMode === 'local'"
        class="channel-detail-page__new-content"
        :visible="newContentVisible"
        :count="newContentCount"
        @apply="applyNewContent"
      />

      <!-- Error -->
      <div v-if="feedError">
        <AppEmptyState variant="error" title="频道内容加载失败" :copy="feedError">
          <template #actions>
            <Button variant="secondary" outlined size="sm" @click="refreshContent">重试内容加载</Button>
          </template>
        </AppEmptyState>
      </div>

      <!-- Remote mode: external channel grid -->
      <RemoteChannelVideoGrid
        v-if="channelDataMode === 'remote'"
        :items="remoteItems"
        :loading="remoteLoading"
        :all-loaded="remoteAllLoaded"
        :error="remoteError"
        @open="openRemoteResult"
        @load-more="loadMoreRemote"
      />

      <!-- Local mode: tabbed feed -->
      <router-view v-else v-slot="{ Component, route: childRoute }">
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
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRouteTabSync } from '../composables/useRouteTabSync'
import { useFeedFilters } from '../composables/useFeedFilters'
import { useRefreshTriggers } from '../composables/useRefreshTriggers'
import FeedToolbar from '@/features/video/components/feed/FeedToolbar.vue'
import ChannelHeader from '@/features/video/components/feed/ChannelHeader.vue'
import RemoteChannelVideoGrid from '@/features/video/components/feed/RemoteChannelVideoGrid.vue'
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
import { onSubscriptionRemoved } from '@/shared/lib/subscriptionEvents'
import { useRemoteChannel } from '@/features/video/composables/useRemoteChannel'
import { useRemoteVideoMapping } from '@/features/video/composables/useRemoteVideoMapping'
import type { SubscriptionListItem } from '@/features/video/types/subscription'

defineOptions({ name: 'ChannelDetailView' })

const router = useRouter()
const route = useRoute()
const { openVideo, openSubscription, openProfile } = useVideoCardNavigation(router)

const subscriptionId = computed(() => route.params.id as string)
const { activeTab, nsfw, sortBy, special, timeRange, duration, contentType, filters } = useFeedFilters({ subscriptionIdRef: subscriptionId })

const tabs = ref(VIDEO_TABS)
const isRefreshing = ref(false)
const feedError = ref<string | null>(null)
const channelHeaderRef = ref<{ refresh?: () => Promise<void> } | null>(null)
// ponytail: child component (VideoTab via router-view) shares a refresh() surface.
const videoChildRef = ref<{
  refresh?: () => void
  fetchTop?: (pageSize?: number) => Promise<VideoListItem[]>
  prependVideos?: (items: VideoListItem[]) => void
  getFirstId?: () => number | null
} | null>(null)

const channelDataMode = ref<'local' | 'remote'>('local')
// ponytail: minimal shape read across the view (site/url/profile); the full channel
// object is opaque from the child @loaded emit, only these keys are consumed.
type ChannelDetail = { site?: string; url?: string; [key: string]: unknown }
const channelDetail = ref<ChannelDetail | null>(null)

const remoteChannel = useRemoteChannel()
const {
  items: remoteItems,
  loading: remoteLoading,
  allLoaded: remoteAllLoaded,
  error: remoteError,
} = remoteChannel
const loadMoreRemote = () => {
  const channel = channelDetail.value
  if (!channel?.site || !channel?.url) return
  return remoteChannel.loadMore({ site: channel.site, url: channel.url, profile: channel })
}
let loadedRemoteChannelKey = ''

// ponytail: remote-video → playback-seed mapping + playability gating live in
// useRemoteVideoMapping (shared with Subscribed.vue). channelDetail is read as
// the active channel; its opaque shape carries the id/name/url/avatar/is_nsfw
// fields the seed synthesiser needs.
const { openRemoteResult } = useRemoteVideoMapping({
  activeChannel: computed(() => channelDetail.value as unknown as SubscriptionListItem | null),
})

const childFilters = computed(() => filters.value)
const remoteChannelKey = computed(() => {
  const channel = channelDetail.value
  return channel ? `${channel.site || ''}::${channel.url || ''}` : ''
})

const refreshContent = () => {
  feedError.value = null
  if (channelDataMode.value === 'remote') return fetchRemoteChannel(true)
  return videoChildRef.value?.refresh?.()
}

const refreshCurrentList = () => {
  void channelHeaderRef.value?.refresh?.()
  return refreshContent()
}

const handleChannelSynced = () => {
  if (channelDataMode.value === 'remote') {
    channelDataMode.value = 'local'
  }
  refreshCurrentList()
}

const setSpecialFilter = (value: string) => {
  special.value = value === 'yes' ? 'yes' : 'all'
  const query = { ...route.query }
  if (special.value === 'yes') query.special = 'yes'
  else delete query.special
  router.replace({ query })
}

// Reddit-style new-content detection for the local subscription feed.
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
  isEnabled: () => channelDataMode.value === 'local' && !!videoChildRef.value,
})

// R key / window-focus auto-refresh probes silently in local mode; remote
// mode keeps the explicit re-fetch behaviour.
useRefreshTriggers({
  onRefresh: () => {
    if (channelDataMode.value === 'remote') refreshCurrentList()
    else checkNewContent()
  },
})
useRouteTabSync(router, route, activeTab, subscriptionId)

watch(
  [subscriptionId, activeTab, nsfw, sortBy, timeRange, duration, contentType, special, channelDataMode],
  resetNewContent,
)

const handleChannelModeChange = async (mode: 'local' | 'remote') => {
  channelDataMode.value = mode
  if (mode === 'remote' && loadedRemoteChannelKey !== remoteChannelKey.value) {
    await fetchRemoteChannel(true)
  }
}

const fetchRemoteChannel = async (isReset = false) => {
  const channel = channelDetail.value
  if (!channel?.site || !channel?.url) return

  if (isReset) {
    loadedRemoteChannelKey = remoteChannelKey.value
  }

  isRefreshing.value = true
  await remoteChannel.fetchRemote({ site: channel.site, url: channel.url, profile: channel }, isReset)
  isRefreshing.value = false
}

watch(remoteChannelKey, () => {
  loadedRemoteChannelKey = ''
  if (channelDataMode.value === 'remote') fetchRemoteChannel(true)
})

watch(() => route.query.special, (value) => {
  special.value = value === 'yes' ? 'yes' : 'all'
}, { immediate: true })

onMounted(() => {
  onSubscriptionRemoved(({ subscriptionId: removedId }) => {
    if (String(route.params.id || '') === String(removedId)) router.replace({ name: 'AllVideos' })
  })
})
</script>

<style scoped>
.channel-detail-page {
  --app-page-max-width: var(--app-content-media-max);
}

.channel-detail-page__new-content {
  margin-bottom: 0.75rem;
}

.channel-remote-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  min-height: 2.25rem;
  padding-inline: 0.125rem;
}

.channel-remote-toolbar__label {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-md);
  font-weight: 500;
}
</style>
