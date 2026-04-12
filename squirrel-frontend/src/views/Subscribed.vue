<template>
  <div class="subscribed-page flex h-full flex-col bg-background text-foreground">
    <section class="subscribed-shell">
      <div class="toolbar-container">
        <FeedToolbar
          class="subscribed-toolbar"
          :show-tabs="false"
          :tabs-with-counts="[]"
          :nsfw="nsfw"
          :site="site"
          :sort-by="sortBy"
          :is-refreshing="isRefreshing"
          :filter-scope="'subscription'"
          @update:nsfw="(value) => { nsfw = value }"
          @update:site="(value) => { site = value }"
          @update:sortBy="(value) => { sortBy = value; handleSortChange(value) }"
          @refresh="refreshList"
        >
          <template #actions>
            <div class="toolbar-left-actions">
              <div class="sort-tabs" role="tablist" aria-label="排序方式">
                <button
                  v-for="opt in sortOptions"
                  :key="opt.value"
                  class="sort-tab"
                  :class="{ 'is-active': sortBy === opt.value }"
                  role="tab"
                  :aria-selected="sortBy === opt.value"
                  @click="handleSortChange(opt.value)"
                >
                  {{ opt.label }}
                </button>
              </div>
              <div class="toolbar-divider" aria-hidden="true"></div>
            </div>
            <div class="toolbar-right-actions">
              <Button size="xs" class="subscribed-toolbar__button whitespace-nowrap" @click="showAddDialog = true">
                <PlusIcon class="h-4 w-4" />
                <span>添加订阅</span>
              </Button>
              <Button size="xs" variant="secondary" class="subscribed-toolbar__button subscribed-toolbar__button--secondary whitespace-nowrap" @click="showImportDialog = true">
                <ArrowDownTrayIcon class="h-4 w-4" />
                <span>导入订阅</span>
              </Button>
            </div>
          </template>
        </FeedToolbar>
      </div>
    </section>

    <div
      ref="scrollContainer"
      class="channel-container scrollbar-hide flex-grow overflow-y-auto"
      @scroll="handleScrollPosition"
    >
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

      <div class="content-container">
        <div v-if="loading && subscriptions.length" class="subscribed-inline-loading">
          <LoadingIndicator :loading="true" text="正在加载订阅" size="sm" />
        </div>

        <Transition name="fade-list">
          <div v-if="loading && !subscriptions.length" key="skeleton" class="subscription-list subscription-list--loading">
            <SubscriptionSkeleton v-for="i in 14" :key="i" :delay="i * 70" />
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

          <TransitionGroup v-else key="list" name="subscription-row" tag="div" class="subscription-list">
            <article
              v-for="subscription in subscriptions"
              :key="subscription.id"
              class="subscription-row"
              :class="{ 'is-refreshing': isResetting }"
            >
              <!-- Left: Avatar -->
              <div class="subscription-row__avatar-wrap" @click="getSubscriptionVideos(subscription.id)">
                <div class="subscription-row__avatar-container">
                  <SubscriptionAvatar
                    :src="subscription.avatar"
                    :name="subscription.name"
                    size="lg"
                    class="subscription-row__avatar"
                  />
                  <div v-if="getRefreshState(subscription.id).isRefreshing" class="subscription-row__avatar-pulse"></div>
                </div>
              </div>

              <!-- Center: Identity & Metadata -->
              <div class="subscription-row__main" @click="getSubscriptionVideos(subscription.id)">
                <div class="subscription-row__name-row">
                  <h3 class="subscription-row__name" :title="subscription.name">{{ subscription.name }}</h3>
                  <span class="subscription-row__site-badge">
                    {{ subscription.site || 'unknown' }}
                  </span>
                  <span v-if="subscription.type === 'PLAYLIST'" class="subscription-row__type-tag">播放列表</span>
                  <span v-if="subscription.is_nsfw" class="subscription-row__nsfw-tag">NSFW</span>
                </div>
                <div class="subscription-row__meta">
                  <span
                    class="subscription-row__status-badge"
                    :class="getStatusBadgeClass(getRefreshState(subscription.id).status)"
                  >
                    <span
                      v-if="getRefreshState(subscription.id).isRefreshing"
                      class="status-badge-dot animate-pulse"
                    ></span>
                    {{ getStatusText(getRefreshState(subscription.id).status, getRefreshState(subscription.id).phase) }}
                  </span>
                  <span class="subscription-row__sep" aria-hidden="true"></span>
                  <span class="subscription-row__date">{{ formatDate(subscription.created_at) }}</span>
                </div>
              </div>

              <!-- Stats -->
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

              <!-- Actions: always visible -->
              <div class="subscription-row__actions">
                <button
                  class="row-action-btn"
                  :disabled="getRefreshState(subscription.id).isRefreshing"
                  :title="getRefreshState(subscription.id).isRefreshing ? '更新中' : '刷新'"
                  @click="handleRefreshSubscription(subscription.id)"
                >
                  <ArrowPathIcon class="row-action-icon" :class="{ 'is-spinning': getRefreshState(subscription.id).isRefreshing }" />
                </button>
                <button
                  class="row-action-btn"
                  title="设置"
                  @click="openSettings(subscription)"
                >
                  <Cog6ToothIcon class="row-action-icon" />
                </button>
              </div>
            </article>
          </TransitionGroup>
        </Transition>

        <div
          v-show="loading || (!allLoaded && subscriptions.length > 0)"
          ref="loadingTrigger"
          class="subscribed-loading-trigger"
        >
          <LoadingIndicator v-if="loading" :loading="true" text="加载更多" size="sm" />
          <span v-else class="subscribed-trigger-hint">滚动加载更多</span>
        </div>

        <div v-if="allLoaded && subscriptions.length" class="subscribed-bottom-copy">
          {{ subscriptions.length }} 个订阅 · 已经到底啦
        </div>
      </div>
    </div>

    <Dialog :open="showSettings" @update:open="handleSettingsOpenChange">
      <DialogContent class="max-w-lg gap-0 overflow-hidden p-0">
        <div class="subscription-dialog__hero">
          <DialogHeader class="space-y-2 px-6 pb-4 pt-6">
            <DialogTitle class="text-xl font-semibold tracking-[-0.03em]">
              {{ selectedSubscription?.name || '订阅设置' }}
            </DialogTitle>
            <DialogDescription>
              调整频道设置、手动触发更新，或取消订阅。
            </DialogDescription>
          </DialogHeader>
        </div>

        <div v-if="selectedSubscription" class="space-y-5 px-6 py-5">
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
            <Button
              class="w-full"
              :disabled="selectedRefreshState.isRefreshing"
              @click="handleRefreshSubscription(selectedSubscription.id)"
            >
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

        <DialogFooter class="border-t border-border/70 bg-secondary/24 px-6 py-4 sm:justify-end">
          <Button size="sm" variant="ghost" :disabled="isUnsubscribing" @click="closeSettings">关闭</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <AddChannelDialog
      :show="showAddDialog"
      @added="handleChannelAdded"
      @close="showAddDialog = false"
    />

    <ImportSubscriptionDialog
      :show="showImportDialog"
      @close="showImportDialog = false"
      @imported="handleSubscriptionsImported"
    />
  </div>
