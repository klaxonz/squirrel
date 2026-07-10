<template>
  <AppPageShell variant="compact" fill>
    <div class="subscription-page">
      <div class="subscription-control-bar">
        <nav class="subscription-view-nav" aria-label="订阅视图">
          <Button
            v-for="option in viewOptions"
            :key="option.value"
            unstyled
            type="button"
            class="subscription-view-nav__item"
            :class="{ 'is-active': activeView === option.value }"
            :aria-current="activeView === option.value ? 'page' : undefined"
            @click="activeView = option.value"
          >
            <AppIcon :name="option.icon" class="h-4 w-4" />
            <span>{{ option.label }}</span>
            <span
              v-if="option.count != null && option.count > 0"
              class="subscription-view-nav__count app-mono"
            >
              {{ option.count > 999 ? '999+' : option.count }}
            </span>
          </Button>
        </nav>

        <section class="subscription-toolbar" aria-label="订阅筛选和操作">
          <AppSearchInput
            v-if="activeView === 'channels'"
            :model-value="channelSearch"
            class="subscription-toolbar__search"
            placeholder="搜索频道..."
            aria-label="搜索频道"
            @update:model-value="channelSearch = $event"
          />

          <Popover>
            <PopoverTrigger as-child>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                class="subscription-toolbar__filter"
                :class="{ 'is-active': activeFilterCount > 0 }"
                :aria-label="activeFilterCount > 0 ? `筛选，已启用 ${activeFilterCount} 项` : '筛选'"
              >
                <AppIcon name="filter" class="h-3.5 w-3.5" />
                <span>筛选</span>
                <span
                  v-if="activeFilterCount > 0"
                  class="subscription-toolbar__filter-count app-mono"
                >
                  {{ activeFilterCount }}
                </span>
              </Button>
            </PopoverTrigger>

            <PopoverContent
              align="end"
              :side-offset="8"
              class="w-80 p-0"
            >
              <div class="subscription-filter-panel">
                <header class="subscription-filter-panel__header">
                  <div>
                    <strong>筛选</strong>
                    <span>{{ filterDescription }}</span>
                  </div>
                  <Button
                    v-if="activeFilterCount > 0"
                    type="button"
                    variant="ghost"
                    size="xs"
                    @click="clearToolbarFilters"
                  >
                    重置
                  </Button>
                </header>

                <div class="subscription-filter-panel__fields">
                  <label class="subscription-filter-panel__field">
                    <span>来源</span>
                    <Select
                      :model-value="site || 'all'"
                      @update:model-value="handleSiteFilterChange"
                    >
                      <SelectTrigger aria-label="按来源筛选">
                        <SelectValue placeholder="全部来源" />
                      </SelectTrigger>
                      <SelectContent class="min-w-48">
                        <SelectItem value="all">全部来源</SelectItem>
                        <SelectItem
                          v-for="option in siteOptionsList"
                          :key="option.value"
                          :value="option.value"
                        >
                          <span class="subscription-filter-panel__site-option">
                            <SiteIcon :site="option.value" class="h-4 w-4 rounded-sm" />
                            <span>{{ option.label }}</span>
                          </span>
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </label>

                  <label v-if="isFeedView" class="subscription-filter-panel__field">
                    <span>内容分级</span>
                    <Select
                      :model-value="nsfw"
                      @update:model-value="handleNsfwFilterChange"
                    >
                      <SelectTrigger aria-label="内容分级">
                        <SelectValue placeholder="全部内容" />
                      </SelectTrigger>
                      <SelectContent class="min-w-36">
                        <SelectItem
                          v-for="option in contentLevelOptions"
                          :key="option.value"
                          :value="option.value"
                        >
                          {{ option.label }}
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </label>

                  <label
                    v-else-if="activeView === 'channels'"
                    class="subscription-filter-panel__toggle"
                  >
                    <span>
                      <strong>特别关注</strong>
                      <small>只显示特别关注的频道</small>
                    </span>
                    <Switch
                      :model-value="librarySpecialOnly"
                      aria-label="只显示特别关注的频道"
                      @update:model-value="librarySpecialOnly = $event"
                    />
                  </label>
                </div>
              </div>
            </PopoverContent>
          </Popover>

          <span class="subscription-toolbar__divider" aria-hidden="true" />

          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            class="subscription-toolbar__icon-action"
            :loading="pageLoading"
            title="刷新当前视图"
            aria-label="刷新当前视图"
            @click="refreshCurrentView"
          >
            <AppIcon v-if="!pageLoading" name="refresh" class="h-4 w-4" />
          </Button>
          <Button
            v-if="activeView === 'channels'"
            type="button"
            variant="ghost"
            size="icon-sm"
            class="subscription-toolbar__icon-action"
            title="导入订阅"
            aria-label="导入订阅"
            @click="showImportDialog = true"
          >
            <AppIcon name="download" class="h-4 w-4" />
          </Button>
          <Button
            type="button"
            size="sm"
            class="subscription-toolbar__add"
            @click="showAddDialog = true"
          >
            <AppIcon name="plus" class="h-4 w-4" />
            添加订阅
          </Button>
        </section>
      </div>

      <div class="subscription-workspace">
        <main ref="contentScroll" class="subscription-content custom-scrollbar">
          <template v-if="isFeedView">
            <div v-if="feedError && !feedItems.length" class="subscription-content__empty">
              <AppEmptyState variant="error" title="内容加载失败" :copy="feedError">
                <template #actions>
                  <Button variant="outline" size="sm" @click="fetchFeed(true)">重试</Button>
                </template>
              </AppEmptyState>
            </div>

            <div v-else-if="loadingFeed && !feedItems.length" class="subscription-feed-skeletons">
              <AppSkeleton
                v-for="index in 7"
                :key="index"
                height="6.5rem"
                rounded="var(--radius-lg)"
                shimmer
              />
            </div>

            <div v-else-if="!feedItems.length" class="subscription-content__empty">
              <AppEmptyState
                variant="plain"
                :icon="activeView === 'inbox' ? 'inbox' : 'subscriptions'"
                :title="feedEmptyTitle"
                :copy="feedEmptyCopy"
              >
                <template v-if="channelsTotal === 0 && !feedSearch" #actions>
                  <Button size="sm" @click="showAddDialog = true">添加订阅</Button>
                  <Button variant="outline" size="sm" @click="showImportDialog = true">导入订阅</Button>
                </template>
              </AppEmptyState>
            </div>

            <div v-else class="subscription-feed">
              <section
                v-for="day in feedDayGroups"
                :key="day.key"
                class="subscription-feed-day"
              >
                <header class="subscription-feed-day__header">
                  <h2>{{ day.label }}</h2>
                  <span>{{ day.count }} 条更新</span>
                </header>

                <div class="subscription-feed-day__items">
                  <SubscriptionInboxItem
                    v-for="item in day.items"
                    :key="item.video.id"
                    :video="item.video"
                    :channel-name="item.channelName"
                    :channel-avatar="item.channelAvatar"
                    :subscription-id="item.subscriptionId"
                    @open="openVideo"
                    @open-channel="inspectChannelById"
                    @read-change="handleReadChange"
                  />
                </div>
              </section>
            </div>

            <div ref="feedTrigger" class="subscription-load-trigger">
              <AppSpinner v-if="loadingMoreFeed" />
            </div>
          </template>

          <template v-else>
            <div class="subscription-list-view">
              <div v-if="channelsError && !visibleChannels.length" class="subscription-content__empty">
                <AppEmptyState variant="error" title="频道加载失败" :copy="channelsError">
                  <template #actions>
                    <Button variant="outline" size="sm" @click="fetchChannels(true)">重试</Button>
                  </template>
                </AppEmptyState>
              </div>

              <div v-else-if="loadingChannels && !visibleChannels.length" class="subscription-channel-table">
                <div class="subscription-channel-table__body">
                  <SubscriptionCardSkeleton v-for="index in 10" :key="index" />
                </div>
              </div>

              <div v-else-if="!visibleChannels.length" class="subscription-content__empty">
                <AppEmptyState
                  variant="plain"
                  :icon="activeView === 'issues' ? 'statusSuccess' : 'subscriptions'"
                  :title="activeView === 'issues' ? '没有需要处理的频道' : '没有匹配频道'"
                  :copy="activeView === 'issues' ? '当前所有频道同步状态正常。' : '调整搜索或筛选条件后再试。'"
                />
              </div>

              <section v-else class="subscription-channel-table" aria-label="订阅频道列表">
                <div class="subscription-channel-table__header" aria-hidden="true">
                  <span>频道</span>
                  <span>视频</span>
                  <span>未读</span>
                  <span>最近成功</span>
                  <span>同步状态</span>
                  <span />
                </div>
                <div class="subscription-channel-table__body">
                  <SubscriptionCard
                    v-for="channel in visibleChannels"
                    :key="channel.id"
                    :subscription="channel"
                    :selected="selectedChannel?.id === channel.id"
                    :toggling="togglingSpecialIds.has(channel.id)"
                    @click="selectChannel(channel)"
                    @toggle-special="toggleSpecialFollow"
                  />
                </div>
              </section>

              <div
                v-if="activeView === 'channels'"
                ref="channelTrigger"
                class="subscription-load-trigger"
              >
                <AppSpinner v-if="loadingMoreChannels" />
              </div>
            </div>
          </template>
        </main>

        <SubscriptionChannelInspector
          v-if="selectedChannel"
          :channel="selectedChannel"
          :can-open-remote="canOpenSelectedRemote"
          :refreshing="refreshingChannelId === selectedChannel.id"
          :toggling-special="togglingSpecialIds.has(selectedChannel.id)"
          @close="selectedChannelSnapshot = null"
          @open-detail="openSubscription(selectedChannel.id)"
          @open-remote="openSelectedRemote"
          @refresh="refreshSelectedChannel"
          @toggle-special="toggleSpecialFollow(selectedChannel)"
          @open-video="openRecentVideo"
        />
      </div>
    </div>

    <AddChannelDialog
      :show="showAddDialog"
      @added="handleSubscriptionsChanged"
      @close="showAddDialog = false"
    />
    <ImportSubscriptionDialog
      :show="showImportDialog"
      @imported="handleSubscriptionsChanged"
      @close="showImportDialog = false"
    />
  </AppPageShell>
