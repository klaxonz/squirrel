<template>
  <AppPageShell variant="compact" surface="consume" width="media">
    <div v-if="pageError" class="app-page-content app-page-content--media">
        <AppEmptyState variant="error" title="加载失败" :copy="pageError">
          <template #actions>
            <Button v-if="!queryError" severity="secondary" outlined size="sm" @click="refresh">重试</Button>
          </template>
        </AppEmptyState>
    </div>

    <template v-else>
      <section class="app-media-header remote-channel-header">
        <div class="app-media-header__inner remote-channel-header__inner">
          <div class="remote-channel-header__identity">
            <a
              v-if="channelUrl"
              :href="channelUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="remote-channel-header__avatar-link"
            >
            <SubscriptionAvatar :src="profile.avatar" :name="profile.name || siteLabel" size="full" class="remote-channel-header__avatar" />
            </a>
            <SubscriptionAvatar
              v-else
              :src="profile.avatar"
              :name="profile.name || siteLabel"
              size="full"
              class="remote-channel-header__avatar"
            />
            <div class="remote-channel-header__copy">
              <div class="remote-channel-header__title-row">
                <a
                  v-if="channelUrl"
                  :href="channelUrl"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="remote-channel-header__name-link"
                >
                  <h1 class="app-h2 truncate">{{ profile.name || siteLabel }}</h1>
                </a>
                <h1 v-else class="app-h2 truncate">{{ profile.name || siteLabel }}</h1>
                <span class="remote-channel-site-badge">{{ siteLabel }}</span>
                <span v-if="profile.is_nsfw" class="remote-channel-nsfw-badge">敏感</span>
              </div>
              <p v-if="profile.description" class="remote-channel-header__desc">
                {{ profile.description }}
              </p>
              <div v-if="profileStats.length" class="remote-channel-header__stats">
                <span v-for="stat in profileStats" :key="stat.label" class="remote-channel-header__stat">
                  <span class="remote-channel-header__stat-label">{{ stat.label }}</span>
                  <span class="remote-channel-header__stat-value">{{ stat.value }}</span>
                </span>
              </div>
            </div>
          </div>

          <div class="remote-channel-header__actions">
            <div v-if="localSubscriptionRoute" class="remote-channel-switch">
              <Button type="button" text severity="secondary" size="sm" @click="openLocalChannel">
                <AppIcon name="library" class="h-3.5 w-3.5" />
                本地
              </Button>
              <Button type="button" severity="secondary" size="sm" disabled>
                <AppIcon name="siteFallback" class="h-3.5 w-3.5" />
                远端
              </Button>
            </div>
            <Button
              v-if="channelUrl"
              type="button"
              :variant="isSubscriptionChecked && isSubscribed ? 'outline' : 'default'"
              size="sm"
              :disabled="isCheckingSubscription || isSubscribing"
              @click="handleSubscribe"
            >
              {{ subscriptionButtonText }}
            </Button>
          </div>
          <div class="remote-channel-subscription-feedback">
            <p v-if="subscriptionError" role="alert" class="remote-channel-subscription-error">
              {{ subscriptionError }}
              <button type="button" class="remote-channel-inline-action" @click="retrySubscriptionAction">重试</button>
            </p>
            <p v-else role="status" aria-live="polite" class="remote-channel-subscription-status">
              {{ subscriptionStatusText }}
            </p>
          </div>
        </div>
      </section>

      <div ref="root" class="app-page-content app-page-content--media">

      <div v-if="items.length > 0" class="remote-channel-grid app-video-grid app-video-grid--feed">
        <article
          v-for="item in items"
          :key="item.site + ':' + item.url"
          class="remote-channel-card group"
          :class="{ 'remote-channel-card--disabled': !canPlayRemoteResult(item) }"
        >
          <div class="remote-channel-thumb">
            <VideoThumbnail :src="item.thumbnail" :alt="item.title" fit="cover" />
            <span v-if="item.duration" class="app-media-duration-badge app-media-duration-badge--compact app-mono">
              {{ formatDuration(item.duration) }}
            </span>
          </div>

          <div class="remote-channel-card__body">
            <h3 class="remote-channel-title">
              {{ item.title }}
            </h3>
            <div class="remote-channel-meta">
              {{ displayDate(item) }}
            </div>
            <button
              v-if="canPlayRemoteResult(item)"
              type="button"
              class="remote-channel-primary-action"
              :aria-label="`播放 ${item.title}`"
              @click="openResult(item)"
            >
              <AppIcon name="play" class="h-3.5 w-3.5 fill-current" />
              播放
            </button>
            <a
              v-else-if="externalResultUrl(item)"
              :href="externalResultUrl(item) || undefined"
              target="_blank"
              rel="noopener noreferrer"
              class="remote-channel-external-action"
              :aria-label="`在源站打开 ${item.title}`"
            >
              <AppIcon name="externalLink" class="h-3.5 w-3.5" />
              在源站打开
            </a>
            <div v-else class="remote-channel-unavailable">
              <button type="button" disabled class="remote-channel-disabled-action">无法播放</button>
              <span>该视频没有可用的播放或源站地址</span>
            </div>
          </div>
        </article>
      </div>

      <div v-if="loading" class="app-video-grid app-video-grid--feed">
        <VideoSkeleton v-for="i in skeletonCount" :key="i" :delay="(i - 1) * 50" />
      </div>

      <div v-if="items.length > 0" class="remote-channel-pagination" role="status" aria-live="polite">
        <span>{{ paginationStatusText }}</span>
        <Button
          v-if="!allLoaded"
          type="button"
          severity="secondary" outlined
          :disabled="loading"
          @click="loadMore"
        >
          {{ loading ? '加载中' : '加载更多' }}
        </Button>
      </div>

      <div v-if="!loading && !pageError && items.length === 0" class="app-page-empty app-page-empty--compact">
        <AppEmptyState variant="plain" icon="inbox" title="暂无频道视频" />
      </div>

      <div v-if="items.length && !allLoaded" ref="loadMoreTrigger" class="h-20 w-full" aria-hidden="true" />
      </div>
    </template>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, nextTick, onActivated, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'
