<template>
  <AppPageShell class="latest-videos-page" variant="compact" :fill="false">
    <!-- Channel Header -->
    <ChannelHeader
      v-if="subscriptionId"
      :subscription-id="subscriptionId"
      :mode="channelDataMode"
      @update:mode="handleChannelModeChange"
      @loaded="channelDetail = $event"
      @synced="handleChannelSynced"
    />

    <!-- Sticky Toolbar -->
    <div class="sticky top-0 z-30">
      <FeedToolbar
        :active-tab="activeTab"
        :nsfw="nsfw"
        :sort-by="sortBy"
        :site="site"
        :subscription-id="subscriptionId"
        :tabs="tabs"
        :is-refreshing="isRefreshing"
        :show-tabs="searchMode === 'local'"
        :show-sort="searchMode === 'local'"
        :show-filter="searchMode === 'local'"
        @update:activeTab="activeTab = $event"
        @update:nsfw="nsfw = $event"
        @update:sortBy="sortBy = $event"
        @update:site="site = $event"
        @refresh="refreshCurrentList"
      />
    </div>

    <!-- Main Content Area -->
    <div class="app-page-content">

      <!-- Continue Watching (Only on Home "All" tab) -->
      <ContinueWatching
        v-if="!subscriptionId && searchMode === 'local' && activeTab === 'all' && !searchQuery"
        @openModal="handleOpenModal"
      />

      <div v-if="loadError" class="px-6 pt-6">
        <div class="bg-destructive/5 border border-destructive/20 rounded-2xl p-4 flex items-center justify-between">
          <p class="text-sm text-destructive font-medium">{{ loadError?.message || loadError }}</p>
          <button @click="refreshCurrentList" class="text-xs font-bold uppercase tracking-widest px-4 py-2 bg-destructive text-white rounded-full">重试</button>
        </div>
      </div>

      <keep-alive v-if="searchMode === 'remote'">
        <RemoteSearchResults
          ref="remoteSearchRef"
          :query="searchQuery"
          :site="site"
          @error="loadError = $event"
          @loading-change="isRefreshing = !!$event"
        />
      </keep-alive>

      <RemoteChannelVideoGrid
        v-else-if="subscriptionId && channelDataMode === 'remote'"
        class="p-6"
        :items="remoteItems"
        :loading="remoteLoading"
        :all-loaded="remoteAllLoaded"
        :error="remoteError"
        @open="openRemoteResult"
        @load-more="loadMoreRemote"
      />

      <router-view v-else v-slot="{ Component }">
        <keep-alive :max="10">
          <component
            :is="Component"
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
import { computed, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUIStore } from '@/stores/ui'
import { useRouteTabSync } from '../composables/useRouteTabSync'
import { useFeedFilters } from '../composables/useFeedFilters'
import { useRefreshTriggers } from '../composables/useRefreshTriggers'
import FeedToolbar from '@/components/feed/FeedToolbar.vue'
import ChannelHeader from '@/components/feed/ChannelHeader.vue'
import RemoteChannelVideoGrid from '@/components/feed/RemoteChannelVideoGrid.vue'
import RemoteSearchResults from '@/components/feed/RemoteSearchResults.vue'
import ContinueWatching from '@/components/feed/ContinueWatching.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import { VIDEO_TABS } from '@/constants/videos'
import { rememberVideoPlaybackSeed } from '@/composables/videoPlaybackSeed'
import { onSubscriptionRemoved } from '@/utils/subscriptionEvents'

defineOptions({ name: 'LatestVideos' })

type RemoteProfile = {
  id?: string | number | null
  type?: string | null
  name: string
  url?: string | null
  avatar?: string | null
  description?: string | null
  site?: string | null
  is_nsfw?: boolean | null
}

