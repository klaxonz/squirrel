<template>
  <AppPageShell variant="compact" fill>
    <AppTwoColumnLayout
      ref="layoutRef"
      class="subscribed-workbench"
      sidebar-always
      :show-sidebar="mainView !== 'channels'"
      sidebar-width="17rem"
      content-width="100rem"
    >
      <template #sidebar>
        <SubscriptionSidebar
          ref="sidebarRef"
          :channels="list"
          :total="channelsTotal"
          :loading="loadingChannels"
          :loading-more="loadingMoreChannels"
          :finished="channelsFinished"
          :error="channelsError"
          :search="sidebarSearch"
          :site="site || ''"
          :site-options="siteOptionsList"
          :special-filter="specialFilter"
          :active-channel-id="activeChannelId"
          :toggling-ids="togglingSpecialIds"
          @add="showAddDialog = true"
          @import="showImportDialog = true"
          @retry="fetchChannels(true)"
          @clear-filters="clearSidebarFilters"
          @select-all="handleSelectAllChannels"
          @select-channel="handleChannelClick"
          @toggle-special="toggleSpecialFollow"
          @toggle-special-filter="toggleSpecialFilter"
          @update:search="sidebarSearch = $event"
          @update:site="handleSiteFilterChange"
        />
      </template>

      <template #header>
        <div class="subscribed-header">
          <div class="subscribed-header__identity">
            <Button
              v-if="activeChannel && mainView !== 'channels'"
              unstyled
              type="button"
              class="subscribed-header__avatar-btn"
              :aria-label="`打开 ${activeChannel.name}`"
              @click="openActiveChannelDetail"
            >
              <SubscriptionAvatar
                :src="activeChannel.avatar"
                :name="activeChannel.name"
                size="md"
                class="subscribed-avatar"
              />
            </Button>

            <div class="subscribed-header__copy">
              <div class="subscribed-header__title-row">
                <Button
                  unstyled
                  type="button"
                  class="subscribed-header__title"
                  :disabled="!activeChannel || mainView === 'channels'"
                  @click="activeChannel && openActiveChannelDetail()"
                >
                  {{ pageTitle }}
                </Button>

                <Button
                  v-if="activeChannel && mainView !== 'channels'"
                  type="button"
                  variant="ghost"
                  size="mini-icon"
                  class="subscribed-header__star"
                  :class="{ 'is-active': activeChannel.is_special_followed }"
                  :disabled="togglingSpecialIds.has(activeChannel.id)"
                  :aria-pressed="activeChannel.is_special_followed"
                  aria-label="切换特别关注"
                  @click="toggleSpecialFollow(activeChannel)"
                >
                  <AppSpinner v-if="togglingSpecialIds.has(activeChannel.id)" size="sm" />
                  <AppIcon
                    v-else
                    name="star"
                    class="h-3.5 w-3.5"
                  />
                </Button>

                <span
                  v-if="activeChannel && mainView !== 'channels' && isSubscriptionSyncFailed(activeChannel)"
                  class="subscribed-header__health subscribed-header__health--error"
                  :title="subscriptionSyncErrorLabel(activeChannel)"
                >
                  <AppIcon name="warning" class="h-3 w-3" />
                  同步异常
                </span>
                <span
                  v-else-if="activeChannel && mainView !== 'channels' && isSubscriptionSyncBusy(activeChannel)"
                  class="subscribed-header__health"
                >
                  <AppSpinner size="sm" />
                  同步中
                </span>

              </div>

              <span class="subscribed-header__meta">{{ headerSubtitle }}</span>
            </div>
          </div>

          <div class="subscribed-header__actions">
            <AppSegmentedControl
              :model-value="mainView"
              :options="mainViewOptions"
              aria-label="订阅视图"
              size="sm"
              @update:model-value="handleMainViewChange"
            >
              <template #option="{ option }">
                <AppIcon v-if="option.icon" :name="option.icon" class="h-3.5 w-3.5" />
                <span>{{ option.label }}</span>
              </template>
            </AppSegmentedControl>

            <Select
              v-if="mainView !== 'remote'"
              :model-value="nsfw"
              @update:model-value="handleNsfwFilterChange"
            >
              <SelectTrigger
                class="subscribed-content-filter"
                :class="{ 'is-active': nsfw !== 'all' }"
                aria-label="内容分级"
              >
                <AppIcon :name="nsfw === 'yes' ? 'warning' : 'eye'" class="h-3.5 w-3.5" />
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
              variant="ghost"
              size="icon-sm"
              :disabled="headerLoading"
              title="刷新内容"
              aria-label="刷新内容"
              @click="handleRefresh"
            >
              <AppSpinner v-if="headerLoading" size="sm" />
              <AppIcon v-else name="refresh" class="h-4 w-4" />
            </Button>
          </div>
        </div>
      </template>

      <div
        ref="gridWrapper"
        class="app-workbench__content subscribed-content"
        :class="{ 'subscribed-content--channels': mainView === 'channels' }"
      >
        <RemoteChannelVideoGrid
          v-if="mainView === 'remote'"
          :items="remoteItems"
          :loading="remoteLoading"
          :all-loaded="remoteAllLoaded"
          :error="remoteError"
          :scroll-root="feedContainer"
          @open="openRemoteResult"
          @load-more="loadMoreRemote"
          @retry="fetchRemoteChannel(true)"
        />

        <div v-else-if="mainView === 'feed'" class="app-content-stack app-content-stack--feed">
          <div v-if="fetchError && !loadingFeed" class="app-page-empty">
            <AppEmptyState variant="error" title="加载失败" :copy="fetchError">
              <template #actions>
                <Button variant="outline" size="sm" @click="fetchFeed(true)">重试</Button>
              </template>
            </AppEmptyState>
          </div>

          <div v-else-if="!feedItems.length && !loadingFeed" class="app-page-empty">
            <AppEmptyState
              variant="plain"
              icon="inbox"
              :title="feedEmptyTitle"
              :copy="feedEmptyCopy"
            >
              <template v-if="!list.length && !hasSidebarFilters" #actions>
                <Button size="sm" @click="showAddDialog = true">添加订阅</Button>
                <Button size="sm" variant="outline" @click="showImportDialog = true">导入订阅</Button>
              </template>
            </AppEmptyState>
          </div>

          <div v-if="loadingFeed && !feedItems.length" class="app-video-grid app-video-grid--feed">
            <VideoSkeleton v-for="i in videoSkeletonCount" :key="i" :delay="(i - 1) * 50" />
          </div>

          <div v-else-if="feedItems.length" class="app-video-grid app-video-grid--feed">
            <VideoItem
              v-for="video in feedItems"
              :key="video.id"
              :video="video"
              show-avatar
              @openModal="openVideo"
              @goToSubscription="openSubscription"
            />
          </div>

          <div v-if="loadingMoreFeed" class="app-video-grid app-video-grid--feed">
            <VideoSkeleton v-for="i in videoSkeletonCount" :key="i" :delay="(i - 1) * 50" />
          </div>
          <div ref="feedTrigger" class="h-20" />
        </div>

        <div v-else class="app-content-stack app-content-stack--dense">
          <section class="subscribed-channel-toolbar" aria-label="频道筛选和操作">
            <div class="subscribed-channel-toolbar__filters">
              <AppSearchInput
                :model-value="sidebarSearch"
                class="subscribed-channel-toolbar__search"
                placeholder="搜索频道名称..."
                aria-label="搜索频道名称"
                @update:model-value="sidebarSearch = $event"
              />

              <Select
                :model-value="site || 'all'"
                @update:model-value="handleSiteFilterChange"
              >
                <SelectTrigger
                  class="subscribed-channel-toolbar__select"
                  :class="{ 'is-active': site }"
                  aria-label="按来源筛选频道"
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
                    <span class="subscribed-channel-toolbar__source-option">
                      <SiteIcon :site="option.value" class="h-4 w-4 rounded-sm" />
                      <span>{{ option.label }}</span>
                    </span>
                  </SelectItem>
                </SelectContent>
              </Select>

              <Button
                type="button"
                variant="outline"
                size="sm"
                class="subscribed-channel-toolbar__special"
                :class="{ 'is-active': specialFilter === 'yes' }"
                :aria-pressed="specialFilter === 'yes'"
                @click="toggleSpecialFilter"
              >
                <AppIcon
                  name="star"
                  class="h-3.5 w-3.5"
                />
                特别关注
              </Button>

              <Button
                v-if="hasSidebarFilters"
                type="button"
                variant="ghost"
                size="icon-sm"
                title="清除频道筛选"
                aria-label="清除频道筛选"
                @click="clearSidebarFilters"
              >
                <AppIcon name="close" class="h-4 w-4" />
              </Button>
            </div>

            <div class="subscribed-channel-toolbar__actions">
              <span class="subscribed-channel-toolbar__count app-mono">
                {{ channelsTotal }} 个频道
              </span>
              <Button variant="outline" size="sm" @click="showImportDialog = true">
                <AppIcon name="download" class="h-4 w-4" />
                导入
              </Button>
              <Button size="sm" @click="showAddDialog = true">
                <AppIcon name="plus" class="h-4 w-4" />
                添加频道
              </Button>
            </div>
          </section>

          <div v-if="channelsError && !list.length && !loadingChannels" class="app-page-empty">
            <AppEmptyState variant="error" title="加载失败" :copy="channelsError">
              <template #actions>
                <Button variant="outline" size="sm" @click="fetchChannels(true)">重试</Button>
              </template>
            </AppEmptyState>
          </div>

          <div v-else-if="!list.length && !loadingChannels" class="app-page-empty">
            <AppEmptyState
              variant="plain"
              icon="inbox"
              :title="hasSidebarFilters ? '暂无匹配频道' : '还没有订阅频道'"
              :copy="hasSidebarFilters ? '请尝试更换筛选条件。' : '添加频道或导入订阅后，会显示在这里。'"
            >
              <template v-if="!hasSidebarFilters" #actions>
                <Button size="sm" @click="showAddDialog = true">添加订阅</Button>
                <Button size="sm" variant="outline" @click="showImportDialog = true">导入订阅</Button>
              </template>
              <template v-else #actions>
                <Button size="sm" variant="outline" @click="clearSidebarFilters">清除筛选</Button>
              </template>
            </AppEmptyState>
          </div>

          <section v-if="list.length" class="subscribed-channel-table" aria-label="订阅频道列表">
            <div class="subscribed-channel-table__header" aria-hidden="true">
              <span>频道</span>
              <span>视频</span>
              <span>未读</span>
              <span>最近成功</span>
              <span>同步状态</span>
              <span />
            </div>
            <div class="subscribed-channel-table__body">
              <SubscriptionCard
                v-for="sub in list"
                :key="sub.id"
                :subscription="sub"
                :toggling="togglingSpecialIds.has(sub.id)"
                @click="handleChannelClick(sub.id)"
                @toggleSpecial="toggleSpecialFollow"
              />
            </div>
          </section>

          <div v-if="loadingChannels && !list.length" class="subscribed-channel-table">
            <div class="subscribed-channel-table__body">
              <SubscriptionCardSkeleton v-for="i in 10" :key="i" />
            </div>
          </div>
          <div v-if="!channelsFinished" ref="gridMoreTrigger" class="h-20" />
        </div>
      </div>
    </AppTwoColumnLayout>

    <AddChannelDialog :show="showAddDialog" @added="handleRefresh" @close="showAddDialog = false" />
    <ImportSubscriptionDialog :show="showImportDialog" @close="showImportDialog = false" @imported="handleRefresh" />
  </AppPageShell>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted, onMounted, nextTick } from 'vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import { useRouter } from 'vue-router'
