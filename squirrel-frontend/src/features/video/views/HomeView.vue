<template>
  <AppPageShell class="home-view-page" variant="compact" :fill="false">
    <div ref="contentRef" class="app-page-content app-page-content--cinema">

      <header class="app-cinema-hero-pro">
        <!-- Featured backdrop: staggered card stack -->
        <div
          v-if="featuredVideos.length > 0"
          class="app-cinema-hero-pro__backdrop app-cinema-hero-pro__backdrop--stack"
        >
          <button
            v-for="(video, idx) in featuredVideos"
            :key="video.id"
            type="button"
            class="app-hero-stack-card"
            :class="[
              { 'app-hero-stack-card--active': idx === activeFeaturedIndex },
              `app-hero-stack-card--${cardVisualPos(idx)}`,
            ]"
            :aria-label="`切换到 ${video.title}`"
            @click="activateFeatured(idx)"
          >
            <img
              :src="video.thumbnail || ''"
              :alt="video.title"
              class="app-hero-stack-card__img"
              loading="eager"
            />
          </button>
        </div>
        <!-- Fallback: gradient only (featured API has its own cache, single-video blur is gone) -->
        <div v-else class="app-cinema-hero-pro__backdrop app-cinema-hero-pro__backdrop--fallback" />
        <div class="app-cinema-hero-pro__scrim" />

        <div class="app-cinema-hero-pro__inner">
          <p class="app-cinema-hero-pro__eyebrow">{{ heroEyebrow }}</p>
          <h1 class="app-cinema-hero-pro__title">{{ heroTitle }}</h1>
          <p v-if="heroSub" class="app-cinema-hero-pro__sub">{{ heroSub }}</p>

          <div v-if="heroVideo" class="app-cinema-hero-pro__actions">
            <button
              type="button"
              class="app-hero-cta"
              @click="handleOpenModal(heroVideo)"
            >
              <AppIcon name="play" class="app-play-icon size-4" />
              {{ heroCtaLabel }}
              <span v-if="heroRemainingText" class="app-hero-cta__meta">{{ heroRemainingText }}</span>
            </button>
            <button
              v-if="heroChannelId"
              type="button"
              class="app-hero-cta app-hero-cta--ghost"
              @click="goToChannelDetail(String(heroChannelId))"
            >
              查看频道
            </button>
          </div>
          <div v-else class="app-cinema-hero-pro__actions">
            <button
              type="button"
              class="app-hero-cta"
              @click="scrollToFirstRail"
            >
              <AppIcon name="chevronDown" class="size-4" />
              开始探索
            </button>
          </div>
        </div>
      </header>

      <SpotlightRow
        ref="spotlightRef"
        @openModal="handleOpenModal"
        @goToSubscription="goToChannelDetail"
      />
      <ContinueWatching
        ref="continueWatchingRef"
        @openModal="handleOpenModal"
        @viewMore="goToContinueWatching"
        @goToSubscription="goToChannelDetail"
        @heroChange="handleHeroChange"
      />
      <SpecialFollowVideos
        ref="specialFollowRef"
        @openModal="handleOpenModal"
        @goToSubscription="goToChannelDetail"
        @viewMore="goToSpecialFollowVideos"
      />
    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onActivated, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import SpotlightRow from '@/features/video/components/feed/SpotlightRow.vue'
import ContinueWatching from '@/features/video/components/feed/ContinueWatching.vue'
import SpecialFollowVideos from '@/features/video/components/feed/SpecialFollowVideos.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { formatDuration } from '@/shared/lib/dateFormat'
import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import { getFeaturedVideos } from '@/shared/api/video'
import { Logger } from '@/shared/lib/logger'
import type { VideoHistoryEntry, VideoListItem } from '@/features/video/types/video'

// Home view: recommendation rows + cinematic hero. The full tabbed feed lives in VideosView (/videos).
defineOptions({ name: 'HomeView' })

const router = useRouter()