import { errorMessage as resolveError } from '@/shared/lib/errorMessage'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import VideoSkeleton from '@/features/video/components/feed/VideoSkeleton.vue'
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import { Button } from '@/shared/ui/button'
import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import { prefetchDesktopPlaybackSource } from '@/features/video/composables/useVideoOperations'
import { useSkeletonCount } from '@/features/video/composables/useSkeletonCount'
import { formatDuration } from '@/shared/lib/dateFormat'
import { getMainScrollRoot } from '@/shared/composables/useMainScrollRoot'
import { useDesktopBridge } from '@/shared/composables/useDesktopBridge'
import { getSubscriptionStatus, subscribe, unsubscribe } from '@/shared/api'

type RemoteProfile = {
  id?: string | number | null
  type?: string | null
  name: string
  url?: string | null
  avatar?: string | null
  description?: string | null
  site?: string | null
  is_nsfw?: boolean | null
  banner?: string | null
  subscriber_count?: number | null
  video_count?: number | null
}

type RemoteSearchItem = {
  source: 'remote'
  site: string
  id?: string | number | null
  title: string
  url: string
  thumbnail?: string | null
  duration?: number | null
  publish_date?: string | null
  published_text?: string | null
  uploader?: string | null
  uploader_url?: string | null
  uploader_avatar?: string | null
  subscriptions?: RemoteProfile[]
  actors?: RemoteProfile[]
  description?: string | null
}

const REMOTE_PLAYABLE_SITE_PATTERNS: Record<string, RegExp> = {
  bilibili: /(?:bilibili\.com\/video\/|b23\.tv\/)/i,
  youtube: /(?:youtube\.com\/|youtu\.be\/)/i,
}
const SUPPORTED_REMOTE_CHANNEL_SITES = new Set(Object.keys(REMOTE_PLAYABLE_SITE_PATTERNS))

const route = useRoute()
const router = useRouter()

const items = ref<RemoteSearchItem[]>([])
const profile = ref<RemoteProfile>({
  name: '',
  url: '',
  avatar: '',
  description: '',
})
const loading = ref(false)
const allLoaded = ref(false)
const currentPage = ref(1)
const nextCursor = shallowRef<unknown>(null)
const errorMessage = ref('')
const { isDesktop: isDesktopEnv } = useDesktopBridge()
const loadMoreTrigger = ref<HTMLElement | null>(null)
const isCheckingSubscription = ref(false)
const isSubscriptionChecked = ref(false)
const isSubscribed = ref(false)
const isSubscribing = ref(false)
const subscriptionId = ref<number | null>(null)
const subscriptionError = ref('')
const failedSubscriptionAction = ref<'status' | 'toggle' | null>(null)

