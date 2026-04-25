<template>
  <div class="subscribed-page flex h-full flex-col bg-background text-foreground">
    <section class="subscribed-shell">
      <div class="toolbar-container">
        <FeedToolbar
          class="subscribed-toolbar"
          :show-tabs="false"
          :tabs="[]"
          :nsfw="nsfw"
          :site="site"
          :sort-by="sortBy"
          :is-refreshing="isRefreshing"
          :filter-scope="'subscription'"
          @update:nsfw="(value) => { nsfw = value }"
          @update:site="(value) => { site = value }"
          @update:sortBy="(value) => { sortBy = value }"
          @refresh="refreshList"
        >
          <template #actions>
            <div class="toolbar-right-actions">
              <Button size="xs" class="subscribed-toolbar__button whitespace-nowrap" @click="showAddDialog = true">
                <PlusIcon class="h-4 w-4" />
                <span>添加订阅</span>
              </Button>
              <Button
                size="xs"
                variant="secondary"
                class="subscribed-toolbar__button subscribed-toolbar__button--secondary whitespace-nowrap"
                @click="showImportDialog = true"
              >
                <ArrowDownTrayIcon class="h-4 w-4" />
                <span>导入订阅</span>
              </Button>
            </div>
          </template>
        </FeedToolbar>
      </div>
    </section>

    <div class="channel-container">
      <div v-if="loadError" class="content-container content-container--alert">
        <Alert variant="destructive" class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <AlertTitle>加载失败</AlertTitle>
            <AlertDescription class="break-words">
              {{ `加载失败：${loadError?.message || loadError}` }}
            </AlertDescription>
          </div>
          <Button variant="secondary" size="sm" class="rounded-full" @click="refreshList">重试</Button>
        </Alert>
      </div>

      <div class="content-container content-container--fill">
        <Transition name="fade-list">
          <div v-if="loading && !subscriptions.length" key="loading" class="subscription-list subscription-list--loading">
            <LoadingIndicator :loading="true" text="正在加载订阅" size="sm" />
          </div>

          <div v-else-if="hasLoadedOnce && !loading && !subscriptions.length" key="empty" class="subscribed-empty-card">
            <p class="subscribed-empty-card__eyebrow">订阅库</p>
            <h2 class="subscribed-empty-card__title">还没有可展示的订阅</h2>
            <p class="subscribed-empty-card__copy">可以直接添加一个频道，或者从支持的站点批量导入。</p>
            <div class="subscribed-empty-card__actions">
              <Button size="sm" @click="showAddDialog = true">添加订阅</Button>
              <Button size="sm" variant="secondary" @click="showImportDialog = true">导入订阅</Button>
            </div>
          </div>

          <div v-else key="list" class="subscription-list-wrapper">
            <VirtualList
              class="subscription-virtual-list scrollbar-hide"
              :items="sortedSubscriptions"
              :item-size="subscriptionItemSize"
              key-field="id"
              :buffer="480"
              buffer-mode="px"
              :prerender="12"
              :range-change-throttle-ms="30"
              :bottom-padding="allLoaded && subscriptions.length ? 72 : 24"
              cache-key="subscribed-page"
              @range-change="handleVisibleRangeChange"
            >
              <template #item="{ item: subscription }">
                <article class="subscription-row" :class="{ 'is-refreshing': isResetting }">
                  <div class="subscription-row__header" @click="getSubscriptionVideos(subscription.id)">
                    <div class="subscription-row__avatar-wrap">
                      <div class="subscription-row__avatar-container">
                        <SubscriptionAvatar
                          :src="subscription.avatar"
                          :name="subscription.name"
                          size="lg"
                          class="subscription-row__avatar"
                        />
                        <div
                          v-if="getSubscriptionRefreshState(subscription.id).isRefreshing"
                          class="subscription-row__avatar-pulse"
                        ></div>
                      </div>
                    </div>

                    <div class="subscription-row__main">
                      <div class="subscription-row__name-row">
                        <h3 class="subscription-row__name" :title="subscription.name">{{ subscription.name }}</h3>
                        <span class="subscription-row__site-badge">{{ subscription.site || 'unknown' }}</span>
                        <span v-if="subscription.type === 'PLAYLIST'" class="subscription-row__type-tag">播放列表</span>
                        <span v-if="subscription.is_nsfw" class="subscription-row__nsfw-tag">NSFW</span>
                      </div>
                      <div class="subscription-row__meta">
                        <span
                          class="subscription-row__status-badge"
                          :class="getStatusBadgeClass(getSubscriptionRefreshState(subscription.id).status)"
                        >
                          <span
                            v-if="getSubscriptionRefreshState(subscription.id).isRefreshing"
                            class="status-badge-dot animate-pulse"
                          ></span>
                          {{ getStatusText(
                            getSubscriptionRefreshState(subscription.id).status,
                            getSubscriptionRefreshState(subscription.id).phase,
                          ) }}
                        </span>
                        <span class="subscription-row__sep" aria-hidden="true"></span>
                        <span class="subscription-row__date">{{ formatDate(subscription.created_at) }}</span>
                      </div>
                    </div>

                    <div class="subscription-row__stats" @click="getSubscriptionVideos(subscription.id)">
                      <div class="subscription-row__stat-item">
                        <span class="subscription-row__stat-value tabular-nums">{{ subscription.total_videos }}</span>
                        <span class="subscription-row__stat-label">视频</span>
                      </div>
                      <div class="subscription-row__stat-sep" aria-hidden="true"></div>
                      <div class="subscription-row__stat-item">
                        <span class="subscription-row__stat-value tabular-nums">{{ subscription.total_extract }}</span>
                        <span class="subscription-row__stat-label">已解析</span>
                      </div>
                    </div>

                    <div class="subscription-row__actions">
                      <button
                        class="row-action-btn"
                        :disabled="getSubscriptionRefreshState(subscription.id).isRefreshing"
                        :title="getSubscriptionRefreshState(subscription.id).isRefreshing ? '更新中' : '刷新'"
                        @click.stop="handleRefreshSubscription(subscription.id)"
                      >
                        <ArrowPathIcon
                          class="row-action-icon"
                          :class="{ 'is-spinning': getSubscriptionRefreshState(subscription.id).isRefreshing }"
                        />
                      </button>
                      <button class="row-action-btn" title="设置" @click.stop="openSettings(subscription)">
                        <Cog6ToothIcon class="row-action-icon" />
                      </button>
                    </div>
                  </div>

                  <div v-if="subscription.recent_videos?.length" class="subscription-row__recent-grid">
                    <button
                      v-for="video in subscription.recent_videos"
                      :key="video.id"
                      type="button"
                      class="recent-video-card"
                      @click.stop="openRecentVideo(video)"
                    >
                      <div class="recent-video-card__thumb-wrap">
                        <img
                          v-if="video.thumbnail && !hasThumbnailError(subscription.id, video.id)"
                          :src="video.thumbnail"
                          :alt="video.title || '视频缩略图'"
                          class="recent-video-card__thumb"
                          referrerpolicy="no-referrer"
                          @error="handleThumbnailError(subscription.id, video.id)"
                        >
                        <div v-else class="recent-video-card__thumb-placeholder">
                          <Icon icon="lucide:image-off" class="recent-video-card__thumb-placeholder-icon" />
                          <span class="recent-video-card__thumb-placeholder-text">暂无封面</span>
                        </div>
                        <span v-if="video.duration" class="recent-video-card__duration">{{ formatDuration(video.duration) }}</span>
                      </div>
                      <p class="recent-video-card__title">{{ video.title || '未知视频' }}</p>
                      <p class="recent-video-card__meta">{{ formatDate(video.publish_date) }}</p>
                    </button>
                  </div>
                  <div v-else class="subscription-row__recent-empty">暂无最近视频</div>
                </article>
              </template>
            </VirtualList>
          </div>
        </Transition>

        <div v-if="allLoaded && subscriptions.length" class="subscribed-bottom-copy">
          {{ subscriptions.length }} 个订阅 · 已经到底啦
        </div>
      </div>
    </div>

    <Dialog :open="showSettings" @update:open="handleSettingsOpenChange">
      <DialogContent class="max-w-lg gap-0 overflow-hidden p-0">
        <DialogHeader class="px-6 pb-2 pt-6">
          <DialogTitle class="text-lg font-semibold tracking-[-0.02em]">订阅设置</DialogTitle>
        </DialogHeader>

        <div v-if="selectedSubscription" class="space-y-4 px-6 pb-6">
          <div class="subscription-dialog__summary">
            <SubscriptionAvatar
              :src="selectedSubscription.avatar"
              :name="selectedSubscription.name"
              size="lg"
              class="subscription-dialog__avatar"
            />

            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-center gap-2">
                <p class="truncate text-sm font-semibold text-foreground">{{ selectedSubscription.name }}</p>
                <Badge v-if="selectedSubscription.type === 'PLAYLIST'" variant="secondary">播放列表</Badge>
                <Badge v-if="selectedSubscription.is_nsfw" variant="destructive">NSFW</Badge>
              </div>
              <p class="mt-1 text-xs text-muted-foreground">
                {{ selectedRefreshState.status === 'failed'
                  ? '最近一次同步失败'
                  : getStatusText(selectedRefreshState.status, selectedRefreshState.phase) || '等待同步' }}
              </p>
            </div>
          </div>

          <div class="subscription-dialog__row">
            <div>
              <p class="text-sm font-medium text-foreground">标记为敏感内容</p>
              <p class="mt-1 text-xs text-muted-foreground">用于控制缩略图模糊和过滤行为。</p>
            </div>
            <Switch
              :checked="!!selectedSubscription.is_nsfw"
              @update:checked="(value) => { selectedSubscription.is_nsfw = !!value; updateNsfwStatus(!!value) }"
            />
          </div>

          <div class="subscription-dialog__actions">
            <Button class="w-full" :disabled="selectedRefreshState.isRefreshing" @click="handleRefreshSubscription(selectedSubscription.id)">
              {{ selectedRefreshState.isRefreshing
                ? getStatusText(selectedRefreshState.status, selectedRefreshState.phase) || '更新中'
                : '手动更新' }}
            </Button>

            <Button
              v-if="selectedRefreshState.status === 'failed'"
              variant="secondary"
              class="w-full"
              @click="handleRetryRefresh(selectedSubscription.id)"
            >
              重试更新
            </Button>

            <Alert v-if="selectedRefreshState.status === 'failed'" variant="destructive">
              <AlertDescription>
                {{ selectedRefreshState.lastError || '更新失败' }}
              </AlertDescription>
            </Alert>

            <Button
              variant="destructive"
              class="w-full"
              :disabled="selectedRefreshState.isRefreshing || isUnsubscribing"
              @click="unsubscribe(selectedSubscription.id)"
            >
              <span v-if="isUnsubscribing" class="subscription-dialog__spinner" aria-hidden="true"></span>
              <span>{{ isUnsubscribing ? '取消中' : '取消订阅' }}</span>
            </Button>

            <p v-if="unsubscribeError" class="text-xs text-destructive">{{ unsubscribeError }}</p>
          </div>
        </div>

        <DialogFooter class="px-6 py-4 sm:justify-end">
          <Button size="sm" variant="ghost" :disabled="isUnsubscribing" @click="closeSettings">关闭</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <AddChannelDialog :show="showAddDialog" @added="handleChannelAdded" @close="showAddDialog = false" />

    <ImportSubscriptionDialog
      :show="showImportDialog"
      @close="showImportDialog = false"
      @imported="handleSubscriptionsImported"
    />
  </div>
