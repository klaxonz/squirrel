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

      <!-- Cinematic Full-Bleed Spotlight Hero -->
      <div v-if="showSpotlightHero" class="relative w-[calc(100%+3rem)] -mx-6 -mt-6 mb-8 overflow-hidden group cursor-pointer bg-black" @click="handleOpenModal(spotlightVideo)">
        <!-- Full-Width Background Image -->
        <div class="absolute inset-0 z-0">
          <img :src="spotlightVideo?.thumbnail" class="w-full h-full object-cover object-center opacity-60 group-hover:scale-105 transition-transform duration-1000" />
          <!-- Heavy gradient on left for text readability -->
          <div class="absolute inset-0 bg-gradient-to-r from-black/90 via-black/50 to-transparent"></div>
          <!-- Bottom gradient to blend into the app's native background -->
          <div class="absolute inset-0 bg-gradient-to-t from-background via-transparent to-transparent"></div>
        </div>

        <!-- Content Overlay -->
        <div class="relative z-10 w-full h-[320px] lg:h-[380px] flex items-end pb-8 px-8 md:px-12">
          <div class="max-w-3xl flex flex-col gap-3">
            <div class="flex items-center gap-3 text-sm text-white/80 font-medium">
              <span class="flex items-center gap-1.5 text-primary tracking-widest uppercase text-xs font-bold drop-shadow">
                <AppIcon name="star" class="w-4 h-4 fill-primary"/> SPOTLIGHT
              </span>
              <span class="flex items-center gap-1.5 drop-shadow">
                <AppIcon name="time" class="w-4 h-4"/> 
                {{ formatDate(spotlightVideo?.uploaded_at || spotlightVideo?.created_at) }}
              </span>
            </div>
            
            <h2 class="text-2xl md:text-3xl lg:text-4xl font-bold leading-tight text-white line-clamp-2 drop-shadow-md">
              {{ spotlightVideo?.title }}
            </h2>
            
            <p class="text-white/70 text-sm md:text-base line-clamp-2 max-w-xl drop-shadow">
              {{ spotlightVideo?.description || 'No description available for this video.' }}
            </p>

            <div class="flex items-center gap-5 mt-3">
              <button class="flex items-center gap-2 bg-white text-black hover:bg-white/90 px-6 py-2 rounded-sm text-sm font-bold transition-colors">
                <AppIcon name="play" class="w-4 h-4" />
                立即播放
              </button>
              
              <div class="flex items-center gap-2.5 text-white/80 hover:text-white transition-colors" @click.stop="goToChannelDetail(spotlightVideo?.subscriptions?.[0]?.id)">
                <SubscriptionAvatar :src="spotlightVideo?.subscriptions?.[0]?.avatar" :name="spotlightVideo?.subscriptions?.[0]?.name" size="sm" class="ring-1 ring-white/20" />
                <span class="text-xs font-medium drop-shadow">{{ spotlightVideo?.subscriptions?.[0]?.name || '未知频道' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Secondary Feed Sections (Grid layout on wide screens for better space utilization) -->
      <div v-if="!subscriptionId && searchMode === 'local' && activeTab === 'all' && !searchQuery" class="grid grid-cols-1 xl:grid-cols-2 gap-x-6 gap-y-2 mb-6">
        <!-- Continue Watching Section -->
        <ContinueWatching
          class="!mb-0"
          @openModal="handleOpenModal"
          @viewMore="goToContinueWatching"
        />

        <!-- Special Follows Section -->
        <SpecialFollowVideos
          class="!mb-0"
          @openModal="handleOpenModal"
          @goToSubscription="goToChannelDetail"
          @viewMore="goToSpecialFollowVideos"
        />
      </div>

      <!-- Sentinel for Sticky Toolbar -->
      <div ref="toolbarSentinel" class="h-px w-full invisible pointer-events-none -mt-6 absolute"></div>

      <!-- Zero-height Sticky Wrapper to respect AppLayout's scroll container -->
      <div class="sticky top-6 z-50 h-0 w-full overflow-visible pointer-events-none">
        <!-- Pure Dynamic Island (Only visible when scrolling) -->
        <div 
          class="mx-auto w-fit transition-all duration-500 ease-out bg-background/90 backdrop-blur-3xl shadow-2xl border border-border/15 rounded-full ring-1 ring-black/5 dark:ring-white/10 px-2 py-0.5"
          :class="[
            isToolbarSticky 
              ? 'opacity-100 translate-y-0 scale-100 pointer-events-auto' 
              : 'opacity-0 -translate-y-6 scale-95 pointer-events-none'
          ]"
        >
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
            @loaded="handleChildLoaded"
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
import SpecialFollowVideos from '@/components/feed/SpecialFollowVideos.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import { VIDEO_TABS } from '@/constants/videos'
import { rememberVideoPlaybackSeed } from '@/composables/videoPlaybackSeed'
import { onSubscriptionRemoved } from '@/utils/subscriptionEvents'
import AppIcon from '@/components/common/AppIcon.vue'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import { formatDate, formatDuration } from '@/utils/dateFormat'

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
const { activeTab, nsfw, sortBy, site, searchQuery, special, filters } = useFeedFilters({ subscriptionIdRef: subscriptionId })

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

const spotlightVideo = ref<any>(null)
const toolbarSentinel = ref<HTMLElement | null>(null)
const isToolbarSticky = ref(false)
const showSpotlightHero = computed(() => !subscriptionId.value && searchMode.value === 'local' && activeTab.value === 'all' && !searchQuery.value && spotlightVideo.value != null)

const handleChildLoaded = (videos: any) => {
  if (Array.isArray(videos) && videos.length > 0) {
    spotlightVideo.value = videos[0]
  } else {
    spotlightVideo.value = null
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

watch(() => route.query.special, (value) => {
  special.value = !subscriptionId.value && value === 'yes' ? 'yes' : 'all'
}, { immediate: true })

onMounted(() => {
  onSubscriptionRemoved(({ subscriptionId }) => {
    if (String(route.params.id || '') === String(subscriptionId)) router.replace({ name: 'AllVideos' })
  })

  const scrollContainer = document.getElementById('app-main-scroll')
  if (scrollContainer && toolbarSentinel.value) {
    const observer = new IntersectionObserver(([entry]) => {
      // The element is sticky when the sentinel scrolls past the sticky offset (24px = top-6)
      isToolbarSticky.value = !entry.isIntersecting && entry.boundingClientRect.top < (entry.rootBounds?.top || 0) + 24
    }, {
      root: scrollContainer,
      rootMargin: '-24px 0px 0px 0px',
      threshold: 0
    })
    observer.observe(toolbarSentinel.value)
  }
})
</script>

<style scoped>
.latest-videos-page {
  --app-page-max-width: 2400px;
}
</style>