let requestToken = 0
let subscriptionStatusToken = 0
let subscriptionMutationToken = 0
let observer: IntersectionObserver | null = null
let scrollRoot: HTMLElement | null = null
let loadedChannelKey = ''

// --- Adaptive skeleton count ----------------------------------------------
// Mirrors the auto-fill `.app-video-grid--feed` via the same minCardWidth/gap
// formula — no breakpoint table to keep in sync with the CSS class.
const { count: skeletonCount, attachRef: root } = useSkeletonCount({
  minCardWidth: 320,   // matches --app-video-grid-min
  gap: 40,             // matches --app-video-grid-gap-y (2.5rem)
  cardHeight: 220,     // thumbnail + 2-line title + date
})

const queryValue = (key: string) => {
  const value = route.query[key]
  return Array.isArray(value) ? String(value[0] || '') : String(value || '')
}

const site = computed(() => queryValue('site').trim().toLowerCase())
const channelUrl = computed(() => queryValue('url').trim())
const isHttpUrl = (value: string) => {
  try {
    const parsed = new URL(value)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
  } catch {
    return false
  }
}
const queryError = computed(() => {
  if (!site.value || !channelUrl.value) return '缺少远端频道站点或地址'
  if (!SUPPORTED_REMOTE_CHANNEL_SITES.has(site.value)) return `不支持的远端频道站点：${site.value}`
  if (!isHttpUrl(channelUrl.value)) return '远端频道地址必须是有效的 HTTP(S) 地址'
  return ''
})
const pageError = computed(() => queryError.value || errorMessage.value)
const siteLabel = computed(() => {
  const labels: Record<string, string> = {
    bilibili: 'Bilibili',
    youtube: 'YouTube',
  }
  return labels[site.value] || site.value
})

const subscriptionButtonText = computed(() => {
  if (isCheckingSubscription.value) return '检查中'
  if (isSubscribing.value) return isSubscribed.value ? '取消中' : '订阅中'
  return isSubscriptionChecked.value && isSubscribed.value ? '取消订阅' : '订阅'
})
const subscriptionStatusText = computed(() => {
  if (isCheckingSubscription.value) return '正在检查订阅状态'
  if (isSubscribing.value) return isSubscribed.value ? '正在取消订阅' : '正在订阅'
  if (!isSubscriptionChecked.value) return '订阅状态尚未确认'
  return isSubscribed.value ? '已订阅此频道' : '尚未订阅此频道'
})
const paginationStatusText = computed(() => {
  if (loading.value) return `正在加载第 ${currentPage.value + 1} 页，已显示 ${items.value.length} 个视频`
  if (allLoaded.value) return `已加载全部 ${items.value.length} 个视频`
  return `已显示 ${items.value.length} 个视频，第 ${currentPage.value} 页`
})
const localSubscriptionRoute = computed(() => {
  if (!isSubscriptionChecked.value || !isSubscribed.value || !subscriptionId.value) return null
  return {
    name: 'SubscriptionAllVideos',
    params: { id: String(subscriptionId.value) },
  }
})

const routeProfile = computed(() => ({
  id: queryValue('id') || null,
  type: 'CHANNEL',
  name: queryValue('name'),
  url: channelUrl.value,
  avatar: queryValue('avatar'),
  is_nsfw: queryValue('is_nsfw') === 'true',
}))
const channelKey = computed(() => `${site.value}::${channelUrl.value}`)

const formatCount = (value: number | null | undefined) => {
  if (value == null || !Number.isFinite(Number(value))) return ''
  const n = Number(value)
  if (n >= 100_000_000) return `${(n / 100_000_000).toFixed(1).replace(/\.0$/, '')}亿`
  if (n >= 10_000) return `${(n / 10_000).toFixed(1).replace(/\.0$/, '')}万`
  return String(n)
}

const profileStats = computed(() => {
  const stats: Array<{ label: string; value: string }> = []
  const subs = formatCount(profile.value.subscriber_count)
  const videos = formatCount(profile.value.video_count)
  if (subs) stats.push({ label: '订阅', value: subs })
  if (videos) stats.push({ label: '视频', value: videos })
  return stats
})

const displayDate = (item: RemoteSearchItem) => {
  if (item.published_text) return item.published_text
  if (!item.publish_date) return ''
  const date = new Date(item.publish_date)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString()
}

const appendUniqueItems = (nextItems: RemoteSearchItem[]) => {
  const seen = new Set(items.value.map((item) => item.url))
  const uniqueItems = nextItems.filter((item) => {
    if (!item.url || seen.has(item.url)) return false
    seen.add(item.url)
    return true
  })
  items.value = items.value.concat(uniqueItems)
}

