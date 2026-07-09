<template>
  <AppPageShell class="home-view-page" variant="compact" :fill="false">
    <div ref="contentRef" class="app-page-content app-page-content--media home-page-content">
      <div class="app-content-stack app-content-stack--feed">
        <header class="home-media-hero" aria-label="推荐内容">
          <div class="home-media-hero__inner">
            <div class="app-hero-main-card">
              <img
                v-if="activeFeaturedVideo?.thumbnail"
                :key="activeFeaturedVideo.id"
                :src="activeFeaturedVideo.thumbnail"
                :alt="activeFeaturedVideo.title"
                class="app-hero-main-card__img"
                loading="eager"
              />
              <Button
                v-if="heroVideo"
                type="button"
                variant="ghost"
                class="app-hero-main-card__cover-action"
                :aria-label="`播放 ${heroVideo.title}`"
                @click="openVideo(heroVideo)"
              />
              <div class="app-hero-main-card__scrim" aria-hidden="true" />

              <div class="app-hero-main-card__content">
                <p class="home-media-hero__kicker">{{ heroEyebrow }}</p>
                <h1 class="home-media-hero__title">{{ heroTitle }}</h1>
                <p v-if="heroSub" class="home-media-hero__sub">{{ heroSub }}</p>

                <div v-if="heroVideo" class="home-media-hero__actions">
                  <Button
                    type="button"
                    variant="default"
                    size="sm"
                    class="app-hero-cta"
                    @click="openVideo(heroVideo)"
                  >
                    <AppIcon name="play" class="app-play-icon size-4" />
                    {{ heroCtaLabel }}
                    <span v-if="heroRemainingText" class="app-hero-cta__meta">{{ heroRemainingText }}</span>
                  </Button>
                  <Button
                    v-if="heroChannelId"
                    type="button"
                    variant="outline"
                    size="sm"
                    class="app-hero-cta app-hero-cta--ghost"
                    @click="openSubscription(heroChannelId)"
                  >
                    查看频道
                  </Button>
                </div>
                <div v-else class="home-media-hero__actions">
                  <Button
                    type="button"
                    variant="default"
                    size="sm"
                    class="app-hero-cta"
                    @click="scrollToFirstRail"
                  >
                    <AppIcon name="chevronDown" class="size-4" />
                    开始探索
                  </Button>
                </div>
              </div>
            </div>

            <div v-if="secondaryFeaturedVideos.length > 0" class="app-hero-feature-grid" aria-label="更多推荐">
              <Button
                v-for="{ video } in secondaryFeaturedVideos"
                :key="video.id"
                type="button"
                variant="ghost"
                class="app-hero-feature-card"
                :aria-label="`播放 ${video.title}`"
                @click="openVideo(video)"
              >
                <img :src="video.thumbnail || ''" :alt="video.title" class="app-hero-feature-card__img" loading="lazy" />
                <span class="app-hero-feature-card__content">
                  <span class="app-hero-feature-card__title">{{ video.title }}</span>
                  <span class="app-hero-feature-card__meta-row">
                    <span class="app-hero-feature-card__meta">{{ video.subscriptions?.[0]?.name || video.site || '未知' }}</span>
                    <span v-if="video.duration" class="app-hero-feature-card__duration">{{ formatDuration(video.duration) }}</span>
                  </span>
                </span>
              </Button>
            </div>
          </div>
        </header>

        <SpotlightRow
          ref="spotlightRef"
          @openModal="openVideo"
          @goToSubscription="openSubscription"
        />
        <ContinueWatching
          ref="continueWatchingRef"
          @openModal="openVideo"
          @viewMore="goToContinueWatching"
          @goToSubscription="openSubscription"
          @heroChange="handleHeroChange"
        />
        <SpecialFollowVideos
          ref="specialFollowRef"
          @openModal="openVideo"
          @goToSubscription="openSubscription"
          @viewMore="goToSpecialFollowVideos"
        />
      </div>
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
import { Button } from '@/shared/ui/button'
import { formatDuration } from '@/shared/lib/dateFormat'
import { useVideoCardNavigation } from '@/features/video/composables/useVideoCardNavigation'
import { getFeaturedVideos } from '@/shared/api/video'
import { Logger } from '@/shared/lib/logger'
import type { VideoHistoryEntry, VideoListItem } from '@/features/video/types/video'

// Home view: recommendation rows + media hero. The full tabbed feed lives in VideosView (/videos).
defineOptions({ name: 'HomeView' })

const router = useRouter()
const { openVideo, openSubscription } = useVideoCardNavigation(router)

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

// Respect user's reduced-motion preference: skip auto-rotate entirely.
const prefersReducedMotion = () =>
  typeof window !== 'undefined'
  && typeof window.matchMedia === 'function'
  && window.matchMedia('(prefers-reduced-motion: reduce)').matches

