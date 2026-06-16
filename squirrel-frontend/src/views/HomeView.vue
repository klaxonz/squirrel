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

    <!-- Main Content Area -->
    <div class="app-page-content">

      <!-- Cinematic Spotlight Hero -->
      <div v-if="showSpotlightHero" class="relative w-full mb-6 border border-border/10 overflow-hidden group bg-black"
           :style="{ borderRadius: 'var(--app-card-radius)' }"
           @mouseenter="handleSpotlightMouseEnter" @mouseleave="handleSpotlightMouseLeave">
        <div class="relative w-full h-[clamp(220px,36vh,400px)]">
          <!-- Active Carousel Item (single-frame render; others stay in registry cache) -->
          <div
            v-if="activeSpotlightVideo"
            :key="activeSpotlightVideo.id"
            class="absolute inset-0 cursor-pointer"
            @click="handleOpenModal(activeSpotlightVideo)"
          >
            <!-- Full-Width Background Image Layers -->
            <div class="absolute inset-0 z-0 bg-black">
              <!-- Blurred Background for cinematic full-bleed effect -->
              <VideoThumbnail :src="activeSpotlightVideo?.thumbnail" :alt="activeSpotlightVideo?.title" fit="cover" position="center" blur no-fade img-class="opacity-40 scale-125 transition-transform [transition-duration:10000ms] ease-out" />

              <!-- Uncropped Foreground Image aligned to the right -->
              <div class="absolute inset-0 flex justify-end md:pr-12">
                <VideoThumbnail :src="activeSpotlightVideo?.thumbnail" :alt="activeSpotlightVideo?.title" fit="contain" position="center" no-fade img-class="md:w-3/4 md:object-right opacity-95 transition-transform [transition-duration:10000ms] ease-out scale-[1.03]" />
              </div>

              <!-- Heavy gradient on left for text readability (placed over the image) -->
              <div class="absolute inset-0 bg-gradient-to-r from-black/95 via-black/60 to-transparent"></div>
              <!-- Dark bottom vignette for text contrast -->
              <div class="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-black/90 via-black/40 to-transparent pointer-events-none"></div>
            </div>

            <!-- Content Overlay -->
            <div class="relative z-10 w-full h-full flex items-end pb-12 px-8 md:px-12">
              <div class="max-w-3xl flex flex-col gap-3">
                <div class="flex items-center gap-3 text-sm text-white/80 font-medium">
                  <span class="flex items-center gap-1.5 text-primary tracking-widest uppercase text-xs font-bold drop-shadow">
                    <AppIcon name="star" class="w-4 h-4 fill-primary"/> SPOTLIGHT
                  </span>
                  <span class="flex items-center gap-1.5 drop-shadow">
                    <AppIcon name="time" class="w-4 h-4"/>
                    {{ formatDate(activeSpotlightVideo?.uploaded_at || activeSpotlightVideo?.created_at) }}
                  </span>
                </div>

                <h2 class="text-2xl md:text-3xl lg:text-4xl font-bold leading-tight text-white line-clamp-2 drop-shadow-md">
                  {{ activeSpotlightVideo?.title }}
                </h2>

                <p class="text-white/70 text-sm md:text-base line-clamp-2 max-w-xl drop-shadow">
                  {{ activeSpotlightVideo?.description || 'No description available for this video.' }}
                </p>

                <div class="flex items-center gap-5 mt-3">
                  <button class="flex items-center gap-2 bg-white text-black hover:bg-white/90 px-6 py-2 rounded-sm text-sm font-bold transition-colors"
                          @click.stop="handleOpenModal(activeSpotlightVideo)">
                    <AppIcon name="play" class="w-4 h-4" />
                    立即播放
                  </button>

                  <div class="flex items-center gap-2.5 text-white/80 hover:text-white transition-colors" @click.stop="goToChannelDetail(activeSpotlightVideo?.subscriptions?.[0]?.id)">
                    <SubscriptionAvatar :src="activeSpotlightVideo?.subscriptions?.[0]?.avatar" :name="activeSpotlightVideo?.subscriptions?.[0]?.name" size="sm" class="ring-1 ring-white/20" />
                    <span class="text-xs font-medium drop-shadow">{{ activeSpotlightVideo?.subscriptions?.[0]?.name || '未知频道' }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Carousel Indicators -->
        <div v-if="spotlightVideos.length > 1" class="absolute bottom-5 left-8 md:left-12 flex items-center gap-2 z-20">
          <button 
            v-for="(_, index) in spotlightVideos" 
            :key="index"
            class="h-1.5 rounded-full transition-all duration-300 overflow-hidden relative"
            :class="index === activeSpotlightIndex ? 'w-10 bg-white/30' : 'w-2 bg-white/40 hover:bg-white/60'"
            @click.stop="setSpotlightIndex(index)"
          >
            <!-- Progress bar effect for active item -->
            <div 
              v-if="index === activeSpotlightIndex" 
              class="absolute inset-y-0 left-0 bg-white"
              :style="{ animation: `spotlight-progress ${SPOTLIGHT_INTERVAL}ms linear forwards`, animationPlayState: isSpotlightHovered ? 'paused' : 'running' }"
            ></div>
          </button>
        </div>
      </div>

      <!-- Secondary Feed Sections (Grid layout on wide screens for better space utilization) -->
      <div v-if="!subscriptionId && searchMode === 'local' && activeTab === 'all' && !searchQuery" class="grid grid-cols-1 xl:grid-cols-2 gap-x-6 gap-y-2 mb-6 mt-2">
        <!-- Continue Watching Section -->
        <ContinueWatching
          ref="continueWatchingRef"
          class="!mb-0"
          @openModal="handleOpenModal"
          @viewMore="goToContinueWatching"
        />

        <!-- Special Follows Section -->
        <SpecialFollowVideos
          ref="specialFollowRef"
          class="!mb-0"
          @openModal="handleOpenModal"
          @goToSubscription="goToChannelDetail"
          @viewMore="goToSpecialFollowVideos"
        />
      </div>

      <!-- Persistent Sticky Toolbar (always visible, zero-flicker) -->
      <div v-if="searchMode === 'local' || subscriptionId"
           class="sticky top-0 z-20 -mx-6 px-6 py-2 bg-background/95 backdrop-blur border-b border-border/10">
        <FeedToolbar
          :active-tab="activeTab"
          :nsfw="nsfw"
          :sort-by="sortBy"
          :site="site"
          :special="special"
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
          @update:special="setSpecialFilter"
          @refresh="refreshCurrentList"
        />
      </div>

      <!-- Main Feed Section Header -->
      <div v-if="searchMode === 'local' && !searchQuery" class="px-6 flex items-center justify-between mb-2">
        <h2 class="text-xl font-bold tracking-tight text-foreground/90 flex items-center gap-2">
          <AppIcon name="list" class="w-5 h-5 text-primary" />
          最新动态
        </h2>
      </div>

      <div v-if="loadError" class="px-6 pt-6">
        <div class="bg-destructive/10 rounded-sm p-4 flex items-center justify-between">
          <p class="text-sm text-destructive font-medium">{{ loadError?.message || loadError }}</p>
          <button @click="refreshCurrentList" class="text-xs font-bold uppercase tracking-widest px-4 py-2 bg-destructive text-white rounded-full">重试</button>
        </div>
      </div>

      <template v-if="searchMode === 'remote'">
        <div v-if="searchQuery" class="px-6 flex items-center justify-between mb-2 mt-4">
          <h2 class="text-[16px] font-bold tracking-tight text-foreground/90 flex items-center gap-2">
            <AppIcon name="siteFallback" class="w-5 h-5 text-primary opacity-80" />
            远端搜索结果
          </h2>
          
          <!-- Remote Site Selector -->
          <Select :model-value="site || 'all'" @update:model-value="updateRemoteSite">
            <SelectTrigger class="h-8 w-auto min-w-[120px] bg-accent/40 border-0 text-[12px] font-bold rounded-full transition-colors hover:bg-accent/60">
              <SelectValue placeholder="全部站点" />
            </SelectTrigger>
            <SelectContent class="border-border/10 bg-background/70 backdrop-blur-2xl shadow-2xl rounded-md min-w-[140px]">
              <SelectItem value="all" class="text-xs">全部站点</SelectItem>
              <SelectItem v-for="opt in siteOptions" :key="opt.value" :value="opt.value" class="text-xs">{{ opt.label }}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <keep-alive>
          <RemoteSearchResults
            ref="remoteSearchRef"
            :query="searchQuery"
            :site="site"
            @error="loadError = $event"
            @loading-change="isRefreshing = !!$event"
          />
        </keep-alive>
      </template>

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
            @loaded="handleChildLoaded"
          />
        </keep-alive>
      </router-view>
    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onActivated, onMounted, ref, watch } from 'vue'
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
import SpecialFollowVideos from '@/components/feed/SpecialFollowVideos.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import { VIDEO_TABS } from '@/constants/videos'
import { rememberVideoPlaybackSeed } from '@/composables/videoPlaybackSeed'
import { onSubscriptionRemoved } from '@/utils/subscriptionEvents'
import AppIcon from '@/components/common/AppIcon.vue'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import VideoThumbnail from '@/components/feed/VideoThumbnail.vue'
import { formatDate, formatDuration } from '@/utils/dateFormat'
import { useSites } from '@/composables/useSites'
import { useRemoteChannel, type RemoteVideoItem } from '@/composables/useRemoteChannel'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