</template>

<script setup>
import { computed, inject, onMounted, onUnmounted, reactive, ref, shallowRef, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import { ArrowDownTrayIcon, ArrowPathIcon, Cog6ToothIcon, PlusIcon } from '@heroicons/vue/24/outline'
import FeedToolbar from '@/components/feed/FeedToolbar.vue'
import LoadingIndicator from '@/components/feed/LoadingIndicator.vue'
import VirtualList from '@/components/feed/VirtualList.vue'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import AddChannelDialog from '@/components/dialogs/AddChannelDialog.vue'
import ImportSubscriptionDialog from '@/components/dialogs/ImportSubscriptionDialog.vue'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Switch } from '@/components/ui/switch'
import { useRefreshTriggers } from '../composables/useRefreshTriggers'
import { useSubscriptionRefresh } from '../composables/useSubscriptionRefresh'
import { useFeedFilters } from '../composables/useFeedFilters'
import { formatDate, formatDuration } from '../utils/dateFormat'
import { notifySubscriptionRemoved } from '@/utils/subscriptionEvents'
import { rememberVideoPlaybackSeed } from '@/composables/videoPlaybackSeed'
import {
  getSubscriptions as apiGetSubscriptions,
  unsubscribe as apiUnsubscribe,
  updateNsfwStatus as apiUpdateNsfwStatus,
} from '@/api'

