<template>
  <div class="flex h-full overflow-hidden bg-background text-foreground selection:bg-primary/10">
    <aside class="hidden w-72 shrink-0 flex-col border-r border-border/50 bg-background lg:flex">
      <div class="flex h-14 shrink-0 items-center justify-between border-b border-border/50 px-4">
        <div class="min-w-0">
          <h1 class="truncate text-sm font-semibold">订阅</h1>
          <p class="mt-0.5 text-xs text-muted-foreground">{{ list.length }} 个频道</p>
        </div>
        <Button variant="ghost" size="icon" class="h-8 w-8 rounded-md" @click="showAddDialog = true">
          <AppIcon name="plus" class="w-4 h-4" />
        </Button>
      </div>

      <div class="shrink-0 space-y-2 border-b border-border/50 p-3">
        <div class="relative">
          <AppIcon name="search" class="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <input 
            v-model="sidebarSearch"
            placeholder="搜索订阅" 
            class="h-9 w-full rounded-md border border-border/50 bg-background pl-9 pr-3 text-sm outline-none transition-colors placeholder:text-muted-foreground/70 focus:border-ring"
          />
        </div>
        
        <div ref="siteFilterRef" class="relative">
          <button
            @click="showSiteDropdown = !showSiteDropdown"
            class="flex h-9 w-full items-center justify-between rounded-md border border-border/50 bg-background px-3 text-sm transition-colors hover:bg-accent/40"
            :class="site ? 'text-foreground' : 'text-muted-foreground'"
          >
            <div class="flex items-center gap-2">
              <AppIcon name="filter" class="h-3.5 w-3.5" />
              <span>{{ activeSiteLabel }}</span>
            </div>
            <AppIcon name="chevronRight" class="h-3.5 w-3.5 transition-transform" :class="{ 'rotate-90': showSiteDropdown }" />
          </button>

          <div v-if="showSiteDropdown" class="absolute left-0 right-0 top-full z-50 mt-1 rounded-lg border border-border/50 bg-background p-1 shadow-lg">
            <div class="max-h-[280px] overflow-y-auto custom-scrollbar">
              <button @click="site = ''; showSiteDropdown = false" class="flex h-8 w-full items-center rounded-md px-2.5 text-left text-sm transition-colors hover:bg-accent" :class="!site ? 'font-medium text-foreground' : 'text-muted-foreground'">全部来源</button>
              <button v-for="opt in siteOptionsList" :key="opt.value" @click="site = opt.value; showSiteDropdown = false" class="flex h-8 w-full items-center gap-2 rounded-md px-2.5 text-left text-sm transition-colors hover:bg-accent" :class="site === opt.value ? 'font-medium text-foreground' : 'text-muted-foreground'">
                <SiteIcon :site="opt.value" class="h-3.5 w-3.5 rounded-sm" />
                <span class="flex-1 truncate">{{ opt.label }}</span>
              </button>
            </div>
          </div>
        </div>

        <button
          type="button"
          class="flex h-9 w-full items-center gap-2 rounded-md border px-3 text-sm transition-colors"
          :class="specialFilter === 'yes' ? 'border-amber-400/40 bg-amber-400/10 text-amber-600' : 'border-border/50 bg-background text-muted-foreground hover:bg-accent/40 hover:text-foreground'"
          @click="toggleSpecialFilter"
        >
          <AppIcon name="star" class="h-3.5 w-3.5" :class="{ 'fill-current': specialFilter === 'yes' }" />
          <span class="flex-1 text-left">特别关注</span>
        </button>
      </div>

      <div ref="channelsContainer" class="flex-1 space-y-1 overflow-y-auto p-2 custom-scrollbar">
        <div
          v-for="sub in filteredChannels"
          :key="sub.id"
          role="button"
          tabindex="0"
          @click="handleChannelClick(sub.id)"
          @keydown.enter.prevent="handleChannelClick(sub.id)"
          @keydown.space.prevent="handleChannelClick(sub.id)"
          class="group flex h-10 w-full items-center gap-2.5 rounded-md px-2 text-left text-sm transition-colors"
          :class="activeChannelId === sub.id ? 'bg-accent text-foreground' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'"
        >
          <div class="relative shrink-0">
            <SubscriptionAvatar :src="sub.avatar" :name="sub.name" size="md" />
            <div v-if="sub.unread_count > 0" class="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-primary ring-2 ring-background" />
          </div>
          <span class="flex-1 truncate font-medium">{{ sub.name }}</span>
          <button
            type="button"
            class="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md opacity-100 transition-colors lg:opacity-0 lg:group-hover:opacity-100"
            :class="sub.is_special_followed ? 'text-amber-500' : 'text-muted-foreground/40 hover:bg-accent hover:text-foreground'"
            aria-label="切换特别关注"
            @click.stop="toggleSpecialFollow(sub)"
          >
            <AppIcon name="star" class="h-3.5 w-3.5" :class="{ 'fill-current': sub.is_special_followed }" />
          </button>
          <SiteTag :site="sub.site" class="origin-right scale-90 opacity-0 transition-opacity group-hover:opacity-100" />
        </div>

        <div v-if="loadingChannels" class="space-y-2 p-2">
          <div v-for="i in 5" :key="i" class="h-10 w-full animate-pulse rounded-md bg-accent/40" />
        </div>
        
        <div ref="channelsTrigger" class="flex h-10 w-full items-center justify-center">
          <div v-if="loadingMoreChannels" class="h-4 w-4 animate-spin rounded-full border-2 border-primary/20 border-t-primary" />
        </div>

        <div v-if="channelsFinished && !filteredChannels.length" class="py-10 text-center">
          <AppIcon name="inbox" class="mx-auto h-7 w-7 text-muted-foreground/30" />
          <p class="mt-2 text-xs font-medium text-muted-foreground">暂无匹配订阅</p>
        </div>
      </div>

      <div class="shrink-0 border-t border-border/50 p-3">
        <Button variant="outline" class="h-9 w-full justify-start rounded-md" @click="showImportDialog = true">
          <AppIcon name="download" class="mr-2 h-4 w-4 text-muted-foreground" />
          <span class="text-sm font-medium">导入订阅</span>
        </Button>
      </div>
    </aside>

    <main class="flex min-w-0 flex-1 flex-col bg-background">
      <header class="flex h-14 shrink-0 items-center justify-between border-b border-border/50 px-4 lg:px-6">
        <div class="flex min-w-0 items-center gap-3">
          <div class="min-w-0">
            <div class="flex min-w-0 items-center gap-2">
              <h2 class="max-w-[360px] truncate text-base font-semibold">
                {{ activeChannelName || '订阅动态' }}
              </h2>
              <div v-if="canOpenRemoteChannel" class="flex shrink-0 rounded-md border border-border/50 bg-muted p-0.5">
                <button
                  type="button"
                  class="inline-flex h-7 items-center gap-1.5 rounded-[5px] px-2.5 text-xs font-medium transition-colors"
                  :class="channelDataMode === 'local' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
                  @click="openLocalChannel"
                >
                  <AppIcon name="library" class="h-3.5 w-3.5" />
                  本地
                </button>
                <button
                  type="button"
                  class="inline-flex h-7 items-center gap-1.5 rounded-[5px] px-2.5 text-xs font-medium transition-colors"
                  :class="channelDataMode === 'remote' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
                  @click="openRemoteChannel"
                >
                  <AppIcon name="siteFallback" class="h-3.5 w-3.5" />
                  远端
                </button>
              </div>
              <button
                v-if="activeChannelId"
                type="button"
                class="inline-flex h-7 shrink-0 items-center gap-1.5 rounded-md border border-border/50 px-2.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent/60 hover:text-foreground"
                @click="openActiveChannelDetail"
              >
                <AppIcon name="chevronRight" class="h-3.5 w-3.5" />
                详情
              </button>
              <button
                v-if="activeChannel"
                type="button"
                class="inline-flex h-7 shrink-0 items-center justify-center rounded-md border px-2 transition-colors"
                :class="activeChannel.is_special_followed ? 'border-amber-400/40 bg-amber-400/10 text-amber-600' : 'border-border/50 text-muted-foreground hover:bg-accent/60 hover:text-foreground'"
                aria-label="切换特别关注"
                @click="toggleSpecialFollow(activeChannel)"
              >
                <AppIcon name="star" class="h-3.5 w-3.5" :class="{ 'fill-current': activeChannel.is_special_followed }" />
              </button>
            </div>
            <p class="mt-0.5 text-xs text-muted-foreground">
              {{ headerSubtitle }}
            </p>
          </div>
          <div v-if="headerLoading" class="flex gap-1">
            <div class="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.3s]" />
            <div class="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.15s]" />
            <div class="h-1.5 w-1.5 animate-bounce rounded-full bg-primary" />
          </div>
        </div>

        <div class="flex items-center gap-2">
          <div class="flex shrink-0 rounded-md bg-muted p-0.5">
            <button @click="showLocalFeed" class="h-8 rounded-[6px] px-3 text-sm font-medium transition-colors" :class="channelDataMode === 'local' && viewMode === 'feed' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'">最近发布</button>
            <button @click="showLocalGrid" class="h-8 rounded-[6px] px-3 text-sm font-medium transition-colors" :class="channelDataMode === 'local' && viewMode === 'grid' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'">频道</button>
          </div>
          <button class="hidden h-9 items-center gap-2 rounded-md border px-3 text-sm font-medium transition-colors md:flex" :class="nsfw === 'all' ? 'border-border/50 text-muted-foreground hover:bg-accent/60' : 'border-destructive/20 bg-destructive/10 text-destructive'" @click="nsfw = nsfw === 'all' ? 'yes' : 'all'">
            <span class="h-2 w-2 rounded-full" :class="nsfw === 'all' ? 'bg-muted-foreground/30' : 'bg-destructive'" />
            成年内容
          </button>
          <Button variant="ghost" size="icon" class="h-9 w-9 rounded-md" @click="handleRefresh">
            <AppIcon name="refresh" class="h-4 w-4" :class="{ 'animate-spin': headerLoading }" />
          </Button>
        </div>
      </header>

      <div ref="feedContainer" class="flex-1 overflow-y-auto custom-scrollbar">
        <div class="mx-auto w-full max-w-[1600px] p-4 lg:p-6">
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

          <div v-else-if="viewMode === 'feed'" class="space-y-10">
            <div v-if="!feedItems.length && !loadingFeed" class="flex min-h-[24rem] flex-col items-center justify-center text-center">
              <AppIcon name="inbox" class="h-9 w-9 text-muted-foreground/30" />
              <h3 class="mt-4 text-sm font-semibold">暂无内容</h3>
              <p class="mt-1 text-sm text-muted-foreground">订阅频道更新后会显示在这里。</p>
            </div>

            <div v-for="group in videoGroups" :key="group.title" class="space-y-4">
              <div class="flex h-7 items-center">
                <h3 class="text-xs font-semibold text-muted-foreground">{{ group.title }}</h3>
              </div>
              <div class="grid grid-cols-1 gap-x-5 gap-y-8 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 3xl:grid-cols-5">
                <VideoItem v-for="video in group.videos" :key="video.id" :video="video" show-avatar @openModal="handleOpenVideo" />
              </div>
            </div>

            <div v-if="loadingMoreFeed" class="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 3xl:grid-cols-5">
              <VideoSkeleton v-for="i in 8" :key="i" />
            </div>
            <div ref="feedTrigger" class="h-20" />
          </div>

          <div v-else class="space-y-6">
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
              <SubscriptionCard
                v-for="sub in filteredChannels"
                :key="sub.id"
                :subscription="sub"
                @click="handleChannelClick(sub.id)"
                @toggleSpecial="toggleSpecialFollow"
              />
            </div>
            <div v-if="loadingChannels && !list.length" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
              <SubscriptionCardSkeleton v-for="i in 12" :key="i" />
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
import { ref, computed, watch, onUnmounted, onMounted, nextTick, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { onClickOutside } from '@vueuse/core'
import AppIcon from '@/components/common/AppIcon.vue'
import { Button } from '@/components/ui/button'
import SubscriptionCard from '@/components/feed/SubscriptionCard.vue'
import SubscriptionCardSkeleton from '@/components/feed/SubscriptionCardSkeleton.vue'
import RemoteChannelVideoGrid from '@/components/feed/RemoteChannelVideoGrid.vue'
import VideoItem from '@/components/feed/VideoItem.vue'
import VideoSkeleton from '@/components/feed/VideoSkeleton.vue'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import SiteTag from '@/components/common/SiteTag.vue'
import SiteIcon from '@/components/common/SiteIcon.vue'
import AddChannelDialog from '@/components/dialogs/AddChannelDialog.vue'
import ImportSubscriptionDialog from '@/components/dialogs/ImportSubscriptionDialog.vue'
import { useFeedFilters } from '../composables/useFeedFilters'
import { useSites } from '../composables/useSites'
import { getSubscriptions, getVideoList, updateSpecialFollowStatus } from '@/api'
import { rememberVideoPlaybackSeed } from '@/composables/videoPlaybackSeed'

defineOptions({ name: 'Subscribed' })

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
const { nsfw, site } = useFeedFilters()
const { options: siteOptions, fetchSites } = useSites()

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

// Data State (Channels)
const list = ref<any[]>([])
const loadingChannels = ref(false)
const loadingMoreChannels = ref(false)
const channelsFinished = ref(false)
const channelsPage = ref(1)
const CHANNELS_PAGE_SIZE = 100
let channelsRequestToken = 0
let sidebarSearchTimer: number | null = null
const togglingSpecialIds = ref<Set<string | number>>(new Set())

// Data State (Feed)
const feedItems = ref<any[]>([])
const loadingFeed = ref(false)
const loadingMoreFeed = ref(false)
const feedFinished = ref(false)
const feedPage = ref(1)
const FEED_PAGE_SIZE = 48 // Increased for better dense layout
let feedRequestToken = 0
const remoteItems = ref<RemoteSearchItem[]>([])
const remoteLoading = ref(false)
const remoteAllLoaded = ref(false)
const remotePage = ref(1)
const remoteNextCursor = shallowRef<unknown>(null)
const remoteError = ref('')
let remoteRequestToken = 0
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
const canOpenRemoteChannel = computed(() => {
  return window.desktopApp?.isDesktop === true && !!activeChannel.value?.site && !!activeChannel.value?.url
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

const sortChannels = (items: any[]) => {
  return [...items].sort((a, b) => {
    if (a.is_special_followed !== b.is_special_followed) return a.is_special_followed ? -1 : 1
    return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
  })
}

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

const toggleSpecialFollow = async (subscription: any) => {
  if (!subscription?.id || togglingSpecialIds.value.has(subscription.id)) return

  const nextValue = !subscription.is_special_followed
  togglingSpecialIds.value = new Set(togglingSpecialIds.value).add(subscription.id)

  const { error } = await updateSpecialFollowStatus(subscription.id, nextValue)
  if (!error) applySpecialFollowState(subscription.id, nextValue)

  const nextIds = new Set(togglingSpecialIds.value)
  nextIds.delete(subscription.id)
  togglingSpecialIds.value = nextIds
}

const videoGroups = computed(() => {
  const groups: Record<string, any[]> = {}
  feedItems.value.forEach(video => {
    const publishDate = video.uploaded_at || video.created_at
    if (!publishDate) return
    const date = new Date(publishDate)
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1)
    let title = ''
    const videoDate = new Date(date.getFullYear(), date.getMonth(), date.getDate())
    if (videoDate.getTime() === today.getTime()) title = '今天'
    else if (videoDate.getTime() === yesterday.getTime()) title = '昨天'
    else {
      const diffDays = Math.floor((today.getTime() - videoDate.getTime()) / (1000 * 60 * 60 * 24))
      if (diffDays < 7) title = '本周'
      else if (diffDays < 30) title = '本月'
      else title = `${date.getFullYear()}年${date.getMonth() + 1}月`
    }
    if (!groups[title]) groups[title] = []
    groups[title].push(video)
  })
  return Object.entries(groups).map(([title, videos]) => ({ title, videos }))
})

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
    const { data } = await getSubscriptions(params)
    if (requestToken !== channelsRequestToken) return
    const items = data?.data || data?.items || []
    if (isReset) list.value = items; else list.value.push(...items)
    if (items.length < CHANNELS_PAGE_SIZE) channelsFinished.value = true
    else channelsPage.value = requestPage + 1
  } finally {
    if (requestToken === channelsRequestToken) {
      loadingChannels.value = false; loadingMoreChannels.value = false
    }
  }
}

