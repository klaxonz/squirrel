<template>
  <AppPageShell variant="compact" :fill="false">
    <div ref="root" class="app-page-content app-page-content--media">
      <div v-if="errorMessage" class="app-page-section">
        <AppEmptyState variant="error" title="加载失败" :copy="errorMessage">
          <template #actions>
            <Button variant="outline" size="sm" @click="refresh">重试</Button>
          </template>
        </AppEmptyState>
      </div>

      <section class="remote-channel-header-section">
        <div class="remote-channel-header">
          <SubscriptionAvatar :src="profile.avatar" :name="profile.name || siteLabel" size="xl" />
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <h1 class="app-h2 truncate">{{ profile.name || siteLabel }}</h1>
              <span class="remote-channel-site-badge">
                {{ siteLabel }}
              </span>
            </div>
            <p v-if="profile.description" class="app-copy-wide mt-2 line-clamp-2 text-sm leading-relaxed text-muted-foreground">
              {{ profile.description }}
            </p>
          </div>
          <div class="flex items-center gap-3">
            <div v-if="localSubscriptionRoute" class="remote-channel-switch">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                @click="openLocalChannel"
              >
                <AppIcon name="library" class="h-3.5 w-3.5" />
                本地
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled
              >
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
        </div>
      </section>

      <div v-if="items.length > 0" class="remote-channel-grid app-video-grid app-video-grid--feed">
        <button
          v-for="item in items"
          :key="item.site + ':' + item.url"
          type="button"
          class="remote-channel-card group"
          @click="openResult(item)"
        >
          <div class="remote-channel-thumb">
            <VideoThumbnail :src="item.thumbnail" :alt="item.title" />
            <span v-if="item.duration" class="remote-channel-duration">
              {{ formatDuration(item.duration) }}
            </span>
          </div>

          <div class="flex min-w-0 flex-col gap-1 px-0.5">
            <h3 class="remote-channel-title">
              {{ item.title }}
            </h3>
            <div class="remote-channel-meta">
              {{ displayDate(item) }}
            </div>
          </div>
        </button>
      </div>

      <div v-if="loading" class="app-page-section--grid app-video-grid app-video-grid--feed">
        <VideoSkeleton v-for="i in skeletonCount" :key="i" :delay="(i - 1) * 50" />
      </div>

      <div v-if="items.length > 0 && !allLoaded" class="remote-channel-load-more">
        <Button
          type="button"
          variant="outline"
          :disabled="loading"
          @click="loadMore"
        >
          {{ loading ? '加载中' : '加载更多' }}
        </Button>
      </div>

      <div v-if="!loading && !errorMessage && items.length === 0" class="app-page-empty app-page-empty--compact">
        <AppEmptyState variant="plain" icon="inbox" title="暂无频道视频" />
      </div>

      <div ref="loadMoreTrigger" class="h-20 w-full" />
    </div>
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
  javdb: /javdb\.com\/(?:v|video)\//i,
  pornhub: /pornhub\.com\/(?:view_video\.php|video\/|embed\/)/i,
  youtube: /(?:youtube\.com\/|youtu\.be\/)/i,
  youporn: /youporn\.com\/watch\//i,
}

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

let requestToken = 0
let observer: IntersectionObserver | null = null
let scrollRoot: HTMLElement | null = null
let loadedChannelKey = ''

// --- Adaptive skeleton count ----------------------------------------------
// Mirrors the auto-fill `.app-video-grid--feed` via the same minCardWidth/gap
// formula — no breakpoint table to keep in sync with the CSS class.
const { count: skeletonCount, attachRef: root } = useSkeletonCount({
  minCardWidth: 280,   // matches --app-video-grid-min
  gap: 40,             // matches --app-video-grid-gap-y (2.5rem)
  cardHeight: 220,     // thumbnail + 2-line title + date
})

const queryValue = (key: string) => {
  const value = route.query[key]
  return Array.isArray(value) ? String(value[0] || '') : String(value || '')
}

const site = computed(() => queryValue('site'))
const channelUrl = computed(() => queryValue('url'))
const siteLabel = computed(() => {
  const labels: Record<string, string> = {
    bilibili: 'Bilibili',
    javdb: 'JavDB',
    pornhub: 'Pornhub',
    youtube: 'YouTube',
    youporn: 'YouPorn',
  }
  return labels[site.value] || site.value
})

