<template>
  <div class="subscribed-page flex h-full flex-col bg-background text-foreground">
    <section class="subscribed-shell">
      <div class="toolbar-container">
        <FeedToolbar
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
            <Button size="sm" class="whitespace-nowrap" @click="showAddDialog = true">
              <PlusIcon class="h-4 w-4" />
              <span>添加订阅</span>
            </Button>
            <Button size="sm" variant="secondary" class="whitespace-nowrap" @click="showImportDialog = true">
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
        <div v-if="loading && !subscriptions.length" class="subscribed-empty-state">
          <LoadingIndicator :loading="true" text="正在整理订阅..." size="lg" />
        </div>

        <div v-else-if="!loading && !subscriptions.length" class="subscribed-empty-card">
          <p class="subscribed-empty-card__eyebrow">Subscription Library</p>
          <h2 class="subscribed-empty-card__title">还没有可展示的订阅</h2>
          <p class="subscribed-empty-card__copy">可以直接添加一个频道，或者从支持的站点批量导入。</p>
          <div class="subscribed-empty-card__actions">
            <Button size="sm" @click="showAddDialog = true">添加订阅</Button>
            <Button size="sm" variant="secondary" @click="showImportDialog = true">导入订阅</Button>
          </div>
        </div>

        <TransitionGroup v-else name="subscription-card" tag="div" class="channel-grid">
          <article
            v-for="subscription in subscriptions"
            :key="subscription.id"
            class="channel-item group"
            :class="{ 'is-refreshing': isResetting }"
            @click="getSubscriptionVideos(subscription.id)"
          >
            <div class="channel-item__topbar">
              <Badge
                v-if="getRefreshState(subscription.id).isRefreshing"
                variant="outline"
                class="channel-item__status-badge"
              >
                {{ getYouTubeStyleStatusText(getRefreshState(subscription.id).status, getRefreshState(subscription.id).phase) }}
              </Badge>

              <Button
                variant="ghost"
                size="icon-sm"
                class="settings-toggle"
                @click.stop="openSettings(subscription)"
              >
                <Cog6ToothIcon class="h-4 w-4" />
              </Button>
            </div>

            <div class="channel-item__media">
              <div class="channel-item__avatar-shell">
                <img
                  :alt="subscription.name"
                  :src="getAvatarSrc(subscription.avatar, subscription.id)"
                  class="channel-item__avatar"
                  referrerpolicy="no-referrer"
                  @error="(event) => handleAvatarError(event, subscription.id)"
                />
                <div class="avatar-sheen"></div>
              </div>
            </div>

            <div class="channel-item__body">
              <div class="channel-item__header">
                <div class="channel-item__copy min-w-0">
                  <p class="channel-item__eyebrow">
                    {{ subscription.type === 'PLAYLIST' ? 'Playlist' : 'Channel' }}
                  </p>
                  <h3 class="channel-item__title">{{ subscription.name }}</h3>
                  <p class="channel-item__meta">订阅于 {{ formatDate(subscription.created_at) }}</p>
                </div>
                <div class="channel-item__badges">
                  <Badge v-if="subscription.type === 'PLAYLIST'" variant="secondary">播放列表</Badge>
                </div>
              </div>

              <div class="channel-item__info-strip">
                <div class="channel-item__metric">
                  <span class="channel-item__metric-label">已解析</span>
                  <span class="channel-item__metric-value">{{ subscription.total_extract }}</span>
                </div>
                <span class="channel-item__metric-divider"></span>
                <div class="channel-item__metric">
                  <span class="channel-item__metric-label">总视频</span>
                  <span class="channel-item__metric-value">{{ subscription.total_videos }}</span>
                </div>
              </div>
            </div>
          </article>
        </TransitionGroup>

        <div
          v-if="!allLoaded"
          ref="loadingTrigger"
          class="subscribed-loading-trigger"
        >
          <LoadingIndicator v-if="loading" :loading="true" text="继续加载中..." size="md" />
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
const loadError = ref(null)
const loading = ref(false)
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

  loading.value = false
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
  subscriptions.value = []
  currentPage.value = 1
  allLoaded.value = false
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
  subscriptions.value = []
  currentPage.value = 1
  allLoaded.value = false
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
  subscriptions.value = []
  currentPage.value = 1
  allLoaded.value = false
  loadSubscriptions()
}

