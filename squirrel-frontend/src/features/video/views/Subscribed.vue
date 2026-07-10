<template>
  <AppPageShell variant="compact" fill>
    <div class="subscription-page">
      <header class="subscription-page__header">
        <div class="subscription-page__heading">
          <h1>订阅</h1>
          <p>{{ pageSubtitle }}</p>
        </div>
        <div class="subscription-page__header-actions">
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            :loading="pageLoading"
            title="刷新当前视图"
            aria-label="刷新当前视图"
            @click="refreshCurrentView"
          >
            <AppIcon v-if="!pageLoading" name="refresh" class="h-4 w-4" />
          </Button>
          <Button size="sm" @click="showAddDialog = true">
            <AppIcon name="plus" class="h-4 w-4" />
            添加订阅
          </Button>
        </div>
      </header>

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
        <div class="subscription-toolbar__filters">
          <AppSearchInput
            v-if="isFeedView"
            :model-value="feedSearch"
            class="subscription-toolbar__search"
            placeholder="搜索订阅内容..."
            aria-label="搜索订阅内容"
            @update:model-value="feedSearch = $event"
          />
          <AppSearchInput
            v-else-if="activeView === 'channels'"
            :model-value="channelSearch"
            class="subscription-toolbar__search"
            placeholder="搜索频道..."
            aria-label="搜索频道"
            @update:model-value="channelSearch = $event"
          />

          <Select
            :model-value="site || 'all'"
            @update:model-value="handleSiteFilterChange"
          >
            <SelectTrigger
              class="subscription-toolbar__select"
              :class="{ 'is-active': site }"
              aria-label="按来源筛选"
            >
              <SelectValue placeholder="全部来源" />
            </SelectTrigger>
            <SelectContent class="min-w-48">
              <SelectItem value="all">全部来源</SelectItem>
              <SelectItem
                v-for="option in siteOptionsList"
                :key="option.value"
                :value="option.value"
              >
                <span class="subscription-toolbar__site-option">
                  <SiteIcon :site="option.value" class="h-4 w-4 rounded-sm" />
                  <span>{{ option.label }}</span>
                </span>
              </SelectItem>
            </SelectContent>
          </Select>

          <Select
            v-if="isFeedView"
            :model-value="nsfw"
            @update:model-value="handleNsfwFilterChange"
          >
            <SelectTrigger
              class="subscription-toolbar__select"
              :class="{ 'is-active': nsfw !== 'all' }"
              aria-label="内容分级"
            >
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

          <Button
            v-if="activeView === 'channels'"
            type="button"
            variant="outline"
            size="sm"
            class="subscription-toolbar__special"
            :class="{ 'is-active': librarySpecialOnly }"
            :aria-pressed="librarySpecialOnly"
            @click="librarySpecialOnly = !librarySpecialOnly"
          >
            <AppIcon name="star" class="h-3.5 w-3.5" />
            特别关注
          </Button>

          <Button
            v-if="hasActiveToolbarFilters"
            type="button"
            variant="ghost"
            size="icon-sm"
            title="清除筛选"
            aria-label="清除筛选"
            @click="clearToolbarFilters"
          >
            <AppIcon name="close" class="h-4 w-4" />
          </Button>
        </div>

        <div class="subscription-toolbar__actions">
          <span class="subscription-toolbar__summary">{{ toolbarSummary }}</span>
          <Button
            v-if="activeView === 'channels'"
            variant="outline"
            size="sm"
            @click="showImportDialog = true"
          >
            <AppIcon name="download" class="h-4 w-4" />
            导入
          </Button>
        </div>
      </section>

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

                <section
                  v-for="group in day.channels"
                  :key="group.key"
                  class="subscription-channel-group"
                >
                  <header class="subscription-channel-group__header">
                    <Button
                      unstyled
                      type="button"
                      class="subscription-channel-group__identity"
                      :disabled="group.subscriptionId == null"
                      @click="inspectChannelById(group.subscriptionId)"
                    >
                      <SubscriptionAvatar
                        :src="group.avatar"
                        :name="group.name"
                        size="md"
                      />
                      <span class="subscription-channel-group__copy">
                        <strong>{{ group.name }}</strong>
                        <small>{{ group.items.length }} 个更新</small>
                      </span>
                      <AppIcon
                        v-if="group.subscriptionId != null"
                        name="chevronRight"
                        class="h-3.5 w-3.5"
                      />
                    </Button>
                  </header>

                  <div class="subscription-channel-group__items">
                    <SubscriptionInboxItem
                      v-for="video in group.items"
                      :key="video.id"
                      :video="video"
                      @open="openVideo"
                      @read-change="handleReadChange"
                    />
                  </div>
                </section>
              </section>
            </div>

            <div ref="feedTrigger" class="subscription-load-trigger">
              <AppSpinner v-if="loadingMoreFeed" />
            </div>
          </template>

          <template v-else>
            <div class="subscription-list-view">
              <header class="subscription-list-view__heading">
                <div>
                  <h2>{{ activeView === 'issues' ? '需要处理' : '频道库' }}</h2>
                  <p>
                    {{
                      activeView === 'issues'
                        ? '这里只显示同步失败或存在明确错误的频道。'
                        : '搜索、检查状态并连续管理所有订阅频道。'
                    }}
                  </p>
                </div>
              </header>

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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/select'
import { useToast } from '@/shared/components/toast/useToast'
import { errorMessage } from '@/shared/lib/errorMessage'
import { useUIStore } from '@/shared/stores/ui'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
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

