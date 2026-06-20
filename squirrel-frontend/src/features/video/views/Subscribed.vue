<template>
  <div class="flex h-full overflow-hidden bg-background text-foreground selection:bg-primary/10">
    <aside class="hidden w-[320px] shrink-0 flex-col border-r border-border/20 bg-muted/10 lg:flex">
      <div class="flex h-20 shrink-0 items-center justify-between border-b border-border/20 px-5 bg-background/50 backdrop-blur-sm">
        <div class="min-w-0 flex flex-col justify-center">
          <h1 class="truncate text-lg font-bold tracking-tight text-foreground/90">订阅频道</h1>
          <p class="mt-0.5 text-xs font-medium text-muted-foreground/70">{{ list.length }} 个频道</p>
        </div>
        <Button variant="ghost" size="icon" class="h-9 w-9 rounded-full bg-primary/5 hover:bg-primary/10 text-primary transition-colors" @click="showAddDialog = true">
          <AppIcon name="plus" class="w-5 h-5" />
        </Button>
      </div>

      <div class="shrink-0 space-y-3 border-b border-border/10 p-4 bg-background/20 backdrop-blur-sm z-10">
        <div class="relative group">
          <AppIcon name="search" class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/60 transition-colors group-focus-within:text-primary" />
          <input 
            v-model="sidebarSearch"
            placeholder="搜索订阅..." 
            class="h-10 w-full rounded-xl border border-transparent bg-accent/40 hover:bg-accent/60 pl-10 pr-4 text-sm font-medium outline-none transition-all placeholder:text-muted-foreground/50 focus:border-primary/30 focus:bg-background focus:ring-4 focus:ring-primary/10"
          />
        </div>
        
        <div class="flex items-center gap-2">
          <div ref="siteFilterRef" class="relative flex-1">
            <button
              @click="showSiteDropdown = !showSiteDropdown"
              class="flex h-9 w-full items-center justify-between rounded-lg border border-transparent bg-accent/40 px-3 text-xs font-semibold transition-all hover:bg-accent/60"
              :class="site ? 'text-foreground border-primary/20 bg-primary/5' : 'text-muted-foreground'"
            >
              <div class="flex items-center gap-2">
                <AppIcon name="filter" class="h-3.5 w-3.5" :class="site ? 'text-primary' : ''" />
                <span>{{ activeSiteLabel }}</span>
              </div>
              <AppIcon name="chevronRight" class="h-3.5 w-3.5 transition-transform" :class="{ 'rotate-90': showSiteDropdown }" />
            </button>

            <div v-if="showSiteDropdown" class="absolute left-0 right-0 top-full z-50 mt-1.5 rounded-xl border border-border/50 bg-background/95 backdrop-blur-xl p-1.5 shadow-xl ring-1 ring-black/5">
              <div class="max-h-[280px] overflow-y-auto custom-scrollbar pr-1">
                <button @click="site = ''; showSiteDropdown = false" class="flex h-9 w-full items-center rounded-lg px-3 text-left text-sm font-medium transition-colors hover:bg-accent" :class="!site ? 'text-foreground bg-accent/50' : 'text-muted-foreground'">全部来源</button>
                <div class="h-px w-full bg-border/50 my-1"></div>
                <button v-for="opt in siteOptionsList" :key="opt.value" @click="site = opt.value; showSiteDropdown = false" class="flex h-9 w-full items-center gap-2.5 rounded-lg px-3 text-left text-sm font-medium transition-colors hover:bg-accent" :class="site === opt.value ? 'text-foreground bg-accent/50' : 'text-muted-foreground'">
                  <SiteIcon :site="opt.value" class="h-4 w-4 rounded-sm" />
                  <span class="flex-1 truncate">{{ opt.label }}</span>
                </button>
              </div>
            </div>
          </div>

          <button
            type="button"
            class="flex h-9 flex-1 items-center justify-center gap-2 rounded-lg border border-transparent bg-accent/40 px-3 text-xs font-semibold transition-all hover:bg-accent/60"
            :class="specialFilter === 'yes' ? 'border-amber-400/30 bg-amber-400/10 text-amber-600' : 'text-muted-foreground hover:text-foreground'"
            @click="toggleSpecialFilter"
          >
            <AppIcon name="star" class="h-3.5 w-3.5" :class="{ 'fill-current drop-shadow-sm': specialFilter === 'yes' }" />
            <span>特别关注</span>
          </button>
        </div>
      </div>

      <div ref="channelsContainer" class="flex-1 space-y-1 overflow-y-auto p-3 custom-scrollbar relative">
        <div
          v-for="sub in filteredChannels"
          :key="sub.id"
          role="button"
          tabindex="0"
          @click="handleChannelClick(sub.id)"
          @keydown.enter.prevent="handleChannelClick(sub.id)"
          @keydown.space.prevent="handleChannelClick(sub.id)"
          class="group relative flex h-[3.25rem] w-full items-center gap-3 rounded-xl px-3 text-left text-sm transition-all overflow-hidden"
          :class="activeChannelId === sub.id ? 'bg-primary/10 text-primary shadow-sm ring-1 ring-primary/20' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'"
        >
          <div class="relative shrink-0">
            <SubscriptionAvatar :src="sub.avatar" :name="sub.name" size="md" :class="activeChannelId === sub.id ? 'ring-2 ring-primary/30' : ''" />
            <div v-if="sub.unread_count > 0" class="absolute -right-1.5 -top-1.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-primary-foreground ring-2 ring-background shadow-sm">
              {{ sub.unread_count > 99 ? '99+' : sub.unread_count }}
            </div>
          </div>
          
          <div class="flex-1 min-w-0" :class="{'pr-8': sub.is_special_followed}">
            <span class="block truncate" :class="activeChannelId === sub.id ? 'font-bold' : 'font-medium'">{{ sub.name }}</span>
          </div>

          <button
            v-if="sub.is_special_followed"
            type="button"
            class="shrink-0 inline-flex h-8 w-8 items-center justify-center rounded-lg text-amber-500 hover:bg-amber-500/10 transition-colors"
            aria-label="取消特别关注"
            @click.stop="toggleSpecialFollow(sub)"
          >
            <AppIcon name="star" class="h-4 w-4 fill-current drop-shadow-sm" />
          </button>

          <button
            v-else
            type="button"
            class="absolute right-2 top-1/2 -translate-y-1/2 inline-flex h-8 w-8 items-center justify-center rounded-lg opacity-0 transition-all group-hover:opacity-100 text-muted-foreground/50 hover:text-foreground hover:bg-background/90 backdrop-blur-sm"
            aria-label="设为特别关注"
            @click.stop="toggleSpecialFollow(sub)"
          >
            <AppIcon name="star" class="h-4 w-4" />
          </button>
        </div>

        <div v-if="loadingChannels" class="space-y-2 p-2">
          <div v-for="i in 5" :key="i" class="h-12 w-full animate-pulse rounded-xl bg-accent/40" />
        </div>
        
        <div ref="channelsTrigger" class="flex h-12 w-full items-center justify-center">
          <AppSpinner v-if="loadingMoreChannels" />
        </div>

        <AppEmptyState
          v-if="channelsFinished && !filteredChannels.length"
          class="py-10"
          variant="plain"
          icon="inbox"
          title="暂无匹配订阅"
          copy="请尝试更换筛选条件"
        />
      </div>

      <div class="shrink-0 border-t border-border/30 p-4 bg-background/50 backdrop-blur-sm">
        <Button variant="outline" class="h-10 w-full justify-start rounded-xl border-border/50 hover:bg-background shadow-sm font-medium" @click="showImportDialog = true">
          <AppIcon name="download" class="mr-2 h-4 w-4 text-muted-foreground" />
          导入订阅
        </Button>
      </div>
    </aside>

    <main class="flex min-w-0 flex-1 flex-col bg-background relative">
      <header class="relative flex shrink-0 items-center justify-between border-b border-border/10 bg-background/70 px-4 py-4 lg:px-8 backdrop-blur-2xl z-20">
        <div class="flex min-w-0 items-center gap-4">
          <div v-if="activeChannel" class="shrink-0 relative group cursor-pointer" @click="openActiveChannelDetail">
            <SubscriptionAvatar :src="activeChannel.avatar" :name="activeChannel.name" size="xl" class="ring-2 ring-background shadow-md transition-transform group-hover:scale-105" />
            <div v-if="activeChannel.is_special_followed" class="absolute -bottom-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full bg-amber-400 text-white ring-2 ring-background shadow-sm">
              <AppIcon name="star" class="h-3 w-3 fill-current" />
            </div>
          </div>
          <div v-else class="flex h-[3.25rem] w-[3.25rem] shrink-0 items-center justify-center rounded-[18px] bg-primary/10 text-primary">
            <AppIcon name="library" class="h-6 w-6" />
          </div>

          <div class="min-w-0 flex flex-col justify-center">
            <div class="flex min-w-0 items-center gap-3">
              <h2 class="max-w-[400px] truncate text-xl font-bold tracking-tight text-foreground/90 cursor-pointer hover:text-primary transition-colors" @click="activeChannel && openActiveChannelDetail()">
                {{ activeChannelName || '订阅动态' }}
              </h2>
              
              <div v-if="canOpenRemoteChannel" class="flex shrink-0 rounded-lg border border-border/40 bg-muted/50 p-0.5 shadow-sm">
                <button
                  type="button"
                  class="inline-flex h-6 items-center gap-1.5 rounded-[6px] px-2.5 text-[11px] font-bold uppercase tracking-wider transition-all"
                  :class="channelDataMode === 'local' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
                  @click="openLocalChannel"
                >
                  <AppIcon name="library" class="h-3 w-3" />
                  Local
                </button>
                <button
                  type="button"
                  class="inline-flex h-6 items-center gap-1.5 rounded-[6px] px-2.5 text-[11px] font-bold uppercase tracking-wider transition-all"
                  :class="channelDataMode === 'remote' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
                  @click="openRemoteChannel"
                >
                  <AppIcon name="siteFallback" class="h-3 w-3" />
                  Remote
                </button>
              </div>

              <button
                v-if="activeChannel"
                type="button"
                class="inline-flex h-7 shrink-0 items-center justify-center rounded-full border transition-all"
                :class="activeChannel.is_special_followed ? 'border-amber-400/40 bg-amber-400/10 text-amber-600 ring-1 ring-amber-400/20' : 'border-border/50 text-muted-foreground hover:bg-accent/60 hover:text-foreground'"
                aria-label="切换特别关注"
                @click="toggleSpecialFollow(activeChannel)"
              >
                <AppIcon name="star" class="h-3.5 w-3.5 mx-1.5" :class="{ 'fill-current drop-shadow-sm': activeChannel.is_special_followed }" />
              </button>
            </div>
            
            <div class="mt-1 flex items-center gap-2 text-xs text-muted-foreground/80 font-medium">
              <span>{{ headerSubtitle }}</span>
              <div v-if="headerLoading" class="flex items-center gap-1 ml-2">
                <AppBounceDots />
              </div>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <div class="flex shrink-0 rounded-lg bg-accent/40 p-1">
            <button @click="showLocalFeed" class="h-8 rounded-md px-4 text-sm font-semibold transition-all" :class="channelDataMode === 'local' && viewMode === 'feed' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'">最近发布</button>
            <button @click="showLocalGrid" class="h-8 rounded-md px-4 text-sm font-semibold transition-all" :class="channelDataMode === 'local' && viewMode === 'grid' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'">频道</button>
          </div>
          
          <div class="h-8 w-px bg-border/40 mx-1 hidden md:block"></div>

          <button class="hidden h-9 items-center gap-2 rounded-lg border border-transparent bg-accent/40 px-4 text-sm font-semibold transition-all md:flex" :class="nsfw === 'all' ? 'text-muted-foreground hover:bg-accent/60 hover:text-foreground' : 'bg-destructive/10 text-destructive'" @click="nsfw = nsfw === 'all' ? 'yes' : 'all'">
            <span class="h-2 w-2 rounded-full" :class="nsfw === 'all' ? 'bg-muted-foreground/40' : 'bg-destructive'" />
            成年内容
          </button>
          
          <Button variant="ghost" size="icon" class="h-9 w-9 rounded-lg bg-accent/40 hover:bg-accent/60" @click="handleRefresh">
            <AppIcon name="refresh" class="h-4 w-4 text-foreground/80" :class="{ 'animate-spin': headerLoading }" />
          </Button>
        </div>
      </header>

      <div ref="feedContainer" class="flex-1 overflow-y-auto custom-scrollbar bg-background">
        <div ref="gridWrapper" class="mx-auto w-full max-w-[1800px] p-4 lg:p-6 lg:px-8">
          <RemoteChannelVideoGrid
            v-if="channelDataMode === 'remote'"
            :items="remoteItems"
            :loading="remoteLoading"
            :all-loaded="remoteAllLoaded"
            :error="remoteError"
            :scroll-root="feedContainer"
            @open="openRemoteResult"
            @load-more="loadMoreRemote"
          />

          <div v-else-if="viewMode === 'feed'" class="space-y-12 pb-12">
            <div v-if="fetchError && !loadingFeed" class="min-h-[30rem]">
              <AppEmptyState variant="error" title="加载失败" :copy="fetchError">
                <template #actions>
                  <Button variant="outline" size="sm" @click="fetchFeed(true)">重试</Button>
                </template>
              </AppEmptyState>
            </div>

            <div v-else-if="!feedItems.length && !loadingFeed" class="min-h-[30rem]">
              <AppEmptyState variant="plain" icon="inbox" title="暂无内容" copy="订阅频道更新后会显示在这里。" />
            </div>

            <div v-for="group in videoGroups" :key="group.title" class="space-y-4">
              <div class="flex items-center gap-3 pt-4 pb-2">
                <h3 class="text-[20px] font-bold tracking-tight text-foreground/90">{{ group.title }}</h3>
                <span class="text-[12px] font-semibold text-muted-foreground/60">{{ group.videos.length }} 视频</span>
              </div>
              <div class="grid grid-cols-1 gap-x-5 gap-y-10 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 3xl:grid-cols-5">
                <VideoItem v-for="video in group.videos" :key="video.id" :video="video" show-avatar @openModal="handleOpenVideo" />
              </div>
            </div>

            <div v-if="loadingMoreFeed" class="grid grid-cols-1 gap-x-5 gap-y-10 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 3xl:grid-cols-5 pt-6">
              <VideoSkeleton v-for="i in videoSkeletonCount" :key="i" />
            </div>
            <div ref="feedTrigger" class="h-20" />
          </div>

          <div v-else class="space-y-8 pb-12">
            <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
              <SubscriptionCard
                v-for="sub in filteredChannels"
                :key="sub.id"
                :subscription="sub"
                @click="handleChannelClick(sub.id)"
                @toggleSpecial="toggleSpecialFollow"
              />
            </div>
            <div v-if="loadingChannels && !list.length" class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
              <SubscriptionCardSkeleton v-for="i in channelSkeletonCount" :key="i" />
            </div>
            <div v-if="!channelsFinished" ref="gridMoreTrigger" class="h-20" />
          </div>
        </div>
      </div>
    </main>

    <AddChannelDialog :show="showAddDialog" @added="handleRefresh" @close="showAddDialog = false" />
    <ImportSubscriptionDialog :show="showImportDialog" @close="showImportDialog = false" @imported="handleRefresh" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted, onMounted, nextTick } from 'vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import { useRouter } from 'vue-router'