const router = useRouter()
const emitter = inject('emitter')

const SUBSCRIPTION_REMOVE_DELAY_MS = 120
const SUBSCRIPTIONS_PAGE_SIZE = 100
const VIRTUAL_LIST_PRELOAD_COUNT = 8
const DESKTOP_SUBSCRIPTION_ROW_HEIGHT = 278
const MOBILE_SUBSCRIPTION_ROW_HEIGHT = 290
const MIN_SPIN_MS = 800
const CANCELED_ERROR_TYPE = 'CANCELED'

const isRefreshing = ref(false)
const isResetting = ref(false)
const isCompactLayout = ref(typeof window !== 'undefined' ? window.innerWidth <= 960 : false)
const subscriptions = shallowRef([])
const loadError = ref(null)
const loading = ref(false)
const hasLoadedOnce = ref(false)
const allLoaded = ref(false)
const currentPage = ref(1)
const searchQuery = ref('')
const { nsfw, site, sortBy } = useFeedFilters()

const showSettings = ref(false)
const selectedSubscription = ref(null)
const showAddDialog = ref(false)
const showImportDialog = ref(false)
const unsubscribeError = ref('')
const unsubscribingId = ref(null)
const spinTimer = ref(null)
const spinStartAt = ref(0)
const defaultRefreshState = Object.freeze({
  status: 'idle',
  phase: null,
  lastError: null,
  isRefreshing: false,
})
const sortTextCollator = new Intl.Collator('zh-CN')
const thumbnailErrorMap = reactive({})
let latestLoadRequestId = 0
let listAbortController = null