type FeedChannelGroup = {
  key: string
  name: string
  avatar: string | null
  subscriptionId: string | number | null
  items: VideoListItem[]
}

type FeedDayGroup = {
  key: string
  label: string
  count: number
  channels: FeedChannelGroup[]
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
const unreadTotal = computed(() => (
  channels.value.reduce((total, channel) => total + Math.max(0, channel.unread_count), 0)
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
    count: channelsFinished.value ? unreadTotal.value : null,
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
    count: channelsTotal.value,
  },
])

const pageSubtitle = computed(() => {
  if (activeView.value === 'inbox') return '未读更新，按日期与频道整理'
  if (activeView.value === 'activity') return '所有订阅频道的完整时间流'
  if (activeView.value === 'special') return '只查看特别关注频道的最新内容'
  if (activeView.value === 'issues') return '集中处理同步失败和明确错误'
  return '搜索、检查并管理所有订阅频道'
})

const toolbarSummary = computed(() => {
  if (isFeedView.value) {
    return feedFinished.value
      ? `${feedItems.value.length} 条内容`
      : `已加载 ${feedItems.value.length} 条`
  }
  if (activeView.value === 'issues') return `${issueChannels.value.length} 个需要处理`
  return `${channelsTotal.value} 个频道`
})

const pageLoading = computed(() => (
  isFeedView.value
    ? loadingFeed.value || loadingMoreFeed.value
    : loadingChannels.value || loadingMoreChannels.value
))

