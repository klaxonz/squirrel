<template>
  <AppPageShell variant="compact" :fill="false">
    <div class="app-page-content">
      <div v-if="errorMessage" class="px-6 pt-6">
        <div class="flex items-center justify-between rounded-lg border border-destructive/20 bg-destructive/5 p-4">
          <p class="text-sm font-medium text-destructive">{{ errorMessage }}</p>
          <button class="rounded-lg bg-destructive px-4 py-2 text-xs font-bold uppercase tracking-widest text-white" @click="refresh">
            重试
          </button>
        </div>
      </div>

      <section class="px-6 pt-6">
        <div class="flex min-w-0 items-center gap-4 border-b border-border/40 pb-6">
          <SubscriptionAvatar :src="profile.avatar" :name="profile.name || siteLabel" size="xl" />
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <h1 class="truncate text-xl font-semibold tracking-tight text-foreground">{{ profile.name || siteLabel }}</h1>
              <span class="shrink-0 rounded-[4px] bg-accent/50 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                {{ siteLabel }}
              </span>
            </div>
            <p v-if="profile.description" class="mt-2 line-clamp-2 max-w-4xl text-sm leading-relaxed text-muted-foreground">
              {{ profile.description }}
            </p>
          </div>
          <div class="flex items-center gap-3">
            <div v-if="localSubscriptionRoute" class="flex rounded-lg border border-border/40 bg-muted/40 p-0.5">
              <button
                type="button"
                class="inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-xs font-semibold text-muted-foreground transition-colors hover:text-foreground"
                @click="openLocalChannel"
              >
                <AppIcon name="library" class="h-3.5 w-3.5" />
                本地
              </button>
              <button
                type="button"
                class="inline-flex h-8 items-center gap-1.5 rounded-md bg-background px-3 text-xs font-semibold text-foreground shadow-sm"
                disabled
              >
                <AppIcon name="siteFallback" class="h-3.5 w-3.5" />
                远端
              </button>
            </div>
            <button
              v-if="channelUrl"
              type="button"
              class="h-9 min-w-20 rounded-full px-4 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60"
              :class="isSubscriptionChecked && isSubscribed ? 'bg-secondary text-foreground ring-1 ring-border/40' : 'bg-foreground text-background hover:opacity-90'"
              :disabled="isCheckingSubscription || isSubscribing"
              @click="handleSubscribe"
            >
              {{ subscriptionButtonText }}
            </button>
          </div>
        </div>
      </section>

      <div v-if="items.length > 0" class="grid grid-cols-1 gap-x-5 gap-y-10 p-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6">
        <button
          v-for="item in items"
          :key="item.site + ':' + item.url"
          type="button"
          class="group flex min-w-0 cursor-pointer flex-col gap-2.5 text-left"
          @click="openResult(item)"
        >
          <div class="relative aspect-video overflow-hidden rounded-lg bg-muted transition-colors group-hover:bg-muted/80">
            <img
              v-if="item.thumbnail"
              :src="item.thumbnail"
              :alt="item.title"
              loading="lazy"
              decoding="async"
              referrerpolicy="no-referrer"
              class="h-full w-full object-contain"
            >
            <div v-else class="absolute inset-0 flex items-center justify-center bg-muted">
              <AppIcon name="imageOff" class="h-6 w-6 text-muted-foreground/20" />
            </div>
            <span v-if="item.duration" class="absolute bottom-1.5 right-1.5 inline-flex h-5 items-center rounded-md bg-black/65 px-1.5 text-[10px] font-medium tabular-nums text-white backdrop-blur-sm">
              {{ formatDuration(item.duration) }}
            </span>
          </div>

          <div class="flex min-w-0 flex-col gap-1 px-0.5">
            <h3 class="line-clamp-2 text-[14px] font-semibold leading-[1.3] tracking-tight text-foreground/90 transition-colors group-hover:text-primary">
              {{ item.title }}
            </h3>
            <div class="text-[11px] font-medium text-muted-foreground/50">
              {{ displayDate(item) }}
            </div>
          </div>
        </button>
      </div>

      <div v-if="loading" class="grid grid-cols-1 gap-x-5 gap-y-10 p-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6">
        <VideoSkeleton v-for="i in 12" :key="i" :delay="i * 50" />
      </div>

      <div v-if="items.length > 0 && !allLoaded" class="flex justify-center px-6 pb-8">
        <button
          type="button"
          class="rounded-lg bg-secondary px-5 py-2 text-sm font-semibold text-foreground transition-colors hover:bg-secondary/80 disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="loading"
          @click="loadMore"
        >
          {{ loading ? '加载中' : '加载更多' }}
        </button>
      </div>

      <div v-if="!loading && !errorMessage && items.length === 0" class="flex min-h-[50vh] flex-col items-center justify-center p-10 text-center">
        <div class="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-secondary">
          <AppIcon name="inbox" class="h-10 w-10 text-muted-foreground/30" />
        </div>
        <h3 class="text-xl font-bold text-foreground/60">暂无频道视频</h3>
      </div>

      <div ref="loadMoreTrigger" class="h-20 w-full" />
    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, nextTick, onActivated, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/components/common/AppIcon.vue'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import VideoSkeleton from '@/components/feed/VideoSkeleton.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import { rememberVideoPlaybackSeed } from '@/composables/videoPlaybackSeed'
import { formatDuration } from '@/utils/dateFormat'
import { getSubscriptionStatus, subscribe, unsubscribe } from '@/api'

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

const queryValue = (key: string) => {
  const value = route.query[key]
  return Array.isArray(value) ? String(value[0] || '') : String(value || '')
}

const site = computed(() => queryValue('site'))
const channelUrl = computed(() => queryValue('url'))
const siteLabel = computed(() => {
  const labels: Record<string, string> = {
    bilibili: 'Bilibili',
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
  if (!window.desktopApp?.isDesktop || typeof window.desktopApp?.getRemoteChannel !== 'function') {
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
  } catch (error: any) {
    if (currentToken !== requestToken) return
    errorMessage.value = error?.message || '远端频道加载失败'
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
  const { data, error } = await getSubscriptionStatus(url)
  isCheckingSubscription.value = false

  if (url !== channelUrl.value) return
  if (error) return

  isSubscribed.value = data?.is_subscribed === true
  subscriptionId.value = data?.subscription_id ?? null
  isSubscriptionChecked.value = true
}

watch(channelUrl, async (url) => {
  await refreshSubscriptionStatus(url)
}, { immediate: true })

const handleSubscribe = async () => {
  const url = channelUrl.value
  if (!url || isSubscribing.value) return

  isSubscribing.value = true
  const result = isSubscribed.value && subscriptionId.value
    ? await unsubscribe(subscriptionId.value)
    : await subscribe(url)
  isSubscribing.value = false

  if (result.error) return

  if (!isSubscribed.value) {
    isSubscribed.value = result.data?.is_subscribed === true
    subscriptionId.value = result.data?.subscription_id ?? null
    isSubscriptionChecked.value = true
  }

  await refreshSubscriptionStatus(url)
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
  scrollRoot = document.getElementById('app-main-scroll')
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
