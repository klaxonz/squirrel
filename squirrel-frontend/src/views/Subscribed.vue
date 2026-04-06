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
          :is-refreshing="isRefreshing"
          @update:nsfw="(value) => { nsfw = value }"
          @update:site="(value) => { site = value }"
          @refresh="refreshList"
        >
          <template #actions>
            <Button size="xs" class="subscribed-toolbar__button whitespace-nowrap" @click="showAddDialog = true">
              <PlusIcon class="h-4 w-4" />
              <span>添加订阅</span>
            </Button>
            <Button size="xs" variant="secondary" class="subscribed-toolbar__button subscribed-toolbar__button--secondary whitespace-nowrap" @click="showImportDialog = true">
              <ArrowDownTrayIcon class="h-4 w-4" />
              <span>导入订阅</span>
            </Button>
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
        <Transition name="fade-list">
          <div v-if="loading && !subscriptions.length" key="skeleton" class="subscription-stream">
            <SubscriptionSkeleton v-for="i in 10" :key="i" :delay="i * 50" />
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

          <TransitionGroup v-else key="list" name="subscription-row" tag="div" class="subscription-stream">
            <article
              v-for="subscription in subscriptions"
              :key="subscription.id"
              class="subscription-row group"
              :class="{ 'is-refreshing': isResetting }"
              @click="getSubscriptionVideos(subscription.id)"
            >
              <!-- Left: Avatar with Status -->
              <div class="subscription-row__media">
                <div class="subscription-row__avatar-wrapper">
                  <img
                    :alt="subscription.name"
                    :src="getAvatarSrc(subscription.avatar, subscription.id)"
                    class="subscription-row__avatar"
                    :class="{ 'image-loaded': avatarsLoaded[subscription.id] }"
                    referrerpolicy="no-referrer"
                    @load="avatarsLoaded[subscription.id] = true"
                    @error="(event) => handleAvatarError(event, subscription.id)"
                  />
                  <div v-if="getRefreshState(subscription.id).isRefreshing" class="subscription-row__avatar-pulse"></div>
                </div>
              </div>

              <!-- Center: Identity & Metadata -->
              <div class="subscription-row__main">
                <div class="subscription-row__identity">
                  <h3 class="subscription-row__name" :title="subscription.name">{{ subscription.name }}</h3>
                  <span class="subscription-row__type-tag">
                    {{ subscription.type === 'PLAYLIST' ? '播放列表' : '频道' }}
                  </span>
                </div>
                <div class="subscription-row__meta">
                  <div class="subscription-row__status">
                    <span
                      v-if="getRefreshState(subscription.id).isRefreshing"
                      class="h-1 w-1 animate-pulse rounded-full bg-primary"
                    ></span>
                    <span class="text-[10px] uppercase tracking-tighter opacity-60">
                      {{ getYouTubeStyleStatusText(getRefreshState(subscription.id).status, getRefreshState(subscription.id).phase) }}
                    </span>
                  </div>
                  <span class="subscription-row__dot"></span>
                  <span class="subscription-row__date">{{ formatDate(subscription.created_at) }}</span>
                </div>
              </div>

              <!-- Right: Stats (Desktop Only mostly) -->
              <div class="subscription-row__stats">
                <div class="subscription-row__stat">
                  <span class="subscription-row__stat-value tabular-nums">{{ subscription.total_videos }}</span>
                  <span class="subscription-row__stat-label">全部</span>
                </div>
                <div class="subscription-row__stat">
                  <span class="subscription-row__stat-value tabular-nums">{{ subscription.total_extract }}</span>
                  <span class="subscription-row__stat-label">已解析</span>
                </div>
              </div>

              <!-- Far Right: Actions -->
              <div class="subscription-row__actions">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  class="subscription-row__settings-trigger"
                  @click.stop="openSettings(subscription)"
                >
                  <Cog6ToothIcon class="h-4 w-4" />
                </Button>
              </div>
            </article>
          </TransitionGroup>
        </Transition>

        <div
          v-if="!allLoaded"
          ref="loadingTrigger"
          class="subscribed-loading-trigger"
        >
          <LoadingIndicator v-if="loading" :loading="true" text="正在同步订阅库" size="sm" />
        </div>

        <div v-if="allLoaded && subscriptions.length" class="subscribed-bottom-copy">
          已经到底啦
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
            <img
              :src="getAvatarSrc(selectedSubscription.avatar, selectedSubscription.id)"
              :alt="selectedSubscription.name"
              class="subscription-dialog__avatar"
              referrerpolicy="no-referrer"
              @error="(event) => handleAvatarError(event, selectedSubscription.id)"
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
import { ArrowDownTrayIcon, Cog6ToothIcon, PlusIcon } from '@heroicons/vue/24/outline'
import FeedToolbar from '@/components/feed/FeedToolbar.vue'
import LoadingIndicator from '@/components/feed/LoadingIndicator.vue'
import SubscriptionSkeleton from '@/components/feed/SubscriptionSkeleton.vue'
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
import { useImageFallback } from '../composables/useImageFallback'
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
const avatarsLoaded = ref({})
const loadError = ref(null)
const loading = ref(false)
const hasLoadedOnce = ref(false)
const allLoaded = ref(false)
const currentPage = ref(1)
const searchQuery = ref('')
const { nsfw, site } = useFeedFilters()
const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback()

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

  if (loadingTrigger.value) {
    observer.value.observe(loadingTrigger.value)
  }
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