const hasActiveToolbarFilters = computed(() => {
  if (isFeedView.value) {
    return Boolean(feedSearch.value.trim()) || Boolean(site.value) || nsfw.value !== 'all'
  }
  if (activeView.value === 'channels') {
    return Boolean(channelSearch.value.trim()) || Boolean(site.value) || librarySpecialOnly.value
  }
  return Boolean(site.value)
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
    count: number
    channels: Map<string, FeedChannelGroup>
  }>()

  for (const video of feedItems.value) {
    const rawDate = video.uploaded_at || video.created_at
    const date = new Date(rawDate)
    const dayKey = Number.isNaN(date.getTime()) ? 'unknown' : localDateKey(date)
    const day = dayMap.get(dayKey) || {
      label: feedDayLabel(date),
      count: 0,
      channels: new Map<string, FeedChannelGroup>(),
    }
    const profile = primaryVideoProfile(video)
    const channelKey = profile?.id != null
      ? `id:${String(profile.id)}`
      : `name:${profile?.name || '未知频道'}`
    const group = day.channels.get(channelKey) || {
      key: channelKey,
      name: profile?.name || '未知频道',
      avatar: profile?.avatar || null,
      subscriptionId: profile?.id ?? null,
      items: [],
    }

    group.items.push(video)
    day.channels.set(channelKey, group)
    day.count += 1
    dayMap.set(dayKey, day)
  }

  return Array.from(dayMap.entries()).map(([key, day]) => ({
    key,
    label: day.label,
    count: day.count,
    channels: Array.from(day.channels.values()),
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
    feedSearch.value = ''
    nsfw.value = 'all'
  } else if (activeView.value === 'channels') {
    channelSearch.value = ''
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

.subscription-page__header {
  display: flex;
  min-height: 4.5rem;
  flex: none;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  border-bottom: 1px solid var(--app-hairline);
  padding: 0 var(--space-5);
}

.subscription-page__heading {
  min-width: 0;
}

.subscription-page__heading h1 {
  color: hsl(var(--foreground));
  font-family: var(--app-heading-font);
  font-size: 1.25rem;
  font-weight: 600;
  line-height: 1.2;
}

.subscription-page__heading p {
  margin-top: 0.25rem;
  color: hsl(var(--muted-foreground) / 0.74);
  font-size: 0.75rem;
  font-weight: 500;
}

.subscription-page__header-actions {
  display: flex;
  flex: none;
  align-items: center;
  gap: var(--space-2);
}

.subscription-view-nav {
  display: flex;
  min-height: 2.875rem;
  flex: none;
  align-items: center;
  gap: 0.25rem;
  border-bottom: 1px solid var(--app-hairline);
  padding: 0 var(--space-5);
}

.subscription-view-nav__item {
  display: inline-flex;
  height: 2rem;
  align-items: center;
  gap: 0.45rem;
  border-radius: var(--radius-md);
  padding: 0 0.75rem;
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
  background: hsl(var(--muted) / 0.42);
  color: hsl(var(--foreground));
  outline: none;
}

.subscription-view-nav__item.is-active {
  background: hsl(var(--foreground) / 0.06);
  color: hsl(var(--foreground));
}

.subscription-view-nav__count {
  min-width: 1.25rem;
  border-radius: var(--radius-sm);
  background: hsl(var(--muted) / 0.6);
  padding: 0.125rem 0.3rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.5625rem;
  line-height: 1;
  text-align: center;
}

.subscription-toolbar {
  display: flex;
  min-height: 3.5rem;
  flex: none;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  border-bottom: 1px solid var(--app-hairline);
  padding: 0 var(--space-5);
}

.subscription-toolbar__filters,
.subscription-toolbar__actions {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-2);
}

.subscription-toolbar__filters {
  flex: 1 1 auto;
}

.subscription-toolbar__actions {
  flex: none;
}

.subscription-toolbar__search {
  width: min(22rem, 34vw);
  flex: 0 1 22rem;
}

.subscription-toolbar__select {
  width: 10rem;
  height: 2rem;
  background: hsl(var(--muted) / 0.24);
  font-size: 0.75rem;
  box-shadow: none;
}

.subscription-toolbar__select.is-active {
  border-color: hsl(var(--primary) / 0.22);
  background: hsl(var(--primary) / 0.06);
}

.subscription-toolbar__site-option {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.subscription-toolbar__special {
  height: 2rem;
  gap: 0.4rem;
  border-color: hsl(var(--border) / 0.58);
  background: hsl(var(--muted) / 0.24);
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.subscription-toolbar__special.is-active {
  border-color: hsl(var(--foreground) / 0.12);
  background: hsl(var(--foreground) / 0.045);
  color: hsl(var(--foreground) / 0.72);
}

.subscription-toolbar__summary {
  color: hsl(var(--muted-foreground) / 0.7);
  font-size: 0.6875rem;
  font-weight: 550;
  white-space: nowrap;
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
.subscription-feed-skeletons,
.subscription-list-view {
  width: min(100%, 76rem);
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
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--app-hairline);
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

.subscription-channel-group {
  padding: var(--space-4) 0 var(--space-5);
}

.subscription-channel-group + .subscription-channel-group {
  border-top: 1px solid var(--app-hairline);
}

.subscription-channel-group__header {
  margin-bottom: var(--space-2);
}

.subscription-channel-group__identity {
  display: inline-flex;
  max-width: 100%;
  align-items: center;
  gap: var(--space-3);
  border-radius: var(--radius-md);
  padding: 0.25rem;
  color: hsl(var(--muted-foreground));
  text-align: left;
  cursor: pointer;
}

.subscription-channel-group__identity:hover:not(:disabled),
.subscription-channel-group__identity:focus-visible:not(:disabled) {
  background: hsl(var(--muted) / 0.4);
  color: hsl(var(--foreground));
  outline: none;
}

.subscription-channel-group__identity:disabled {
  cursor: default;
}

.subscription-channel-group__copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.1rem;
}

.subscription-channel-group__copy strong {
  overflow: hidden;
  color: hsl(var(--foreground));
  font-size: 0.8125rem;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.subscription-channel-group__copy small {
  color: hsl(var(--muted-foreground) / 0.68);
  font-size: 0.625rem;
  font-weight: 500;
}

.subscription-list-view__heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
  padding-bottom: var(--space-4);
}

.subscription-list-view__heading h2 {
  color: hsl(var(--foreground));
  font-family: var(--app-heading-font);
  font-size: 1.0625rem;
  font-weight: 600;
}

.subscription-list-view__heading p {
  margin-top: 0.3rem;
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.75rem;
  font-weight: 500;
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
  .subscription-feed,
  .subscription-feed-skeletons,
  .subscription-list-view {
    padding-inline: var(--space-4);
  }

  .subscription-toolbar__search {
    width: 16rem;
    flex-basis: 16rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .subscription-view-nav__item {
    transition: none;
  }
}
</style>