const subscriptionItemSize = computed(() => (
  isCompactLayout.value ? MOBILE_SUBSCRIPTION_ROW_HEIGHT : DESKTOP_SUBSCRIPTION_ROW_HEIGHT
))

const getThumbnailErrorKey = (subscriptionId, videoId) => `${subscriptionId}-${videoId}`
const hasThumbnailError = (subscriptionId, videoId) => !!thumbnailErrorMap[getThumbnailErrorKey(subscriptionId, videoId)]
const handleThumbnailError = (subscriptionId, videoId) => {
  thumbnailErrorMap[getThumbnailErrorKey(subscriptionId, videoId)] = true
}

const wait = (ms) => new Promise((resolve) => {
  window.setTimeout(resolve, ms)
})

const {
  refreshStates,
  getRefreshState,
  triggerRefresh,
  retryRefresh,
  getStatusText,
  cleanup: cleanupRefresh,
  setSubscriptionMeta,
} = useSubscriptionRefresh()

const sortedSubscriptions = computed(() => {
  if (subscriptions.value.length < 2) {
    return subscriptions.value
  }

  const sorted = [...subscriptions.value]

  if (sortBy.value === 'name') {
    sorted.sort((a, b) => sortTextCollator.compare(a.name || '', b.name || ''))
    return sorted
  }

  if (sortBy.value === 'site') {
    sorted.sort((a, b) => sortTextCollator.compare(a.site || '', b.site || ''))
    return sorted
  }

  if (sortBy.value === 'recent') {
    sorted.sort((a, b) => new Date(b.updated_at || 0).getTime() - new Date(a.updated_at || 0).getTime())
  }

  return sorted
})

const selectedRefreshState = computed(() => {
  if (!selectedSubscription.value) {
    return defaultRefreshState
  }

  return refreshStates.get(selectedSubscription.value.id) || defaultRefreshState
})

const isUnsubscribing = computed(() => unsubscribingId.value === selectedSubscription.value?.id)
const getSubscriptionRefreshState = (subscriptionId) => refreshStates.get(subscriptionId) || defaultRefreshState

const updateLayoutMode = () => {
  isCompactLayout.value = window.innerWidth <= 960
}

const clearSpinTimer = () => {
  if (spinTimer.value) {
    clearTimeout(spinTimer.value)
    spinTimer.value = null
  }
}

const createSubscriptionParams = () => ({
  query: searchQuery.value,
  nsfw: nsfw.value,
  site: site.value,
  page: currentPage.value,
  page_size: SUBSCRIPTIONS_PAGE_SIZE,
})

const normalizeSubscription = (subscription) => ({
  ...subscription,
  total_videos: subscription.total_videos || 0,
  total_extract: subscription.total_extract || 0,
  recent_videos: Array.isArray(subscription.recent_videos) ? subscription.recent_videos : [],
})

const patchSubscription = (subscriptionId, patch) => {
  const index = subscriptions.value.findIndex((subscription) => subscription.id === subscriptionId)
  if (index === -1) {
    return
  }

  const nextSubscriptions = [...subscriptions.value]
  nextSubscriptions[index] = {
    ...nextSubscriptions[index],
    ...patch,
  }
  subscriptions.value = nextSubscriptions

  if (selectedSubscription.value?.id === subscriptionId) {
    selectedSubscription.value = {
      ...selectedSubscription.value,
      ...patch,
    }
  }
}