import { onClickOutside } from '@vueuse/core'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppBounceDots from '@/shared/components/AppBounceDots.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import { Button } from '@/shared/ui/button'
import SubscriptionCard from '@/features/video/components/feed/SubscriptionCard.vue'
import SubscriptionCardSkeleton from '@/features/video/components/feed/SubscriptionCardSkeleton.vue'
import RemoteChannelVideoGrid from '@/features/video/components/feed/RemoteChannelVideoGrid.vue'
import VideoItem from '@/features/video/components/feed/VideoItem.vue'
import VideoSkeleton from '@/features/video/components/feed/VideoSkeleton.vue'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import SiteIcon from '@/shared/components/SiteIcon.vue'
import AddChannelDialog from '@/features/video/components/dialogs/AddChannelDialog.vue'
import ImportSubscriptionDialog from '@/features/video/components/dialogs/ImportSubscriptionDialog.vue'
import { useFeedFilters } from '../composables/useFeedFilters'
import { useSites } from '../composables/useSites'
import { useRemoteChannel } from '@/features/video/composables/useRemoteChannel'
import { useDesktopBridge } from '@/shared/composables/useDesktopBridge'
import { useRemoteVideoMapping } from '@/features/video/composables/useRemoteVideoMapping'
import { useFeedGrouping } from '@/features/video/composables/useFeedGrouping'
import { sortSubscriptions } from '@/features/video/lib/subscriptionSort'
import { getSubscriptions, getVideoList, updateSpecialFollowStatus } from '@/shared/api'
import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import { useSkeletonCount, type GridBreakpoint } from '@/features/video/composables/useSkeletonCount'
import type { SubscriptionListItem } from '@/features/video/types/subscription'
import type { VideoListItem } from '@/features/video/types/video'