</template>

<script setup>
import { computed, inject, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowDownTrayIcon, ArrowPathIcon, Cog6ToothIcon, PlusIcon } from '@heroicons/vue/24/outline'
import FeedToolbar from '@/components/feed/FeedToolbar.vue'
import LoadingIndicator from '@/components/feed/LoadingIndicator.vue'
import SubscriptionSkeleton from '@/components/feed/SubscriptionSkeleton.vue'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import AddChannelDialog from '@/components/dialogs/AddChannelDialog.vue'
import ImportSubscriptionDialog from '@/components/dialogs/ImportSubscriptionDialog.vue'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Switch } from '@/components/ui/switch'
import { useRefreshTriggers } from '../composables/useRefreshTriggers'
import { useScrollPosition } from '../composables/useScrollPosition'
import { useSubscriptionRefresh } from '../composables/useSubscriptionRefresh'
import { useFeedFilters } from '../composables/useFeedFilters'
import { formatDate } from '../utils/dateFormat'
import {
  getSubscriptions as apiGetSubscriptions,
  unsubscribe as apiUnsubscribe,
  updateNsfwStatus as apiUpdateNsfwStatus,
} from '@/api'

const router = useRouter()
const emitter = inject('emitter')

const isRefreshing = ref(false)
const isResetting = ref(false)
const { scrollContainer, handleScroll: handleScrollPosition, restoreScrollPosition } = useScrollPosition('subscribed-page')

const subscriptions = ref([])
const loadError = ref(null)
const loading = ref(false)
const hasLoadedOnce = ref(false)
const allLoaded = ref(false)
const currentPage = ref(1)
const searchQuery = ref('')
const { nsfw, site, sortBy } = useFeedFilters()