</template>

<script setup lang="ts">
import {
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
  watch,
} from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppSearchInput from '@/shared/components/layout/AppSearchInput.vue'
import SiteIcon from '@/shared/components/SiteIcon.vue'
import { Button } from '@/shared/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/shared/ui/popover'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/select'
import { Switch } from '@/shared/ui/switch'
import { useToast } from '@/shared/components/toast/useToast'
import { errorMessage } from '@/shared/lib/errorMessage'
import { useUIStore } from '@/shared/stores/ui'
import SubscriptionCard from '@/features/video/components/feed/SubscriptionCard.vue'
import SubscriptionCardSkeleton from '@/features/video/components/feed/SubscriptionCardSkeleton.vue'
import SubscriptionInboxItem from '@/features/video/components/subscription/SubscriptionInboxItem.vue'
import SubscriptionChannelInspector from '@/features/video/components/subscription/SubscriptionChannelInspector.vue'
import AddChannelDialog from '@/features/video/components/dialogs/AddChannelDialog.vue'
import ImportSubscriptionDialog from '@/features/video/components/dialogs/ImportSubscriptionDialog.vue'
import { useSites } from '@/features/video/composables/useSites'
import { useDesktopBridge } from '@/shared/composables/useDesktopBridge'
import { useVideoCardNavigation } from '@/features/video/composables/useVideoCardNavigation'
import { sortSubscriptions } from '@/features/video/lib/subscriptionSort'
import { isSubscriptionSyncFailed } from '@/features/video/lib/subscriptionPresenters'
import {
  getSubscriptionDetail,
  getSubscriptions,
  getVideoList,
  triggerRefresh,
  updateSpecialFollowStatus,
} from '@/shared/api'
import type { AppIconName } from '@/shared/icons/app-icons'
import type {
  SubscriptionDetail,
  SubscriptionListItem,
} from '@/features/video/types/subscription'
import type {
  VideoListItem,
  VideoProfile,
} from '@/features/video/types/video'