defineOptions({ name: 'Subscribed' })

const router = useRouter()
const { nsfw, site } = useFeedFilters()
const { options: siteOptions, fetchSites } = useSites()
const desktopBridge = useDesktopBridge()

// UI State
const viewMode = ref<'feed' | 'grid'>('feed')
const channelDataMode = ref<'local' | 'remote'>('local')
const sidebarSearch = ref('')
const showSiteDropdown = ref(false)
const siteFilterRef = ref<HTMLElement | null>(null)
const specialFilter = ref<'all' | 'yes'>('all')
const activeChannelId = ref<string | number | null>(null)
const activeChannelNameCache = ref('')
const showAddDialog = ref(false)
const showImportDialog = ref(false)
const feedContainer = ref<HTMLElement | null>(null)
const channelsContainer = ref<HTMLElement | null>(null)

// --- Adaptive skeleton counts ---------------------------------------------
// Shared width measurement on the centered content wrapper. Two configs,
// one per branch (feed videos vs subscription channel cards).
const gridWrapper = ref<HTMLElement | null>(null)

// Feed video grid: `grid-cols-1 sm:2 xl:3 2xl:4 3xl:5`, gap-y-10 (40px).
const VIDEO_BREAKPOINTS: GridBreakpoint[] = [
  [1920, 5], // 3xl
  [1536, 4], // 2xl
  [1280, 3], // xl
  [640, 2],  // sm
  [0, 1],    // base
]
const { count: videoSkeletonCount, attachRef: videoGridRef } = useSkeletonCount({
  breakpoints: VIDEO_BREAKPOINTS,
  cardHeight: 220,
  rowGap: 40,
})