import { useUIStore } from '@/shared/stores/ui'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppSearchInput from '@/shared/components/layout/AppSearchInput.vue'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'
import AppTwoColumnLayout from '@/shared/components/layout/AppTwoColumnLayout.vue'
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
import SubscriptionSidebar from '@/features/video/components/SubscriptionSidebar.vue'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
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
import { useVideoCardNavigation } from '@/features/video/composables/useVideoCardNavigation'
import { sortSubscriptions } from '@/features/video/lib/subscriptionSort'
import {
  isSubscriptionSyncBusy,
  isSubscriptionSyncFailed,
  subscriptionSyncErrorLabel,
} from '@/features/video/lib/subscriptionPresenters'
import { getSubscriptions, getVideoList, updateSpecialFollowStatus } from '@/shared/api'
import { useSkeletonCount } from '@/features/video/composables/useSkeletonCount'
import type { AppIconName } from '@/shared/icons/app-icons'
import type { SubscriptionListItem } from '@/features/video/types/subscription'
import type { VideoListItem } from '@/features/video/types/video'

defineOptions({ name: 'Subscribed' })

type MainView = 'feed' | 'channels' | 'remote'

const router = useRouter()
const uiStore = useUIStore()
const toast = useToast()
const { openVideo, openSubscription } = useVideoCardNavigation(router)
const { nsfw, site } = useFeedFilters()
const { options: siteOptions, fetchSites } = useSites()
const desktopBridge = useDesktopBridge()

