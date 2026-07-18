<template>
  <AppPageShell variant="compact" surface="organize" width="table" fill>
    <div class="subscription-page">
      <AppToolbarFrame bordered compact>
        <div class="subscription-toolbar">
          <div class="subscription-toolbar__navigation">
            <AppSectionNav
              v-model="workspaceMode"
              :options="workspaceOptions"
              aria-label="订阅工作区"
            />
            <span class="subscription-toolbar__divider" aria-hidden="true" />
            <AppSegmentedControl
              :model-value="activeScope"
              :options="scopeOptions"
              aria-label="订阅范围"
              size="sm"
              @update:model-value="handleScopeChange"
            >
              <template #option="{ option }">
                <span>{{ option.label }}</span>
                <span
                  v-if="option.value === 'issues' && issueCount > 0"
                  class="subscription-toolbar__scope-count app-mono"
                >
                  {{ issueCount > 999 ? '999+' : issueCount }}
                </span>
              </template>
            </AppSegmentedControl>
          </div>

          <section class="subscription-toolbar__actions" aria-label="订阅筛选和操作">
            <PopoverRoot>
              <PopoverTrigger as-child>
                <Button
                  type="button"
                  text severity="secondary"
                  size="sm"
                  class="app-filter-toolbar-button"
                  :class="{ 'is-active': activeFilterCount > 0 }"
                  :aria-label="activeFilterCount > 0 ? `筛选，已启用 ${activeFilterCount} 项` : '筛选'"
                >
                  <AppIcon name="filter" class="h-3.5 w-3.5" />
                  <span>筛选</span>
                  <span
                    v-if="activeFilterCount > 0"
                    class="app-filter-toolbar-button__count app-mono"
                  >
                    {{ activeFilterCount }}
                  </span>
                </Button>
              </PopoverTrigger>

              <PopoverContent class="app-filter-popover">
                <AppFilterPanel
                  :active-count="activeFilterCount"
                  @reset="clearToolbarFilters"
                >
                  <AppFilterSection label="来源">
                    <AppFilterOptionList
                      :model-value="site || 'all'"
                      :options="subscriptionSiteFilterOptions"
                      label="按来源筛选"
                      @update:model-value="handleSiteFilterChange"
                    >
                      <template #leading="{ option }">
                        <span
                          v-if="option.value === 'all'"
                          class="app-filter-all-icon"
                          aria-hidden="true"
                        >
                          <AppIcon name="layoutGrid" />
                        </span>
                        <SiteIcon
                          v-else
                          :site="option.value"
                          :icon-url="option.iconUrl"
                          :label="option.label"
                          size="sm"
                          rounded="sm"
                        />
                      </template>
                    </AppFilterOptionList>
                  </AppFilterSection>

                  <AppFilterSection v-if="isFeedView" label="分级" layout="row" divided>
                    <AppSegmentedControl
                      :model-value="nsfw"
                      :options="nsfwOptions"
                      aria-label="内容分级"
                      size="sm"
                      fill
                      @update:model-value="handleNsfwFilterChange"
                    />
                  </AppFilterSection>
                </AppFilterPanel>
              </PopoverContent>
            </PopoverRoot>

            <Button
              type="button"
              text severity="secondary"
              size="sm" icon-only
              class="subscription-toolbar__icon-action"
              :loading="pageLoading"
              title="刷新当前视图"
              aria-label="刷新当前视图"
              @click="refreshCurrentView"
            >
              <AppIcon v-if="!pageLoading" name="refresh" class="h-4 w-4" />
            </Button>
            <Button
              v-if="!isFeedView"
              type="button"
              text severity="secondary"
              size="sm" icon-only
              class="subscription-toolbar__icon-action"
              title="导入订阅"
              aria-label="导入订阅"
              @click="showImportDialog = true"
            >
              <AppIcon name="download" class="h-4 w-4" />
            </Button>
            <Button
              type="button"
              text severity="secondary"
              size="sm"
              class="subscription-toolbar__add"
              @click="showAddDialog = true"
            >
              <AppIcon name="plus" class="h-4 w-4" />
              添加订阅
            </Button>
          </section>
        </div>
      </AppToolbarFrame>

      <div class="subscription-workspace">
        <main ref="contentScroll" class="subscription-content custom-scrollbar">
          <template v-if="isFeedView">
            <div v-if="feedError && !feedItems.length" class="subscription-content__empty">
              <AppEmptyState variant="error" title="内容加载失败" :copy="feedError">
                <template #actions>
                  <Button severity="secondary" outlined size="sm" @click="fetchFeed(true)">重试</Button>
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
                :icon="activityScope === 'unread' ? 'inbox' : 'subscriptions'"
                :title="feedEmptyTitle"
                :copy="feedEmptyCopy"
              >
                <template v-if="subscriptionCount === 0 && !feedSearch" #actions>
                  <Button size="sm" @click="showAddDialog = true">添加订阅</Button>
                  <Button severity="secondary" outlined size="sm" @click="showImportDialog = true">导入订阅</Button>
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
              <div v-if="channelsError && !channels.length" class="subscription-content__empty">
                <AppEmptyState variant="error" title="频道加载失败" :copy="channelsError">
                  <template #actions>
                    <Button severity="secondary" outlined size="sm" @click="fetchChannels(true)">重试</Button>
                  </template>
                </AppEmptyState>
              </div>

              <div v-else-if="loadingChannels && !channels.length" class="subscription-channel-table">
                <div class="subscription-channel-table__body">
                  <SubscriptionCardSkeleton v-for="index in 10" :key="index" />
                </div>
              </div>

              <div v-else-if="!channels.length" class="subscription-content__empty">
                <AppEmptyState
                  variant="plain"
                  :icon="channelScope === 'issues' ? 'statusSuccess' : 'subscriptions'"
                  :title="channelScope === 'issues' ? '没有需要处理的频道' : '没有匹配频道'"
                  :copy="channelScope === 'issues' ? '当前所有频道同步状态正常。' : '调整搜索或筛选条件后再试。'"
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
                    v-for="channel in channels"
                    :key="channel.id"
                    :subscription="channel"
                    :selected="selectedChannel?.id === channel.id"
                    :toggling="togglingSpecialIds.has(channel.id)"
                    @click="selectChannel(channel)"
                    @toggle-special="toggleSpecialFollow"
                  />
                </div>
              </section>

              <div ref="channelTrigger" class="subscription-load-trigger">
                <AppSpinner v-if="loadingMoreChannels" />
              </div>
            </div>
          </template>
        </main>

        <button
          v-if="selectedChannel"
          type="button"
          class="subscription-inspector-backdrop"
          aria-label="关闭频道详情"
          @click="selectedChannelSnapshot = null"
        />

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
import AppFilterOptionList from '@/shared/components/layout/AppFilterOptionList.vue'
import AppFilterPanel from '@/shared/components/layout/AppFilterPanel.vue'
import AppFilterSection from '@/shared/components/layout/AppFilterSection.vue'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'
import AppSectionNav from '@/shared/components/layout/AppSectionNav.vue'
import AppToolbarFrame from '@/shared/components/layout/AppToolbarFrame.vue'
import SiteIcon from '@/shared/components/SiteIcon.vue'
import { PopoverContent, PopoverRoot, PopoverTrigger } from '@/shared/ui/popover'
import { Button } from '@/shared/ui/button'
import { useToast } from '@/shared/components/toast/useToast'
import { errorMessage } from '@/shared/lib/errorMessage'
import { useUIStore } from '@/shared/stores/ui'
import { useUserSettings } from '@/shared/composables/useUserSettings'
import SubscriptionCard from '@/features/video/components/feed/SubscriptionCard.vue'
import SubscriptionCardSkeleton from '@/features/video/components/feed/SubscriptionCardSkeleton.vue'
import SubscriptionInboxItem from '@/features/video/components/subscription/SubscriptionInboxItem.vue'
import SubscriptionChannelInspector from '@/features/video/components/subscription/SubscriptionChannelInspector.vue'
import AddChannelDialog from '@/features/video/components/dialogs/AddChannelDialog.vue'
import ImportSubscriptionDialog from '@/features/video/components/dialogs/ImportSubscriptionDialog.vue'
import { useSites } from '@/features/video/composables/useSites'
import { NSFW_OPTIONS } from '@/features/video/constants/feedFilters'
import { useDesktopBridge } from '@/shared/composables/useDesktopBridge'
import { useVideoCardNavigation } from '@/features/video/composables/useVideoCardNavigation'
import { sortSubscriptions } from '@/features/video/lib/subscriptionSort'
import {
  getSubscriptionDetail,
  getSubscriptions,
  getVideoList,
  triggerRefresh,
  updateSpecialFollowStatus,
} from '@/shared/api'
import type {
  SubscriptionDetail,
  SubscriptionListItem,
} from '@/features/video/types/subscription'
import type {
  VideoListItem,
  VideoProfile,
} from '@/features/video/types/video'