const applySubscriptionPage = (mappedSubscriptions, requestedPage) => {
  mappedSubscriptions.forEach((subscription) => {
    getRefreshState(subscription.id)
    setSubscriptionMeta(subscription.id, { name: subscription.name, avatar: subscription.avatar })
  })

  if (requestedPage === 1) {
    subscriptions.value = mappedSubscriptions
    return
  }

  const existingIds = new Set(subscriptions.value.map((subscription) => subscription.id))
  const deduped = mappedSubscriptions.filter((subscription) => !existingIds.has(subscription.id))
  subscriptions.value = [...subscriptions.value, ...deduped]
}

const resetSubscriptionState = ({ clearItems = true } = {}) => {
  currentPage.value = 1
  allLoaded.value = false
  loadError.value = null

  if (clearItems) {
    hasLoadedOnce.value = false
    subscriptions.value = []
  }
}

const loadSubscriptions = async ({ force = false } = {}) => {
  if ((loading.value && !force) || (allLoaded.value && !force)) {
    return
  }

  const requestId = ++latestLoadRequestId
  const requestedPage = currentPage.value

  loading.value = true
  listAbortController?.abort()
  listAbortController = new AbortController()

  try {
    const { data, error } = await apiGetSubscriptions(createSubscriptionParams(), {
      signal: listAbortController.signal,
    })

    if (requestId !== latestLoadRequestId) {
      return
    }

    if (error?.type === CANCELED_ERROR_TYPE) {
      return
    }

    if (error) {
      loadError.value = error || '获取订阅列表失败'
      return
    }

    const newSubscriptions = Array.isArray(data?.data) ? data.data : (Array.isArray(data) ? data : [])
    const mappedSubscriptions = newSubscriptions.map((subscription) => normalizeSubscription(subscription))

    applySubscriptionPage(mappedSubscriptions, requestedPage)
    loadError.value = null
    currentPage.value = requestedPage + 1
    allLoaded.value = newSubscriptions.length < SUBSCRIPTIONS_PAGE_SIZE
  } finally {
    if (requestId === latestLoadRequestId) {
      hasLoadedOnce.value = true
      loading.value = false
      listAbortController = null
    }
  }
}

const loadMore = () => {
  if (loading.value || allLoaded.value) {
    return
  }
  loadSubscriptions()
}

const handleVisibleRangeChange = ({ end }) => {
  if (!sortedSubscriptions.value.length || loading.value || allLoaded.value) {
    return
  }

  if (end >= sortedSubscriptions.value.length - VIRTUAL_LIST_PRELOAD_COUNT) {
    loadMore()
  }
}

useRefreshTriggers({ onRefresh: refreshList })

async function refreshList() {
  clearSpinTimer()
  isRefreshing.value = true
  isResetting.value = true
  resetSubscriptionState({ clearItems: false })
  spinStartAt.value = Date.now()

  try {
    await loadSubscriptions({ force: true })
  } finally {
    const elapsed = Date.now() - spinStartAt.value
    const remain = Math.max(0, MIN_SPIN_MS - elapsed)
    clearSpinTimer()
    spinTimer.value = setTimeout(() => {
      isRefreshing.value = false
      isResetting.value = false
      clearSpinTimer()
    }, remain)
  }
}

const handleGlobalSearch = async (query) => {
  searchQuery.value = query || ''
  resetSubscriptionState()
  await loadSubscriptions({ force: true })
  isRefreshing.value = false
}

watch([nsfw, site], async () => {
  resetSubscriptionState()
  await loadSubscriptions({ force: true })
})

const openSettings = (subscription) => {
  selectedSubscription.value = { ...subscription }
  setSubscriptionMeta(subscription.id, { name: subscription.name, avatar: subscription.avatar })
  showSettings.value = true
}

const closeSettings = () => {
  showSettings.value = false
  selectedSubscription.value = null
  unsubscribeError.value = ''
}

const handleSettingsOpenChange = (open) => {
  if (unsubscribingId.value) {
    return
  }

  if (!open) {
    closeSettings()
  }
}

const unsubscribe = async (subscriptionId) => {
  if (!subscriptionId || unsubscribingId.value) {
    return
  }

  unsubscribeError.value = ''
  unsubscribingId.value = subscriptionId

  const { error } = await apiUnsubscribe(subscriptionId)

  if (error) {
    unsubscribeError.value = error?.message || '取消订阅失败'
    unsubscribingId.value = null
    return
  }

  closeSettings()
  notifySubscriptionRemoved(subscriptionId)
  await wait(SUBSCRIPTION_REMOVE_DELAY_MS)
  subscriptions.value = subscriptions.value.filter((subscription) => subscription.id !== subscriptionId)
  unsubscribingId.value = null
}

