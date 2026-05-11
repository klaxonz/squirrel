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
      </div>

      <div ref="channelsContainer" class="flex-1 space-y-1 overflow-y-auto p-2 custom-scrollbar">
        <button
          v-for="sub in filteredChannels"
          :key="sub.id"
          @click="handleChannelClick(sub.id)"
          class="group flex h-10 w-full items-center gap-2.5 rounded-md px-2 text-left text-sm transition-colors"
          :class="activeChannelId === sub.id ? 'bg-accent text-foreground' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'"
        >
          <div class="relative shrink-0">
            <SubscriptionAvatar :src="sub.avatar" :name="sub.name" size="sm" class="h-7 w-7 rounded-md object-cover" />
            <div v-if="sub.unread_count > 0" class="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-primary ring-2 ring-background" />
          </div>
          <span class="flex-1 truncate font-medium">{{ sub.name }}</span>
          <SiteTag :site="sub.site" class="origin-right scale-90 opacity-0 transition-opacity group-hover:opacity-100" />
        </button>

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
            <h2 class="max-w-[360px] truncate text-base font-semibold">
              {{ activeChannelName || '订阅动态' }}
            </h2>
            <p class="mt-0.5 text-xs text-muted-foreground">
              {{ viewMode === 'feed' ? `${feedItems.length} 个视频` : `${filteredChannels.length} 个频道` }}
            </p>
          </div>
          <div v-if="loadingFeed" class="flex gap-1">
            <div class="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.3s]" />
            <div class="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.15s]" />
            <div class="h-1.5 w-1.5 animate-bounce rounded-full bg-primary" />
          </div>
        </div>

        <div class="flex items-center gap-2">
          <div class="flex shrink-0 rounded-md bg-muted p-0.5">
            <button @click="viewMode = 'feed'" class="h-8 rounded-[6px] px-3 text-sm font-medium transition-colors" :class="viewMode === 'feed' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'">最近发布</button>
            <button @click="viewMode = 'grid'" class="h-8 rounded-[6px] px-3 text-sm font-medium transition-colors" :class="viewMode === 'grid' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'">频道</button>
          </div>
          <button class="hidden h-9 items-center gap-2 rounded-md border px-3 text-sm font-medium transition-colors md:flex" :class="nsfw === 'all' ? 'border-border/50 text-muted-foreground hover:bg-accent/60' : 'border-destructive/20 bg-destructive/10 text-destructive'" @click="nsfw = nsfw === 'all' ? 'yes' : 'all'">
            <span class="h-2 w-2 rounded-full" :class="nsfw === 'all' ? 'bg-muted-foreground/30' : 'bg-destructive'" />
            成年内容
          </button>
          <Button variant="ghost" size="icon" class="h-9 w-9 rounded-md" @click="handleRefresh">
            <AppIcon name="refresh" class="h-4 w-4" :class="{ 'animate-spin': loadingFeed }" />
          </Button>
        </div>
      </header>

      <div ref="feedContainer" class="flex-1 overflow-y-auto custom-scrollbar">
        <div class="mx-auto w-full max-w-[1600px] p-4 lg:p-6">
          <div v-if="viewMode === 'feed'" class="space-y-10">
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
              <SubscriptionCard v-for="sub in filteredChannels" :key="sub.id" :subscription="sub" @click="handleChannelClick(sub.id)" />
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
import { ref, computed, watch, onUnmounted, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { onClickOutside } from '@vueuse/core'
import AppIcon from '@/components/common/AppIcon.vue'
import { Button } from '@/components/ui/button'
import SubscriptionCard from '@/components/feed/SubscriptionCard.vue'
import SubscriptionCardSkeleton from '@/components/feed/SubscriptionCardSkeleton.vue'
import VideoItem from '@/components/feed/VideoItem.vue'
import VideoSkeleton from '@/components/feed/VideoSkeleton.vue'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import SiteTag from '@/components/common/SiteTag.vue'
import SiteIcon from '@/components/common/SiteIcon.vue'
import AddChannelDialog from '@/components/dialogs/AddChannelDialog.vue'
import ImportSubscriptionDialog from '@/components/dialogs/ImportSubscriptionDialog.vue'
import { useFeedFilters } from '../composables/useFeedFilters'
import { useSites } from '../composables/useSites'
import { getSubscriptions, getVideoList } from '@/api'
import { rememberVideoPlaybackSeed } from '@/composables/videoPlaybackSeed'

defineOptions({ name: 'Subscribed' })

const router = useRouter()
const { nsfw, site } = useFeedFilters()
const { options: siteOptions, fetchSites } = useSites()

// UI State
const viewMode = ref<'feed' | 'grid'>('feed')
const sidebarSearch = ref('')
const showSiteDropdown = ref(false)
const siteFilterRef = ref<HTMLElement | null>(null)
const activeChannelId = ref<string | number | null>(null)
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

// Data State (Feed)
const feedItems = ref<any[]>([])
const loadingFeed = ref(false)
const loadingMoreFeed = ref(false)
const feedFinished = ref(false)
const feedPage = ref(1)
const FEED_PAGE_SIZE = 48 // Increased for better dense layout

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
  return list.value.find(c => c.id === activeChannelId.value)?.name || ''
})

