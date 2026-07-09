<template>
  <AppPageShell variant="compact" fill>
    <AppTwoColumnLayout
      ref="layoutRef"
      sidebar-always
      sidebar-width="17.5rem"
      content-width="112.5rem"
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
          :active-site-label="activeSiteLabel"
          :site-dropdown-open="showSiteDropdown"
          :special-filter="specialFilter"
          :active-channel-id="activeChannelId"
          :toggling-ids="togglingSpecialIds"
          @add="showAddDialog = true"
          @import="showImportDialog = true"
          @retry="fetchChannels(true)"
          @clear-filters="clearSidebarFilters"
          @select-channel="handleChannelClick"
          @toggle-special="toggleSpecialFollow"
          @toggle-special-filter="toggleSpecialFilter"
          @update:search="sidebarSearch = $event"
          @update:site="site = $event"
          @update:site-dropdown-open="showSiteDropdown = $event"
        />
      </template>

      <template #header>
        <div class="subscribed-header">
          <div class="subscribed-header__identity">
            <button
              v-if="activeChannel"
              type="button"
              class="subscribed-header__avatar-btn"
              :aria-label="`打开 ${activeChannel.name}`"
              @click="openActiveChannelDetail"
            >
              <SubscriptionAvatar :src="activeChannel.avatar" :name="activeChannel.name" size="xl" class="subscribed-avatar" />
              <span v-if="activeChannel.is_special_followed" class="subscribed-star-badge">
                <AppIcon name="star" class="h-2.5 w-2.5 fill-current" />
              </span>
            </button>
            <div v-else class="subscribed-empty-avatar" aria-hidden="true">
              <AppIcon name="library" class="h-4 w-4" />
            </div>

            <div class="subscribed-header__copy">
              <div class="subscribed-header__title-row">
                <button
                  type="button"
                  class="subscribed-header__title"
                  :disabled="!activeChannel"
                  @click="activeChannel && openActiveChannelDetail()"
                >
                  {{ activeChannelName || '订阅动态' }}
                </button>

                <Button
                  v-if="activeChannel"
                  type="button"
                  variant="ghost"
                  size="icon-sm"
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
                    :class="{ 'fill-current': activeChannel.is_special_followed }"
                  />
                </Button>
              </div>

              <div class="subscribed-header__subtitle">
                <template v-for="(part, index) in headerMetaParts" :key="`${part}-${index}`">
                  <span v-if="index > 0" class="subscribed-header__sep" aria-hidden="true">·</span>
                  <span>{{ part }}</span>
                </template>
                <span
                  v-if="activeChannel && isSubscriptionSyncFailed(activeChannel)"
                  class="subscribed-header__health subscribed-header__health--error"
                  :title="subscriptionSyncErrorLabel(activeChannel)"
                >
                  <span class="subscribed-header__sep" aria-hidden="true">·</span>
                  <AppIcon name="warning" class="h-3 w-3" />
                  同步异常
                </span>
                <span
                  v-else-if="activeChannel && isSubscriptionSyncBusy(activeChannel)"
                  class="subscribed-header__health"
                >
                  <span class="subscribed-header__sep" aria-hidden="true">·</span>
                  同步中
                </span>
                <AppBounceDots v-if="headerLoading" class="subscribed-header__loading" />
              </div>
            </div>
          </div>

          <div class="subscribed-header__actions">
            <AppSegmentedControl
              :model-value="mainView"
              :options="mainViewOptions"
              aria-label="订阅视图"
              size="sm"
              @update:model-value="handleMainViewChange"
            />

            <Button
              class="subscribed-nsfw-toggle"
              :variant="nsfw !== 'all' ? 'secondary' : 'ghost'"
              size="sm"
              :aria-pressed="nsfw !== 'all'"
              :aria-label="nsfwLabel"
              :title="nsfwLabel"
              @click="nsfw = nsfw === 'all' ? 'yes' : 'all'"
            >
              <AppIcon
                name="warning"
                class="h-3.5 w-3.5"
                :class="nsfw === 'all' ? 'text-muted-foreground/70' : 'text-destructive'"
              />
              成年内容
            </Button>

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

      <div ref="gridWrapper" class="app-workbench__content subscribed-content">
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

        <div v-else class="app-content-stack">
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

          <div v-else class="app-video-grid app-video-grid--compact">
            <SubscriptionCard
              v-for="sub in list"
              :key="sub.id"
              :subscription="sub"
              :toggling="togglingSpecialIds.has(sub.id)"
              @click="handleChannelClick(sub.id)"
              @toggleSpecial="toggleSpecialFollow"
            />
          </div>
          <div v-if="loadingChannels && !list.length" class="app-video-grid app-video-grid--compact">
            <SubscriptionCardSkeleton v-for="i in channelSkeletonCount" :key="i" />
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
import AppBounceDots from '@/shared/components/AppBounceDots.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'
import AppTwoColumnLayout from '@/shared/components/layout/AppTwoColumnLayout.vue'
import { Button } from '@/shared/ui/button'
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
import type { SubscriptionListItem } from '@/features/video/types/subscription'
import type { VideoListItem } from '@/features/video/types/video'