// Single workspace axis: recent activity | channel management | desktop remote source.
const mainView = ref<MainView>('feed')
const sidebarSearch = ref('')
const feedSearch = ref('')
const specialFilter = ref<'all' | 'yes'>('all')
const activeChannelId = ref<string | number | null>(null)
const activeChannelSnapshot = ref<SubscriptionListItem | null>(null)
const showAddDialog = ref(false)
const showImportDialog = ref(false)
const layoutRef = ref<{ scrollEl: HTMLElement | null } | null>(null)
const feedContainer = computed(() => layoutRef.value?.scrollEl ?? null)
const sidebarRef = ref<{ listContainer: HTMLElement | null; loadMore: HTMLElement | null } | null>(null)

const gridWrapper = ref<HTMLElement | null>(null)

const { count: videoSkeletonCount, attachRef: videoGridRef } = useSkeletonCount({
  minCardWidth: 280,
  gap: 40,
  cardHeight: 220,
})

watch(gridWrapper, (node) => {
  videoGridRef.value = node
}, { immediate: true })

// Data State (Channels)
const list = ref<SubscriptionListItem[]>([])
const channelsTotal = ref(0)
const loadingChannels = ref(false)
const loadingMoreChannels = ref(false)
const channelsFinished = ref(false)
const channelsError = ref<string | null>(null)
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

