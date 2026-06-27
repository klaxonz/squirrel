<template>
  <div class="flex h-full overflow-hidden bg-background text-foreground selection:bg-primary/10">
    <SubscriptionSidebar
      ref="sidebarRef"
      :channels="filteredChannels"
      :loading="loadingChannels"
      :loading-more="loadingMoreChannels"
      :finished="channelsFinished"
      :search="sidebarSearch"
      :site="site || ''"
      :site-options="siteOptionsList"
      :active-site-label="activeSiteLabel"
      :site-dropdown-open="showSiteDropdown"
      :special-filter="specialFilter"
      :active-channel-id="activeChannelId"
      @add="showAddDialog = true"
      @import="showImportDialog = true"
      @select-channel="handleChannelClick"
      @toggle-special="toggleSpecialFollow"
      @toggle-special-filter="toggleSpecialFilter"
      @update:search="sidebarSearch = $event"
      @update:site="site = $event"
      @update:site-dropdown-open="showSiteDropdown = $event"
    />

    <main class="flex min-w-0 flex-1 flex-col bg-background relative">
      <header class="relative flex shrink-0 items-center justify-between border-b border-border/10 bg-background/70 px-4 py-4 lg:px-8 backdrop-blur-2xl z-20">
        <div class="flex min-w-0 items-center gap-4">
          <div v-if="activeChannel" class="shrink-0 relative group cursor-pointer" @click="openActiveChannelDetail">
            <SubscriptionAvatar :src="activeChannel.avatar" :name="activeChannel.name" size="xl" class="ring-2 ring-background shadow-md transition-transform group-hover:scale-105" />
            <div v-if="activeChannel.is_special_followed" class="absolute -bottom-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full bg-warning/10 text-warning ring-2 ring-background shadow-sm">
              <AppIcon name="star" class="h-3 w-3 fill-current" />
            </div>
          </div>
          <div v-else class="flex h-[3.25rem] w-[3.25rem] shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <AppIcon name="library" class="h-6 w-6" />
          </div>

          <div class="min-w-0 flex flex-col justify-center">
            <div class="flex min-w-0 items-center gap-3">
              <h2 class="app-h2 max-w-[400px] truncate cursor-pointer hover:text-primary transition-colors" @click="activeChannel && openActiveChannelDetail()">
                {{ activeChannelName || '订阅动态' }}
              </h2>
              
              <div v-if="canOpenRemoteChannel" class="flex shrink-0 rounded-lg border border-border/40 bg-muted/50 p-0.5 shadow-sm">
                <button
                  type="button"
                  class="inline-flex h-6 items-center gap-1.5 rounded px-2.5 text-xs font-bold uppercase tracking-wider transition-all"
                  :class="channelDataMode === 'local' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
                  @click="openLocalChannel"
                >
                  <AppIcon name="library" class="h-3 w-3" />
                  Local
                </button>
                <button
                  type="button"
                  class="inline-flex h-6 items-center gap-1.5 rounded px-2.5 text-xs font-bold uppercase tracking-wider transition-all"
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
                :class="activeChannel.is_special_followed ? 'border-warning/40 bg-warning/10 text-warning ring-1 ring-warning/20' : 'border-border/50 text-muted-foreground hover:bg-accent/60 hover:text-foreground'"
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

        <div class="flex items-center gap-1.5">
          <!-- View toggle (feed / channels) — segmented control, aligns with FeedToolbar's pill language -->
          <div class="flex shrink-0 items-center gap-0.5 rounded-full bg-muted/40 p-0.5">
            <button
              class="flex h-8 items-center gap-1.5 rounded-full px-3 text-sm font-semibold transition-all outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
              :class="channelDataMode === 'local' && viewMode === 'feed' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground'"
              :aria-pressed="channelDataMode === 'local' && viewMode === 'feed'"
              @click="showLocalFeed"
            >
              <AppIcon name="film" class="h-3.5 w-3.5" />
              最近发布
            </button>
            <button
              class="flex h-8 items-center gap-1.5 rounded-full px-3 text-sm font-semibold transition-all outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
              :class="channelDataMode === 'local' && viewMode === 'grid' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground'"
              :aria-pressed="channelDataMode === 'local' && viewMode === 'grid'"
              @click="showLocalGrid"
            >
              <AppIcon name="layoutGrid" class="h-3.5 w-3.5" />
              频道
            </button>
          </div>

          <!-- NSFW toggle — pill, size-8, clear active state + aria -->
          <button
            class="hidden h-8 shrink-0 items-center gap-1.5 rounded-full px-3 text-sm font-semibold transition-all outline-none focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-2 focus-visible:ring-offset-background md:inline-flex"
            :class="nsfw === 'all' ? 'bg-muted/40 text-muted-foreground hover:bg-muted/70 hover:text-foreground' : 'border border-destructive/30 bg-destructive/10 text-destructive hover:bg-destructive/15'"
            :aria-pressed="nsfw !== 'all'"
            :title="nsfw === 'all' ? '显示成年内容' : '隐藏成年内容'"
            @click="nsfw = nsfw === 'all' ? 'yes' : 'all'"
          >
            <span class="h-1.5 w-1.5 rounded-full" :class="nsfw === 'all' ? 'bg-muted-foreground/50' : 'bg-destructive'" />
            成年内容
          </button>

          <!-- Refresh — size-8 icon pill, matches FeedToolbar refresh -->
          <button
            class="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted/40 text-muted-foreground transition-colors outline-none hover:bg-muted/70 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            :disabled="headerLoading"
            title="刷新内容"
            aria-label="刷新内容"
            @click="handleRefresh"
          >
            <AppSpinner v-if="headerLoading" size="sm" />
            <AppIcon v-else name="refresh" class="h-4 w-4" />
          </button>
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

            <div class="app-video-grid app-video-grid--feed pb-12">
              <VideoItem v-for="video in feedItems" :key="video.id" :video="video" show-avatar @openModal="handleOpenVideo" />
            </div>

            <div v-if="loadingMoreFeed" class="app-video-grid app-video-grid--feed pt-6">
              <VideoSkeleton v-for="i in videoSkeletonCount" :key="i" />
            </div>
            <div ref="feedTrigger" class="h-20" />
          </div>

          <div v-else class="space-y-8 pb-12">
            <div class="app-video-grid" style="--app-grid-min: 320px;">
              <SubscriptionCard
                v-for="sub in filteredChannels"
                :key="sub.id"
                :subscription="sub"
                @click="handleChannelClick(sub.id)"
                @toggleSpecial="toggleSpecialFollow"
              />
            </div>
            <div v-if="loadingChannels && !list.length" class="app-video-grid" style="--app-grid-min: 320px;">
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
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppBounceDots from '@/shared/components/AppBounceDots.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import { Button } from '@/shared/ui/button'
import SubscriptionSidebar from '@/features/video/components/SubscriptionSidebar.vue'
import SubscriptionCard from '@/features/video/components/feed/SubscriptionCard.vue'
import SubscriptionCardSkeleton from '@/features/video/components/feed/SubscriptionCardSkeleton.vue'
import RemoteChannelVideoGrid from '@/features/video/components/feed/RemoteChannelVideoGrid.vue'
import VideoItem from '@/features/video/components/feed/VideoItem.vue'
import VideoSkeleton from '@/features/video/components/feed/VideoSkeleton.vue'
import AddChannelDialog from '@/features/video/components/dialogs/AddChannelDialog.vue'
import ImportSubscriptionDialog from '@/features/video/components/dialogs/ImportSubscriptionDialog.vue'
import { useFeedFilters } from '../composables/useFeedFilters'
import { useSites } from '../composables/useSites'
import { useRemoteChannel } from '@/features/video/composables/useRemoteChannel'
import { useDesktopBridge } from '@/shared/composables/useDesktopBridge'
import { useRemoteVideoMapping } from '@/features/video/composables/useRemoteVideoMapping'
import { sortSubscriptions } from '@/features/video/lib/subscriptionSort'
import { getSubscriptions, getVideoList, updateSpecialFollowStatus } from '@/shared/api'
import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import { useSkeletonCount } from '@/features/video/composables/useSkeletonCount'
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
const specialFilter = ref<'all' | 'yes'>('all')
const activeChannelId = ref<string | number | null>(null)
const activeChannelNameCache = ref('')
const showAddDialog = ref(false)
const showImportDialog = ref(false)
const feedContainer = ref<HTMLElement | null>(null)
// The sidebar exposes its list container + load-more sentinel via defineExpose
// so this view's IntersectionObserver + scroll-reset can reach the DOM nodes
// inside the extracted component.
const sidebarRef = ref<{ listContainer: HTMLElement | null; loadMore: HTMLElement | null } | null>(null)

