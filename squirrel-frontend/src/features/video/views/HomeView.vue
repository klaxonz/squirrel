<template>
  <AppPageShell class="home-view-page" variant="compact" :fill="false">
    <div ref="contentRef" class="app-page-content app-page-content--cinema">

      <header class="app-cinema-hero-pro">
        <div class="app-cinema-hero-pro__backdrop app-cinema-hero-pro__backdrop--fallback" />
        <div class="app-cinema-hero-pro__scrim" />

        <div class="app-cinema-hero-pro__inner">
          <div class="app-hero-main-card">
            <img
              v-if="activeFeaturedVideo?.thumbnail"
              :key="activeFeaturedVideo.id"
              :src="activeFeaturedVideo.thumbnail"
              :alt="activeFeaturedVideo.title"
              class="app-hero-main-card__img"
              loading="eager"
            />
            <button
              v-if="heroVideo"
              type="button"
              class="app-hero-main-card__cover-action"
              :aria-label="`播放 ${heroVideo.title}`"
              @click="handleOpenModal(heroVideo)"
            />
            <div class="app-hero-main-card__scrim" />

            <div class="app-hero-main-card__content">
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
          </div>

          <div v-if="secondaryFeaturedVideos.length > 0" class="app-hero-feature-grid" aria-label="推荐轮播">
            <button
              v-for="{ video } in secondaryFeaturedVideos"
              :key="video.id"
              type="button"
              class="app-hero-feature-card"
              :aria-label="`播放 ${video.title}`"
              @click="handleOpenModal(video)"
            >
              <img :src="video.thumbnail || ''" :alt="video.title" class="app-hero-feature-card__img" loading="lazy" />
              <span class="app-hero-feature-card__content">
                <span class="app-hero-feature-card__title">{{ video.title }}</span>
                <span class="app-hero-feature-card__meta-row">
                  <span class="app-hero-feature-card__meta">{{ video.subscriptions?.[0]?.name || video.site || '未知' }}</span>
                  <span v-if="video.duration" class="app-hero-feature-card__duration">{{ formatDuration(video.duration) }}</span>
                </span>
              </span>
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
const activeFeaturedVideo = computed(() => featuredVideos.value[activeFeaturedIndex.value] ?? null)
const secondaryFeaturedVideos = computed(() =>
  featuredVideos.value
    .map((video, index) => ({ video, index }))
    .filter(({ index }) => index !== activeFeaturedIndex.value)
    .slice(0, 4),
)

const heroVideo = computed<VideoHistoryEntry | VideoListItem | null>(() => {
  const active = activeFeaturedVideo.value
  if (active?.thumbnail) return active
  return historyHero.value
})

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