const feedTrigger = ref<HTMLElement | null>(null)
const gridMoreTrigger = ref<HTMLElement | null>(null)
let feedObserver: IntersectionObserver | null = null
let channelsObserver: IntersectionObserver | null = null
let gridObserver: IntersectionObserver | null = null

const activeChannel = computed(() => {
  if (!activeChannelId.value) return null
  return list.value.find(c => c.id === activeChannelId.value)
    || (activeChannelSnapshot.value?.id === activeChannelId.value ? activeChannelSnapshot.value : null)
})

const { openRemoteResult } = useRemoteVideoMapping({ activeChannel })

const canOpenRemoteChannel = computed(() => {
  return desktopBridge.isDesktop() && !!activeChannel.value?.site && !!activeChannel.value?.url
})
const remoteChannelKey = computed(() => {
  const channel = activeChannel.value
  return channel ? `${channel.site || ''}::${channel.url || ''}` : ''
})

const hasSidebarFilters = computed(() => {
  return Boolean(site.value) || specialFilter.value === 'yes' || Boolean(sidebarSearch.value.trim())
})

const pageTitle = computed(() => {
  if (mainView.value === 'channels') return '频道管理'
  if (mainView.value === 'remote') {
    return activeChannel.value ? `${activeChannel.value.name} · 远端` : '远端内容'
  }
  if (activeChannel.value) return activeChannel.value.name
  return '订阅动态'
})

const headerSubtitle = computed(() => {
  if (mainView.value === 'remote') return `${remoteItems.value.length} 条远端内容`
  if (mainView.value === 'channels') {
    return hasSidebarFilters.value
      ? `${channelsTotal.value} 个匹配频道`
      : `${channelsTotal.value} 个频道`
  }
  if (activeChannel.value) {
    const parts: string[] = []
    if (activeChannel.value.site) parts.push(activeChannel.value.site)
    parts.push(`${activeChannel.value.total_videos} 个视频`)
    if (activeChannel.value.unread_count > 0) parts.push(`${activeChannel.value.unread_count} 未读`)
    if (activeChannel.value.pending_video_count > 0) {
      parts.push(`${activeChannel.value.pending_video_count} 待处理`)
    }
    return parts.join(' · ')
  }
  if (loadingChannels.value && channelsTotal.value === 0) return '正在加载订阅频道'
  if (channelsTotal.value === 0) return '添加频道后，近期视频会集中显示在这里'
  return `${channelsTotal.value} 个频道 · 已加载 ${feedItems.value.length} 条近期内容`
})