const replaceWithUniqueItems = (nextItems: RemoteSearchItem[]) => {
  items.value = []
  appendUniqueItems(nextItems)
}

const loadPage = async (page: number) => {
  if (queryError.value) return
  if (!isDesktopEnv() || typeof window.desktopApp?.getRemoteChannel !== 'function') {
    errorMessage.value = '当前桌面端不支持远端频道'
    return
  }

  const currentToken = ++requestToken
  loading.value = true
  errorMessage.value = ''
  let timer: ReturnType<typeof setTimeout> | undefined

  try {
    const result = await Promise.race([
      window.desktopApp.getRemoteChannel({
        site: site.value,
        url: channelUrl.value,
        limit: 30,
        page,
        cursor: page > 1 && nextCursor.value ? { ...(nextCursor.value as Record<string, unknown>) } : undefined,
        profile: routeProfile.value,
      }),
      new Promise<never>((_, reject) => {
        timer = setTimeout(() => reject(new Error('远端频道加载超时')), 60000)
      }),
    ])
    if (currentToken !== requestToken) return

    profile.value = result.profile || routeProfile.value
    const nextItems = Array.isArray(result.items) ? result.items : []
    if (page === 1) replaceWithUniqueItems(nextItems)
    else appendUniqueItems(nextItems)
    currentPage.value = page
    nextCursor.value = result.next_cursor || null
    allLoaded.value = result.has_more === false
  } catch (error: unknown) {
    if (currentToken !== requestToken) return
    // ponytail: desktop bridge path bypasses handleRequest; reject is plain Error
    errorMessage.value = resolveError(error, '远端频道加载失败')
  } finally {
    clearTimeout(timer)
    if (currentToken === requestToken) loading.value = false
    if (currentToken === requestToken) {
      await nextTick()
      checkNearBottom()
    }
  }
}

const refresh = async () => {
  requestToken += 1
  items.value = []
  profile.value = routeProfile.value
  currentPage.value = 1
  nextCursor.value = null
  allLoaded.value = false
  errorMessage.value = ''
  loadedChannelKey = channelKey.value
  if (queryError.value) return
  await loadPage(1)
}

const loadMore = async () => {
  if (loading.value || allLoaded.value || !items.value.length) return
  await loadPage(currentPage.value + 1)
}

const checkNearBottom = () => {
  if (!scrollRoot || loading.value || allLoaded.value || errorMessage.value || !items.value.length) return
  const remaining = scrollRoot.scrollHeight - scrollRoot.scrollTop - scrollRoot.clientHeight
  if (remaining <= 900) {
    void loadMore()
  }
}

const refreshSubscriptionStatus = async (url: string) => {
  const currentToken = ++subscriptionStatusToken
  isSubscribed.value = false
  isSubscriptionChecked.value = false
  subscriptionId.value = null
  subscriptionError.value = ''
  failedSubscriptionAction.value = null
  if (!url || queryError.value) return

  isCheckingSubscription.value = true
  try {
    const data = await getSubscriptionStatus(url)
    if (currentToken !== subscriptionStatusToken || url !== channelUrl.value) return
    isSubscribed.value = data?.is_subscribed === true
    subscriptionId.value = data?.subscription_id ?? null
    isSubscriptionChecked.value = true
  } catch (error: unknown) {
    if (currentToken !== subscriptionStatusToken || url !== channelUrl.value) return
    subscriptionError.value = resolveError(error, '无法检查订阅状态')
    failedSubscriptionAction.value = 'status'
  } finally {
    if (currentToken === subscriptionStatusToken) isCheckingSubscription.value = false
  }
}

watch(channelUrl, async (url) => {
  subscriptionMutationToken += 1
  isSubscribing.value = false
  await refreshSubscriptionStatus(url)
}, { immediate: true })