// feed rows share a refresh() surface via defineExpose; minimal interface
// avoids coupling the parent to specific component instances.
const spotlightRef = ref<{ refresh?: () => void } | null>(null)
const continueWatchingRef = ref<{ refresh?: () => void } | null>(null)
const specialFollowRef = ref<{ refresh?: () => void } | null>(null)

// ── Local cache for featured videos ──
const FEATURED_CACHE_KEY = 'app:home:featured-videos'

interface CachedFeatured {
  items: VideoListItem[]
  ts: number
}

const readCachedFeatured = (): CachedFeatured | null => {
  try {
    const raw = localStorage.getItem(FEATURED_CACHE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as CachedFeatured
    if (!Array.isArray(parsed.items) || parsed.items.length === 0) return null
    return parsed
  } catch {
    return null
  }
}

const writeCachedFeatured = (items: VideoListItem[]) => {
  try {
    localStorage.setItem(FEATURED_CACHE_KEY, JSON.stringify({ items, ts: Date.now() }))
  } catch { /* quota exceeded — non-critical */ }
}

// ── Hero state ──
const cached = readCachedFeatured()
const featuredVideos = ref<VideoListItem[]>(cached?.items ?? [])
const activeFeaturedIndex = ref(0)

// History-based hero (from ContinueWatching)
const historyHero = ref<VideoHistoryEntry | null>(null)

const handleHeroChange = (video: VideoHistoryEntry | null) => {
  if (video?.id === historyHero.value?.id) return
  historyHero.value = video
}

// Composite hero: centre featured card takes priority, history as fallback
const heroVideo = computed<VideoHistoryEntry | VideoListItem | null>(() => {
  const active = featuredVideos.value[activeFeaturedIndex.value]
  if (active && active.thumbnail) return active
  return historyHero.value
})

// ── Card visual position: maps card index to a named position relative to active ──
const cardVisualPos = (idx: number): string => {
  const total = featuredVideos.value.length
  if (total <= 1) return 'centre'
  const diff = idx - activeFeaturedIndex.value
  if (diff === 0) return 'centre'
  if (diff === 1) return 'right'
  if (diff === -1) return 'left'
  if (diff > 1) return 'far-right'
  return 'far-left'
}

// ── Auto-rotation ──
const AUTO_ROTATE_INTERVAL = 6_000 // 6 seconds
let autoRotateTimer: ReturnType<typeof setInterval> | null = null

const startAutoRotate = () => {
  stopAutoRotate()
  if (featuredVideos.value.length <= 1) return
  autoRotateTimer = setInterval(() => {
    const next = (activeFeaturedIndex.value + 1) % featuredVideos.value.length
    activeFeaturedIndex.value = next
  }, AUTO_ROTATE_INTERVAL)
}

const stopAutoRotate = () => {
  if (autoRotateTimer !== null) {
    clearInterval(autoRotateTimer)
    autoRotateTimer = null
  }
}

const activateFeatured = (idx: number) => {
  if (idx === activeFeaturedIndex.value) return
  activeFeaturedIndex.value = idx
  // Reset timer on manual interaction
  startAutoRotate()
}

// ── Hero text ──
const heroEyebrow = computed(() =>
  heroVideo.value ? '归仓 · 继续观看' : '归仓 · 你的影音仓',
)
const heroTitle = computed(() =>
  heroVideo.value ? heroVideo.value.title : '今天看点什么',
)
const heroSub = computed(() => {
  if (heroVideo.value) {
    const subs = heroVideo.value.subscriptions
    const who = subs?.[0]?.name
    return who ? `来自 ${who} · 从你离开的地方继续` : '从你离开的地方继续这段旅程'
  }
  return '从你订阅的频道精选、未看完的内容,以及特别关注的更新中,挑出今天的观看清单。'
})

const heroCtaLabel = computed(() => {
  const v = heroVideo.value
  if (!v) return '开始观看'
  const pos = Number(v.last_position || 0)
  return pos > 0 ? '继续观看' : '开始观看'
})

const heroRemainingText = computed(() => {
  const v = heroVideo.value
  if (!v) return ''
  const dur = Number(v.duration || 0)
  const pos = Number(v.last_position || 0)
  const remaining = dur - pos
  if (remaining > 0) return `剩 ${formatDuration(remaining)}`
  return ''
})

const heroChannelId = computed(() => heroVideo.value?.subscriptions?.[0]?.id ?? null)

// ── Actions ──
const scrollToFirstRail = () => {
  const firstRail = contentRef.value?.querySelector('section')
  firstRail?.scrollIntoView({ block: 'start' })
}

let lastRefreshedAt = 0

const handleOpenModal = (video: { id: string | number }) => {
  rememberVideoPlaybackSeed(video)
  router.push(`/video/${video.id}`)
}

const goToChannelDetail = (id: string | number | null | undefined) => {
  if (id == null || id === '') return
  router.push(`/subscription/${id}/all`)
}
const goToContinueWatching = () => router.push({ name: 'History', query: { mode: 'continue' } })
const goToSpecialFollowVideos = () => router.push({ name: 'AllVideos', query: { special: 'yes' } })

const contentRef = ref<HTMLElement | null>(null)

const refresh = () => {
  Promise.allSettled([
    spotlightRef.value?.refresh?.(),
    continueWatchingRef.value?.refresh?.(),
    specialFollowRef.value?.refresh?.(),
    loadFeaturedVideos(),
  ]).finally(() => {
    lastRefreshedAt = Date.now()
  })
}

// Load featured backdrop pool. Uses local cache to avoid fallback flash on refresh.
const loadFeaturedVideos = async () => {
  try {
    const items = await getFeaturedVideos()
    if (Array.isArray(items) && items.length > 0) {
      featuredVideos.value = items.slice(0, 3)
      writeCachedFeatured(featuredVideos.value)
      // Reset active index if it's now out of bounds
      if (activeFeaturedIndex.value >= featuredVideos.value.length) {
        activeFeaturedIndex.value = 0
      }
      startAutoRotate()
    }
  } catch (e) {
    Logger.warn('Failed to load featured hero backdrop:', e)
  }
}

// HomeView is kept-alive at the app root; refresh recommendation rows when
// returning to the home page, throttled to avoid hammering the API on rapid nav.
onActivated(() => {
  const now = Date.now()
  if (now - lastRefreshedAt < 30_000) return
  refresh()
})

onMounted(() => {
  lastRefreshedAt = Date.now()
  // If we have cached data, show it immediately; API refresh happens in background
  if (featuredVideos.value.length > 0) {
    startAutoRotate()
  }
  loadFeaturedVideos()
})

onBeforeUnmount(() => {
  stopAutoRotate()
})
</script>

<style scoped>
.home-view-page {
  --app-page-max-width: 2400px;
}

.app-page-content--cinema {
  padding-top: 0;
}

/* ── CTA buttons ── */
.app-hero-cta {
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  height: 2.25rem;
  padding: 0 1rem;
  border: 0;
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
  color: hsl(var(--primary-foreground));
  background: var(--brand-gradient);
  box-shadow: inset 0 0 0 1px hsl(var(--primary) / 0.35), 0 6px 18px hsl(var(--primary) / 0.18);
  transition: transform var(--duration-fast) var(--ease-spring),
              box-shadow var(--duration-fast) var(--ease-default);
  cursor: pointer;
}
.app-hero-cta:hover {
  transform: translateY(-1px);
  box-shadow: inset 0 0 0 1px hsl(var(--primary) / 0.4), 0 8px 22px hsl(var(--primary) / 0.22);
}
.app-hero-cta:active {
  transform: translateY(0) scale(0.98);
}
.app-hero-cta:focus-visible {
  outline: none;
  box-shadow: inset 0 0 0 1px hsl(var(--primary) / 0.4), 0 8px 22px hsl(var(--primary) / 0.22), 0 0 0 3px hsl(var(--ring) / 0.4);
}
.app-hero-cta__meta {
  display: inline-flex;
  align-items: center;
  align-self: stretch;
  padding-left: 0.5rem;
  margin-left: 0.25rem;
  border-left: 1px solid hsl(0 0% 100% / 0.25);
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  font-weight: 500;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  opacity: 0.85;
}
.app-hero-cta--ghost {
  background: hsl(0 0% 100% / 0.16);
  color: hsl(0 0% 100%);
  box-shadow: inset 0 0 0 1px hsl(0 0% 100% / 0.35), 0 4px 14px hsl(24 10% 6% / 0.2);
  backdrop-filter: blur(8px);
}
.app-hero-cta--ghost:hover {
  background: hsl(0 0% 100% / 0.26);
  box-shadow: inset 0 0 0 1px hsl(0 0% 100% / 0.5), 0 4px 14px hsl(24 10% 6% / 0.25);
}

/* ── Fallback gradient backdrop ── */
.app-cinema-hero-pro__backdrop--fallback {
  background: radial-gradient(ellipse 60% 80% at 30% 40%,
    hsl(38 92% 56% / 0.12) 0%,
    hsl(28 88% 50% / 0.06) 40%,
    transparent 70%);
  filter: none;
  transform: none;
}

/* ── Staggered card stack backdrop ── */
.app-cinema-hero-pro__backdrop--stack {
  filter: none;
  transform: none;
  background: none;
  display: block;
  padding: 0;
}

.app-hero-stack-card {
  position: absolute;
  top: 0;
  bottom: 0;
  height: 100%;
  width: auto;
  max-width: none;
  padding: 0;
  border: 0;
  border-radius: var(--radius-xl);
  overflow: hidden;
  background: none;
  cursor: pointer;
  box-shadow: 0 4px 24px hsl(var(--hero-scrim) / 0.25);
  transition:
    transform 0.5s var(--ease-spring),
    opacity 0.4s ease,
    filter 0.4s ease,
    box-shadow 0.4s ease;
}

.app-hero-stack-card__img {
  display: block;
  height: 100%;
  width: auto;
  aspect-ratio: 16 / 9;
  object-fit: cover;
}

/* Inactive (side) cards: dimmed, pushed to sides */
.app-hero-stack-card:not(.app-hero-stack-card--active) {
  opacity: 0.45;
  filter: brightness(0.6) saturate(0.85);
  box-shadow: 0 2px 12px hsl(var(--hero-scrim) / 0.15);
}
.app-hero-stack-card:not(.app-hero-stack-card--active):hover {
  opacity: 0.7;
  filter: brightness(0.75) saturate(1);
  box-shadow: 0 4px 20px hsl(var(--hero-scrim) / 0.3);
}

/* Active (centre) card: full brightness, highest z */
.app-hero-stack-card--active {
  z-index: 3;
  opacity: 1;
  filter: brightness(1) saturate(1);
  box-shadow:
    0 12px 40px hsl(var(--hero-scrim) / 0.5),
    0 0 0 1px hsl(0 0% 100% / 0.1);
  cursor: default;
}

/* Position transforms — cards sized by height, so they extend off-screen naturally */
.app-hero-stack-card--centre {
  z-index: 3;
  left: 50%;
  transform: translateX(-50%) rotate(0deg);
}
.app-hero-stack-card--left {
  z-index: 2;
  left: 50%;
  transform: translateX(-78%) rotate(-5deg);
}
.app-hero-stack-card--right {
  z-index: 2;
  left: 50%;
  transform: translateX(-22%) rotate(5deg);
}
.app-hero-stack-card--far-left {
  z-index: 1;
  left: 50%;
  transform: translateX(-100%) rotate(-8deg);
}
.app-hero-stack-card--far-right {
  z-index: 1;
  left: 50%;
  transform: translateX(0%) rotate(8deg);
}
</style>