const openRecentVideo = (video) => {
  const videoId = video?.id
  if (!videoId) return

  rememberVideoPlaybackSeed(video)
  router.push(`/video/${videoId}`)
}

const getSubscriptionVideos = (subscriptionId) => {
  router.push(`/subscription/${subscriptionId}/all`)
}

const reloadSubscriptions = () => {
  resetSubscriptionState()
  loadSubscriptions({ force: true })
}

const handleChannelAdded = () => {
  reloadSubscriptions()
}

const handleSubscriptionsImported = () => {
  reloadSubscriptions()
}

const updateNsfwStatus = async (isNsfw) => {
  const subscriptionId = selectedSubscription.value?.id
  if (!subscriptionId) {
    return
  }

  const { error } = await apiUpdateNsfwStatus(subscriptionId, isNsfw)

  if (!error) {
    patchSubscription(subscriptionId, { is_nsfw: isNsfw })
    return
  }

  patchSubscription(subscriptionId, { is_nsfw: !isNsfw })
}

const handleRefreshSubscription = async (subscriptionId) => {
  await triggerRefresh(subscriptionId)
}

const handleRetryRefresh = async (subscriptionId) => {
  await retryRefresh(subscriptionId)
}

const getStatusBadgeClass = (status) => {
  switch (status) {
    case 'queued': return 'badge--queued'
    case 'in_progress': return 'badge--progress'
    case 'completed': return 'badge--completed'
    case 'failed': return 'badge--failed'
    default: return 'badge--idle'
  }
}

onMounted(() => {
  updateLayoutMode()
  window.addEventListener('resize', updateLayoutMode)
  loadSubscriptions()
  emitter?.on?.('search:subscribed', handleGlobalSearch)
})

onUnmounted(() => {
  clearSpinTimer()
  listAbortController?.abort()
  window.removeEventListener('resize', updateLayoutMode)
  emitter?.off?.('search:subscribed', handleGlobalSearch)
  cleanupRefresh()
})
</script>

<style scoped>
.subscribed-page {
  min-height: 100%;
}

.toolbar-container,
.content-container {
  width: 100%;
  margin: 0 auto;
  padding: 0 1rem;
}

@media (min-width: 640px) {
  .toolbar-container,
  .content-container {
    padding: 0 1.5rem;
  }
}

@media (min-width: 1024px) {
  .toolbar-container,
  .content-container {
    padding: 0 2rem;
  }
}

.subscribed-shell {
  padding-top: 0.5rem;
}

.subscribed-toolbar {
  padding: 0.75rem 0;
}

.subscribed-toolbar :deep(.toolbar-slot-actions) {
  gap: 0.5rem;
}

.toolbar-right-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.subscribed-toolbar__button {
  gap: 0.35rem;
  padding-inline: 0.65rem;
  border-radius: calc(var(--radius-sm) + 1px);
}

.subscribed-toolbar__button--secondary {
  border-color: hsl(var(--border) / 0.55);
  background: hsl(var(--background) / 0.65);
}

.channel-container {
  flex: 1;
  min-height: 0;
  padding-top: 0.75rem;
}