// NOTE: This view serves two routes — the home feed (/videos) and the
// subscription/channel detail (/subscription/:id) — branching internally on
// `subscriptionId`. The two layouts are disjoint (Hero/continue-watching/
// special-follows are home-only; ChannelHeader + remote mode are channel-only),
// so this is a known design debt: splitting into HomeView + ChannelDetailView
// would remove the scattered `subscriptionId` conditionals. Kept unified for
// now to avoid coupling this rename to a larger refactor.
defineOptions({ name: 'HomeView' })

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
const { activeTab, nsfw, sortBy, site, searchQuery, special, filters } = useFeedFilters({ subscriptionIdRef: subscriptionId })
const { options: siteOptions, fetchSites } = useSites()

const tabs = ref(VIDEO_TABS)
const isRefreshing = ref(false)
const loadError = ref<any>(null)
const videoChildRef = ref<any>(null)
const remoteSearchRef = ref<any>(null)
const continueWatchingRef = ref<any>(null)
const specialFollowRef = ref<any>(null)
let secondarySectionsRefreshedAt = 0
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
const searchMode = computed({
  get: () => uiStore.homeSearchMode,
  set: (value: 'local' | 'remote') => uiStore.setHomeSearchMode(value),
})

const childFilters = computed(() => filters.value)
const remoteChannelKey = computed(() => {
  const channel = channelDetail.value
  return channel ? `${channel.site || ''}::${channel.url || ''}` : ''
})