defineOptions({ name: 'Subscribed' })

type SubscriptionView = 'inbox' | 'activity' | 'special' | 'issues' | 'channels'

type FeedDayItem = {
  video: VideoListItem
  channelName: string
  channelAvatar: string | null
  subscriptionId: string | number | null
}

type FeedDayGroup = {
  key: string
  label: string
  count: number
  items: FeedDayItem[]
}

const router = useRouter()
const uiStore = useUIStore()
const toast = useToast()
const desktopBridge = useDesktopBridge()
const { openVideo, openSubscription } = useVideoCardNavigation(router)
const { options: siteOptions, fetchSites } = useSites()

const activeView = ref<SubscriptionView>('inbox')
const feedSearch = ref('')
const channelSearch = ref('')
const site = ref<string | undefined>()
const nsfw = ref<'all' | 'yes' | 'no'>('all')
const librarySpecialOnly = ref(false)
const showAddDialog = ref(false)
const showImportDialog = ref(false)

const contentScroll = ref<HTMLElement | null>(null)
const feedTrigger = ref<HTMLElement | null>(null)
const channelTrigger = ref<HTMLElement | null>(null)
let feedObserver: IntersectionObserver | null = null
let channelObserver: IntersectionObserver | null = null
let feedSearchTimer: number | null = null
let channelSearchTimer: number | null = null

const channels = ref<SubscriptionListItem[]>([])
const channelsTotal = ref(0)
const channelsPage = ref(1)
const channelsFinished = ref(false)
const loadingChannels = ref(false)
const loadingMoreChannels = ref(false)
const channelsError = ref<string | null>(null)
const CHANNEL_PAGE_SIZE = 100
let channelsRequestToken = 0

const feedItems = ref<VideoListItem[]>([])
const feedCursor = ref<string | null>(null)
const feedFinished = ref(false)
const loadingFeed = ref(false)
const loadingMoreFeed = ref(false)
const feedError = ref<string | null>(null)
const FEED_PAGE_SIZE = 50
let feedRequestToken = 0

const selectedChannelSnapshot = ref<SubscriptionListItem | null>(null)
const togglingSpecialIds = ref<Set<string | number>>(new Set())
const refreshingChannelId = ref<string | number | null>(null)