defineOptions({ name: 'Subscribed' })

type SubscriptionWorkspace = 'activity' | 'channels'
type ActivityScope = 'unread' | 'all' | 'special'
type ChannelScope = 'all' | 'issues' | 'special'

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
const { settings, loadUserSettings } = useUserSettings()

const workspaceMode = ref<SubscriptionWorkspace>('activity')
const activityScope = ref<ActivityScope>('unread')
const channelScope = ref<ChannelScope>('all')
const feedSearch = ref(uiStore.getSearchQuery('subscribed').trim())
const channelSearch = ref('')
const site = ref<string | undefined>()
const nsfw = ref<'all' | 'yes' | 'no'>('all')
const showAddDialog = ref(false)
const showImportDialog = ref(false)

const contentScroll = ref<HTMLElement | null>(null)
const feedTrigger = ref<HTMLElement | null>(null)
const channelTrigger = ref<HTMLElement | null>(null)

let feedObserver: IntersectionObserver | null = null
let channelObserver: IntersectionObserver | null = null

const channels = ref<SubscriptionListItem[]>([])
const channelsTotal = ref(0)
const subscriptionCount = ref<number | null>(null)
const issueCount = ref(0)
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

const isFeedView = computed(() => workspaceMode.value === 'activity')
const activeScope = computed(() => (
  isFeedView.value ? activityScope.value : channelScope.value
))