const SPOTLIGHT_INTERVAL = 6000
const spotlightVideos = ref<any[]>([])
const activeSpotlightIndex = ref(0)
const activeSpotlightVideo = computed(() => spotlightVideos.value[activeSpotlightIndex.value])
const isSpotlightHovered = ref(false)
let spotlightTimer: ReturnType<typeof setInterval> | null = null

const showSpotlightHero = computed(() => !subscriptionId.value && searchMode.value === 'local' && activeTab.value === 'all' && !searchQuery.value && spotlightVideos.value.length > 0)

const updateRemoteSite = (value: unknown) => {
  const nextSite = String(value || 'all')
  site.value = nextSite === 'all' ? '' : nextSite
}

const startSpotlightTimer = () => {
  if (spotlightTimer) clearInterval(spotlightTimer)
  spotlightTimer = setInterval(() => {
    nextSpotlight()
  }, SPOTLIGHT_INTERVAL)
}

const stopSpotlightTimer = () => {
  if (spotlightTimer) {
    clearInterval(spotlightTimer)
    spotlightTimer = null
  }
}

const handleSpotlightMouseEnter = () => {
  isSpotlightHovered.value = true
  stopSpotlightTimer()
}

const handleSpotlightMouseLeave = () => {
  isSpotlightHovered.value = false
  // Restart timer if we have multiple videos
  if (spotlightVideos.value.length > 1) {
    startSpotlightTimer()
  }
}