// Load featured hero pool. Uses local cache to avoid fallback flash on refresh.
const loadFeaturedVideos = async () => {
  try {
    const items = await getFeaturedVideos()
    if (Array.isArray(items) && items.length > 0) {
      featuredVideos.value = items.slice(0, 5)
      writeCachedFeatured(featuredVideos.value)
      // Reset active index if it's now out of bounds
      if (activeFeaturedIndex.value >= featuredVideos.value.length) {
        activeFeaturedIndex.value = 0
      }
      startAutoRotate()
    }
  } catch (e) {
    Logger.warn('Failed to load featured hero videos:', e)
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
  padding-top: 0.75rem;
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
  color: hsl(0 0% 100%);
  background: var(--brand-gradient);
  box-shadow: inset 0 0 0 1px hsl(var(--primary) / 0.35), 0 6px 18px hsl(var(--primary) / 0.18);
  text-shadow: 0 1px 2px hsl(var(--hero-scrim) / 0.35);
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
  background: hsl(var(--hero-scrim) / 0.42);
  color: hsl(0 0% 100%);
  box-shadow: inset 0 0 0 1px hsl(0 0% 100% / 0.22), 0 4px 14px hsl(24 10% 6% / 0.22);
  backdrop-filter: blur(8px);
}
.app-hero-cta--ghost:hover {
  background: hsl(var(--hero-scrim) / 0.58);
  box-shadow: inset 0 0 0 1px hsl(0 0% 100% / 0.34), 0 6px 18px hsl(24 10% 6% / 0.28);
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

.app-cinema-hero-pro {
  min-height: 0;
  height: auto;
  padding: 0;
}

.app-cinema-hero-pro__inner {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  align-items: start;
  gap: 0.75rem;
  height: auto;
  min-height: 0;
  padding: 0;
}

.app-hero-main-card {
  position: relative;
  min-width: 0;
  aspect-ratio: 16 / 9;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: hsl(0 0% 100% / 0.08);
  box-shadow: 0 18px 42px hsl(var(--hero-scrim) / 0.42), 0 0 0 1px hsl(0 0% 100% / 0.14);
}

.app-hero-main-card__img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.app-hero-main-card__cover-action {
  position: absolute;
  inset: 0;
  z-index: 1;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
}

.app-hero-main-card__cover-action:focus-visible {
  outline: none;
  box-shadow: inset 0 0 0 3px hsl(var(--ring) / 0.58);
}

.app-hero-main-card__scrim {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  background:
    linear-gradient(to top, hsl(var(--hero-scrim) / 0.9), hsl(var(--hero-scrim) / 0.18) 58%, transparent),
    linear-gradient(to right, hsl(var(--hero-scrim) / 0.72), transparent 68%);
}

.app-hero-main-card__content {
  position: absolute;
  inset-inline: 0;
  bottom: 0;
  z-index: 3;
  padding: clamp(1.25rem, 2.1vw, 2.25rem);
}

.app-hero-feature-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  min-width: 0;
  min-height: 0;
}

.app-hero-feature-card {
  position: relative;
  min-width: 0;
  min-height: 0;
  aspect-ratio: 16 / 9;
  padding: 0;
  border: 0;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: hsl(0 0% 100% / 0.08);
  box-shadow: 0 10px 28px hsl(var(--hero-scrim) / 0.28);
  cursor: pointer;
  transition: transform var(--duration-fast) var(--ease-spring),
    box-shadow var(--duration-fast) var(--ease-default),
    opacity var(--duration-fast) var(--ease-default);
}

.app-hero-feature-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 36px hsl(var(--hero-scrim) / 0.38);
}

.app-hero-feature-card:active {
  transform: scale(0.98);
}

.app-hero-feature-card:focus-visible {
  outline: none;
  box-shadow: 0 16px 36px hsl(var(--hero-scrim) / 0.38), 0 0 0 3px hsl(var(--ring) / 0.55);
}

.app-hero-feature-card__img {
  display: block;
  position: absolute;
  inset: -1px;
  width: calc(100% + 2px);
  height: calc(100% + 2px);
  object-fit: cover;
  transition: transform var(--duration-normal) var(--ease-default), filter var(--duration-normal) var(--ease-default);
}

.app-hero-feature-card:hover .app-hero-feature-card__img {
  filter: brightness(1.08);
  transform: scale(1.04);
}

.app-hero-feature-card__meta-row {
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  min-width: 0;
}

.app-hero-feature-card__duration {
  display: inline-flex;
  flex: 0 0 auto;
  height: 1.25rem;
  align-items: center;
  border-radius: var(--radius-sm);
  padding-inline: 0.375rem;
  background: hsl(0 0% 0% / 0.72);
  color: hsl(0 0% 100%);
  font-family: var(--font-mono);
  font-size: 0.625rem;
  font-weight: 600;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.app-hero-feature-card__content {
  position: absolute;
  inset-inline: 0;
  bottom: -1px;
  display: grid;
  gap: 0.25rem;
  padding: 3.2rem 0.75rem 1.15rem;
  color: hsl(0 0% 100%);
  background: linear-gradient(to top, hsl(var(--hero-scrim) / 0.88), hsl(var(--hero-scrim) / 0.5) 48%, transparent);
  text-align: left;
}

.app-hero-feature-card__title {
  overflow: hidden;
  font-size: 0.8125rem;
  font-weight: 650;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-hero-feature-card__meta {
  overflow: hidden;
  min-width: 0;
  color: hsl(0 0% 100% / 0.7);
  font-size: 0.6875rem;
  font-weight: 500;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 960px) {
  .app-cinema-hero-pro {
    height: auto;
  }

  .app-cinema-hero-pro__inner {
    grid-template-columns: 1fr;
  }

  .app-hero-main-card {
    aspect-ratio: auto;
    min-height: 320px;
  }

  .app-hero-feature-card {
    aspect-ratio: 16 / 9;
  }
}

@media (max-width: 640px) {
  .app-page-content--cinema {
    padding-top: 0.5rem;
  }

  .app-cinema-hero-pro__inner,
  .app-hero-feature-grid {
    gap: 0.5rem;
  }

  .app-hero-main-card {
    min-height: 300px;
  }
}
</style>