const headerLoading = computed(() => {
  if (mainView.value === 'remote') return remoteLoading.value
  if (mainView.value === 'channels') return loadingChannels.value || loadingMoreChannels.value
  return loadingFeed.value || loadingMoreFeed.value
})

const feedEmptyTitle = computed(() => {
  if (activeChannel.value) return '该频道暂无内容'
  if (!list.value.length && !hasSidebarFilters.value) return '还没有订阅内容'
  return '暂无内容'
})

const feedEmptyCopy = computed(() => {
  if (activeChannel.value) return '同步完成后，新视频会出现在这里。'
  if (!list.value.length && !hasSidebarFilters.value) return '添加频道地址，或从站点导入已有订阅。'
  if (hasSidebarFilters.value) return '当前筛选下没有视频，可更换来源或特别关注条件。'
  return '订阅频道更新后会显示在这里。'
})

const siteOptionsList = computed(() => siteOptions.value || [])
const contentLevelOptions = [
  { value: 'all', label: '全部内容' },
  { value: 'no', label: '普通内容' },
  { value: 'yes', label: '成年内容' },
] as const

const mainViewOptions = computed(() => {
  const options: { value: MainView; label: string; icon: AppIconName }[] = [
    { value: 'feed', label: '动态', icon: 'playlistVideo' },
    { value: 'channels', label: '频道', icon: 'subscriptions' },
  ]
  if (canOpenRemoteChannel.value) {
    options.push({ value: 'remote', label: '远端', icon: 'siteFallback' })
  }
  return options
})

const sortChannels = sortSubscriptions

const clearActiveChannel = () => {
  activeChannelId.value = null
  activeChannelSnapshot.value = null
  loadedRemoteChannelKey = ''
  if (mainView.value === 'remote') mainView.value = 'feed'
}

const applySpecialFollowState = (subscriptionId: string | number, isSpecialFollowed: boolean) => {
  const updated = list.value.map((item) => (
    item.id === subscriptionId ? { ...item, is_special_followed: isSpecialFollowed } : item
  ))
  if (specialFilter.value === 'yes' && !isSpecialFollowed) {
    list.value = updated.filter((item) => item.id !== subscriptionId)
    channelsTotal.value = Math.max(0, channelsTotal.value - 1)
  } else {
    list.value = sortChannels(updated)
  }
  if (activeChannelSnapshot.value?.id === subscriptionId) {
    activeChannelSnapshot.value = {
      ...activeChannelSnapshot.value,
      is_special_followed: isSpecialFollowed,
    }
  }
  if (specialFilter.value === 'yes' && !isSpecialFollowed && activeChannelId.value === subscriptionId) {
    clearActiveChannel()
    fetchFeed(true)
  }
}

const toggleSpecialFilter = () => {
  specialFilter.value = specialFilter.value === 'yes' ? 'all' : 'yes'
}

const clearSidebarFilters = () => {
  sidebarSearch.value = ''
  site.value = undefined
  specialFilter.value = 'all'
}

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

const toggleSpecialFollow = async (subscription: SubscriptionListItem) => {
  if (!subscription?.id || togglingSpecialIds.value.has(subscription.id)) return

  const nextValue = !subscription.is_special_followed
  togglingSpecialIds.value = new Set(togglingSpecialIds.value).add(subscription.id)

  try {
    await updateSpecialFollowStatus(subscription.id, nextValue)
    applySpecialFollowState(subscription.id, nextValue)
  } catch (err) {
    toast.error(errorMessage(err, nextValue ? '设为特别关注失败' : '取消特别关注失败'))
  } finally {
    const nextIds = new Set(togglingSpecialIds.value)
    nextIds.delete(subscription.id)
    togglingSpecialIds.value = nextIds
  }
}