const handleSubscribe = async () => {
  const url = channelUrl.value
  if (!url || queryError.value || isSubscribing.value) return

  const currentToken = ++subscriptionMutationToken
  const wasSubscribed = isSubscribed.value
  const currentSubscriptionId = subscriptionId.value
  subscriptionError.value = ''
  failedSubscriptionAction.value = null
  isSubscribing.value = true
  try {
    const data = wasSubscribed && currentSubscriptionId
      ? await unsubscribe(currentSubscriptionId)
      : await subscribe(url)
    if (currentToken !== subscriptionMutationToken || url !== channelUrl.value) return

    if (!wasSubscribed) {
      isSubscribed.value = data?.is_subscribed === true
      subscriptionId.value = data?.subscription_id ?? null
      isSubscriptionChecked.value = true
    }

    await refreshSubscriptionStatus(url)
  } catch (error: unknown) {
    if (currentToken !== subscriptionMutationToken || url !== channelUrl.value) return
    subscriptionError.value = resolveError(error, wasSubscribed ? '取消订阅失败' : '订阅失败')
    failedSubscriptionAction.value = 'toggle'
  } finally {
    if (currentToken === subscriptionMutationToken) isSubscribing.value = false
  }
}

const retrySubscriptionAction = async () => {
  if (failedSubscriptionAction.value === 'toggle') {
    await handleSubscribe()
    return
  }
  await refreshSubscriptionStatus(channelUrl.value)
}

const openLocalChannel = async () => {
  if (!localSubscriptionRoute.value) return
  await router.push(localSubscriptionRoute.value)
}

const hashRemoteUrl = (url: string) => {
  let hash = 0
  for (let index = 0; index < url.length; index += 1) {
    hash = Math.imul(31, hash) + url.charCodeAt(index)
    hash |= 0
  }
  return Math.abs(hash).toString(36)
}

const buildRemoteVideoSeed = (item: RemoteSearchItem) => {
  const url = String(item.url || '').trim()
  return {
    id: `remote-${item.site}-${hashRemoteUrl(url)}`,
    source: 'remote',
    site: item.site,
    title: item.title,
    url,
    thumbnail: item.thumbnail || '',
    duration: item.duration || null,
    publish_date: item.publish_date || null,
    uploaded_at: item.publish_date || null,
    description: item.description || '',
    subscriptions: item.subscriptions?.length ? item.subscriptions : [profile.value],
    actors: item.actors || [],
  }
}

const canPlayRemoteResult = (item: RemoteSearchItem) => {
  const pattern = REMOTE_PLAYABLE_SITE_PATTERNS[item.site]
  return !!pattern && pattern.test(String(item.url || ''))
}

const externalResultUrl = (item: RemoteSearchItem) => {
  const url = String(item.url || '').trim()
  return isHttpUrl(url) ? url : ''
}

const openResult = async (item: RemoteSearchItem) => {
  if (!item.url || !canPlayRemoteResult(item)) return

  const videoSeed = buildRemoteVideoSeed(item)
  rememberVideoPlaybackSeed(videoSeed)
  void prefetchDesktopPlaybackSource(videoSeed)
  await router.push({ name: 'VideoPlay', params: { videoId: videoSeed.id } })
}

watch(channelKey, (nextChannelKey) => {
  if (route.name !== 'RemoteChannelDetail') return
  if (nextChannelKey === loadedChannelKey) return
  refresh()
}, { immediate: true })

onActivated(() => {
  if (channelKey.value === loadedChannelKey) return
  refresh()
})

onMounted(() => {
  scrollRoot = getMainScrollRoot()
  observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) void loadMore()
  }, {
    root: scrollRoot,
    rootMargin: '600px',
  })

  if (loadMoreTrigger.value) observer.observe(loadMoreTrigger.value)
  scrollRoot?.addEventListener('scroll', checkNearBottom, { passive: true })
})

onUnmounted(() => {
  observer?.disconnect()
  scrollRoot?.removeEventListener('scroll', checkNearBottom)
  scrollRoot = null
})
</script>

<style scoped>
.remote-channel-header__inner {
  --app-page-max-width: var(--app-content-media-max);
  align-items: flex-start;
}

.remote-channel-header__identity {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  align-items: flex-start;
  gap: var(--space-4);
}

.remote-channel-header__avatar-link {
  display: block;
  flex: none;
  text-decoration: none;
}

.remote-channel-header__avatar {
  width: 3.5rem;
  height: 3.5rem;
  flex: none;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--app-surface-radius);
}

.remote-channel-header__copy {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 0.375rem;
}

.remote-channel-header__title-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-2);
}

.remote-channel-header__name-link {
  min-width: 0;
  color: inherit;
  text-decoration: none;
}

.remote-channel-header__name-link:hover {
  text-decoration: underline;
  text-underline-offset: 0.15em;
}

.remote-channel-header__desc {
  margin: 0;
  max-width: 42rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.remote-channel-header__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
}

