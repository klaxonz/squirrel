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
        <div class="bg-destructive/10 rounded-sm p-4 flex items-center justify-between">
          <p class="text-sm text-destructive font-medium">{{ loadError?.message || loadError }}</p>
          <button @click="refreshCurrentList" class="text-xs font-bold uppercase tracking-widest px-4 py-2 bg-destructive text-white rounded-full">重试</button>
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
            @error="loadError = $event"
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
import FeedToolbar from '@/components/feed/FeedToolbar.vue'
import ChannelHeader from '@/components/feed/ChannelHeader.vue'
import RemoteChannelVideoGrid from '@/components/feed/RemoteChannelVideoGrid.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import { VIDEO_TABS } from '@/constants/videos'
import { rememberVideoPlaybackSeed } from '@/composables/videoPlaybackSeed'
import { onSubscriptionRemoved } from '@/utils/subscriptionEvents'
import { useRemoteChannel, type RemoteVideoItem } from '@/composables/useRemoteChannel'

defineOptions({ name: 'ChannelDetailView' })

const REMOTE_PLAYABLE_SITE_PATTERNS: Record<string, RegExp> = {
  bilibili: /(?:bilibili\.com\/video\/|b23\.tv\/)/i,
  pornhub: /pornhub\.com\/(?:view_video\.php|video\/|embed\/)/i,
  youtube: /(?:youtube\.com\/|youtu\.be\/)/i,
  youporn: /youporn\.com\/watch\//i,
}

const router = useRouter()
const route = useRoute()

const subscriptionId = computed(() => route.params.id as string)
const { activeTab, nsfw, sortBy, special, timeRange, duration, contentType, filters } = useFeedFilters({ subscriptionIdRef: subscriptionId })

const tabs = ref(VIDEO_TABS)
const isRefreshing = ref(false)
const loadError = ref<any>(null)
const videoChildRef = ref<any>(null)

const channelDataMode = ref<'local' | 'remote'>('local')
const channelDetail = ref<any>(null)

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

const handleOpenModal = (video: any) => {
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

const hashRemoteUrl = (url: string) => {
  let hash = 0
  for (let index = 0; index < url.length; index += 1) {
    hash = Math.imul(31, hash) + url.charCodeAt(index)
    hash |= 0
  }
  return Math.abs(hash).toString(36)
}

const buildRemoteVideoSeed = (item: RemoteVideoItem) => {
  const channel = channelDetail.value
  const url = String(item.url || '').trim()
  return {
    id: `remote-${item.site}-${hashRemoteUrl(url)}`,
    source: 'remote',
    site: item.site,
    title: item.title,
    url,
    thumbnail: item.thumbnail || '',
    duration: item.duration || null,
    publish_date: item.publish_date || null,
    uploaded_at: item.publish_date || null,
    description: item.description || '',
    subscriptions: item.subscriptions?.length ? item.subscriptions : [{
      id: channel?.id ?? null,
      type: 'CHANNEL',
      name: channel?.name || '',
      url: channel?.url || '',
      avatar: channel?.avatar || '',
      is_nsfw: channel?.is_nsfw === true,
    }],
    actors: item.actors || [],
  }
}

const canPlayRemoteResult = (item: RemoteVideoItem) => {
  const pattern = REMOTE_PLAYABLE_SITE_PATTERNS[item.site]
  return !!pattern && pattern.test(String(item.url || ''))
}

const openRemoteResult = async (item: RemoteVideoItem) => {
  if (!item.url || !canPlayRemoteResult(item)) return

  const videoSeed = buildRemoteVideoSeed(item)
  rememberVideoPlaybackSeed(videoSeed)
  await router.push({ name: 'VideoPlay', params: { videoId: videoSeed.id } })
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