// Subscription card grid: `grid-cols-1 sm:2 lg:3 xl:4 2xl:5`, gap-5 (20px).
// Cards are taller (avatar header + 3 thumbs + footer ≈ 280px).
const CHANNEL_BREAKPOINTS: GridBreakpoint[] = [
  [1536, 5], // 2xl
  [1280, 4], // xl
  [1024, 3], // lg
  [640, 2],  // sm
  [0, 1],    // base
]
const { count: channelSkeletonCount, attachRef: channelGridRef } = useSkeletonCount({
  breakpoints: CHANNEL_BREAKPOINTS,
  cardHeight: 280,
  rowGap: 20,
})

// Both branches render inside the same centered wrapper; point each composable's
// observer at it so column counts track the real container width.
watch(gridWrapper, (node) => {
  videoGridRef.value = node
  channelGridRef.value = node
}, { immediate: true })

// Data State (Channels)
const list = ref<SubscriptionListItem[]>([])
const loadingChannels = ref(false)
const loadingMoreChannels = ref(false)
const channelsFinished = ref(false)
const channelsPage = ref(1)
const CHANNELS_PAGE_SIZE = 100
let channelsRequestToken = 0
let sidebarSearchTimer: number | null = null
const togglingSpecialIds = ref<Set<string | number>>(new Set())