const isFeedView = computed(() => (
  activeView.value === 'inbox'
  || activeView.value === 'activity'
  || activeView.value === 'special'
))

const siteOptionsList = computed(() => siteOptions.value || [])
const issueChannels = computed(() => channels.value.filter(isSubscriptionSyncFailed))
const visibleChannels = computed(() => (
  activeView.value === 'issues' ? issueChannels.value : channels.value
))
const selectedChannel = computed(() => {
  const snapshot = selectedChannelSnapshot.value
  if (!snapshot) return null
  return channels.value.find((channel) => channel.id === snapshot.id) || snapshot
})
const canOpenSelectedRemote = computed(() => (
  Boolean(
    selectedChannel.value
    && desktopBridge.isDesktop()
    && selectedChannel.value.site
    && selectedChannel.value.url,
  )
))

const contentLevelOptions = [
  { value: 'all', label: '全部内容' },
  { value: 'no', label: '普通内容' },
  { value: 'yes', label: '成年内容' },
] as const

const viewOptions = computed<{
  value: SubscriptionView
  label: string
  icon: AppIconName
  count: number | null
}[]>(() => [
  {
    value: 'inbox',
    label: '收件箱',
    icon: 'inbox',
    count: null,
  },
  { value: 'activity', label: '全部动态', icon: 'list', count: null },
  { value: 'special', label: '特别关注', icon: 'star', count: null },
  {
    value: 'issues',
    label: '需要处理',
    icon: 'warning',
    count: channelsFinished.value ? issueChannels.value.length : null,
  },
  {
    value: 'channels',
    label: '频道库',
    icon: 'library',
    count: null,
  },
])

const pageLoading = computed(() => (
  isFeedView.value
    ? loadingFeed.value || loadingMoreFeed.value
    : loadingChannels.value || loadingMoreChannels.value
))

const activeFilterCount = computed(() => {
  let count = site.value ? 1 : 0
  if (isFeedView.value && nsfw.value !== 'all') count += 1
  if (activeView.value === 'channels' && librarySpecialOnly.value) count += 1
  return count
})

const filterDescription = computed(() => {
  if (isFeedView.value) return '按来源和内容分级缩小范围'
  if (activeView.value === 'channels') return '按来源和关注状态缩小范围'
  return '按来源缩小范围'
})

const feedEmptyTitle = computed(() => {
  if (feedSearch.value.trim()) return '没有匹配内容'
  if (activeView.value === 'inbox') return '收件箱已清空'
  if (activeView.value === 'special') return '特别关注暂无更新'
  return '暂无订阅动态'
})

const feedEmptyCopy = computed(() => {
  if (feedSearch.value.trim()) return '调整搜索关键词或筛选条件后再试。'
  if (activeView.value === 'inbox') return '新的未读视频会按日期和频道出现在这里。'
  if (activeView.value === 'special') return '将频道设为特别关注后，其更新会集中显示在这里。'
  return '频道更新后，最新内容会显示在这里。'
})

const feedDayGroups = computed<FeedDayGroup[]>(() => {
  const dayMap = new Map<string, {
    label: string
    items: FeedDayItem[]
  }>()

  for (const video of feedItems.value) {
    const rawDate = video.uploaded_at || video.created_at
    const date = new Date(rawDate)
    const dayKey = Number.isNaN(date.getTime()) ? 'unknown' : localDateKey(date)
    const day = dayMap.get(dayKey) || {
      label: feedDayLabel(date),
      items: [],
    }
    const profile = primaryVideoProfile(video)

    day.items.push({
      video,
      channelName: profile?.name || '未知频道',
      channelAvatar: profile?.avatar || null,
      subscriptionId: profile?.id ?? null,
    })
    dayMap.set(dayKey, day)
  }

  return Array.from(dayMap.entries()).map(([key, day]) => ({
    key,
    label: day.label,
    count: day.items.length,
    items: day.items,
  }))
})

const localDateKey = (date: Date) => (
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
)