const fetchChannels = async (isReset = false) => {
  if (!isReset && (loadingChannels.value || loadingMoreChannels.value || channelsFinished.value)) return
  if (isReset) {
    channelsPage.value = 1
    channelsFinished.value = false
    channelsError.value = null
    loadingChannels.value = true
    loadingMoreChannels.value = false
  } else {
    loadingMoreChannels.value = true
  }

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
      channelsError.value = null
      const items = result?.data || []
      const total = Number(result?.total)
      channelsTotal.value = Number.isFinite(total) && total >= 0
        ? total
        : (isReset ? items.length : list.value.length + items.length)
      if (isReset) list.value = items
      else list.value.push(...items)
      const refreshedActiveChannel = list.value.find((item) => item.id === activeChannelId.value)
      if (refreshedActiveChannel) activeChannelSnapshot.value = refreshedActiveChannel
      if (items.length < CHANNELS_PAGE_SIZE || list.value.length >= channelsTotal.value) {
        channelsFinished.value = true
      } else {
        channelsPage.value = requestPage + 1
      }
    } catch (err) {
      if (requestToken !== channelsRequestToken) return
      channelsError.value = errorMessage(err, '订阅列表加载失败')
      if (isReset) {
        channelsTotal.value = 0
        list.value = []
      }
      // Keep finished=false on failure so the user can retry from empty/error UI.
    }
  } finally {
    if (requestToken === channelsRequestToken) {
      loadingChannels.value = false
      loadingMoreChannels.value = false
    }
  }
}

const fetchFeed = async (isReset = false) => {
  if (!isReset && (loadingFeed.value || loadingMoreFeed.value || feedFinished.value)) return
  if (isReset) {
    feedCursor.value = null
    feedFinished.value = false
    loadingFeed.value = true
    loadingMoreFeed.value = false
  } else {
    loadingMoreFeed.value = true
  }

  const requestToken = ++feedRequestToken
  const wasReset = isReset
  try {
    const nsfwValue = nsfw.value === 'only' ? 'yes' : (['all', 'yes', 'no'].includes(nsfw.value) ? nsfw.value : 'all')
    const data = await getVideoList({
      cursor: feedCursor.value,
      pageSize: FEED_PAGE_SIZE,
      page_size: FEED_PAGE_SIZE,
      query: feedSearch.value,
      nsfw: nsfwValue,
      site: site.value || undefined,
      subscription_id: activeChannelId.value || undefined,
      sort_by: 'publish_date',
      special: !activeChannelId.value && specialFilter.value === 'yes' ? 'yes' : undefined,
    })
    if (requestToken !== feedRequestToken) return
    fetchError.value = null
    const items = data?.data || []
    if (wasReset) feedItems.value = items
    else feedItems.value.push(...items)
    feedCursor.value = data?.next_cursor ?? null
    if (items.length < FEED_PAGE_SIZE || !data?.next_cursor) feedFinished.value = true
  } catch (err) {
    if (requestToken !== feedRequestToken) return
    fetchError.value = errorMessage(err, '内容加载失败')
    feedFinished.value = true
  } finally {
    if (requestToken === feedRequestToken) {
      loadingFeed.value = false
      loadingMoreFeed.value = false
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
  const channel = list.value.find((item) => item.id === id)
  if (!channel) return
  activeChannelId.value = id
  activeChannelSnapshot.value = channel
  mainView.value = 'feed'
  fetchFeed(true)
  scrollToTop(feedContainer.value)
}

const handleSelectAllChannels = () => {
  clearActiveChannel()
  mainView.value = 'feed'
  fetchFeed(true)
  scrollToTop(feedContainer.value)
}

const openActiveChannelDetail = () => {
  if (!activeChannelId.value) return
  openSubscription(activeChannelId.value)
}

const handleRefresh = () => {
  fetchChannels(true)
  if (mainView.value === 'remote') fetchRemoteChannel(true)
  else if (mainView.value === 'feed') fetchFeed(true)
  resetAllScroll()
}

const handleMainViewChange = (value: string | number) => {
  if (value === 'remote') {
    void openRemoteChannel()
    return
  }
  if (value === 'channels') {
    mainView.value = 'channels'
    nextTick(() => initObservers())
    return
  }
  mainView.value = 'feed'
  nextTick(() => initObservers())
}

const openRemoteChannel = async () => {
  const channel = activeChannel.value
  if (!canOpenRemoteChannel.value || !channel) return

  mainView.value = 'remote'
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
  feedObserver?.disconnect()
  channelsObserver?.disconnect()
  gridObserver?.disconnect()

  const scrollContainer = feedContainer.value
  const channelsEl = sidebarRef.value?.listContainer ?? null

  feedObserver = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && mainView.value === 'feed' && !loadingFeed.value && !loadingMoreFeed.value && !feedFinished.value) {
      fetchFeed()
    }
  }, { root: scrollContainer, rootMargin: '800px' })
  if (feedTrigger.value) feedObserver.observe(feedTrigger.value)

  channelsObserver = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && !loadingChannels.value && !loadingMoreChannels.value && !channelsFinished.value) {
      fetchChannels()
    }
  }, { root: channelsEl, rootMargin: '200px' })
  const channelsSentinel = sidebarRef.value?.loadMore ?? null
  if (channelsSentinel) channelsObserver.observe(channelsSentinel)

  if (mainView.value === 'channels') {
    gridObserver = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && !loadingChannels.value && !loadingMoreChannels.value && !channelsFinished.value) {
        fetchChannels()
      }
    }, { root: scrollContainer, rootMargin: '400px' })
    if (gridMoreTrigger.value) gridObserver.observe(gridMoreTrigger.value)
  }
}