// Data State (Feed)
const feedItems = ref<VideoListItem[]>([])
const loadingFeed = ref(false)
const loadingMoreFeed = ref(false)
const feedFinished = ref(false)
const feedCursor = ref<string | null>(null)
const fetchError = ref<string | null>(null)
const FEED_PAGE_SIZE = 48
let feedRequestToken = 0

const remoteChannel = useRemoteChannel()
const {
  items: remoteItems,
  loading: remoteLoading,
  allLoaded: remoteAllLoaded,
  error: remoteError,
} = remoteChannel
const loadMoreRemote = () => {
  const channel = activeChannel.value
  if (!channel || !canOpenRemoteChannel.value) return
  return remoteChannel.loadMore({ site: channel.site ?? '', url: channel.url, profile: channel })
}
let loadedRemoteChannelKey = ''

// Observers
const feedTrigger = ref<HTMLElement | null>(null)
const channelsTrigger = ref<HTMLElement | null>(null)
const gridMoreTrigger = ref<HTMLElement | null>(null)
let feedObserver: IntersectionObserver | null = null
let channelsObserver: IntersectionObserver | null = null
let gridObserver: IntersectionObserver | null = null

onClickOutside(siteFilterRef, () => { showSiteDropdown.value = false })

const activeChannelName = computed(() => {
  if (!activeChannelId.value) return ''
  return list.value.find(c => c.id === activeChannelId.value)?.name || activeChannelNameCache.value
})
const activeChannel = computed(() => {
  if (!activeChannelId.value) return null
  return list.value.find(c => c.id === activeChannelId.value) || null
})

