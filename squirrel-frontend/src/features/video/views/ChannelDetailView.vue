<template>
  <AppPageShell class="channel-detail-page" variant="compact" :fill="false">
    <!-- Channel Header -->
    <ChannelHeader
      :subscription-id="subscriptionId"
      :mode="channelDataMode"
      @update:mode="handleChannelModeChange"
      @loaded="channelDetail = $event"
      @synced="handleChannelSynced"
    />

    <!-- Main Content Area -->
    <div class="app-page-content">

      <!-- Persistent Sticky Toolbar (always visible, zero-flicker) -->
      <div class="sticky top-0 z-20 -mx-6 px-6 py-2 bg-background/95 backdrop-blur border-b border-border/10">
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
          :is-refreshing="isRefreshing"
          :show-tabs="true"
          :show-sort="true"
          :show-filter="true"
          @update:activeTab="activeTab = $event"
          @update:nsfw="nsfw = $event"
          @update:sortBy="sortBy = $event"
          @update:time-range="timeRange = $event"
          @update:duration="duration = $event"
          @update:content-type="contentType = $event"
          @update:special="setSpecialFilter"
          @refresh="refreshCurrentList"
        />
      </div>

      <!-- Error -->
      <div v-if="loadError" class="px-6 pt-6">
        <div class="rounded-md border border-destructive/20 bg-destructive/10 p-4 flex items-center justify-between gap-4">
          <p class="text-sm text-destructive font-medium">{{ loadError }}</p>
          <Button variant="destructive" size="sm" @click="refreshCurrentList">重试</Button>
        </div>
      </div>

      <!-- Remote mode: external channel grid -->
      <RemoteChannelVideoGrid
        v-if="channelDataMode === 'remote'"
        class="p-6"
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
            ref="videoChildRef"
            @goToSubscription="goToChannelDetail"
            @openModal="handleOpenModal"
            @error="loadError = String($event || '')"
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
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import { Button } from '@/shared/ui/button'
import { VIDEO_TABS } from '@/features/video/constants/videos'
import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import { onSubscriptionRemoved } from '@/shared/lib/subscriptionEvents'
import { useRemoteChannel } from '@/features/video/composables/useRemoteChannel'
import { useRemoteVideoMapping } from '@/features/video/composables/useRemoteVideoMapping'
import type { SubscriptionListItem } from '@/features/video/types/subscription'

defineOptions({ name: 'ChannelDetailView' })

const router = useRouter()
const route = useRoute()

const subscriptionId = computed(() => route.params.id as string)
const { activeTab, nsfw, sortBy, special, timeRange, duration, contentType, filters } = useFeedFilters({ subscriptionIdRef: subscriptionId })

const tabs = ref(VIDEO_TABS)
const isRefreshing = ref(false)
const loadError = ref<string | null>(null)
// ponytail: child component (VideoTab via router-view) shares a refresh() surface.
const videoChildRef = ref<{ refresh?: () => void } | null>(null)

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

const refreshCurrentList = () => {
  loadError.value = null
  if (channelDataMode.value === 'remote') {
    fetchRemoteChannel(true)
    return
  }
  videoChildRef.value?.refresh?.()
}

const handleChannelSynced = () => {
  if (channelDataMode.value === 'remote') {
    channelDataMode.value = 'local'
  }
  refreshCurrentList()
}

const handleOpenModal = (video: { id: string | number }) => {
  rememberVideoPlaybackSeed(video)
  router.push(`/video/${video.id}`)
}

const goToChannelDetail = (id: string) => router.push(`/subscription/${id}/all`)

const setSpecialFilter = (value: string) => {
  special.value = value === 'yes' ? 'yes' : 'all'
  const query = { ...route.query }
  if (special.value === 'yes') query.special = 'yes'
  else delete query.special
  router.replace({ query })
}

useRefreshTriggers({ onRefresh: refreshCurrentList })
useRouteTabSync(router, route, activeTab, subscriptionId)

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
  --app-page-max-width: 2400px;
}
</style>