const subscriptionButtonText = computed(() => {
  if (isCheckingSubscription.value) return '检查中'
  if (isSubscribing.value) return '订阅中'
  return isSubscriptionChecked.value && isSubscribed.value ? '取消订阅' : '订阅'
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

const loadPage = async (page: number) => {
  if (!isDesktopEnv() || typeof window.desktopApp?.getRemoteChannel !== 'function') {
    errorMessage.value = '当前桌面端不支持远端频道'
    return
  }
  if (!site.value || !channelUrl.value) {
    errorMessage.value = '缺少远端频道地址'
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
    if (page === 1) items.value = nextItems
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
  items.value = []
  profile.value = routeProfile.value
  currentPage.value = 1
  nextCursor.value = null
  allLoaded.value = false
  loadedChannelKey = channelKey.value
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
  isSubscribed.value = false
  isSubscriptionChecked.value = false
  subscriptionId.value = null
  if (!url) return

  isCheckingSubscription.value = true
  try {
    const data = await getSubscriptionStatus(url)
    if (url !== channelUrl.value) return
    isSubscribed.value = data?.is_subscribed === true
    subscriptionId.value = data?.subscription_id ?? null
    isSubscriptionChecked.value = true
  } catch {
    if (url !== channelUrl.value) return
    // silent — subscription status check failure just leaves it unchecked
  } finally {
    isCheckingSubscription.value = false
  }
}

watch(channelUrl, async (url) => {
  await refreshSubscriptionStatus(url)
}, { immediate: true })

const handleSubscribe = async () => {
  const url = channelUrl.value
  if (!url || isSubscribing.value) return

  isSubscribing.value = true
  try {
    const data = isSubscribed.value && subscriptionId.value
      ? await unsubscribe(subscriptionId.value)
      : await subscribe(url)

    if (!isSubscribed.value) {
      isSubscribed.value = data?.is_subscribed === true
      subscriptionId.value = data?.subscription_id ?? null
      isSubscriptionChecked.value = true
    }

    await refreshSubscriptionStatus(url)
  } catch {
    // silent — a failed subscribe/unsubscribe leaves the toggle unchanged
  } finally {
    isSubscribing.value = false
  }
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

const openResult = async (item: RemoteSearchItem) => {
  if (!item.url || !canPlayRemoteResult(item)) return

  const videoSeed = buildRemoteVideoSeed(item)
  rememberVideoPlaybackSeed(videoSeed)
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
.remote-channel-header-section {
  padding: 1.5rem 1.5rem 0;
}

.remote-channel-header {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 1rem;
  border-bottom: 1px solid hsl(var(--border) / 0.42);
  padding-bottom: 1.5rem;
}

.remote-channel-site-badge {
  flex: none;
  border: 1px solid hsl(var(--border) / 0.45);
  border-radius: 0.375rem;
  background: hsl(var(--muted) / 0.34);
  padding: 0.125rem 0.375rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.625rem;
  font-weight: 700;
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
  padding: 1.5rem;
}

.remote-channel-card {
  display: flex;
  min-width: 0;
  cursor: pointer;
  flex-direction: column;
  gap: 0.625rem;
  border: 0;
  background: transparent;
  text-align: left;
}

.remote-channel-thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.42);
  border-radius: 0.625rem;
  background: hsl(var(--muted));
  transition: border-color 0.15s ease;
}

.remote-channel-card:hover .remote-channel-thumb {
  border-color: hsl(var(--primary) / 0.32);
}

.remote-channel-duration {
  position: absolute;
  right: 0.25rem;
  bottom: 0.25rem;
  display: inline-flex;
  height: 1.25rem;
  align-items: center;
  border-radius: 0.375rem;
  background: hsl(0 0% 0% / 0.72);
  padding: 0 0.375rem;
  color: white;
  font-size: 0.625rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
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
  color: hsl(var(--primary));
}

.remote-channel-meta {
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
}

.remote-channel-load-more {
  display: flex;
  justify-content: center;
  padding: 0 1.5rem 2rem;
}

@media (prefers-reduced-motion: reduce) {
  .remote-channel-thumb,
  .remote-channel-title {
    transition: none;
  }
}
</style>