const siteOptionsList = computed(() => siteOptions.value || [])
const activeSiteLabel = computed(() => {
  if (!site.value) return '全部来源'
  return siteOptionsList.value.find(opt => opt.value === site.value)?.label || '未知来源'
})

const filteredChannels = computed(() => {
  let res = list.value
  // Site filtering is handled server-side via the `site` API parameter
  if (sidebarSearch.value) {
    const q = sidebarSearch.value.toLowerCase()
    res = res.filter(c => c.name.toLowerCase().includes(q))
  }
  return res
})

const videoGroups = computed(() => {
  const groups: Record<string, any[]> = {}
  feedItems.value.forEach(video => {
    const publishDate = video.publish_date || video.created_at
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
  if (loadingChannels.value || (loadingMoreChannels.value && !isReset) || (channelsFinished.value && !isReset)) return
  if (isReset) { channelsPage.value = 1; channelsFinished.value = false; loadingChannels.value = true } 
  else { loadingMoreChannels.value = true }

  try {
    const nsfwValue = nsfw.value === 'only' ? 'yes' : (['all', 'yes', 'no'].includes(nsfw.value) ? nsfw.value : 'all')
    const params: Record<string, unknown> = {
      nsfw: nsfwValue,
      page: channelsPage.value,
      pageSize: CHANNELS_PAGE_SIZE,
      page_size: CHANNELS_PAGE_SIZE,
    }
    if (site.value) params.site = site.value
    const { data } = await getSubscriptions(params)
    const items = data?.data || data?.items || []
    if (isReset) list.value = items; else list.value.push(...items)
    if (items.length < CHANNELS_PAGE_SIZE) channelsFinished.value = true
    else channelsPage.value++
  } finally {
    loadingChannels.value = false; loadingMoreChannels.value = false
  }
}

const fetchFeed = async (isReset = false) => {
  if (loadingFeed.value || (loadingMoreFeed.value && !isReset) || (feedFinished.value && !isReset)) return
  if (isReset) { feedPage.value = 1; feedFinished.value = false; loadingFeed.value = true } 
  else { loadingMoreFeed.value = true }

  try {
    const nsfwValue = nsfw.value === 'only' ? 'yes' : (['all', 'yes', 'no'].includes(nsfw.value) ? nsfw.value : 'all')
    const { data } = await getVideoList({
      page: feedPage.value,
      pageSize: FEED_PAGE_SIZE,
      page_size: FEED_PAGE_SIZE,
      nsfw: nsfwValue,
      subscription_id: activeChannelId.value || undefined,
      sort_by: 'publish_date'
    })
    const items = data?.data || data?.items || []
    if (isReset) feedItems.value = items; else feedItems.value.push(...items)
    if (items.length < FEED_PAGE_SIZE) feedFinished.value = true
    else feedPage.value++
  } finally {
    loadingFeed.value = false; loadingMoreFeed.value = false
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
  activeChannelId.value = activeChannelId.value === id ? null : id
  viewMode.value = 'feed'; fetchFeed(true)
  scrollToTop(feedContainer.value)
}

const handleRefresh = () => {
  fetchChannels(true); fetchFeed(true)
  resetAllScroll()
}
const handleOpenVideo = (video: any) => { rememberVideoPlaybackSeed(video); router.push(`/video/${video.id}`) }

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

watch([nsfw, site], () => { fetchChannels(true); fetchFeed(true); resetAllScroll() })

watch(sidebarSearch, () => { nextTick(() => scrollToTop(channelsContainer.value)) })
onUnmounted(() => { feedObserver?.disconnect(); channelsObserver?.disconnect(); gridObserver?.disconnect() })
</script>

<style scoped>
.no-scrollbar::-webkit-scrollbar { display: none; }
.no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
.custom-scrollbar::-webkit-scrollbar { width: 5px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(var(--primary), 0.1); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(var(--primary), 0.2); }
</style>
