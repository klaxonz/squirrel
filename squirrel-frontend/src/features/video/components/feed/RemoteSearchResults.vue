<template>
  <div ref="root" class="w-full">
    <div v-if="!isDesktop" class="min-h-[60vh] p-10">
      <AppEmptyState variant="plain" icon="search" title="远端搜索仅桌面端可用" copy="桌面端会直接请求源站并使用本机站点会话。" />
    </div>

    <div v-else-if="!trimmedQuery" class="min-h-[60vh] p-10">
      <AppEmptyState variant="plain" icon="search" title="输入关键词开始远端搜索" copy="结果来自源站，不会写入本地数据。" />
    </div>

    <div v-else>
      <div v-if="errorMessage" class="px-6 pt-6">
        <div class="flex items-center justify-between rounded-lg border border-destructive/20 bg-destructive/5 p-4">
          <p class="text-sm font-medium text-destructive">{{ errorMessage }}</p>
          <button class="rounded-lg bg-destructive px-4 py-2 text-xs font-bold uppercase tracking-widest text-white" @click="refresh">
            重试
          </button>
        </div>
      </div>

      <div v-if="items.length > 0" class="grid grid-cols-1 gap-x-5 gap-y-10 p-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6">
        <article
          v-for="item in items"
          :key="item.site + ':' + item.url"
          class="group flex min-w-0 cursor-pointer flex-col gap-2.5 text-left"
          role="button"
          tabindex="0"
          @click="openResult(item)"
          @keydown.enter.prevent="openResult(item)"
          @keydown.space.prevent="openResult(item)"
        >
          <div class="relative aspect-video overflow-hidden rounded-sm bg-muted transition-colors group-hover:brightness-110">
            <VideoThumbnail :src="item.thumbnail" :alt="item.title" />
            <span v-if="item.duration" class="absolute bottom-1.5 right-1.5 inline-flex h-5 items-center rounded-md bg-black/65 px-1.5 text-[10px] font-medium tabular-nums text-white backdrop-blur-sm">
              {{ formatDuration(item.duration) }}
            </span>
          </div>

          <div class="flex min-w-0 flex-col gap-1 px-0.5">
            <h3 class="line-clamp-2 text-[14px] font-semibold leading-[1.3] tracking-tight text-foreground/90 transition-colors group-hover:text-primary">
              {{ item.title }}
            </h3>
            <div class="flex items-center gap-1.5 text-[12px] font-medium text-muted-foreground/80">
              <button
                v-if="primarySubscription(item)?.url"
                type="button"
                class="flex min-w-0 items-center gap-1.5 text-left transition-colors hover:text-foreground"
                @click.stop="openRemoteChannel(item, primarySubscription(item))"
              >
                <SubscriptionAvatar
                  :src="primarySubscription(item)?.avatar"
                  :name="primarySubscription(item)?.name"
                  size="xs"
                />
                <span class="truncate">{{ primarySubscription(item)?.name }}</span>
              </button>
              <template v-else>
                <SubscriptionAvatar
                  v-if="primarySubscription(item)"
                  :src="primarySubscription(item)?.avatar"
                  :name="primarySubscription(item)?.name"
                  size="xs"
                />
                <span v-if="primarySubscription(item)?.name || item.uploader" class="truncate">
                  {{ primarySubscription(item)?.name || item.uploader }}
                </span>
              </template>
              <span class="shrink-0 rounded-[4px] bg-accent/50 px-1 py-0 text-[9px] font-bold uppercase tracking-wider text-muted-foreground">
                {{ siteLabel(item.site) }}
              </span>
            </div>
            <div v-if="actorText(item)" class="truncate text-[11px] font-medium text-muted-foreground/60">
              {{ actorText(item) }}
            </div>
            <div class="text-[11px] font-medium text-muted-foreground/50">
              {{ displayDate(item) }}
            </div>
          </div>
        </article>
      </div>

      <div v-if="loading" class="grid grid-cols-1 gap-x-5 gap-y-10 p-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6">
        <VideoSkeleton v-for="i in skeletonCount" :key="i" :delay="(i - 1) * 50" />
      </div>

      <div v-if="!loading && !errorMessage && items.length === 0" class="min-h-[60vh] p-10">
        <AppEmptyState variant="plain" icon="inbox" title="未找到远端结果" copy="换个关键词或站点再试。" />
      </div>

    </div>

    <div ref="loadMoreTrigger" class="h-20 w-full" />
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import VideoSkeleton from './VideoSkeleton.vue'
import VideoThumbnail from './VideoThumbnail.vue'
import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import { useSkeletonCount, type GridBreakpoint } from '@/features/video/composables/useSkeletonCount'
import { formatDuration } from '@/shared/lib/dateFormat'