.content-container--fill {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.subscription-list {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.subscription-list--loading {
  min-height: calc(100dvh - 12rem);
}

.subscription-list-wrapper {
  flex: 1;
  min-height: 0;
}

.subscription-virtual-list {
  height: calc(100dvh - 10.75rem);
  min-height: 24rem;
  padding-bottom: 0.5rem;
}

.subscription-row {
  display: grid;
  grid-template-rows: 5rem 1fr;
  height: 100%;
  box-sizing: border-box;
  background: hsl(var(--background));
  overflow: hidden;
  transition: background 0.15s ease;
}

.subscription-row:hover {
  background: hsl(var(--secondary) / 0.08);
}

.subscription-row__header {
  display: grid;
  grid-template-columns: 3rem minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 0 1.25rem;
  padding: 0.875rem 1rem;
  cursor: pointer;
}

.subscription-row__avatar-wrap {
  display: flex;
  justify-content: center;
}

.subscription-row__avatar-container {
  position: relative;
  width: 2.75rem;
  height: 2.75rem;
}

.subscription-row__avatar {
  width: 100%;
  height: 100%;
  border-radius: calc(var(--radius-sm) - 1px);
}

.subscription-row__avatar :deep(.avatar-image) {
  filter: grayscale(0.15);
  transition: filter 0.2s ease;
}

.subscription-row:hover .subscription-row__avatar :deep(.avatar-image) {
  filter: grayscale(0);
}

.subscription-row__avatar-pulse {
  position: absolute;
  inset: -3px;
  border: 2px solid hsl(var(--primary) / 0.65);
  border-radius: calc(var(--radius-sm) + 2px);
  animation: stream-pulse 1.5s ease-in-out infinite;
}

.subscription-row__main {
  min-width: 0;
}

.subscription-row__name-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.3rem;
}

.subscription-row__name {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.subscription-row__site-badge,
.subscription-row__type-tag,
.subscription-row__nsfw-tag {
  flex-shrink: 0;
  border-radius: 3px;
}

.subscription-row__site-badge {
  font-size: 0.6rem;
  font-weight: 600;
  color: hsl(var(--primary) / 0.75);
  padding: 0.1rem 0.35rem;
  background: hsl(var(--primary) / 0.08);
  letter-spacing: 0.04em;
  text-transform: lowercase;
}

.subscription-row__type-tag {
  font-size: 0.55rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: hsl(var(--muted-foreground) / 0.7);
  padding: 0.08rem 0.3rem;
  background: hsl(var(--secondary) / 0.45);
}

.subscription-row__nsfw-tag {
  font-size: 0.55rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: hsl(var(--destructive) / 0.85);
  padding: 0.08rem 0.3rem;
  background: hsl(var(--destructive) / 0.1);
}

.subscription-row__meta {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.subscription-row__status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.65rem;
  font-weight: 500;
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
}

.badge--idle {
  color: hsl(var(--muted-foreground) / 0.6);
  background: hsl(var(--secondary) / 0.25);
}

.badge--queued {
  color: hsl(var(--muted-foreground));
  background: hsl(var(--secondary) / 0.4);
}

.badge--progress {
  color: hsl(var(--primary) / 0.9);
  background: hsl(var(--primary) / 0.1);
}

.badge--completed {
  color: hsl(142 70% 40% / 0.9);
  background: hsl(142 70% 40% / 0.1);
}

.badge--failed {
  color: hsl(var(--destructive) / 0.85);
  background: hsl(var(--destructive) / 0.1);
}

.status-badge-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

.subscription-row__sep {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: hsl(var(--border));
  flex-shrink: 0;
}

.subscription-row__date {
  font-size: 0.65rem;
  color: hsl(var(--muted-foreground) / 0.5);
}

.subscription-row__stats {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 0 0.5rem;
}

.subscription-row__stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  min-width: 2.5rem;
}

.subscription-row__stat-value {
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  line-height: 1;
}

.subscription-row__stat-label {
  font-size: 0.55rem;
  color: hsl(var(--muted-foreground) / 0.5);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.subscription-row__stat-sep {
  width: 1px;
  height: 1.5rem;
  background: hsl(var(--border) / 0.5);
  flex-shrink: 0;
}

.subscription-row__actions {
  display: flex;
  align-items: center;
  gap: 0.125rem;
  opacity: 0.45;
  transition: opacity 0.15s ease;
}

.subscription-row:hover .subscription-row__actions,
.subscription-row__actions:focus-within {
  opacity: 1;
}

.row-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border: none;
  background: transparent;
  border-radius: calc(var(--radius-sm) - 1px);
  cursor: pointer;
  color: hsl(var(--muted-foreground));
  transition: all 0.15s ease;
}

.row-action-btn:hover {
  background: hsl(var(--secondary) / 0.4);
  color: hsl(var(--foreground));
}

.row-action-btn:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

.row-action-icon {
  width: 0.875rem;
  height: 0.875rem;
}

.row-action-icon.is-spinning {
  animation: spin 0.8s linear infinite;
}

.subscription-row__recent-grid {
  display: flex;
  gap: 0.5rem;
  padding: 0.2rem 1rem 0.85rem;
  overflow-x: auto;
  overflow-y: hidden;
  min-height: 0;
  scrollbar-width: none;
}

.subscription-row__recent-grid::-webkit-scrollbar {
  display: none;
}

.recent-video-card {
  display: block;
  width: 13rem;
  min-width: 13rem;
  max-width: 13rem;
  box-sizing: border-box;
  border: none;
  background: transparent;
  border-radius: var(--radius-sm);
  padding: 0.2rem;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease;
}

.recent-video-card:hover {
  background: hsl(var(--secondary) / 0.22);
}

.recent-video-card__thumb-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  border-radius: calc(var(--radius-sm) - 1px);
  overflow: hidden;
  background: hsl(var(--secondary) / 0.6);
}