// ponytail: remote-video → playback-seed mapping + playability gating live in
// useRemoteVideoMapping. The url-hash id scheme + the playability pattern table
// are reusable by any surface that renders remote videos (search, detail, feed).
const { openRemoteResult } = useRemoteVideoMapping({ activeChannel })

const canOpenRemoteChannel = computed(() => {
  return desktopBridge.isDesktop() && !!activeChannel.value?.site && !!activeChannel.value?.url
})
const remoteChannelKey = computed(() => {
  const channel = activeChannel.value
  return channel ? `${channel.site || ''}::${channel.url || ''}` : ''
})
const headerSubtitle = computed(() => {
  if (channelDataMode.value === 'remote') return `${remoteItems.value.length} 个远端视频`
  return viewMode.value === 'feed' ? `${feedItems.value.length} 个视频` : `${filteredChannels.value.length} 个频道`
})
const headerLoading = computed(() => {
  return channelDataMode.value === 'remote' ? remoteLoading.value : loadingFeed.value
})

const siteOptionsList = computed(() => siteOptions.value || [])
const activeSiteLabel = computed(() => {
  if (!site.value) return '全部来源'
  return siteOptionsList.value.find(opt => opt.value === site.value)?.label || '未知来源'
})

const filteredChannels = computed(() => {
  return list.value
})

// ponytail: the "special-followed first, then recency" ordering lives in the
// shared sortSubscriptions util (reusable by any subscription-list surface).
const sortChannels = sortSubscriptions

const applySpecialFollowState = (subscriptionId: string | number, isSpecialFollowed: boolean) => {
  const updated = list.value.map((item) => (
    item.id === subscriptionId ? { ...item, is_special_followed: isSpecialFollowed } : item
  ))
  list.value = specialFilter.value === 'yes' && !isSpecialFollowed
    ? updated.filter((item) => item.id !== subscriptionId)
    : sortChannels(updated)
  if (specialFilter.value === 'yes' && !isSpecialFollowed && activeChannelId.value === subscriptionId) {
    activeChannelId.value = null
    activeChannelNameCache.value = ''
    fetchFeed(true)
  }
}

const toggleSpecialFilter = () => {
  specialFilter.value = specialFilter.value === 'yes' ? 'all' : 'yes'
}

const toggleSpecialFollow = async (subscription: SubscriptionListItem) => {
  if (!subscription?.id || togglingSpecialIds.value.has(subscription.id)) return

  const nextValue = !subscription.is_special_followed
  togglingSpecialIds.value = new Set(togglingSpecialIds.value).add(subscription.id)

  try {
    await updateSpecialFollowStatus(subscription.id, nextValue)
    applySpecialFollowState(subscription.id, nextValue)
  } catch {
    // silent — toggle failure leaves the prior special-follow state
  } finally {
    const nextIds = new Set(togglingSpecialIds.value)
    nextIds.delete(subscription.id)
    togglingSpecialIds.value = nextIds
  }
}