// --- Adaptive skeleton counts ---------------------------------------------
// Shared width measurement on the centered content wrapper. Two configs,
// one per branch (feed videos vs subscription channel cards).
const gridWrapper = ref<HTMLElement | null>(null)

// Skeleton counts mirror the auto-fill grids via the same minCardWidth/gap
// formula (no breakpoint tables to keep in sync with the CSS classes).
// Feed grid: `.app-video-grid--feed` (min 280px, gap-y 40px).
const { count: videoSkeletonCount, attachRef: videoGridRef } = useSkeletonCount({
  minCardWidth: 280,
  gap: 40,
  cardHeight: 220,
})

// Subscription card grid: `.app-video-grid` with --app-grid-min: 320px, gap 24px.
// Cards are taller (avatar header + 3 thumbs + footer ≈ 280px).
const { count: channelSkeletonCount, attachRef: channelGridRef } = useSkeletonCount({
  minCardWidth: 320,
  gap: 24,
  cardHeight: 280,
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
const gridMoreTrigger = ref<HTMLElement | null>(null)
let feedObserver: IntersectionObserver | null = null
let channelsObserver: IntersectionObserver | null = null
let gridObserver: IntersectionObserver | null = null

// Site-filter dropdown click-outside is now handled inside SubscriptionSidebar
// (the dropdown trigger lives there). showSiteDropdown is still owned here so
// the header/view can react to it, but the outside-click close is local to the
// sidebar component.

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
  nextTick(() => scrollToTop(sidebarRef.value?.listContainer ?? null))
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
  const channelsEl = sidebarRef.value?.listContainer ?? null

  // 1. Feed Observer
  feedObserver = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && !loadingFeed.value && !loadingMoreFeed.value && !feedFinished.value) fetchFeed()
  }, { root: scrollContainer, rootMargin: '800px' })
  if (feedTrigger.value) feedObserver.observe(feedTrigger.value)

  // 2. Channels Sidebar Observer — sentinel + scroll root both live inside the
  // extracted SubscriptionSidebar, reached via its defineExpose'd refs.
  channelsObserver = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && !loadingChannels.value && !loadingMoreChannels.value && !channelsFinished.value) fetchChannels()
  }, { root: channelsEl, rootMargin: '200px' })
  const channelsSentinel = sidebarRef.value?.loadMore ?? null
  if (channelsSentinel) channelsObserver.observe(channelsSentinel)

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
    nextTick(() => scrollToTop(sidebarRef.value?.listContainer ?? null))
  }, 250)
})
onUnmounted(() => {
  if (sidebarSearchTimer !== null) window.clearTimeout(sidebarSearchTimer)
  feedObserver?.disconnect(); channelsObserver?.disconnect(); gridObserver?.disconnect()
})
</script>