const siteOptionsList = computed(() => siteOptions.value || [])
const visibleSiteOptions = computed(() => (
  siteOptionsList.value.filter((option) => settings.value.showNsfw || option.isNsfw !== true)
))
const subscriptionSiteFilterOptions = computed(() => [
  {
    value: 'all',
    label: '全部来源',
    iconUrl: null as string | null,
  },
  ...visibleSiteOptions.value.map((option) => ({
    value: option.value,
    label: option.label,
    iconUrl: option.iconUrl ?? null,
  })),
])
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

const nsfwOptions = NSFW_OPTIONS

const workspaceOptions: {
  value: SubscriptionWorkspace
  label: string
  badge: string | null
}[] = [
  { value: 'activity', label: '动态', badge: null },
  { value: 'channels', label: '频道', badge: null },
]

const scopeOptions = computed(() => (
  isFeedView.value
    ? [
        { value: 'unread', label: '未读' },
        { value: 'all', label: '全部' },
        { value: 'special', label: '特别关注' },
      ]
    : [
        { value: 'all', label: '全部' },
        { value: 'issues', label: '需处理' },
        { value: 'special', label: '特别关注' },
      ]
))

const pageLoading = computed(() => (
  isFeedView.value
    ? loadingFeed.value || loadingMoreFeed.value
    : loadingChannels.value || loadingMoreChannels.value
))