const feedDayLabel = (date: Date) => {
  if (Number.isNaN(date.getTime())) return '日期未知'
  const today = new Date()
  const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  const targetStart = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const diffDays = Math.round((todayStart.getTime() - targetStart.getTime()) / 86_400_000)
  if (diffDays === 0) return '今天'
  if (diffDays === 1) return '昨天'
  if (diffDays > 1 && diffDays < 7) return `${diffDays} 天前`
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`
}

const primaryVideoProfile = (video: VideoListItem): VideoProfile | null => (
  video.subscriptions?.[0] || video.actors?.[0] || null
)

const handleSiteFilterChange = (value: unknown) => {
  const nextValue = String(value ?? '')
  site.value = nextValue === 'all' || nextValue === '' ? undefined : nextValue
}

const handleNsfwFilterChange = (value: unknown) => {
  const nextValue = String(value ?? '')
  if (nextValue === 'all' || nextValue === 'yes' || nextValue === 'no') {
    nsfw.value = nextValue
  }
}

const clearToolbarFilters = () => {
  site.value = undefined
  if (isFeedView.value) {
    nsfw.value = 'all'
  } else if (activeView.value === 'channels') {
    librarySpecialOnly.value = false
  }
}

const channelListParams = (page: number) => {
  const params: Record<string, unknown> = {
    page,
    pageSize: CHANNEL_PAGE_SIZE,
    page_size: CHANNEL_PAGE_SIZE,
    nsfw: 'all',
  }
  if (site.value) params.site = site.value
  if (activeView.value === 'channels') {
    const query = channelSearch.value.trim()
    if (query) params.query = query
    if (librarySpecialOnly.value) params.special = 'yes'
  }
  return params
}

const fetchChannels = async (reset = false) => {
  if (!reset && (loadingChannels.value || loadingMoreChannels.value || channelsFinished.value)) return

  if (reset) {
    channelsPage.value = 1
    channelsFinished.value = false
    loadingChannels.value = true
    loadingMoreChannels.value = false
    channelsError.value = null
  } else {
    loadingMoreChannels.value = true
  }

  const requestToken = ++channelsRequestToken
  const loadAllPages = activeView.value !== 'channels'
  let nextPage = reset ? 1 : channelsPage.value
  let merged = reset ? [] : [...channels.value]
  let reachedEnd = false

  try {
    do {
      const result = await getSubscriptions(channelListParams(nextPage))
      if (requestToken !== channelsRequestToken) return

      const items = result?.data || []
      const total = Number(result?.total)
      channelsTotal.value = Number.isFinite(total) && total >= 0
        ? total
        : merged.length + items.length
      merged = nextPage === 1 ? items : [...merged, ...items]
      reachedEnd = items.length < CHANNEL_PAGE_SIZE || merged.length >= channelsTotal.value
      nextPage += 1
    } while (loadAllPages && !reachedEnd)

    channels.value = sortSubscriptions(merged)
    channelsPage.value = nextPage
    channelsFinished.value = reachedEnd
    channelsError.value = null

    if (selectedChannelSnapshot.value) {
      const refreshed = channels.value.find((channel) => (
        channel.id === selectedChannelSnapshot.value?.id
      ))
      if (refreshed) selectedChannelSnapshot.value = refreshed
    }
  } catch (error) {
    if (requestToken !== channelsRequestToken) return
    channelsError.value = errorMessage(error, '订阅频道加载失败')
    if (reset) {
      channels.value = []
      channelsTotal.value = 0
    }
  } finally {
    if (requestToken === channelsRequestToken) {
      loadingChannels.value = false
      loadingMoreChannels.value = false
    }
  }
}

const fetchFeed = async (reset = false) => {
  if (!isFeedView.value) return
  if (!reset && (loadingFeed.value || loadingMoreFeed.value || feedFinished.value)) return

  if (reset) {
    feedCursor.value = null
    feedFinished.value = false
    loadingFeed.value = true
    loadingMoreFeed.value = false
    feedError.value = null
  } else {
    loadingMoreFeed.value = true
  }

  const requestToken = ++feedRequestToken
  try {
    const result = await getVideoList({
      cursor: feedCursor.value,
      pageSize: FEED_PAGE_SIZE,
      page_size: FEED_PAGE_SIZE,
      query: feedSearch.value.trim() || undefined,
      category: activeView.value === 'inbox' ? 'unread' : 'all',
      special: activeView.value === 'special' ? 'yes' : undefined,
      site: site.value,
      nsfw: nsfw.value,
      sort_by: 'publish_date',
    })
    if (requestToken !== feedRequestToken) return

    const items = result?.data || []
    feedItems.value = reset ? items : [...feedItems.value, ...items]
    feedCursor.value = result?.next_cursor ?? null
    feedFinished.value = !result?.has_more || !result?.next_cursor || items.length < FEED_PAGE_SIZE
    feedError.value = null
  } catch (error) {
    if (requestToken !== feedRequestToken) return
    feedError.value = errorMessage(error, '订阅内容加载失败')
    if (reset) feedItems.value = []
  } finally {
    if (requestToken === feedRequestToken) {
      loadingFeed.value = false
      loadingMoreFeed.value = false
    }
  }
}

const subscriptionDetailToListItem = (detail: SubscriptionDetail): SubscriptionListItem => ({
  ...detail,
  url: detail.url || '',
  created_at: detail.created_at || null,
  updated_at: detail.updated_at || null,
  last_sync_at: detail.last_sync_at || null,
  last_success_at: detail.last_success_at || null,
  next_sync_at: detail.next_sync_at || null,
  unread_count: 0,
  recent_videos: [],
})

const selectChannel = (channel: SubscriptionListItem) => {
  selectedChannelSnapshot.value = channel
}

const inspectChannelById = async (id: string | number | null) => {
  if (id == null) return
  const existing = channels.value.find((channel) => String(channel.id) === String(id))
  if (existing) {
    selectChannel(existing)
    return
  }

  try {
    const detail = await getSubscriptionDetail(id)
    selectedChannelSnapshot.value = subscriptionDetailToListItem(detail)
  } catch (error) {
    toast.error(errorMessage(error, '频道详情加载失败'))
  }
}

const applySpecialFollowState = (subscriptionId: string | number, enabled: boolean) => {
  const removeFromFilteredLibrary = (
    activeView.value === 'channels'
    && librarySpecialOnly.value
    && !enabled
  )

  channels.value = channels.value
    .map((channel) => (
      channel.id === subscriptionId
        ? { ...channel, is_special_followed: enabled }
        : channel
    ))
    .filter((channel) => (
      !(removeFromFilteredLibrary && channel.id === subscriptionId)
    ))

  if (selectedChannelSnapshot.value?.id === subscriptionId) {
    selectedChannelSnapshot.value = removeFromFilteredLibrary
      ? null
      : {
          ...selectedChannelSnapshot.value,
          is_special_followed: enabled,
        }
  }

  if (removeFromFilteredLibrary) {
    channelsTotal.value = Math.max(0, channelsTotal.value - 1)
  }
}

const toggleSpecialFollow = async (channel: SubscriptionListItem) => {
  if (togglingSpecialIds.value.has(channel.id)) return
  const nextValue = !channel.is_special_followed
  togglingSpecialIds.value = new Set(togglingSpecialIds.value).add(channel.id)

  try {
    await updateSpecialFollowStatus(channel.id, nextValue)
    applySpecialFollowState(channel.id, nextValue)
    if (activeView.value === 'special') void fetchFeed(true)
  } catch (error) {
    toast.error(errorMessage(error, nextValue ? '设为特别关注失败' : '取消特别关注失败'))
  } finally {
    const nextIds = new Set(togglingSpecialIds.value)
    nextIds.delete(channel.id)
    togglingSpecialIds.value = nextIds
  }
}

const refreshSelectedChannel = async () => {
  const channel = selectedChannel.value
  if (!channel || refreshingChannelId.value === channel.id) return
  refreshingChannelId.value = channel.id
  try {
    await triggerRefresh(channel.id)
    toast.success('同步任务已加入队列')
    await fetchChannels(true)
  } catch (error) {
    toast.error(errorMessage(error, '同步频道失败'))
  } finally {
    refreshingChannelId.value = null
  }
}

const openSelectedRemote = () => {
  const channel = selectedChannel.value
  if (!channel || !canOpenSelectedRemote.value) return
  router.push({
    name: 'RemoteChannelDetail',
    query: {
      id: String(channel.id),
      site: channel.site || '',
      url: channel.url,
      name: channel.name,
      avatar: channel.avatar || '',
      is_nsfw: String(channel.is_nsfw),
    },
  })
}

const openRecentVideo = (videoId: number) => {
  openVideo({ id: videoId })
}

const handleReadChange = (payload: { videoId: number; isRead: boolean }) => {
  const video = feedItems.value.find((item) => item.id === payload.videoId)
  if (!video) return

  if (activeView.value === 'inbox' && payload.isRead) {
    feedItems.value = feedItems.value.filter((item) => item.id !== payload.videoId)
  } else {
    feedItems.value = feedItems.value.map((item) => (
      item.id === payload.videoId
        ? { ...item, last_position: payload.isRead ? Math.max(1, Number(item.duration || 1)) : 0 }
        : item
    ))
  }

  const profileId = primaryVideoProfile(video)?.id
  if (profileId == null) return
  const delta = payload.isRead ? -1 : 1
  channels.value = channels.value.map((channel) => (
    String(channel.id) === String(profileId)
      ? { ...channel, unread_count: Math.max(0, channel.unread_count + delta) }
      : channel
  ))
  if (selectedChannelSnapshot.value && String(selectedChannelSnapshot.value.id) === String(profileId)) {
    selectedChannelSnapshot.value = {
      ...selectedChannelSnapshot.value,
      unread_count: Math.max(0, selectedChannelSnapshot.value.unread_count + delta),
    }
  }
}

const refreshCurrentView = async () => {
  if (isFeedView.value) {
    await Promise.all([fetchChannels(true), fetchFeed(true)])
  } else {
    await fetchChannels(true)
  }
}

const handleSubscriptionsChanged = async () => {
  showAddDialog.value = false
  showImportDialog.value = false
  await refreshCurrentView()
}

const scrollToTop = () => {
  if (contentScroll.value) contentScroll.value.scrollTop = 0
}

const initObservers = () => {
  feedObserver?.disconnect()
  channelObserver?.disconnect()

  feedObserver = new IntersectionObserver((entries) => {
    if (
      entries[0]?.isIntersecting
      && isFeedView.value
      && !loadingFeed.value
      && !loadingMoreFeed.value
      && !feedFinished.value
    ) {
      void fetchFeed()
    }
  }, { root: contentScroll.value, rootMargin: '600px' })
  if (feedTrigger.value) feedObserver.observe(feedTrigger.value)

  channelObserver = new IntersectionObserver((entries) => {
    if (
      entries[0]?.isIntersecting
      && activeView.value === 'channels'
      && !loadingChannels.value
      && !loadingMoreChannels.value
      && !channelsFinished.value
    ) {
      void fetchChannels()
    }
  }, { root: contentScroll.value, rootMargin: '400px' })
  if (channelTrigger.value) channelObserver.observe(channelTrigger.value)
}

watch(activeView, async () => {
  scrollToTop()
  if (isFeedView.value) {
    await Promise.all([fetchChannels(true), fetchFeed(true)])
  } else {
    await fetchChannels(true)
  }
  await nextTick()
  initObservers()
})

watch(site, async () => {
  scrollToTop()
  if (isFeedView.value) {
    await Promise.all([fetchChannels(true), fetchFeed(true)])
  } else {
    await fetchChannels(true)
  }
})

watch(nsfw, () => {
  if (isFeedView.value) void fetchFeed(true)
})

watch(librarySpecialOnly, () => {
  if (activeView.value === 'channels') void fetchChannels(true)
})

watch(feedSearch, () => {
  if (feedSearchTimer !== null) window.clearTimeout(feedSearchTimer)
  feedSearchTimer = window.setTimeout(() => {
    if (isFeedView.value) void fetchFeed(true)
  }, 250)
})

watch(channelSearch, () => {
  if (channelSearchTimer !== null) window.clearTimeout(channelSearchTimer)
  channelSearchTimer = window.setTimeout(() => {
    if (activeView.value === 'channels') void fetchChannels(true)
  }, 250)
})

watch(() => uiStore.searchTrigger, async () => {
  const viewChanged = activeView.value !== 'activity'

  if (feedSearchTimer !== null) {
    window.clearTimeout(feedSearchTimer)
    feedSearchTimer = null
  }

  feedSearch.value = uiStore.searchQuery.trim()
  activeView.value = 'activity'

  await nextTick()
  if (feedSearchTimer !== null) {
    window.clearTimeout(feedSearchTimer)
    feedSearchTimer = null
  }

  if (!viewChanged) void fetchFeed(true)
})

watch(contentScroll, () => {
  nextTick(initObservers)
})

onMounted(async () => {
  fetchSites()
  await Promise.all([fetchChannels(true), fetchFeed(true)])
  await nextTick()
  initObservers()
})

onUnmounted(() => {
  if (feedSearchTimer !== null) window.clearTimeout(feedSearchTimer)
  if (channelSearchTimer !== null) window.clearTimeout(channelSearchTimer)
  feedObserver?.disconnect()
  channelObserver?.disconnect()
})
</script>

<style scoped>
.subscription-page {
  display: flex;
  width: 100%;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
}

.subscription-control-bar {
  display: flex;
  min-height: 3.5rem;
  flex: none;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  border-bottom: 1px solid var(--app-hairline);
  padding: 0 var(--space-5);
}

.subscription-view-nav {
  display: flex;
  min-width: 0;
  flex: none;
  align-items: center;
  gap: 0.25rem;
}

.subscription-view-nav__item {
  display: inline-flex;
  height: 3.5rem;
  align-items: center;
  gap: 0.45rem;
  padding: 0 0.625rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 550;
  cursor: pointer;
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.subscription-view-nav__item:hover,
.subscription-view-nav__item:focus-visible {
  background: hsl(var(--muted) / 0.28);
  color: hsl(var(--foreground));
  outline: none;
}

.subscription-view-nav__item.is-active {
  color: hsl(var(--foreground));
  box-shadow: inset 0 -2px 0 hsl(var(--foreground) / 0.58);
}

.subscription-view-nav__count {
  min-width: 0;
  color: hsl(var(--muted-foreground) / 0.76);
  font-size: 0.5625rem;
  line-height: 1;
  text-align: center;
}

.subscription-toolbar {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex: none;
  align-items: center;
  gap: var(--space-2);
}

.subscription-toolbar__search {
  width: 15rem;
  flex: 0 1 15rem;
}

.subscription-toolbar__filter {
  gap: 0.4rem;
  color: hsl(var(--muted-foreground) / 0.84);
  font-size: 0.75rem;
}

.subscription-toolbar__filter.is-active {
  border-color: hsl(var(--foreground) / 0.1);
  background: hsl(var(--foreground) / 0.045);
  color: hsl(var(--foreground) / 0.82);
}

.subscription-toolbar__filter-count {
  display: grid;
  min-width: 1rem;
  height: 1rem;
  place-items: center;
  border-radius: 999px;
  background: hsl(var(--foreground) / 0.08);
  color: hsl(var(--foreground) / 0.72);
  font-size: 0.5625rem;
  line-height: 1;
}

.subscription-toolbar__divider {
  width: 1px;
  height: 1rem;
  flex: none;
  background: var(--app-hairline);
}

.subscription-toolbar__icon-action {
  color: hsl(var(--muted-foreground) / 0.78);
}

.subscription-toolbar__add {
  box-shadow: none;
}

.subscription-filter-panel {
  padding: var(--space-4);
}

.subscription-filter-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  padding-bottom: var(--space-4);
}

.subscription-filter-panel__header > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.2rem;
}

.subscription-filter-panel__header strong {
  color: hsl(var(--foreground));
  font-size: 0.8125rem;
  font-weight: 650;
}

.subscription-filter-panel__header span {
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.6875rem;
}

.subscription-filter-panel__fields {
  display: grid;
  gap: var(--space-4);
}

.subscription-filter-panel__field {
  display: grid;
  gap: var(--space-2);
}

.subscription-filter-panel__field > span {
  color: hsl(var(--muted-foreground) / 0.82);
  font-size: 0.6875rem;
  font-weight: 600;
}

.subscription-filter-panel__site-option {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.subscription-filter-panel__toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  border-top: 1px solid var(--app-hairline);
  padding-top: var(--space-4);
}

.subscription-filter-panel__toggle > span {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.2rem;
}

.subscription-filter-panel__toggle strong {
  color: hsl(var(--foreground) / 0.9);
  font-size: 0.75rem;
  font-weight: 600;
}

.subscription-filter-panel__toggle small {
  color: hsl(var(--muted-foreground) / 0.68);
  font-size: 0.6875rem;
}

.subscription-workspace {
  display: flex;
  min-height: 0;
  flex: 1 1 auto;
  overflow: hidden;
}

.subscription-content {
  min-width: 0;
  min-height: 0;
  flex: 1 1 auto;
  overflow-y: auto;
}

.subscription-content__empty {
  display: flex;
  min-height: 28rem;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
}

.subscription-feed,
.subscription-feed-skeletons {
  width: min(100%, 72rem);
  margin: 0 auto;
  padding: var(--space-5) var(--space-6) var(--app-content-padding-bottom);
}

.subscription-list-view {
  width: min(100%, 88rem);
  margin: 0 auto;
  padding: var(--space-5) var(--space-6) var(--app-content-padding-bottom);
}

.subscription-feed-skeletons {
  display: grid;
  gap: var(--space-3);
}

.subscription-feed-day + .subscription-feed-day {
  margin-top: var(--space-8);
}

.subscription-feed-day__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  border-bottom: 1px solid var(--app-hairline);
  padding-bottom: var(--space-3);
}

.subscription-feed-day__header h2 {
  color: hsl(var(--foreground));
  font-family: var(--app-heading-font);
  font-size: 1rem;
  font-weight: 600;
}

.subscription-feed-day__header span {
  color: hsl(var(--muted-foreground) / 0.68);
  font-size: 0.6875rem;
  font-weight: 550;
}

.subscription-feed-day__items {
  min-width: 0;
}

.subscription-feed-day__items > * + * {
  border-top: 1px solid var(--app-hairline);
}

.subscription-channel-table {
  --subscription-table-columns:
    minmax(15rem, 1fr)
    5.5rem
    5.5rem
    8rem
    minmax(6.5rem, 8rem)
    1.75rem;
  overflow: hidden;
  border-top: 1px solid var(--app-hairline);
  border-bottom: 1px solid var(--app-hairline);
}

.subscription-channel-table__header {
  position: sticky;
  top: 0;
  z-index: var(--z-content);
  display: grid;
  grid-template-columns: var(--subscription-table-columns);
  align-items: center;
  gap: 1rem;
  border-bottom: 1px solid var(--app-hairline);
  background: hsl(var(--background) / 0.96);
  padding: 0.5rem 0.75rem;
  color: hsl(var(--muted-foreground) / 0.68);
  font-size: 0.625rem;
  font-weight: 600;
}

.subscription-channel-table__header > :nth-child(2),
.subscription-channel-table__header > :nth-child(3) {
  justify-self: end;
}

.subscription-channel-table__body > :last-child {
  border-bottom: 0;
}

.subscription-load-trigger {
  display: flex;
  width: 100%;
  height: 4rem;
  align-items: center;
  justify-content: center;
}

@media (max-width: 1200px) {
  .subscription-control-bar {
    gap: var(--space-3);
    padding-inline: var(--space-4);
  }

  .subscription-view-nav__item {
    gap: 0.35rem;
    padding-inline: 0.5rem;
  }

  .subscription-feed,
  .subscription-feed-skeletons,
  .subscription-list-view {
    padding-inline: var(--space-4);
  }

  .subscription-toolbar__search {
    width: 12rem;
    flex-basis: 12rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .subscription-view-nav__item {
    transition: none;
  }
}
</style>