const handleChildLoaded = (videos: any) => {
  if (Array.isArray(videos) && videos.length > 0) {
    spotlightVideos.value = videos.slice(0, 5) // Display up to top 5 videos in carousel
    activeSpotlightIndex.value = 0
    if (spotlightVideos.value.length > 1) {
      startSpotlightTimer()
    }
  } else {
    spotlightVideos.value = []
    stopSpotlightTimer()
  }
}

const nextSpotlight = () => {
  if (spotlightVideos.value.length > 1) {
    activeSpotlightIndex.value = (activeSpotlightIndex.value + 1) % spotlightVideos.value.length
  }
}

const setSpotlightIndex = (index: number) => {
  activeSpotlightIndex.value = index
  if (spotlightVideos.value.length > 1 && !isSpotlightHovered.value) {
    startSpotlightTimer()
  }
}

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

const goToContinueWatching = () => router.push({ name: 'History', query: { mode: 'continue' } })

const goToSpecialFollowVideos = () => router.push({ name: 'AllVideos', query: { special: 'yes' } })

const setSpecialFilter = (value: string) => {
  special.value = value === 'yes' ? 'yes' : 'all'
  const query = { ...route.query }
  if (special.value === 'yes') query.special = 'yes'
  else delete query.special
  router.replace({ query })
}

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

watch(() => uiStore.searchTrigger, () => {
  if (route.meta.search === 'home' || !route.meta.search) {
    searchQuery.value = uiStore.searchQuery
  }
})

watch(subscriptionId, (value) => {
  channelDataMode.value = 'local'
  channelDetail.value = null
  loadedRemoteChannelKey = ''
  if (value && searchMode.value === 'remote') {
    searchMode.value = 'local'
  }
})

watch(remoteChannelKey, () => {
  loadedRemoteChannelKey = ''
  if (subscriptionId.value && channelDataMode.value === 'remote') fetchRemoteChannel(true)
})

watch(searchMode, (value) => {
  if (value === 'remote') {
    site.value = undefined
  }
})

watch(() => route.query.special, (value) => {
  special.value = !subscriptionId.value && value === 'yes' ? 'yes' : 'all'
}, { immediate: true })

onActivated(() => {
  // HomeView is kept-alive at the app root; refresh secondary sections when
  // returning to the home feed, throttled to avoid hammering the API on rapid nav.
  const now = Date.now()
  if (now - secondarySectionsRefreshedAt < 30_000) return
  secondarySectionsRefreshedAt = now
  continueWatchingRef.value?.refresh?.()
  specialFollowRef.value?.refresh?.()
})

onMounted(() => {
  onSubscriptionRemoved(({ subscriptionId }) => {
    if (String(route.params.id || '') === String(subscriptionId)) router.replace({ name: 'AllVideos' })
  })

  fetchSites()
})
</script>

<style scoped>
.latest-videos-page {
  --app-page-max-width: 2400px;
}

@keyframes spotlight-progress {
  from { width: 0%; }
  to { width: 100%; }
}
</style>