const showSettings = ref(false)
const selectedSubscription = ref(null)
const observer = ref(null)
const loadingTrigger = ref(null)
const showAddDialog = ref(false)
const showImportDialog = ref(false)
const unsubscribeError = ref('')
const unsubscribingId = ref(null)
const SUBSCRIPTION_REMOVE_DELAY_MS = 120

const wait = (ms) => new Promise((resolve) => {
  window.setTimeout(resolve, ms)
})

const {
  getRefreshState,
  triggerRefresh,
  retryRefresh,
  getStatusText,
  cleanup: cleanupRefresh,
  setSubscriptionMeta,
} = useSubscriptionRefresh()

const selectedRefreshState = computed(() => {
  if (!selectedSubscription.value) {
    return {
      status: 'idle',
      phase: null,
      lastError: null,
      isRefreshing: false,
    }
  }

  return getRefreshState(selectedSubscription.value.id)
})

const isUnsubscribing = computed(() => unsubscribingId.value === selectedSubscription.value?.id)

const setupIntersectionObserver = () => {
  if (observer.value) {
    observer.value.disconnect()
    observer.value = null
  }

  const el = document.querySelector('.subscribed-loading-trigger')
  if (!el) return

  observer.value = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting && !loading.value && !allLoaded.value) {
        loadMore()
      }
    },
    {
      root: scrollContainer.value,
      rootMargin: '100px',
      threshold: 0,
    },
  )
  observer.value.observe(el)
}

const loadSubscriptions = async () => {
  if (loading.value || allLoaded.value) return

  loading.value = true

  const { data, error } = await apiGetSubscriptions({
    query: searchQuery.value,
    nsfw: nsfw.value,
    site: site.value,
    page: currentPage.value,
    page_size: 100,
  })

  if (!error) {
    const newSubscriptions = Array.isArray(data?.data) ? data.data : (Array.isArray(data) ? data : [])
    const mapped = newSubscriptions.map((subscription) => ({
      ...subscription,
      total_videos: subscription.total_videos || 0,
      total_extract: subscription.total_extract || 0,
    }))

    if (currentPage.value === 1) {
      subscriptions.value = mapped
    } else {
      const existingIds = new Set(subscriptions.value.map((subscription) => subscription.id))
      const deduped = mapped.filter((subscription) => !existingIds.has(subscription.id))
      subscriptions.value = [...subscriptions.value, ...deduped]
    }

    currentPage.value++
    if (newSubscriptions.length < 20) {
      allLoaded.value = true
    }

    nextTick(() => {
      if (loadingTrigger.value && observer.value) {
        observer.value.unobserve(loadingTrigger.value)
        observer.value.observe(loadingTrigger.value)
      }
      restoreScrollPosition()
    })
  } else {
    loadError.value = error || '获取订阅列表失败'
  }

  hasLoadedOnce.value = true
  loading.value = false
}

const resetSubscriptionList = () => {
  hasLoadedOnce.value = false
  subscriptions.value = []
  currentPage.value = 1
  allLoaded.value = false
}

const MIN_SPIN_MS = 800
const spinTimer = ref(null)
const spinStartAt = ref(0)

const clearSpinTimer = () => {
  if (spinTimer.value) {
    clearTimeout(spinTimer.value)
    spinTimer.value = null
  }
}

useRefreshTriggers({ onRefresh: refreshList })