const activeFilterCount = computed(() => {
  let count = site.value ? 1 : 0
  if (isFeedView.value && nsfw.value !== 'all') count += 1
  return count
})

const feedEmptyTitle = computed(() => {
  if (feedSearch.value.trim()) return '没有匹配内容'
  if (activityScope.value === 'unread') return '收件箱已清空'
  if (activityScope.value === 'special') return '特别关注暂无更新'
  return '暂无订阅动态'
})

const feedEmptyCopy = computed(() => {
  if (feedSearch.value.trim()) return '调整搜索关键词或筛选条件后再试。'
  if (activityScope.value === 'unread') return '新的未读视频会按日期和频道出现在这里。'
  if (activityScope.value === 'special') return '将频道设为特别关注后，其更新会集中显示在这里。'
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

const handleSiteFilterChange = (value: string) => {
  site.value = value === 'all' || value === '' ? undefined : value
}

const handleNsfwFilterChange = (value: string | number) => {
  if (value === 'all' || value === 'yes' || value === 'no') {
    nsfw.value = value
  }
}

const handleScopeChange = (value: string | number) => {
  if (isFeedView.value) {
    if (value === 'unread' || value === 'all' || value === 'special') {
      activityScope.value = value
    }
    return
  }
  if (value === 'all' || value === 'issues' || value === 'special') {
    channelScope.value = value
  }
}

const clearToolbarFilters = () => {
  site.value = undefined
  if (isFeedView.value) nsfw.value = 'all'
}

const channelListParams = (page: number) => {
  const params: Record<string, unknown> = {
    page,
    pageSize: CHANNEL_PAGE_SIZE,
    page_size: CHANNEL_PAGE_SIZE,
    nsfw: 'all',
  }
  if (site.value) params.site = site.value
  const query = channelSearch.value.trim()
  if (query) params.query = query
  if (channelScope.value === 'special') params.special = 'yes'
  if (channelScope.value === 'issues') params.status = 'issues'
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
  let nextPage = reset ? 1 : channelsPage.value
  let merged = reset ? [] : [...channels.value]

  try {
    const result = await getSubscriptions(channelListParams(nextPage))
    if (requestToken !== channelsRequestToken) return

    const items = result?.data || []
    const total = Number(result?.total)
    channelsTotal.value = Number.isFinite(total) && total >= 0
      ? total
      : merged.length + items.length
    merged = nextPage === 1 ? items : [...merged, ...items]
    const reachedEnd = items.length < CHANNEL_PAGE_SIZE || merged.length >= channelsTotal.value
    nextPage += 1

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

const fetchWorkspaceCounts = async () => {
  try {
    const [allResult, issueResult] = await Promise.all([
      getSubscriptions({ page: 1, pageSize: 1, nsfw: 'all' }),
      getSubscriptions({ page: 1, pageSize: 1, nsfw: 'all', status: 'issues' }),
    ])
    const allTotal = Number(allResult?.total)
    const issueTotal = Number(issueResult?.total)
    subscriptionCount.value = Number.isFinite(allTotal) && allTotal >= 0 ? allTotal : 0
    issueCount.value = Number.isFinite(issueTotal) && issueTotal >= 0 ? issueTotal : 0
  } catch {
    // Counts are supporting metadata; keep the current values when their
    // lightweight request fails so the primary workspace remains usable.
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
      category: activityScope.value === 'unread' ? 'unread' : 'all',
      special: activityScope.value === 'special' ? 'yes' : undefined,
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
    workspaceMode.value === 'channels'
    && channelScope.value === 'special'
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
    if (workspaceMode.value === 'activity' && activityScope.value === 'special') {
      void fetchFeed(true)
    }
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
    await Promise.all([fetchChannels(true), fetchWorkspaceCounts()])
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

  if (activityScope.value === 'unread' && payload.isRead) {
    feedItems.value = feedItems.value.filter((item) => item.id !== payload.videoId)
  } else {
    feedItems.value = feedItems.value.map((item) => (
      item.id === payload.videoId
        ? { ...item, is_read: payload.isRead }
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
    await Promise.all([fetchFeed(true), fetchWorkspaceCounts()])
  } else {
    await Promise.all([fetchChannels(true), fetchWorkspaceCounts()])
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
      && workspaceMode.value === 'channels'
      && !loadingChannels.value
      && !loadingMoreChannels.value
      && !channelsFinished.value
    ) {
      void fetchChannels()
    }
  }, { root: contentScroll.value, rootMargin: '400px' })
  if (channelTrigger.value) channelObserver.observe(channelTrigger.value)
}

watch(workspaceMode, async () => {
  scrollToTop()
  if (workspaceMode.value === 'channels') {
    uiStore.setSearchQuery('subscribed', channelSearch.value)
  } else {
    uiStore.setSearchQuery('subscribed', feedSearch.value)
  }

  if (isFeedView.value) {
    await fetchFeed(true)
  } else {
    await fetchChannels(true)
  }
  await nextTick()
  initObservers()
})

watch(site, async () => {
  scrollToTop()
  if (isFeedView.value) {
    await fetchFeed(true)
  } else {
    await fetchChannels(true)
  }
})

watch(
  () => ({
    currentSite: site.value,
    showNsfw: settings.value.showNsfw,
    options: siteOptionsList.value,
  }),
  ({ currentSite, showNsfw, options }) => {
    if (!currentSite || showNsfw) return
    const selected = options.find((option) => option.value === currentSite)
    if (selected?.isNsfw === true) site.value = undefined
  },
  { immediate: true },
)

watch(nsfw, () => {
  if (isFeedView.value) void fetchFeed(true)
})

watch(activityScope, () => {
  if (workspaceMode.value === 'activity') {
    scrollToTop()
    void fetchFeed(true)
  }
})

watch(channelScope, () => {
  if (workspaceMode.value === 'channels') {
    scrollToTop()
    void fetchChannels(true)
  }
})

watch(() => uiStore.getSearchTrigger('subscribed'), async () => {
  const query = uiStore.getSearchQuery('subscribed').trim()

  scrollToTop()
  if (workspaceMode.value === 'channels') {
    channelSearch.value = query
    await fetchChannels(true)
    return
  }

  feedSearch.value = query
  await fetchFeed(true)
})

watch(contentScroll, () => {
  nextTick(initObservers)
})

onMounted(async () => {
  await Promise.all([fetchSites(), loadUserSettings()])
  await Promise.all([fetchFeed(true), fetchWorkspaceCounts()])
  await nextTick()
  initObservers()
})

onUnmounted(() => {
  feedObserver?.disconnect()
  channelObserver?.disconnect()
})
</script>

<style scoped>
.subscription-page {
  --subscription-content-width: var(--app-content-media-max);
  display: flex;
  width: 100%;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
}

.subscription-page :deep(.app-toolbar-frame__inner) {
  max-width: var(--subscription-content-width);
}

.subscription-toolbar {
  display: flex;
  width: 100%;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
}

.subscription-toolbar__navigation,
.subscription-toolbar__actions {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex: none;
  align-items: center;
  gap: var(--space-2);
}

.subscription-toolbar__navigation {
  overflow-x: auto;
  padding-inline: 0.125rem;
  scrollbar-width: none;
}

.subscription-toolbar__navigation::-webkit-scrollbar {
  display: none;
}

.subscription-toolbar__divider {
  width: 1px;
  height: 1.25rem;
  flex: none;
  margin-inline: var(--space-1);
  background: var(--app-hairline);
}

.subscription-toolbar__scope-count {
  margin-left: 0.25rem;
  color: hsl(var(--destructive));
  font-size: var(--app-text-badge-size);
}

.subscription-toolbar__icon-action {
  color: hsl(var(--muted-foreground) / 0.78);
}

.subscription-toolbar__add {
  margin-left: var(--space-1);
  border-color: hsl(var(--border) / 0.58);
  background: transparent;
  color: hsl(var(--foreground));
  font-weight: 620;
  box-shadow: none;
}

.subscription-toolbar__add:hover {
  border-color: hsl(var(--border) / 0.78);
  background: hsl(var(--muted) / 0.42);
}

.subscription-workspace {
  position: relative;
  display: flex;
  min-height: 0;
  flex: 1 1 auto;
  overflow: hidden;
}

.subscription-content {
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  flex: 1 1 auto;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.subscription-inspector-backdrop {
  display: none;
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
  width: min(100%, var(--subscription-content-width));
  margin: 0 auto;
  padding: var(--space-5) var(--space-6) var(--app-content-padding-bottom);
}

.subscription-list-view {
  width: min(100%, var(--subscription-content-width));
  margin: 0 auto;
  padding: var(--space-5) var(--space-6) var(--app-content-padding-bottom);
}

.subscription-feed-skeletons {
  display: grid;
  gap: var(--space-3);
}

.subscription-feed-day + .subscription-feed-day {
  margin-top: var(--space-9);
}

.subscription-feed-day {
  display: grid;
  grid-template-columns: 7.5rem minmax(0, 1fr);
  align-items: start;
  gap: var(--space-6);
}

.subscription-feed-day__header {
  position: sticky;
  top: var(--space-4);
  display: flex;
  align-items: flex-start;
  flex-direction: column;
  gap: 0.375rem;
  padding-top: var(--space-4);
}

.subscription-feed-day__header h2 {
  color: hsl(var(--foreground));
  font-family: var(--app-heading-font);
  font-size: 0.9375rem;
  font-weight: 650;
  letter-spacing: -0.02em;
  line-height: 1.35;
}

.subscription-feed-day__header span {
  color: hsl(var(--muted-foreground) / 0.64);
  font-size: 0.6875rem;
  font-weight: 550;
}

.subscription-feed-day__items {
  min-width: 0;
  width: min(100%, 82rem);
  border-top: 1px solid var(--app-hairline);
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
  font-size: var(--app-text-badge-size);
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
  .subscription-toolbar {
    gap: var(--space-3);
  }

  .subscription-feed,
  .subscription-feed-skeletons,
  .subscription-list-view {
    padding-inline: var(--space-4);
  }

  .subscription-feed-day {
    grid-template-columns: 6.5rem minmax(0, 1fr);
    gap: var(--space-4);
  }
}

@media (max-width: 1180px) {
  .subscription-inspector-backdrop {
    position: absolute;
    inset: 0;
    z-index: var(--z-content);
    display: block;
    border: 0;
    background: hsl(var(--foreground) / 0.12);
    cursor: default;
  }
}

@media (max-width: 900px) {
  .subscription-toolbar__add {
    width: 2rem;
    overflow: hidden;
    padding-inline: 0.4375rem;
    white-space: nowrap;
  }

  .subscription-channel-table {
    --subscription-table-columns:
      minmax(12rem, 1fr)
      4rem
      4rem
      minmax(6.5rem, 7.5rem)
      1.75rem;
  }

  .subscription-channel-table__header > :nth-child(4),
  .subscription-channel-table :deep(.subscription-row__updated) {
    display: none;
  }
}

@media (max-width: 760px) {
  .subscription-feed-day {
    display: block;
  }

  .subscription-feed-day__header {
    position: static;
    align-items: baseline;
    flex-direction: row;
    justify-content: space-between;
    padding: 0 0 var(--space-3);
  }
}

@media (max-width: 640px) {
  .subscription-toolbar {
    align-items: stretch;
    flex-direction: column;
    gap: var(--space-2);
  }

  .subscription-toolbar__actions {
    justify-content: flex-end;
  }

}
</style>