const handleSubscriptionsImported = () => {
  subscriptions.value = []
  currentPage.value = 1
  allLoaded.value = false
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
  max-width: var(--container-max-width, 2560px);
  margin: 0 auto;
  padding: 0 1rem;
}

.subscribed-shell {
  position: relative;
  padding-top: 0.25rem;
}

.channel-container {
  padding-top: 0.15rem;
}

.content-container--alert {
  padding-bottom: 0.75rem;
}

.channel-grid {
  display: grid;
  grid-template-columns: repeat(1, minmax(0, 1fr));
  gap: 0.875rem;
}

.channel-item {
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 13rem;
  border: 1px solid hsl(var(--border) / 0.76);
  border-radius: calc(var(--radius-xl) + 2px);
  background:
    radial-gradient(circle at 50% 18%, hsl(var(--primary) / 0.07), transparent 28%),
    linear-gradient(180deg, hsl(var(--card) / 0.98), hsl(var(--background) / 0.94));
  box-shadow: var(--shadow-sm);
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.channel-item:hover {
  border-color: hsl(var(--border));
  box-shadow: var(--shadow-md);
}

.channel-item__topbar {
  position: absolute;
  top: 0.8rem;
  left: 0.8rem;
  right: 0.8rem;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  z-index: 2;
}

.channel-item__status-badge {
  background: hsl(var(--background) / 0.78);
}

.settings-toggle {
  margin-left: auto;
  opacity: 0;
  border-radius: 9999px;
  background: hsl(var(--background) / 0.76);
  backdrop-filter: blur(10px);
  transition: opacity 0.18s ease, background-color 0.18s ease;
}

.group:hover .settings-toggle,
.group:focus-within .settings-toggle {
  opacity: 1;
}

.channel-item__media {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 7rem;
  padding: 0.95rem 1rem 0.3rem;
}

.channel-item__avatar-shell {
  position: relative;
  width: 4.7rem;
  height: 4.7rem;
  filter: drop-shadow(0 10px 18px hsl(var(--surface-shadow) / 0.12));
}

.channel-item__avatar {
  width: 100%;
  height: 100%;
  border-radius: 1.25rem;
  object-fit: cover;
  border: 1px solid hsl(var(--border) / 0.7);
  box-shadow: var(--shadow-sm);
}

.avatar-sheen {
  position: absolute;
  inset: -0.32rem;
  border-radius: 1.45rem;
  background:
    radial-gradient(circle at top, hsl(var(--primary) / 0.18), transparent 58%),
    linear-gradient(180deg, transparent, hsl(var(--primary) / 0.08));
  pointer-events: none;
  opacity: 0.72;
}

.channel-item__body {
  display: grid;
  flex: 1;
  gap: 0.55rem;
  padding: 0 0.95rem 0.95rem;
  margin-top: -0.15rem;
}

.channel-item__header {
  display: grid;
  gap: 0.45rem;
  justify-items: center;
  text-align: center;
}

.channel-item__copy {
  display: grid;
  gap: 0.18rem;
  justify-items: center;
  max-width: 15rem;
}

.channel-item__eyebrow {
  margin: 0;
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: hsl(var(--muted-foreground));
}

.channel-item__title {
  margin: 0;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.08;
  font-size: 1.06rem;
  font-weight: 800;
  letter-spacing: -0.045em;
  color: hsl(var(--foreground));
  text-wrap: balance;
}

.channel-item__meta {
  margin: 0.1rem 0 0;
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground) / 0.95);
}

.channel-item__badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  justify-content: center;
}

.channel-item__info-strip {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-height: 2.75rem;
  margin-top: auto;
  padding: 0.68rem 0.9rem;
  border: 1px solid hsl(var(--border) / 0.38);
  border-radius: 999px;
  background:
    linear-gradient(90deg, hsl(var(--background) / 0.72), hsl(var(--card) / 0.68));
  box-shadow: inset 0 1px 0 hsl(var(--background) / 0.72);
}

.channel-item__metric {
  display: grid;
  gap: 0.12rem;
  flex: 1 1 0;
  justify-items: center;
}

