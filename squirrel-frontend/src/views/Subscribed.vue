<template>
  <div class="flex h-full bg-background overflow-hidden selection:bg-primary/10">
    <!-- 1. Left Sidebar: Channels Navigation -->
    <aside 
      class="hidden lg:flex flex-col w-[280px] border-r border-border/40 bg-card/30 backdrop-blur-sm transition-all duration-300 relative z-20"
    >
      <!-- Sidebar Header -->
      <div class="p-4 border-b border-border/40 flex items-center justify-between shrink-0">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
            <AppIcon name="library" class="w-4 h-4" />
          </div>
          <span class="font-bold text-[15px] tracking-tight">我的订阅</span>
        </div>
        <Button variant="ghost" size="icon" class="h-8 w-8 rounded-lg hover:bg-accent/50" @click="showAddDialog = true">
          <AppIcon name="plus" class="w-4 h-4" />
        </Button>
      </div>

      <!-- Sidebar Search & Filter -->
      <div class="p-3 space-y-2 shrink-0 border-b border-border/10">
        <div class="relative group">
          <AppIcon name="search" class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/40 group-focus-within:text-primary transition-colors" />
          <input 
            v-model="sidebarSearch"
            placeholder="搜索订阅..." 
            class="w-full h-9 pl-9 pr-3 rounded-xl bg-accent/30 border-transparent text-[13px] transition-all focus:bg-background focus:ring-2 focus:ring-primary/20 outline-none"
          />
        </div>
        
        <div class="relative group/filter" ref="siteFilterRef">
          <button
            @click="showSiteDropdown = !showSiteDropdown"
            class="w-full h-8 flex items-center justify-between px-2.5 rounded-lg text-[11px] font-bold transition-all border border-border/20 hover:border-border/50 hover:bg-accent/20"
            :class="site ? 'bg-primary/5 text-primary border-primary/20' : 'text-muted-foreground'"
          >
            <div class="flex items-center gap-2">
              <AppIcon name="filter" class="w-3 h-3" />
              <span>{{ activeSiteLabel }}</span>
            </div>
            <AppIcon name="chevronRight" class="w-3 h-3 transition-transform duration-300" :class="{ 'rotate-90': !showSiteDropdown, 'rotate-180': showSiteDropdown }" />
          </button>

          <div v-if="showSiteDropdown" class="absolute top-full left-0 right-0 mt-1 bg-popover border border-border/50 rounded-xl shadow-2xl z-50 py-1.5 animate-in fade-in slide-in-from-top-2 duration-200">
            <div class="max-h-[280px] overflow-y-auto custom-scrollbar">
              <button @click="site = ''; showSiteDropdown = false" class="w-full flex items-center px-3 py-2 text-[12px] font-medium hover:bg-accent transition-colors" :class="!site ? 'text-primary' : 'text-foreground/70'">全部来源</button>
              <div class="h-px bg-border/10 my-1 mx-2" />
              <button v-for="opt in siteOptionsList" :key="opt.value" @click="site = opt.value; showSiteDropdown = false" class="w-full flex items-center gap-2.5 px-3 py-2 text-[12px] font-medium hover:bg-accent transition-colors text-left" :class="site === opt.value ? 'text-primary bg-primary/5' : 'text-foreground/70'">
                <SiteIcon :site="opt.value" class="w-3.5 h-3.5 rounded-sm" />
                <span class="flex-1 truncate">{{ opt.label }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Channels List (Infinite Scroll) -->
      <div ref="channelsContainer" class="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-0.5">
        <button
          v-for="sub in filteredChannels"
          :key="sub.id"
          @click="handleChannelClick(sub.id)"
          class="w-full flex items-center gap-3 p-2 rounded-xl transition-all group relative overflow-hidden"
          :class="activeChannelId === sub.id ? 'bg-primary/10 text-primary' : 'hover:bg-accent/50 text-muted-foreground hover:text-foreground'"
        >
          <div class="relative shrink-0">
            <SubscriptionAvatar :src="sub.avatar" :name="sub.name" size="sm" class="w-7 h-7 rounded-lg object-cover ring-1 ring-border/20" />
            <div v-if="sub.unread_count > 0" class="absolute -top-1 -right-1 w-2.5 h-2.5 bg-primary rounded-full border-2 border-background" />
          </div>
          <span class="flex-1 text-[13px] font-medium truncate text-left">{{ sub.name }}</span>
          <SiteTag :site="sub.site" class="opacity-0 group-hover:opacity-100 transition-opacity scale-75 origin-right" />
        </button>

        <!-- Channel Loading States -->
        <div v-if="loadingChannels" class="space-y-2 p-2">
          <div v-for="i in 5" :key="i" class="h-10 w-full bg-accent/20 animate-pulse rounded-xl" />
        </div>
        
        <div ref="channelsTrigger" class="h-10 w-full flex items-center justify-center">
          <div v-if="loadingMoreChannels" class="w-4 h-4 border-2 border-primary/20 border-t-primary rounded-full animate-spin" />
        </div>

        <div v-if="channelsFinished && !filteredChannels.length" class="py-10 text-center space-y-2">
          <AppIcon name="inbox" class="w-8 h-8 mx-auto text-muted-foreground/20" />
          <p class="text-[12px] text-muted-foreground/40 font-medium">暂无匹配订阅</p>
        </div>
      </div>

      <!-- Sidebar Footer -->
      <div class="p-4 border-t border-border/40 space-y-2">
        <Button variant="outline" class="w-full justify-start h-10 rounded-xl border-border/40 hover:bg-accent/50" @click="showImportDialog = true">
          <AppIcon name="download" class="w-4 h-4 mr-2.5 text-muted-foreground" />
          <span class="text-[13px] font-semibold">导入订阅</span>
        </Button>
      </div>
    </aside>

    <!-- 2. Main Content: Video Feed -->
    <main class="flex-1 flex flex-col min-w-0 bg-background/50 relative">
      <header class="sticky top-0 z-30 w-full bg-background/80 backdrop-blur-xl border-b border-border/40 shrink-0">
        <div class="px-6 h-16 flex items-center justify-between">
          <div class="flex items-center gap-4">
            <h2 class="text-[18px] font-black tracking-tight text-foreground truncate max-w-[300px]">
              {{ activeChannelName || '订阅动态' }}
            </h2>
            <div v-if="loadingFeed" class="flex gap-1">
              <div class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:-0.3s]" />
              <div class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:-0.15s]" />
              <div class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" />
            </div>
          </div>

          <div class="flex items-center gap-3">
            <div class="flex bg-accent/30 rounded-xl p-1 shrink-0">
              <button @click="viewMode = 'feed'" class="px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all" :class="viewMode === 'feed' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'">最近发布</button>
              <button @click="viewMode = 'grid'" class="px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all" :class="viewMode === 'grid' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'">频道概览</button>
            </div>
            <div class="w-px h-6 bg-border/20 mx-1 hidden md:block" />
            <button class="h-9 px-4 rounded-xl text-[11px] font-bold transition-all border flex items-center gap-2 shrink-0" :class="nsfw === 'all' ? 'bg-accent/20 text-muted-foreground/60 border-transparent' : 'bg-destructive/10 text-destructive border-destructive/20'" @click="nsfw = nsfw === 'all' ? 'yes' : 'all'"><div class="w-2 h-2 rounded-full" :class="nsfw === 'all' ? 'bg-muted-foreground/20' : 'bg-destructive animate-pulse'" />成年内容</button>
            <Button variant="ghost" size="icon" class="h-9 w-9 rounded-xl hover:bg-accent/50" @click="handleRefresh"><AppIcon name="refresh" class="w-4 h-4" :class="{ 'animate-spin': loadingFeed }" /></Button>
          </div>
        </div>
      </header>

      <div class="flex-1 overflow-y-auto custom-scrollbar p-6 lg:p-8" ref="feedContainer">
        <div class="max-w-[1600px] mx-auto">
          <div v-if="viewMode === 'feed'" class="space-y-12">
            <div v-if="!feedItems.length && !loadingFeed" class="flex flex-col items-center justify-center py-32 text-center animate-in fade-in zoom-in duration-700">
              <div class="w-20 h-20 rounded-3xl bg-accent/20 flex items-center justify-center mb-6"><AppIcon name="inbox" class="w-10 h-10 text-muted-foreground/20" /></div>
              <h3 class="text-xl font-bold mb-2">空空如也</h3>
              <p class="text-muted-foreground text-sm max-w-[280px]">订阅更多频道以获取最新的视频资讯动态。</p>
            </div>

            <div v-for="group in videoGroups" :key="group.title" class="space-y-6">
              <div class="flex items-center gap-4">
                <h3 class="text-[13px] font-black uppercase tracking-[0.2em] text-muted-foreground/60">{{ group.title }}</h3>
                <div class="h-px flex-1 bg-gradient-to-r from-border/40 to-transparent" />
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 3xl:grid-cols-5 gap-x-6 gap-y-10">
                <VideoItem v-for="video in group.videos" :key="video.id" :video="video" show-avatar @openModal="handleOpenVideo" />
              </div>
            </div>

            <div v-if="loadingMoreFeed" class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 3xl:grid-cols-5 gap-6 mt-10">
              <VideoSkeleton v-for="i in 8" :key="i" />
            </div>
            <div ref="feedTrigger" class="h-20" />
          </div>

          <div v-else class="space-y-8">
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6 gap-6">
              <SubscriptionCard v-for="sub in filteredChannels" :key="sub.id" :subscription="sub" @click="handleChannelClick(sub.id)" />
            </div>
            <div v-if="loadingChannels && !list.length" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6 gap-6">
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