const getYouTubeStyleStatusText = (status, phase) => {
  if (status === 'queued') return '排队中'
  if (status === 'in_progress') {
    switch (phase) {
      case 'init': return '准备中'
      case 'fetching_feed': return '检查新内容'
      case 'calculating_delta': return '分析更新'
      case 'extracting': return '解析中'
      case 'finalizing': return '即将完成'
      default: return '更新中'
    }
  }
  if (status === 'completed') return '已完成'
  if (status === 'failed') return '更新失败'
  return '更新中'
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
  max-width: var(--container-max-width, 1440px);
  margin: 0 auto;
  padding: 0 1rem;
}

.subscribed-shell {
  padding-top: 0.5rem;
}

.subscribed-toolbar {
  padding: 1rem 0;
}

.subscribed-toolbar :deep(.toolbar-slot-actions) {
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
  padding-top: 0.5rem;
}

/* Fluid Stream Layout */
.subscription-stream {
  display: flex;
  flex-direction: column;
  border-top: 1px solid hsl(var(--border) / 0.5);
  margin-top: 0.5rem;
}

.subscription-row {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 1rem 0;
  border-bottom: 1px solid hsl(var(--border) / 0.5);
  background: transparent;
  cursor: pointer;
  transition: all 0.1s ease;
}

.subscription-row:hover {
  background: hsl(var(--secondary) / 0.15);
  padding-left: 0.5rem;
  padding-right: 0.5rem;
}

/* Avatar Wrapper */
.subscription-row__media {
  flex-shrink: 0;
}

.subscription-row__avatar-wrapper {
  position: relative;
  width: 2.75rem;
  height: 2.75rem;
}

.subscription-row__avatar {
  width: 100%;
  height: 100%;
  border-radius: var(--radius-sm);
  object-fit: cover;
  filter: grayscale(0.2);
  opacity: 0;
  transition: opacity 0.5s ease, filter 0.2s ease;
  border: 1px solid hsl(var(--border) / 0.4);
}

.subscription-row__avatar.image-loaded {
  opacity: 1;
}

.subscription-row:hover .subscription-row__avatar {
  filter: grayscale(0);
}

.subscription-row__avatar-pulse {
  position: absolute;
  inset: -3px;
  border: 2px solid hsl(var(--primary) / 0.6);
  border-radius: calc(var(--radius-sm) + 3px);
  animation: stream-pulse 1.5s ease-in-out infinite;
}

/* Identity & Metadata */
.subscription-row__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.subscription-row__identity {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.subscription-row__name {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.subscription-row__type-tag {
  font-family: var(--font-mono, monospace);
  font-size: 0.55rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: hsl(var(--muted-foreground) / 0.8);
  padding: 0.05rem 0.25rem;
  background: hsl(var(--secondary) / 0.5);
  border-radius: 2px;
}

.subscription-row__meta {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-family: var(--font-mono, monospace);
  font-size: 0.65rem;
  color: hsl(var(--muted-foreground) / 0.6);
}

.subscription-row__status {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.subscription-row__dot {
  width: 3px;
  height: 3px;
  border-radius: 999px;
  background: currentColor;
}

/* Stats (Single Column Grid feel) */
.subscription-row__stats {
  display: none;
  gap: 3rem;
  margin: 0 2rem;
}

.subscription-row__stat {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  min-width: 5rem;
}

.subscription-row__stat-value {
  font-family: var(--font-mono, monospace);
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.subscription-row__stat-label {
  font-family: var(--font-mono, monospace);
  font-size: 0.55rem;
  letter-spacing: 0.04em;
  color: hsl(var(--muted-foreground) / 0.6);
}

/* Actions */
.subscription-row__actions {
  display: flex;
  align-items: center;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.subscription-row:hover .subscription-row__actions {
  opacity: 1;
}

.subscription-row__settings-trigger {
  color: hsl(var(--muted-foreground));
}

.subscription-row__settings-trigger:hover {
  color: hsl(var(--foreground));
}

/* Empty State (Minimal) */
.subscribed-empty-state,
.subscribed-empty-card {
  min-height: 40vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.subscribed-empty-card {
  flex-direction: column;
  text-align: center;
  gap: 1.5rem;
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
  margin: 3rem 0;
  text-align: center;
  font-family: var(--font-mono, monospace);
  color: hsl(var(--muted-foreground) / 0.4);
  font-size: 0.7rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

/* Dialog Styling */
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
  border-radius: var(--radius-sm);
  object-fit: cover;
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

/* Animation */
@keyframes stream-pulse {
  0% { transform: scale(1); opacity: 0.4; }
  50% { transform: scale(1.05); opacity: 1; }
  100% { transform: scale(1); opacity: 0.4; }
}

.subscription-row-enter-active,
.subscription-row-leave-active {
  transition: all 0.2s cubic-bezier(0.165, 0.84, 0.44, 1);
}

.subscription-row-enter-from {
  opacity: 0;
  transform: translateX(-10px);
}

.subscription-row-leave-to {
  opacity: 0;
  transform: translateX(10px);
}

.fade-list-enter-active,
.fade-list-leave-active {
  transition: opacity 0.4s ease;
}

.fade-list-enter-from,
.fade-list-leave-to {
  opacity: 0;
}

.subscribed-loading-trigger {
  padding: 2rem 0;
  display: flex;
  justify-content: center;
}

@media (min-width: 768px) {
  .subscription-row__stats {
    display: flex;
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