.channel-item__metric-label {
  font-size: 0.6rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: hsl(var(--muted-foreground) / 0.82);
}

.channel-item__metric-value {
  font-size: 0.98rem;
  font-weight: 700;
  letter-spacing: -0.04em;
  color: hsl(var(--foreground));
}

.channel-item__metric-divider {
  width: 1px;
  align-self: stretch;
  background: linear-gradient(180deg, transparent, hsl(var(--border)), transparent);
}

.subscribed-empty-state,
.subscribed-empty-card {
  min-height: min(58vh, 32rem);
  display: flex;
  align-items: center;
  justify-content: center;
}

.subscribed-empty-card {
  flex-direction: column;
  gap: 0.7rem;
  border: 1px solid hsl(var(--border) / 0.72);
  border-radius: calc(var(--radius-3xl) - 2px);
  background:
    radial-gradient(circle at top left, hsl(var(--primary) / 0.08), transparent 34%),
    linear-gradient(180deg, hsl(var(--card) / 0.98), hsl(var(--background) / 0.94));
  box-shadow: 0 24px 54px hsl(var(--surface-shadow) / 0.1);
  text-align: center;
  padding: 2rem 1.2rem;
}

.subscribed-empty-card__eyebrow {
  margin: 0;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: hsl(var(--muted-foreground));
}

.subscribed-empty-card__title {
  margin: 0;
  font-size: clamp(1.15rem, 1rem + 0.3vw, 1.4rem);
  font-weight: 800;
  letter-spacing: -0.03em;
}

.subscribed-empty-card__copy {
  margin: 0;
  max-width: 28rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.88rem;
}

.subscribed-empty-card__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.6rem;
  margin-top: 0.4rem;
}

.subscribed-loading-trigger {
  min-height: 5rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.subscribed-bottom-copy {
  margin: 1rem 0 1.4rem;
  text-align: center;
  color: hsl(var(--muted-foreground));
  font-size: 0.84rem;
}

.subscription-dialog__hero {
  background:
    radial-gradient(circle at top right, hsl(var(--primary) / 0.12), transparent 36%),
    linear-gradient(180deg, hsl(var(--card) / 0.98), hsl(var(--background) / 0.92));
}

.subscription-dialog__summary {
  display: flex;
  align-items: center;
  gap: 0.95rem;
  padding: 0.9rem;
  border: 1px solid hsl(var(--border) / 0.72);
  border-radius: 1.1rem;
  background: hsl(var(--card) / 0.82);
}

.subscription-dialog__avatar {
  width: 3.25rem;
  height: 3.25rem;
  border-radius: 1rem;
  object-fit: cover;
}

.subscription-dialog__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid hsl(var(--border) / 0.72);
  border-radius: 1rem;
  background: hsl(var(--background) / 0.42);
}

.subscription-dialog__actions {
  display: grid;
  gap: 0.75rem;
}

.subscription-dialog__spinner {
  width: 0.78rem;
  height: 0.78rem;
  border: 1.5px solid hsl(var(--destructive-foreground) / 0.28);
  border-top-color: hsl(var(--destructive-foreground));
  border-radius: 9999px;
  animation: subscription-dialog-spin 0.7s linear infinite;
}

.subscription-card-enter-active,
.subscription-card-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.subscription-card-enter-from,
.subscription-card-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.985);
}

.subscription-card-move {
  transition: transform 0.18s ease;
}

.channel-item.is-refreshing::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(90deg, transparent, var(--overlay-light-06), transparent);
  animation: shimmer 1.2s infinite;
  pointer-events: none;
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }

  100% {
    transform: translateX(100%);
  }
}

@keyframes subscription-dialog-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (min-width: 640px) {
  .toolbar-container,
  .content-container {
    padding: 0 1.5rem;
  }

  .channel-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 1024px) {
  .toolbar-container,
  .content-container {
    padding: 0 2rem;
  }

  .channel-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (min-width: 1440px) {
  .channel-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (min-width: 1840px) {
  .channel-grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
}

@media (hover: none) {
  .settings-toggle {
    opacity: 1;
  }
}

@media (max-width: 640px) {
  .subscription-dialog__row {
    align-items: flex-start;
  }
}
</style>