type RemoteProfile = {
  id?: string | number | null
  type?: string | null
  name: string
  url?: string | null
  avatar?: string | null
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

const props = withDefaults(defineProps<{
  query?: string
  site?: string
  limit?: number
}>(), {
  query: '',
  site: '',
  limit: 30,
})

const emit = defineEmits(['loading-change', 'error'])

const REMOTE_SEARCH_TIMEOUT_MS = 95000
const REMOTE_PLAYABLE_SITE_PATTERNS: Record<string, RegExp> = {
  bilibili: /(?:bilibili\.com\/video\/|b23\.tv\/)/i,
  javdb: /javdb\.com\/(?:v|video)\//i,
  pornhub: /pornhub\.com\/(?:view_video\.php|video\/|embed\/)/i,
  youtube: /(?:youtube\.com\/|youtu\.be\/)/i,
  youporn: /youporn\.com\/watch\//i,
}
const router = useRouter()
const isDesktop = window.desktopApp?.isDesktop === true
const items = ref<RemoteSearchItem[]>([])
const loading = ref(false)
const allLoaded = ref(false)
const currentPage = ref(1)
const errorMessage = ref('')
const loadMoreTrigger = ref<HTMLElement | null>(null)
const trimmedQuery = computed(() => String(props.query || '').trim())
const searchKey = computed(() => `${trimmedQuery.value}::${props.site || 'all'}::${props.limit}`)

// --- Adaptive skeleton count ----------------------------------------------
// Mirrors `grid-cols-1 sm:2 md:3 lg:3 xl:4 2xl:5 3xl:6` on the grid container.
const SEARCH_BREAKPOINTS: GridBreakpoint[] = [
  [1920, 6], // 3xl
  [1536, 5], // 2xl
  [1280, 4], // xl
  [1024, 3], // lg
  [768, 3],  // md
  [640, 2],  // sm
  [0, 1],    // base
]
const { count: skeletonCount, attachRef: root } = useSkeletonCount({
  breakpoints: SEARCH_BREAKPOINTS,
  cardHeight: 260, // thumbnail + 2-line title + meta + actor + date
  rowGap: 40,      // matches `gap-y-10` (2.5rem ≈ 40px)
})

let requestToken = 0
let observer: IntersectionObserver | null = null
let loadedSearchKey = ''
const pendingYouPornAvatarUrls = new Set<string>()

const siteLabel = (site: string) => {
  const labels: Record<string, string> = {
    bilibili: 'Bilibili',
    javdb: 'JavDB',
    pornhub: 'Pornhub',
    youtube: 'YouTube',
    youporn: 'YouPorn',
  }
  return labels[site] || site
}

const displayDate = (item: RemoteSearchItem) => {
  if (item.published_text) return item.published_text
  if (!item.publish_date) return ''
  const date = new Date(item.publish_date)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString()
}

const normalizeProfiles = (profiles: RemoteProfile[] | undefined) => {
  if (!Array.isArray(profiles)) return []
  return profiles.filter((profile) => profile?.name).map((profile) => ({
    ...profile,
    name: String(profile.name || '').trim(),
    url: profile.url || '',
    avatar: profile.avatar || '',
  }))
}

const primarySubscription = (item: RemoteSearchItem) => {
  const subscription = normalizeProfiles(item.subscriptions)[0]
  if (subscription) return subscription
  if (!item.uploader || !item.uploader_url) return null
  return {
    type: 'CHANNEL',
    name: item.uploader,
    url: item.uploader_url,
    avatar: item.uploader_avatar || '',
  }
}

const applyYouPornAvatar = (profileUrl: string, avatar: string) => {
  if (!avatar) return
  items.value = items.value.map((item) => {
    if (item.site !== 'youporn' || item.uploader_url !== profileUrl) return item
    const subscriptions = normalizeProfiles(item.subscriptions).map((profile, index) => (
      index === 0 ? { ...profile, avatar } : profile
    ))
    return {
      ...item,
      uploader_avatar: avatar,
      subscriptions: subscriptions.length ? subscriptions : item.subscriptions,
    }
  })
}

const loadYouPornAvatars = (nextItems: RemoteSearchItem[], token: number) => {
  const bridge = window.desktopApp
  if (typeof bridge?.getYouPornProfileAvatar !== 'function') return
  const profileUrls = Array.from(new Set(nextItems
    .filter((item) => item.site === 'youporn' && item.uploader_url && !item.uploader_avatar)
    .map((item) => String(item.uploader_url))))

  for (const profileUrl of profileUrls) {
    if (pendingYouPornAvatarUrls.has(profileUrl)) continue
    pendingYouPornAvatarUrls.add(profileUrl)
    bridge.getYouPornProfileAvatar(profileUrl)
      .then((avatar) => {
        if (token !== requestToken) return
        applyYouPornAvatar(profileUrl, avatar)
      })
      .finally(() => pendingYouPornAvatarUrls.delete(profileUrl))
  }
}

const actorText = (item: RemoteSearchItem) => {
  const actors = normalizeProfiles(item.actors).map((actor) => actor.name).slice(0, 3)
  return actors.length ? actors.join(' / ') : ''
}

const openRemoteChannel = async (item: RemoteSearchItem, profile: RemoteProfile | null) => {
  const url = String(profile?.url || '').trim()
  if (!url) return
  await router.push({
    name: 'RemoteChannelDetail',
    query: {
      site: item.site,
      url,
      id: profile?.id != null ? String(profile.id) : undefined,
      name: profile?.name || undefined,
      avatar: profile?.avatar || undefined,
      is_nsfw: profile?.is_nsfw === true ? 'true' : undefined,
    },
  })
}

const setLoading = (value: boolean) => {
  loading.value = value
  emit('loading-change', value)
}

const appendUniqueItems = (nextItems: RemoteSearchItem[]) => {
  const seen = new Set(items.value.map((item) => item.url))
  const uniqueItems = nextItems.filter((item) => {
    if (!item.url || seen.has(item.url)) return false
    seen.add(item.url)
    return true
  })
  items.value = items.value.concat(uniqueItems)
  return uniqueItems
}

const loadPage = async (page: number) => {
  const query = trimmedQuery.value

  if (!query || !isDesktop) {
    setLoading(false)
    return
  }

  const bridge = window.desktopApp
  if (typeof bridge?.searchRemoteVideos !== 'function') {
    errorMessage.value = '当前桌面端不支持远端搜索'
    emit('error', new Error(errorMessage.value))
    return
  }

  const currentToken = ++requestToken
  setLoading(true)
  let timer: ReturnType<typeof setTimeout> | undefined
  try {
    const result = await Promise.race([
      bridge.searchRemoteVideos({
        query,
        site: props.site || 'all',
        limit: props.limit,
        page,
      }),
      new Promise<never>((_, reject) => {
        timer = setTimeout(() => reject(new Error('远端搜索超时')), REMOTE_SEARCH_TIMEOUT_MS)
      }),
    ])
    if (currentToken !== requestToken) return
    const nextItems = Array.isArray(result?.items) ? result.items : []
    const previousCount = items.value.length
    if (page === 1) {
      items.value = nextItems
    } else {
      appendUniqueItems(nextItems)
    }
    loadYouPornAvatars(nextItems, currentToken)
    currentPage.value = page
    allLoaded.value = result?.has_more === false || (page > 1 && items.value.length === previousCount)
    if (Array.isArray(result?.errors) && result.errors.length > 0 && items.value.length === 0) {
      errorMessage.value = result.errors.join('；')
      emit('error', new Error(errorMessage.value))
    }
  } catch (error: unknown) {
    if (currentToken !== requestToken) return
    // ponytail: desktop bridge path bypasses handleRequest; reject is plain Error
    errorMessage.value = error instanceof Error ? error.message : '远端搜索失败'
    emit('error', error instanceof Error ? error : new Error(errorMessage.value))
  } finally {
    clearTimeout(timer)
    if (currentToken === requestToken) setLoading(false)
  }
}

const refresh = async () => {
  items.value = []
  currentPage.value = 1
  allLoaded.value = false
  errorMessage.value = ''
  loadedSearchKey = searchKey.value
  await loadPage(1)
}

const loadMore = async () => {
  if (loading.value || allLoaded.value || !items.value.length) return
  await loadPage(currentPage.value + 1)
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
  const id = `remote-${item.site}-${hashRemoteUrl(url)}`
  const subscriptions = normalizeProfiles(item.subscriptions)
  const actors = normalizeProfiles(item.actors)
  const uploaderSubscription = item.uploader ? {
    type: 'CHANNEL',
    name: item.uploader,
    url: item.uploader_url || '',
    avatar: item.uploader_avatar || '',
  } : null

  return {
    id,
    source: 'remote',
    site: item.site,
    title: item.title,
    url,
    thumbnail: item.thumbnail || '',
    duration: item.duration || null,
    publish_date: item.publish_date || null,
    uploaded_at: item.publish_date || null,
    description: item.description || '',
    subscriptions: subscriptions.length ? subscriptions : (uploaderSubscription ? [uploaderSubscription] : []),
    actors,
  }
}

const canPlayRemoteResult = (item: RemoteSearchItem) => {
  const pattern = REMOTE_PLAYABLE_SITE_PATTERNS[item.site]
  return !!pattern && pattern.test(String(item.url || ''))
}

const openResult = async (item: RemoteSearchItem) => {
  if (!item.url) return
  if (!canPlayRemoteResult(item)) {
    await window.desktopApp?.openExternal?.(item.url)
    return
  }

  const videoSeed = buildRemoteVideoSeed(item)
  rememberVideoPlaybackSeed(videoSeed)
  await router.push({ name: 'VideoPlay', params: { videoId: videoSeed.id } })
}

watch(searchKey, (nextSearchKey) => {
  if (nextSearchKey === loadedSearchKey) return
  refresh()
}, { immediate: true })

onActivated(() => {
  if (searchKey.value === loadedSearchKey) return
  refresh()
})

onMounted(() => {
  const root = document.getElementById('app-main-scroll')
  observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) {
      loadMore()
    }
  }, {
    root,
    rootMargin: '600px',
  })

  if (loadMoreTrigger.value) observer.observe(loadMoreTrigger.value)
})

onUnmounted(() => observer?.disconnect())

defineExpose({ refresh })
</script>