.remote-channel-header__stat {
  display: inline-flex;
  align-items: baseline;
  gap: 0.35rem;
}

.remote-channel-header__stat-label {
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.remote-channel-header__stat-value {
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.remote-channel-nsfw-badge {
  flex: none;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--radius-sm);
  background: hsl(var(--muted) / 0.4);
  padding: 0.125rem 0.375rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 650;
}

.remote-channel-header__actions {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
}

.remote-channel-subscription-feedback {
  flex-basis: 100%;
  min-height: 1.25rem;
  text-align: right;
}

.remote-channel-subscription-status,
.remote-channel-subscription-error {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  line-height: 1.4;
}

.remote-channel-subscription-error {
  color: hsl(var(--destructive));
}

.remote-channel-inline-action {
  margin-left: 0.35rem;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  font-weight: 650;
  text-decoration: underline;
  text-underline-offset: 0.15em;
  cursor: pointer;
}

.remote-channel-site-badge {
  flex: none;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--radius-sm);
  background: hsl(var(--muted) / 0.4);
  padding: 0.125rem 0.375rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 650;
}

.remote-channel-switch {
  display: flex;
  align-items: center;
  gap: 0.125rem;
  border: 1px solid var(--app-control-border);
  border-radius: var(--app-control-radius);
  background: var(--app-control-bg);
  padding: 2px;
}

.remote-channel-grid {
  padding-block: var(--space-5);
}

.remote-channel-card {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.625rem;
  border: 0;
  background: transparent;
  text-align: left;
}

.remote-channel-card--disabled .remote-channel-thumb {
  filter: saturate(0.55);
  opacity: 0.72;
}

.remote-channel-thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border: 0;
  border-radius: var(--app-card-radius);
  background: var(--app-media-thumb-placeholder);
  isolation: isolate;
  transition: box-shadow var(--duration-base) var(--ease-default);
}

.remote-channel-card:hover .remote-channel-thumb {
  box-shadow: inset 0 0 0 1px hsl(var(--foreground) / 0.16);
}

.remote-channel-card:has(:focus-visible) .remote-channel-thumb {
  box-shadow:
    0 0 0 2px hsl(var(--background)),
    0 0 0 4px hsl(var(--ring) / 0.45),
    inset 0 0 0 1px hsl(var(--foreground) / 0.16);
}

.remote-channel-card__body {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.3rem;
  padding-inline: 0.125rem;
}

.remote-channel-title {
  display: -webkit-box;
  overflow: hidden;
  color: hsl(var(--foreground) / 0.92);
  font-size: 0.875rem;
  font-weight: 650;
  line-height: 1.35;
  transition: color 0.15s ease;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.remote-channel-card:hover .remote-channel-title {
  /* Title stays foreground — primary is for CTA/play only. */
  color: hsl(var(--foreground));
}

.remote-channel-meta {
  min-height: 1rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
}

.remote-channel-primary-action,
.remote-channel-external-action,
.remote-channel-disabled-action {
  display: inline-flex;
  min-height: 2rem;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  margin-top: 0.2rem;
  border: 1px solid hsl(var(--primary));
  border-radius: var(--app-control-radius);
  padding: 0.35rem 0.65rem;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  font-size: 0.75rem;
  font-weight: 650;
  line-height: 1;
  text-decoration: none;
  cursor: pointer;
}

.remote-channel-primary-action:focus-visible,
.remote-channel-external-action:focus-visible,
.remote-channel-inline-action:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: 2px;
}

.remote-channel-external-action {
  border-color: var(--app-control-border);
  background: var(--app-control-bg);
  color: hsl(var(--foreground));
}

.remote-channel-unavailable {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem 0.6rem;
  margin-top: 0.2rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  line-height: 1.4;
}

.remote-channel-disabled-action {
  margin: 0;
  border-color: var(--app-control-border);
  background: hsl(var(--muted) / 0.65);
  color: hsl(var(--muted-foreground));
  cursor: not-allowed;
}

.remote-channel-pagination {
  display: flex;
  min-height: 4rem;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  padding: 0 1.5rem 1rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

@media (max-width: 640px) {
  .remote-channel-header__inner {
    flex-wrap: wrap;
  }

  .remote-channel-header__actions,
  .remote-channel-subscription-feedback {
    justify-content: flex-start;
    text-align: left;
  }
}

@media (prefers-reduced-motion: reduce) {
  .remote-channel-thumb,
  .remote-channel-title {
    transition: none;
  }
}
</style>