const startAutoRotate = () => {
  stopAutoRotate()
  if (featuredVideos.value.length <= 1) return
  if (prefersReducedMotion()) return
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
  heroVideo.value ? '继续观看' : '今日概览',
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
  return '在右侧添加第一个订阅频道，开始建立你的观看队列。'
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

.home-page-content {
  position: relative;
  padding-top: var(--space-4);
}

/* Primary CTA on dark media surface */
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
  background: hsl(var(--primary));
  box-shadow: 0 1px 2px hsl(var(--primary) / 0.28);
  transition:
    transform var(--duration-fast) var(--ease-default),
    box-shadow var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.app-hero-cta:hover {
  box-shadow: 0 2px 8px hsl(var(--primary) / 0.32);
}

.app-hero-cta:active {
  transform: scale(0.985);
}

.app-hero-cta:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(0 0% 0% / 0.4), 0 0 0 4px hsl(var(--ring) / 0.55);
}

.app-hero-cta__meta {
  display: inline-flex;
  align-items: center;
  align-self: stretch;
  padding-left: 0.5rem;
  margin-left: 0.25rem;
  border-inline-start: 1px solid hsl(0 0% 100% / 0.25);
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  font-weight: 500;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  opacity: 0.85;
}

.app-hero-cta--ghost {
  background: hsl(0 0% 0% / 0.35);
  color: hsl(0 0% 100%);
  border: 1px solid hsl(0 0% 100% / 0.18);
  box-shadow: none;
}

.app-hero-cta--ghost:hover {
  background: hsl(0 0% 0% / 0.48);
  border-color: hsl(0 0% 100% / 0.28);
  box-shadow: none;
}

/* Single surface shell — no nested card chrome around the whole hero. */
.home-media-hero {
  position: relative;
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--app-surface-radius);
  background: hsl(var(--card) / 0.42);
}

.home-media-hero__inner {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(18rem, 0.85fr);
  align-items: stretch;
  gap: var(--space-3);
  min-height: 0;
  padding: var(--space-3);
}

.app-hero-main-card {
  position: relative;
  min-width: 0;
  aspect-ratio: 21 / 9;
  overflow: hidden;
  border-radius: var(--radius-lg);
  background: hsl(var(--muted) / 0.55);
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
  box-shadow: inset 0 0 0 3px hsl(var(--ring) / 0.55);
}

.app-hero-main-card__scrim {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  background: linear-gradient(to top, hsl(0 0% 0% / 0.88), hsl(0 0% 0% / 0.2) 55%, transparent 78%);
}

.app-hero-main-card__content {
  position: absolute;
  inset-inline: 0;
  bottom: 0;
  z-index: 3;
  padding: var(--space-5);
}

/* Status line — not a decorative section eyebrow. */
.home-media-hero__kicker {
  margin: 0 0 0.375rem;
  color: hsl(var(--primary));
  font-size: 0.75rem;
  font-weight: 650;
  line-height: 1.25;
}

.home-media-hero__title {
  margin: 0;
  max-width: 34rem;
  color: hsl(0 0% 100%);
  font-family: var(--app-heading-font);
  font-size: var(--app-hero-size);
  font-weight: var(--app-hero-weight);
  line-height: var(--app-hero-leading);
  letter-spacing: var(--app-hero-tracking);
  text-wrap: balance;
}

.home-media-hero__sub {
  margin: 0.5rem 0 0;
  max-width: 36rem;
  color: hsl(0 0% 100% / 0.78);
  font-size: 0.875rem;
  line-height: 1.55;
  text-wrap: pretty;
}

.home-media-hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.625rem;
  margin-top: var(--space-4);
}

.app-hero-feature-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
  min-width: 0;
  min-height: 0;
  height: 100%;
}

.app-hero-feature-card {
  position: relative;
  align-self: stretch;
  justify-self: stretch;
  min-width: 0;
  min-height: 0;
  width: 100%;
  height: 100%;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--radius-lg);
  background: hsl(var(--muted) / 0.45);
  cursor: pointer;
  transition:
    border-color var(--duration-fast) var(--ease-default),
    transform var(--duration-fast) var(--ease-default);
}

.app-hero-feature-card:hover {
  border-color: hsl(var(--primary) / 0.28);
  transform: translateY(-1px);
}

.app-hero-feature-card:active {
  transform: scale(0.985);
}

.app-hero-feature-card:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.5);
}

.app-hero-feature-card__img {
  display: block;
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform var(--duration-base) var(--ease-default);
}

.app-hero-feature-card:hover .app-hero-feature-card__img {
  transform: scale(1.03);
}

.app-hero-feature-card__meta-row {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
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
  bottom: 0;
  display: grid;
  gap: 0.25rem;
  padding: 2.75rem 0.75rem 0.875rem;
  color: hsl(0 0% 100%);
  background: linear-gradient(to top, hsl(0 0% 0% / 0.88), hsl(0 0% 0% / 0.4) 55%, transparent);
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
  color: hsl(0 0% 100% / 0.72);
  font-size: 0.6875rem;
  font-weight: 500;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 1100px) {
  .home-media-hero__inner {
    grid-template-columns: 1fr;
  }

  .app-hero-main-card {
    aspect-ratio: 16 / 9;
    min-height: 18rem;
  }

  .app-hero-feature-grid {
    height: auto;
  }

  .app-hero-feature-card {
    aspect-ratio: 16 / 9;
    min-height: 8.5rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .app-hero-cta,
  .app-hero-feature-card,
  .app-hero-feature-card__img {
    transition: none;
  }

  .app-hero-feature-card:hover,
  .app-hero-feature-card:hover .app-hero-feature-card__img {
    transform: none;
  }
}
</style>