type RemoteSearchItem = {
  source: 'remote'
  site: string
  id?: string | number | null
  title: string
  url: string
  thumbnail?: string | null
  duration?: number | null
  publish_date?: string | null
  published_text?: string | null
  uploader?: string | null
  uploader_url?: string | null
  uploader_avatar?: string | null
  subscriptions?: RemoteProfile[]
  actors?: RemoteProfile[]
  description?: string | null
}

const REMOTE_PLAYABLE_SITE_PATTERNS: Record<string, RegExp> = {
  bilibili: /(?:bilibili\.com\/video\/|b23\.tv\/)/i,
  pornhub: /pornhub\.com\/(?:view_video\.php|video\/|embed\/)/i,
  youtube: /(?:youtube\.com\/|youtu\.be\/)/i,
  youporn: /youporn\.com\/watch\//i,
}

const router = useRouter()
const route = useRoute()
const uiStore = useUIStore()

const subscriptionId = computed(() => route.params.id as string)
const { activeTab, nsfw, sortBy, site, searchQuery, filters } = useFeedFilters({ subscriptionIdRef: subscriptionId })

const tabs = ref(VIDEO_TABS)
const isRefreshing = ref(false)
const loadError = ref<any>(null)
const videoChildRef = ref<any>(null)
const remoteSearchRef = ref<any>(null)
const channelDataMode = ref<'local' | 'remote'>('local')
const channelDetail = ref<any>(null)
const remoteItems = ref<RemoteSearchItem[]>([])
const remoteLoading = ref(false)
const remoteAllLoaded = ref(false)
const remotePage = ref(1)
const remoteNextCursor = shallowRef<unknown>(null)
const remoteError = ref('')
let remoteRequestToken = 0
let loadedRemoteChannelKey = ''
const searchMode = computed({
  get: () => uiStore.homeSearchMode,
  set: (value: 'local' | 'remote') => uiStore.setHomeSearchMode(value),
})

const childFilters = computed(() => filters.value)
const remoteChannelKey = computed(() => {
  const channel = channelDetail.value
  return channel ? `${channel.site || ''}::${channel.url || ''}` : ''
})