// ponytail: date-bucket grouping (今天/昨天/本周/本月/年月) lives in
// useFeedGrouping. The bucket order is now explicit (the original relied on
// Object.entries insertion order, which is fragile for the year-month buckets).
const { videoGroups } = useFeedGrouping({ feedItems })

const fetchChannels = async (isReset = false) => {
  if (!isReset && (loadingChannels.value || loadingMoreChannels.value || channelsFinished.value)) return
  if (isReset) { channelsPage.value = 1; channelsFinished.value = false; loadingChannels.value = true; loadingMoreChannels.value = false } 
  else { loadingMoreChannels.value = true }

  const requestToken = ++channelsRequestToken
  const requestPage = channelsPage.value
  try {
    const nsfwValue = nsfw.value === 'only' ? 'yes' : (['all', 'yes', 'no'].includes(nsfw.value) ? nsfw.value : 'all')
    const params: Record<string, unknown> = {
      nsfw: nsfwValue,
      page: requestPage,
      pageSize: CHANNELS_PAGE_SIZE,
      page_size: CHANNELS_PAGE_SIZE,
    }
    if (site.value) params.site = site.value
    if (specialFilter.value === 'yes') params.special = 'yes'
    const query = sidebarSearch.value.trim()
    if (query) params.query = query
    try {
      const result = await getSubscriptions(params)
      if (requestToken !== channelsRequestToken) return
      const items = result?.data || []
      if (isReset) list.value = items; else list.value.push(...items)
      if (items.length < CHANNELS_PAGE_SIZE) channelsFinished.value = true
      else channelsPage.value = requestPage + 1
    } catch {
      // Channel-list errors aren't surfaced in-region (the sidebar has no error
      // branch); bail without clobbering the feed's fetchError ref, and don't
      // flip channelsFinished so the sidebar stays retryable.
      if (requestToken !== channelsRequestToken) return
    }
  } finally {
    if (requestToken === channelsRequestToken) {
      loadingChannels.value = false; loadingMoreChannels.value = false
    }
  }
}

const fetchFeed = async (isReset = false) => {
  if (!isReset && (loadingFeed.value || loadingMoreFeed.value || feedFinished.value)) return
  if (isReset) { feedCursor.value = null; feedFinished.value = false; loadingFeed.value = true; loadingMoreFeed.value = false }
  else { loadingMoreFeed.value = true }

  const requestToken = ++feedRequestToken
  const wasReset = isReset
  try {
    const nsfwValue = nsfw.value === 'only' ? 'yes' : (['all', 'yes', 'no'].includes(nsfw.value) ? nsfw.value : 'all')
    const data = await getVideoList({
      cursor: feedCursor.value,
      pageSize: FEED_PAGE_SIZE,
      page_size: FEED_PAGE_SIZE,
      nsfw: nsfwValue,
      site: site.value || undefined,
      subscription_id: activeChannelId.value || undefined,
      sort_by: 'publish_date',
      special: !activeChannelId.value && specialFilter.value === 'yes' ? 'yes' : undefined,
    })
    if (requestToken !== feedRequestToken) return
    fetchError.value = null
    const items = data?.data || []
    if (wasReset) feedItems.value = items; else feedItems.value.push(...items)
    // 推进游标；next_cursor 为 null 表示无更多
    feedCursor.value = data?.next_cursor ?? null
    if (items.length < FEED_PAGE_SIZE || !data?.next_cursor) feedFinished.value = true
  } catch (err) {
    if (requestToken !== feedRequestToken) return
    fetchError.value = errorMessage(err, '内容加载失败')
    feedFinished.value = true
  } finally {
    if (requestToken === feedRequestToken) {
      loadingFeed.value = false; loadingMoreFeed.value = false
    }
  }
}

const scrollToTop = (el: HTMLElement | null) => {
  if (el) el.scrollTop = 0
}

const resetAllScroll = () => {
  scrollToTop(feedContainer.value)
  nextTick(() => scrollToTop(channelsContainer.value))
}

const handleChannelClick = (id: string | number) => {
  if (activeChannelId.value === id) {
    activeChannelId.value = null
    activeChannelNameCache.value = ''
  } else {
    activeChannelId.value = id
    activeChannelNameCache.value = list.value.find(c => c.id === id)?.name || ''
  }
  channelDataMode.value = 'local'
  viewMode.value = 'feed'; fetchFeed(true)
  scrollToTop(feedContainer.value)
}