async function refreshList() {
  if (observer.value && loadingTrigger.value) {
    observer.value.unobserve(loadingTrigger.value)
  }
  clearSpinTimer()
  isRefreshing.value = true
  isResetting.value = true
  loadError.value = null
  currentPage.value = 1
  allLoaded.value = false
  spinStartAt.value = Date.now()

  try {
    await loadSubscriptions()
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

const handleGlobalSearch = (query) => {
  if (observer.value && loadingTrigger.value) {
    observer.value.unobserve(loadingTrigger.value)
  }
  searchQuery.value = query
  resetSubscriptionList()
  loadSubscriptions().then(() => {
    nextTick(() => {
      restoreScrollPosition()
    })
    isRefreshing.value = false
  })
}

watch([nsfw, site], async () => {
  if (observer.value && loadingTrigger.value) {
    observer.value.unobserve(loadingTrigger.value)
  }
  resetSubscriptionList()
  await loadSubscriptions()
})

const loadMore = () => {
  loadSubscriptions()
}

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
  if (!subscriptionId || unsubscribingId.value) return

  unsubscribeError.value = ''
  unsubscribingId.value = subscriptionId

  const { error } = await apiUnsubscribe(subscriptionId)

  if (error) {
    unsubscribeError.value = error?.message || '取消订阅失败'
    unsubscribingId.value = null
    return
  }

  closeSettings()
  await wait(SUBSCRIPTION_REMOVE_DELAY_MS)
  subscriptions.value = subscriptions.value.filter((subscription) => subscription.id !== subscriptionId)
  unsubscribingId.value = null
}

const getSubscriptionVideos = (subscriptionId) => {
  router.push(`/subscription/${subscriptionId}/all`)
}

const handleChannelAdded = () => {
  resetSubscriptionList()
  loadSubscriptions()
}

const handleSubscriptionsImported = () => {
  resetSubscriptionList()
  loadSubscriptions()
}

const updateNsfwStatus = async (isNsfw) => {
  const { error } = await apiUpdateNsfwStatus(selectedSubscription.value.id, isNsfw)

  if (!error) {
    const index = subscriptions.value.findIndex((subscription) => subscription.id === selectedSubscription.value.id)
    if (index !== -1) {
      subscriptions.value[index].is_nsfw = isNsfw
    }
  } else {
    selectedSubscription.value.is_nsfw = !isNsfw
  }
}

const handleRefreshSubscription = async (subscriptionId) => {
  await triggerRefresh(subscriptionId)
}

const handleRetryRefresh = async (subscriptionId) => {
  await retryRefresh(subscriptionId)
}

const sortOptions = [
  { value: 'name', label: '名称' },
  { value: 'site', label: '站点' },
  { value: 'recent', label: '最近更新' },
]

const handleSortChange = (value) => {
  sortBy.value = value
  const sorted = [...subscriptions.value]
  if (value === 'name') {
    sorted.sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'))
  } else if (value === 'site') {
    sorted.sort((a, b) => (a.site || '').localeCompare(b.site || '', 'zh-CN'))
  } else if (value === 'recent') {
    sorted.sort((a, b) => new Date(b.updated_at || 0) - new Date(a.updated_at || 0))
  }
  subscriptions.value = sorted
}

watch(sortBy, (val) => handleSortChange(val))

const getStatusBadgeClass = (status) => {
  switch (status) {
    case 'queued': return 'badge--queued'
    case 'in_progress': return 'badge--progress'
    case 'completed': return 'badge--completed'
    case 'failed': return 'badge--failed'
    default: return 'badge--idle'
  }
}

onMounted(async () => {
  try {
    await useSubscriptionRefresh().rehydrateFromServer?.()
  } catch (error) {}

  loadSubscriptions()
  nextTick(() => {
    setupIntersectionObserver()
  })

  emitter?.on?.('search:subscribed', handleGlobalSearch)
})

watch(subscriptions, () => {
  nextTick(() => {
    if (observer.value && loadingTrigger.value) {
      observer.value.unobserve(loadingTrigger.value)
      observer.value.observe(loadingTrigger.value)
    }
  })
}, { deep: true })

onUnmounted(() => {
  if (observer.value) {
    observer.value.disconnect()
  }

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

.toolbar-left-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.toolbar-right-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.toolbar-divider {
  width: 1px;
  height: 1.25rem;
  background: hsl(var(--border) / 0.5);
}

.sort-tabs {
  display: flex;
  align-items: center;
  gap: 0.125rem;
  background: hsl(var(--secondary) / 0.3);
  border-radius: calc(var(--radius-sm) + 2px);
  padding: 2px;
}

.sort-tab {
  padding: 0.2rem 0.6rem;
  border-radius: calc(var(--radius-sm) - 1px);
  font-size: 0.7rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground) / 0.7);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
  letter-spacing: 0.02em;
}

.sort-tab:hover {
  color: hsl(var(--foreground));
  background: hsl(var(--background) / 0.5);
}

.sort-tab.is-active {
  color: hsl(var(--foreground));
  background: hsl(var(--background));
  box-shadow: 0 1px 3px hsl(var(--border) / 0.4);
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
  padding-top: 0.75rem;
}

/* List */
.subscription-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.subscription-list--loading {
  min-height: calc(100dvh - 12rem);
}

.subscription-list--loading .skeleton-row:first-child {
  border-top: 1px solid hsl(var(--border) / 0.5);
}

.subscribed-inline-loading {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  justify-content: center;
  padding: 0.25rem 0 0.5rem;
  margin-bottom: 0.25rem;
  background: linear-gradient(to bottom, hsl(var(--background)) 65%, hsl(var(--background) / 0));
  pointer-events: none;
}

.subscription-row {
  display: grid;
  grid-template-columns: 3rem 1fr auto auto;
  align-items: center;
  gap: 0 1.25rem;
  padding: 0.875rem 0;
  cursor: pointer;
  transition: background 0.1s ease;
}

.subscription-row:hover {
  background: hsl(var(--secondary) / 0.12);
}

/* Avatar */
.subscription-row__avatar-wrap {
  flex-shrink: 0;
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

/* Main info */
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

.subscription-row__site-badge {
  font-size: 0.6rem;
  font-weight: 600;
  color: hsl(var(--primary) / 0.75);
  padding: 0.1rem 0.35rem;
  background: hsl(var(--primary) / 0.08);
  border-radius: 3px;
  letter-spacing: 0.04em;
  text-transform: lowercase;
  flex-shrink: 0;
}

.subscription-row__type-tag {
  font-size: 0.55rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: hsl(var(--muted-foreground) / 0.7);
  padding: 0.08rem 0.3rem;
  background: hsl(var(--secondary) / 0.45);
  border-radius: 3px;
  flex-shrink: 0;
}

.subscription-row__nsfw-tag {
  font-size: 0.55rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: hsl(var(--destructive) / 0.85);
  padding: 0.08rem 0.3rem;
  background: hsl(var(--destructive) / 0.1);
  border-radius: 3px;
  flex-shrink: 0;
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

/* Stats */
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

/* Actions */
.subscription-row__actions {
  display: flex;
  align-items: center;
  gap: 0.125rem;
  opacity: 0.35;
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

/* Empty State */
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
  margin: 2.5rem 0;
  text-align: center;
  color: hsl(var(--muted-foreground) / 0.35);
  font-size: 0.7rem;
  letter-spacing: 0.08em;
}

/* Dialog */
.subscription-dialog__summary {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 1.5rem;
  background: hsl(var(--secondary) / 0.1);
  border-bottom: 1px solid hsl(var(--border) / 0.4);
}

.subscription-dialog__avatar {
  width: 3rem;
  height: 3rem;
  border-radius: calc(var(--radius-sm) - 1px);
  border: 1px solid hsl(var(--border) / 0.4);
}

.subscription-dialog__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
}

.subscription-dialog__actions {
  display: grid;
  gap: 0.75rem;
  padding: 0 1.5rem 1.5rem;
}

/* Animations */
@keyframes stream-pulse {
  0% { transform: scale(1); opacity: 0.4; }
  50% { transform: scale(1.05); opacity: 1; }
  100% { transform: scale(1); opacity: 0.4; }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.subscription-row-enter-active,
.subscription-row-leave-active {
  transition: all 0.2s cubic-bezier(0.165, 0.84, 0.44, 1);
}

.subscription-row-enter-from {
  opacity: 0;
  transform: translateX(-8px);
}

.subscription-row-leave-to {
  opacity: 0;
  transform: translateX(8px);
}

.fade-list-enter-active,
.fade-list-leave-active {
  transition: opacity 0.3s ease;
}

.fade-list-enter-from,
.fade-list-leave-to {
  opacity: 0;
}

.subscribed-loading-trigger {
  padding: 1rem 0;
  display: flex;
  justify-content: center;
  min-height: 2.5rem;
}

.subscribed-trigger-hint {
  font-size: 0.7rem;
  color: hsl(var(--muted-foreground) / 0.35);
  letter-spacing: 0.05em;
}

/* Responsive */
@media (max-width: 640px) {
  .subscription-row {
    grid-template-columns: 2.5rem 1fr auto;
    grid-template-rows: auto auto;
    gap: 0 0.75rem;
    padding: 0.75rem 0;
  }

  .subscription-row__avatar-container {
    width: 2.25rem;
    height: 2.25rem;
    grid-row: 1;
  }

  .subscription-row__avatar-wrap {
    grid-row: 1;
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

  .subscription-row__actions {
    opacity: 0.35;
  }

  .subscription-row:hover .subscription-row__actions {
    opacity: 1;
  }

  .toolbar-left-actions {
    display: none;
  }
}

@media (min-width: 1024px) {
  .toolbar-container,
  .content-container {
    padding: 0 2rem;
  }
}

@media (hover: none) {
  .subscription-row__actions {
    opacity: 1;
  }
}
</style>