const refreshCurrentList = () => {
  loadError.value = null
  if (subscriptionId.value && channelDataMode.value === 'remote') {
    fetchRemoteChannel(true)
    return
  }
  if (searchMode.value === 'remote') {
    remoteSearchRef.value?.refresh?.()
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

const handleTabDoubleClick = (tab: string) => {
  if (tab === activeTab.value) refreshCurrentList()
}

useRefreshTriggers({ onRefresh: refreshCurrentList })
useRouteTabSync(router, route, activeTab, subscriptionId)

const handleChannelModeChange = async (mode: 'local' | 'remote') => {
  channelDataMode.value = mode
  if (mode === 'remote' && loadedRemoteChannelKey !== remoteChannelKey.value) {
    await fetchRemoteChannel(true)
  }
}

const appendUniqueRemoteItems = (nextItems: RemoteSearchItem[]) => {
  const seen = new Set(remoteItems.value.map((item) => item.url))
  const uniqueItems = nextItems.filter((item) => {
    if (!item.url || seen.has(item.url)) return false
    seen.add(item.url)
    return true
  })
  remoteItems.value = remoteItems.value.concat(uniqueItems)
}

const fetchRemoteChannel = async (isReset = false) => {
  const channel = channelDetail.value
  if (!channel?.site || !channel?.url) return

  if (!window.desktopApp?.isDesktop || typeof window.desktopApp?.getRemoteChannel !== 'function') {
    remoteError.value = '当前桌面端不支持远端频道'
    return
  }
  if (!isReset && (remoteLoading.value || remoteAllLoaded.value)) return

  if (isReset) {
    remoteItems.value = []
    remotePage.value = 1
    remoteNextCursor.value = null
    remoteAllLoaded.value = false
    remoteError.value = ''
    loadedRemoteChannelKey = remoteChannelKey.value
  }

  const requestToken = ++remoteRequestToken
  const requestPage = isReset ? 1 : remotePage.value + 1
  remoteLoading.value = true
  isRefreshing.value = true
  let timer: ReturnType<typeof setTimeout> | undefined

  try {
    const result = await Promise.race([
      window.desktopApp.getRemoteChannel({
        site: channel.site,
        url: channel.url,
        limit: 30,
        page: requestPage,
        cursor: requestPage > 1 && remoteNextCursor.value ? { ...(remoteNextCursor.value as Record<string, unknown>) } : undefined,
        profile: {
          id: channel.id != null ? String(channel.id) : null,
          type: 'CHANNEL',
          name: channel.name || '',
          url: channel.url,
          avatar: channel.avatar || '',
          is_nsfw: channel.is_nsfw === true,
        },
      }),
      new Promise<never>((_, reject) => {
        timer = setTimeout(() => reject(new Error('远端频道加载超时')), 60000)
      }),
    ])
    if (requestToken !== remoteRequestToken) return

    const nextItems = Array.isArray(result.items) ? result.items : []
    if (requestPage === 1) remoteItems.value = nextItems
    else appendUniqueRemoteItems(nextItems)
    remotePage.value = requestPage
    remoteNextCursor.value = result.next_cursor || null
    remoteAllLoaded.value = result.has_more === false
  } catch (error: any) {
    if (requestToken !== remoteRequestToken) return
    remoteError.value = error?.message || '远端频道加载失败'
  } finally {
    clearTimeout(timer)
    if (requestToken === remoteRequestToken) {
      remoteLoading.value = false
      isRefreshing.value = false
    }
  }
}

const loadMoreRemote = async () => {
  await fetchRemoteChannel(false)
}

const hashRemoteUrl = (url: string) => {
  let hash = 0
  for (let index = 0; index < url.length; index += 1) {
    hash = Math.imul(31, hash) + url.charCodeAt(index)
    hash |= 0
  }
  return Math.abs(hash).toString(36)
}

const buildRemoteVideoSeed = (item: RemoteSearchItem) => {
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

const canPlayRemoteResult = (item: RemoteSearchItem) => {
  const pattern = REMOTE_PLAYABLE_SITE_PATTERNS[item.site]
  return !!pattern && pattern.test(String(item.url || ''))
}

const openRemoteResult = async (item: RemoteSearchItem) => {
  if (!item.url || !canPlayRemoteResult(item)) return

  const videoSeed = buildRemoteVideoSeed(item)
  rememberVideoPlaybackSeed(videoSeed)
  await router.push({ name: 'VideoPlay', params: { videoId: videoSeed.id } })
}

watch(() => uiStore.searchTrigger, () => {
  if (route.meta.search === 'home' || !route.meta.search) {
    searchQuery.value = uiStore.searchQuery
  }
})

watch(subscriptionId, (value) => {
  channelDataMode.value = 'local'
  channelDetail.value = null
  remoteItems.value = []
  remotePage.value = 1
  remoteNextCursor.value = null
  remoteAllLoaded.value = false
  remoteError.value = ''
  loadedRemoteChannelKey = ''
  if (value && searchMode.value === 'remote') {
    searchMode.value = 'local'
  }
})

watch(remoteChannelKey, () => {
  remoteItems.value = []
  remotePage.value = 1
  remoteNextCursor.value = null
  remoteAllLoaded.value = false
  remoteError.value = ''
  loadedRemoteChannelKey = ''
  if (subscriptionId.value && channelDataMode.value === 'remote') fetchRemoteChannel(true)
})

watch(searchMode, (value) => {
  if (value === 'remote') {
    site.value = undefined
  }
})

onMounted(() => {
  onSubscriptionRemoved(({ subscriptionId }) => {
    if (String(route.params.id || '') === String(subscriptionId)) router.replace({ name: 'AllVideos' })
  })
})
</script>

<style scoped>
.latest-videos-page {
  --app-page-max-width: 2400px;
}
</style>