const openActiveChannelDetail = () => {
  if (!activeChannelId.value) return
  router.push({ name: 'SubscriptionAllVideos', params: { id: String(activeChannelId.value) } })
}

const handleRefresh = () => {
  fetchChannels(true)
  if (channelDataMode.value === 'remote') fetchRemoteChannel(true)
  else fetchFeed(true)
  resetAllScroll()
}
const handleOpenVideo = (video: VideoListItem) => { rememberVideoPlaybackSeed(video); router.push(`/video/${video.id}`) }
const showLocalFeed = () => {
  channelDataMode.value = 'local'
  viewMode.value = 'feed'
}
const showLocalGrid = () => {
  channelDataMode.value = 'local'
  viewMode.value = 'grid'
}
const openLocalChannel = () => {
  channelDataMode.value = 'local'
}
const openRemoteChannel = async () => {
  const channel = activeChannel.value
  if (!canOpenRemoteChannel.value || !channel) return

  channelDataMode.value = 'remote'
  if (loadedRemoteChannelKey !== remoteChannelKey.value) await fetchRemoteChannel(true)
  scrollToTop(feedContainer.value)
}

const fetchRemoteChannel = async (isReset = false) => {
  const channel = activeChannel.value
  if (!channel || !canOpenRemoteChannel.value) return

  if (isReset) loadedRemoteChannelKey = remoteChannelKey.value

  await remoteChannel.fetchRemote(
    { site: channel.site ?? '', url: channel.url, profile: channel },
    isReset,
  )
}

const initObservers = () => {
  // Cleanup existing
  feedObserver?.disconnect()
  channelsObserver?.disconnect()
  gridObserver?.disconnect()

  const scrollContainer = feedContainer.value
  const channelsEl = channelsContainer.value

  // 1. Feed Observer
  feedObserver = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && !loadingFeed.value && !loadingMoreFeed.value && !feedFinished.value) fetchFeed()
  }, { root: scrollContainer, rootMargin: '800px' })
  if (feedTrigger.value) feedObserver.observe(feedTrigger.value)

  // 2. Channels Sidebar Observer
  channelsObserver = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && !loadingChannels.value && !loadingMoreChannels.value && !channelsFinished.value) fetchChannels()
  }, { root: channelsEl, rootMargin: '200px' })
  if (channelsTrigger.value) channelsObserver.observe(channelsTrigger.value)

  // 3. Grid Mode Observer
  if (viewMode.value === 'grid') {
    gridObserver = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && !loadingChannels.value && !loadingMoreChannels.value && !channelsFinished.value) fetchChannels()
    }, { root: scrollContainer, rootMargin: '400px' })
    if (gridMoreTrigger.value) gridObserver.observe(gridMoreTrigger.value)
  }
}

onMounted(async () => {
  fetchSites(); fetchChannels(true); await fetchFeed(true)
  nextTick(() => initObservers())
})

// Re-init observers when view mode changes to bind new triggers
watch(viewMode, () => {
  nextTick(() => initObservers())
})

watch([nsfw, site, specialFilter], () => { fetchChannels(true); fetchFeed(true); resetAllScroll() })

watch(remoteChannelKey, () => {
  loadedRemoteChannelKey = ''
  if (channelDataMode.value === 'remote') fetchRemoteChannel(true)
})

watch(sidebarSearch, () => {
  if (sidebarSearchTimer !== null) window.clearTimeout(sidebarSearchTimer)
  sidebarSearchTimer = window.setTimeout(() => {
    fetchChannels(true)
    nextTick(() => scrollToTop(channelsContainer.value))
  }, 250)
})
onUnmounted(() => {
  if (sidebarSearchTimer !== null) window.clearTimeout(sidebarSearchTimer)
  feedObserver?.disconnect(); channelsObserver?.disconnect(); gridObserver?.disconnect()
})
</script>

<style scoped>
.no-scrollbar::-webkit-scrollbar { display: none; }
.no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
.custom-scrollbar::-webkit-scrollbar { width: 5px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(var(--primary), 0.1); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(var(--primary), 0.2); }
</style>