onMounted(async () => {
  fetchSites()
  fetchChannels(true)
  await fetchFeed(true)
  nextTick(() => initObservers())
})

watch(mainView, () => {
  nextTick(() => initObservers())
})
watch(feedContainer, (el) => {
  if (el) nextTick(() => initObservers())
})

watch(nsfw, () => {
  fetchChannels(true)
  fetchFeed(true)
  resetAllScroll()
})

watch([site, specialFilter], () => {
  clearActiveChannel()
  fetchChannels(true)
  fetchFeed(true)
  resetAllScroll()
})

watch(() => uiStore.searchTrigger, () => {
  const query = uiStore.searchQuery.trim()
  feedSearch.value = query
  clearActiveChannel()
  mainView.value = 'feed'
  fetchFeed(true)
  nextTick(resetAllScroll)
})

watch(remoteChannelKey, () => {
  loadedRemoteChannelKey = ''
  if (mainView.value === 'remote') fetchRemoteChannel(true)
})

watch(canOpenRemoteChannel, (ok) => {
  if (!ok && mainView.value === 'remote') {
    mainView.value = 'feed'
  }
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
  feedObserver?.disconnect()
  channelsObserver?.disconnect()
  gridObserver?.disconnect()
})
</script>

<style scoped>
.subscribed-workbench {
  --app-workbench-header-height: 3.75rem;
}

.subscribed-workbench :deep(.app-sidebar-header__copy .app-h3) {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: 0;
}

.subscribed-header {
  display: flex;
  width: 100%;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.subscribed-header__identity {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  align-items: center;
  gap: var(--space-3);
}

.subscribed-header__avatar-btn {
  flex: none;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
  border-radius: 999px;
}

.subscribed-header__avatar-btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.45);
}

.subscribed-header__title {
  max-width: min(28rem, 38vw);
  overflow: hidden;
  border: 0;
  background: transparent;
  padding: 0;
  color: hsl(var(--foreground));
  font-family: var(--font-sans);
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: 0;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-default);
}

.subscribed-header__copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.2rem;
}

.subscribed-header__title-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.35rem;
}

.subscribed-header__title:hover:not(:disabled) {
  color: hsl(var(--primary));
}

.subscribed-header__title:focus-visible {
  outline: none;
  border-radius: var(--radius-sm);
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.45);
}

.subscribed-header__title:disabled {
  cursor: default;
}

.subscribed-header__star {
  flex: none;
  color: hsl(var(--muted-foreground) / 0.5);
}

.subscribed-header__star.is-active {
  color: hsl(var(--foreground) / 0.72);
}