const fetchFeed = async (isReset = false) => {
  if (!isReset && (loadingFeed.value || loadingMoreFeed.value || feedFinished.value)) return
  if (isReset) { feedPage.value = 1; feedFinished.value = false; loadingFeed.value = true; loadingMoreFeed.value = false } 
  else { loadingMoreFeed.value = true }

  const requestToken = ++feedRequestToken
  const requestPage = feedPage.value
  try {
    const nsfwValue = nsfw.value === 'only' ? 'yes' : (['all', 'yes', 'no'].includes(nsfw.value) ? nsfw.value : 'all')
    const { data } = await getVideoList({
      page: requestPage,
      pageSize: FEED_PAGE_SIZE,
      page_size: FEED_PAGE_SIZE,
      nsfw: nsfwValue,
      site: site.value || undefined,
      subscription_id: activeChannelId.value || undefined,
      sort_by: 'publish_date',
      special: !activeChannelId.value && specialFilter.value === 'yes' ? 'yes' : undefined,
    })
    if (requestToken !== feedRequestToken) return
    const items = data?.data || data?.items || []
    if (isReset) feedItems.value = items; else feedItems.value.push(...items)
    if (items.length < FEED_PAGE_SIZE) feedFinished.value = true
    else feedPage.value = requestPage + 1
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
const handleOpenVideo = (video: any) => { rememberVideoPlaybackSeed(video); router.push(`/video/${video.id}`) }
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
  const channel = activeChannel.value
  if (!channel || !canOpenRemoteChannel.value) return

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
    if (requestToken === remoteRequestToken) remoteLoading.value = false
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
  const channel = activeChannel.value
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
  remoteItems.value = []
  remotePage.value = 1
  remoteNextCursor.value = null
  remoteAllLoaded.value = false
  remoteError.value = ''
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