.recent-video-card__thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.recent-video-card__thumb-placeholder {
  width: 100%;
  height: 100%;
  background: hsl(var(--secondary) / 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.15rem;
  color: hsl(var(--muted-foreground) / 0.75);
}

.recent-video-card__thumb-placeholder-icon {
  width: 1rem;
  height: 1rem;
  opacity: 0.8;
}

.recent-video-card__thumb-placeholder-text {
  font-size: 0.6rem;
  line-height: 1;
}

.recent-video-card__duration {
  position: absolute;
  right: 0.25rem;
  bottom: 0.2rem;
  font-size: 0.6rem;
  font-weight: 600;
  color: #fff;
  background: rgb(0 0 0 / 0.72);
  border-radius: 3px;
  padding: 0.05rem 0.28rem;
  font-variant-numeric: tabular-nums;
}

.recent-video-card__title {
  margin: 0.3rem 0 0;
  font-size: 0.72rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.35;
}

.recent-video-card__meta {
  margin: 0.15rem 0 0;
  font-size: 0.64rem;
  color: hsl(var(--muted-foreground) / 0.8);
  line-height: 1.3;
}

.subscription-row__recent-empty {
  margin: 0 1rem 1rem;
  border: 1px dashed hsl(var(--border) / 0.6);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.68rem;
  color: hsl(var(--muted-foreground));
}

.subscribed-empty-card {
  min-height: 40vh;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  text-align: center;
  gap: 1.25rem;
  padding: 2rem;
  border: 1px dashed hsl(var(--border) / 0.6);
  border-radius: var(--radius-lg);
}

.subscribed-empty-card__eyebrow {
  font-family: var(--font-mono, monospace);
  font-size: 0.75rem;
  color: hsl(var(--primary));
  letter-spacing: 0.2em;
}

.subscribed-empty-card__title {
  font-size: 1.25rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.subscribed-empty-card__copy {
  max-width: 22rem;
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground));
  line-height: 1.6;
}

.subscribed-empty-card__actions {
  display: flex;
  gap: 0.75rem;
}

.subscribed-bottom-copy {
  margin: 1rem 0 0.75rem;
  text-align: center;
  color: hsl(var(--muted-foreground) / 0.35);
  font-size: 0.7rem;
  letter-spacing: 0.08em;
}

.subscription-dialog__summary {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.subscription-dialog__avatar {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: calc(var(--radius-sm) - 1px);
}

.subscription-dialog__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.subscription-dialog__actions {
  display: grid;
  gap: 0.75rem;
}

.subscription-dialog__spinner {
  width: 0.75rem;
  height: 0.75rem;
  margin-right: 0.35rem;
  border-radius: 999px;
  border: 2px solid hsl(var(--destructive-foreground) / 0.35);
  border-top-color: hsl(var(--destructive-foreground));
  animation: spin 0.8s linear infinite;
}

@keyframes stream-pulse {
  0% { transform: scale(1); opacity: 0.4; }
  50% { transform: scale(1.05); opacity: 1; }
  100% { transform: scale(1); opacity: 0.4; }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.fade-list-enter-active,
.fade-list-leave-active {
  transition: opacity 0.3s ease;
}

.fade-list-enter-from,
.fade-list-leave-to {
  opacity: 0;
}

@media (max-width: 960px) {
  .subscription-virtual-list {
    height: calc(100dvh - 11.5rem);
  }

  .subscription-row {
    grid-template-rows: 5.5rem 1fr;
  }

  .subscription-row__header {
    grid-template-columns: 2.5rem minmax(0, 1fr) auto;
    grid-template-rows: auto auto;
    gap: 0 0.75rem;
    padding: 0.75rem;
  }

  .subscription-row__avatar-container {
    width: 2.25rem;
    height: 2.25rem;
  }

  .subscription-row__main {
    grid-column: 2;
    grid-row: 1;
  }

  .subscription-row__stats {
    grid-column: 3;
    grid-row: 1;
    gap: 0.75rem;
    padding: 0;
  }

  .subscription-row__actions {
    grid-column: 2 / 4;
    grid-row: 2;
    opacity: 1;
    padding-top: 0.25rem;
    justify-content: flex-start;
  }

  .subscription-row__recent-grid {
    padding: 0 0.75rem 0.75rem;
  }

  .subscription-row__recent-empty {
    margin: 0 0.75rem 0.75rem;
  }
}

@media (max-width: 640px) {
  .toolbar-right-actions {
    width: 100%;
    justify-content: flex-end;
    flex-wrap: wrap;
  }

  .subscribed-empty-card__actions {
    flex-wrap: wrap;
    justify-content: center;
  }
}

@media (hover: none) {
  .subscription-row__actions {
    opacity: 1;
  }
}
</style>