.subscribed-header__meta {
  display: block;
  min-width: 0;
  overflow: hidden;
  color: hsl(var(--muted-foreground) / 0.78);
  font-size: 0.75rem;
  font-weight: 500;
  line-height: 1.25;
  font-variant-numeric: tabular-nums;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.subscribed-header__health {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 600;
  white-space: nowrap;
}

.subscribed-header__health--error {
  color: hsl(var(--destructive) / 0.92);
}

.subscribed-header__actions {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: nowrap;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-1);
}

.subscribed-avatar {
  border: 1px solid var(--app-surface-border-subtle);
  transition: opacity var(--duration-fast) var(--ease-default);
}

.subscribed-avatar:hover {
  opacity: 0.9;
}

.subscribed-content-filter {
  width: auto;
  min-width: 7.75rem;
  height: 2rem;
  gap: 0.35rem;
  border-color: transparent;
  background: transparent;
  padding: 0 var(--space-2);
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
  box-shadow: none;
}

.subscribed-content-filter:hover {
  border-color: hsl(var(--border) / 0.58);
  background: hsl(var(--muted) / 0.45);
  color: hsl(var(--foreground));
}

.subscribed-content-filter.is-active {
  border-color: hsl(var(--destructive) / 0.18);
  background: hsl(var(--destructive) / 0.08);
  color: hsl(var(--destructive));
}

.subscribed-content {
  --app-workbench-content-width: 100rem;
  padding: var(--space-4) var(--space-5) var(--app-content-padding-bottom);
}

.subscribed-content :deep(.app-video-grid--feed) {
  --app-grid-min: 310px;
  --app-video-grid-gap-x: 1.5rem;
  --app-video-grid-gap-y: 2rem;
}

.subscribed-content--channels {
  --app-workbench-content-width: 78rem;
  padding-top: var(--space-4);
}

.subscribed-channel-toolbar {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  border-bottom: 1px solid var(--app-hairline);
  padding-bottom: var(--space-3);
}

.subscribed-channel-toolbar__filters,
.subscribed-channel-toolbar__actions {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-2);
}

.subscribed-channel-toolbar__filters {
  flex: 1 1 auto;
}

.subscribed-channel-toolbar__actions {
  flex: none;
}

.subscribed-channel-toolbar__search {
  width: min(22rem, 36vw);
  flex: 0 1 22rem;
}

.subscribed-channel-toolbar__select {
  width: 10rem;
  height: 2rem;
  background: hsl(var(--muted) / 0.24);
  font-size: 0.75rem;
  box-shadow: none;
}

.subscribed-channel-toolbar__select.is-active {
  border-color: hsl(var(--primary) / 0.28);
  background: hsl(var(--primary) / 0.08);
}

.subscribed-channel-toolbar__source-option {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.subscribed-channel-toolbar__special {
  height: 2rem;
  gap: 0.4rem;
  border-color: hsl(var(--border) / 0.58);
  background: hsl(var(--muted) / 0.24);
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.subscribed-channel-toolbar__special.is-active {
  border-color: hsl(var(--foreground) / 0.12);
  background: hsl(var(--foreground) / 0.045);
  color: hsl(var(--foreground) / 0.72);
}

.subscribed-channel-toolbar__count {
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.6875rem;
  font-weight: 600;
  white-space: nowrap;
}

.subscribed-channel-table {
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

.subscribed-channel-table__header {
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
  line-height: 1;
}

.subscribed-channel-table__header > :nth-child(2),
.subscribed-channel-table__header > :nth-child(3) {
  justify-self: end;
}

.subscribed-channel-table__body > :last-child {
  border-bottom: 0;
}

@media (max-width: 1180px) {
  .subscribed-header__meta {
    max-width: 18rem;
  }

  .subscribed-channel-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .subscribed-channel-toolbar__filters,
  .subscribed-channel-toolbar__actions {
    width: 100%;
  }

  .subscribed-channel-toolbar__actions {
    justify-content: flex-end;
  }
}

@media (prefers-reduced-motion: reduce) {
  .subscribed-avatar,
  .subscribed-header__title {
    transition: none;
  }
}
</style>