defineOptions({ name: 'Subscribed' })

type MainView = 'feed' | 'grid' | 'remote'

const router = useRouter()
const uiStore = useUIStore()
const toast = useToast()
const { openVideo, openSubscription } = useVideoCardNavigation(router)
const { nsfw, site } = useFeedFilters()
const { options: siteOptions, fetchSites } = useSites()
const desktopBridge = useDesktopBridge()

// Single view axis: feed (recent) | grid (channels) | remote (desktop channel source)
const mainView = ref<MainView>('feed')
const sidebarSearch = ref('')
const feedSearch = ref('')
const showSiteDropdown = ref(false)
const specialFilter = ref<'all' | 'yes'>('all')
const activeChannelId = ref<string | number | null>(null)
const activeChannelNameCache = ref('')
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

const { count: channelSkeletonCount, attachRef: channelGridRef } = useSkeletonCount({
  minCardWidth: 240,
  gap: 24,
  cardHeight: 220,
})

watch(gridWrapper, (node) => {
  videoGridRef.value = node
  channelGridRef.value = node
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

const activeChannelName = computed(() => {
  if (!activeChannelId.value) return ''
  return list.value.find(c => c.id === activeChannelId.value)?.name || activeChannelNameCache.value
})
const activeChannel = computed(() => {
  if (!activeChannelId.value) return null
  return list.value.find(c => c.id === activeChannelId.value) || null
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

/** Quiet meta fragments for the header subtitle — joined with middots in template. */
const headerMetaParts = computed(() => {
  if (mainView.value === 'remote') return [`${remoteItems.value.length} 远端视频`]
  if (mainView.value === 'grid') return [`${channelsTotal.value} 个频道`]
  if (activeChannel.value) {
    const parts = [`${feedItems.value.length} 个视频`]
    if (activeChannel.value.unread_count > 0) parts.push(`${activeChannel.value.unread_count} 未读`)
    return parts
  }
  return [`${feedItems.value.length} 个视频`, `${channelsTotal.value} 个频道`]
})

const headerLoading = computed(() => {
  if (mainView.value === 'remote') return remoteLoading.value
  if (mainView.value === 'grid') return loadingChannels.value || loadingMoreChannels.value
  return loadingFeed.value || loadingMoreFeed.value
})

const nsfwLabel = computed(() => {
  return nsfw.value === 'all'
    ? '当前显示全部内容（含成年），点击仅看成年内容'
    : '当前仅显示成年内容，点击显示全部'
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
const activeSiteLabel = computed(() => {
  if (!site.value) return '全部来源'
  return siteOptionsList.value.find(opt => opt.value === site.value)?.label || '未知来源'
})

const mainViewOptions = computed(() => {
  const options: { value: MainView; label: string }[] = [
    { value: 'feed', label: '最近发布' },
    { value: 'grid', label: '频道' },
  ]
  if (canOpenRemoteChannel.value) {
    options.push({ value: 'remote', label: '远端' })
  }
  return options
})

const sortChannels = sortSubscriptions

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
  if (specialFilter.value === 'yes' && !isSpecialFollowed && activeChannelId.value === subscriptionId) {
    activeChannelId.value = null
    activeChannelNameCache.value = ''
    if (mainView.value === 'remote') mainView.value = 'feed'
    fetchFeed(true)
  }
}

const toggleSpecialFilter = () => {
  specialFilter.value = specialFilter.value === 'yes' ? 'all' : 'yes'
}

const clearSidebarFilters = () => {
  sidebarSearch.value = ''
  site.value = ''
  specialFilter.value = 'all'
  showSiteDropdown.value = false
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
  if (activeChannelId.value === id) {
    activeChannelId.value = null
    activeChannelNameCache.value = ''
    if (mainView.value === 'remote') mainView.value = 'feed'
  } else {
    activeChannelId.value = id
    activeChannelNameCache.value = list.value.find(c => c.id === id)?.name || ''
  }
  // Selecting a channel is a feed triage action; leave remote only when still valid.
  if (mainView.value !== 'remote') {
    mainView.value = 'feed'
  }
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
  if (value === 'grid') {
    mainView.value = 'grid'
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

  if (mainView.value === 'grid') {
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

watch([nsfw, site, specialFilter], () => {
  fetchChannels(true)
  if (mainView.value === 'feed') fetchFeed(true)
  resetAllScroll()
})

watch(() => uiStore.searchTrigger, () => {
  const query = uiStore.searchQuery.trim()
  feedSearch.value = query
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
  align-items: center;
  gap: var(--space-3);
}

.subscribed-header__avatar-btn {
  position: relative;
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

.subscribed-header__copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.subscribed-header__title-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-1);
}

.subscribed-header__title {
  max-width: min(28rem, 48vw);
  overflow: hidden;
  border: 0;
  background: transparent;
  padding: 0;
  color: hsl(var(--foreground));
  font-family: var(--app-heading-font);
  font-size: var(--app-h3-size);
  font-weight: var(--app-h3-weight);
  line-height: var(--app-h3-leading);
  letter-spacing: var(--app-h3-tracking);
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-default);
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
  color: hsl(var(--muted-foreground) / 0.55);
}

.subscribed-header__star.is-active {
  color: hsl(var(--warning));
}

.subscribed-header__subtitle {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.3rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
  line-height: 1.35;
  font-variant-numeric: tabular-nums;
}

.subscribed-header__sep {
  color: hsl(var(--muted-foreground) / 0.45);
}

.subscribed-header__health {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  color: hsl(var(--muted-foreground));
}

.subscribed-header__health--error {
  color: hsl(var(--destructive) / 0.92);
}

.subscribed-header__loading {
  margin-left: 0.15rem;
}

.subscribed-header__actions {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
}

.subscribed-avatar {
  border: 1px solid var(--app-surface-border-subtle);
  transition: opacity var(--duration-fast) var(--ease-default);
}

.subscribed-avatar:hover {
  opacity: 0.9;
}

.subscribed-star-badge {
  position: absolute;
  right: -0.05rem;
  bottom: -0.05rem;
  display: flex;
  width: 1.05rem;
  height: 1.05rem;
  align-items: center;
  justify-content: center;
  border: 1px solid hsl(var(--background));
  border-radius: 999px;
  background: hsl(var(--warning) / 0.16);
  color: hsl(var(--warning));
}

.subscribed-nsfw-toggle {
  display: inline-flex;
}

.subscribed-empty-avatar {
  display: flex;
  width: 3rem;
  height: 3rem;
  flex: none;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: hsl(var(--muted) / 0.55);
  color: hsl(var(--muted-foreground));
  box-shadow: 0 0 0 1px var(--app-surface-border-subtle);
}

.subscribed-content {
  --app-workbench-content-width: 112.5rem;
}

@media (prefers-reduced-motion: reduce) {
  .subscribed-avatar,
  .subscribed-header__title {
    transition: none;
  }
}
</style>
