<template>
  <AppPageShell class="home-view-page" variant="compact" :fill="false">
    <div ref="contentRef" class="app-page-content app-page-content--media home-page-content">
      <div class="app-content-stack app-content-stack--feed">
        <header class="home-media-hero" :aria-label="heroAriaLabel">
          <div class="home-media-hero__inner">
            <div
              class="app-hero-main-card"
              :class="{ 'app-hero-main-card--continue': heroMode === 'continue' }"
            >
              <img
                v-if="heroThumbnail"
                :key="heroVideoKey"
                :src="heroThumbnail"
                :alt="heroTitle"
                class="app-hero-main-card__img"
                loading="eager"
              />
              <Button
                v-if="heroVideo"
                type="button"
                variant="ghost"
                class="app-hero-main-card__cover-action"
                :aria-label="`${heroCtaLabel} ${heroTitle}`"
                @click="openVideo(heroVideo)"
              />
              <div class="app-hero-main-card__scrim" aria-hidden="true" />

              <div class="app-hero-main-card__content">
                <div class="home-media-hero__topline">
                  <p class="home-media-hero__kicker">{{ heroEyebrow }}</p>
                  <button
                    v-if="heroMode === 'continue'"
                    type="button"
                    class="home-media-hero__skip"
                    @click.stop="skipContinueHero"
                  >
                    换推荐
                  </button>
                </div>

                <h1 class="home-media-hero__title">{{ heroTitle }}</h1>
                <p v-if="heroSub" class="home-media-hero__sub">{{ heroSub }}</p>

                <div
                  v-if="heroProgress"
                  class="home-media-hero__progress"
                  role="progressbar"
                  :aria-valuenow="heroProgress.percent"
                  aria-valuemin="0"
                  aria-valuemax="100"
                  :aria-label="`已观看 ${heroProgress.percent}%`"
                >
                  <div
                    class="home-media-hero__progress-fill"
                    :style="{ width: `${heroProgress.percent}%` }"
                  />
                </div>

                <div v-if="heroVideo" class="home-media-hero__actions">
                  <Button
                    type="button"
                    variant="default"
                    class="app-hero-cta"
                    @click="openVideo(heroVideo)"
                  >
                    <AppIcon name="play" class="app-play-icon size-4" />
                    {{ heroCtaLabel }}
                  </Button>
                  <button
                    v-if="heroChannelId"
                    type="button"
                    class="home-media-hero__channel-link"
                    @click.stop="openSubscription(heroChannelId)"
                  >
                    查看频道
                  </button>
                </div>
                <div v-else class="home-media-hero__actions">
                  <Button
                    type="button"
                    variant="default"
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
          :exclude-video-id="continueExcludeId"
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
import { computed, onActivated, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import SpotlightRow from '@/features/video/components/feed/SpotlightRow.vue'
import ContinueWatching from '@/features/video/components/feed/ContinueWatching.vue'
import SpecialFollowVideos from '@/features/video/components/feed/SpecialFollowVideos.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { formatDate, formatDuration } from '@/shared/lib/dateFormat'
import { useVideoCardNavigation } from '@/features/video/composables/useVideoCardNavigation'
import { getFeaturedVideos } from '@/shared/api/video'
import { Logger } from '@/shared/lib/logger'
import type { VideoHistoryEntry, VideoListItem } from '@/features/video/types/video'

// Home view: recommendation rows + media hero. The full tabbed feed lives in VideosView (/videos).
defineOptions({ name: 'HomeView' })

type HeroMode = 'continue' | 'featured' | 'empty'

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

// History-based hero (from ContinueWatching). Takes priority over featured when valid.
const historyHero = ref<VideoHistoryEntry | null>(null)
/** User dismissed this continue-hero id for the current session. */
const dismissedContinueId = ref<number | null>(null)

const handleHeroChange = (video: VideoHistoryEntry | null) => {
  if (video?.id === historyHero.value?.id) return
  historyHero.value = video
}

const skipContinueHero = () => {
  const id = historyHero.value?.id
  if (id != null) dismissedContinueId.value = id
  // Keep historyHero so rail exclusion / later refresh can re-evaluate;
  // mode gate below ignores the dismissed id.
}

const isResumable = (video: VideoHistoryEntry | null | undefined): video is VideoHistoryEntry => {
  if (!video) return false
  if (dismissedContinueId.value === video.id) return false
  return Number(video.last_position || 0) > 0
}

const activeFeaturedVideo = computed(() => featuredVideos.value[activeFeaturedIndex.value] ?? null)

const secondaryFeaturedVideos = computed(() => {
  // When continue owns the main card, all featured slots can fill the side grid.
  // When featured owns the main card, hide the active featured item from the side grid.
  const continueId = isResumable(historyHero.value) ? historyHero.value.id : null
  const hideMainFeatured = continueId == null

  return featuredVideos.value
    .map((video, index) => ({ video, index }))
    .filter(({ video, index }) => {
      if (continueId != null && video.id === continueId) return false
      if (hideMainFeatured && index === activeFeaturedIndex.value) return false
      return true
    })
    .slice(0, 4)
})

/**
 * Mode split is intentional:
 * - continue: unfinished history item owns the main card (no featured auto-rotate)
 * - featured: curated pool owns the main card
 * - empty: no media to spotlight
 */
const heroMode = computed<HeroMode>(() => {
  if (isResumable(historyHero.value)) return 'continue'
  if (activeFeaturedVideo.value) return 'featured'
  return 'empty'
})

const heroVideo = computed<VideoHistoryEntry | VideoListItem | null>(() => {
  if (heroMode.value === 'continue') return historyHero.value
  if (heroMode.value === 'featured') return activeFeaturedVideo.value
  return null
})

const heroThumbnail = computed(() => heroVideo.value?.thumbnail || null)
const heroVideoKey = computed(() => heroVideo.value?.id ?? 'empty')
const continueExcludeId = computed(() =>
  heroMode.value === 'continue' ? (historyHero.value?.id ?? null) : null,
)

// ── Progress (continue mode only; requires real position, not full duration) ──
const heroProgress = computed(() => {
  if (heroMode.value !== 'continue' || !heroVideo.value) return null
  const dur = Number(heroVideo.value.duration || 0)
  const pos = Number(heroVideo.value.last_position || 0)
  if (dur <= 0 || pos <= 0) return null
  // Treat near-start (<2%) as not-yet-meaningful progress for the bar.
  if (pos / dur < 0.02) return null
  const ratio = Math.min(1, pos / dur)
  const remaining = Math.max(0, Math.floor(dur - pos))
  if (remaining <= 0) return null
  return {
    ratio,
    percent: Math.max(1, Math.min(100, Math.round(ratio * 100))),
    remaining,
    remainingText: `剩 ${formatDuration(remaining)}`,
  }
})

// ── Auto-rotation (featured mode only) ──
const AUTO_ROTATE_INTERVAL = 6_000
let autoRotateTimer: ReturnType<typeof setInterval> | null = null

const prefersReducedMotion = () =>
  typeof window !== 'undefined'
  && typeof window.matchMedia === 'function'
  && window.matchMedia('(prefers-reduced-motion: reduce)').matches

const stopAutoRotate = () => {
  if (autoRotateTimer !== null) {
    clearInterval(autoRotateTimer)
    autoRotateTimer = null
  }
}

const startAutoRotate = () => {
  stopAutoRotate()
  if (heroMode.value === 'continue') return
  if (featuredVideos.value.length <= 1) return
  if (prefersReducedMotion()) return
  autoRotateTimer = setInterval(() => {
    if (heroMode.value === 'continue') {
      stopAutoRotate()
      return
    }
    const next = (activeFeaturedIndex.value + 1) % featuredVideos.value.length
    activeFeaturedIndex.value = next
  }, AUTO_ROTATE_INTERVAL)
}

watch(heroMode, (mode) => {
  if (mode === 'continue') stopAutoRotate()
  else startAutoRotate()
})

// ── Hero copy ──
const heroAriaLabel = computed(() => {
  if (heroMode.value === 'continue') return '继续观看'
  if (heroMode.value === 'featured') return '精选推荐'
  return '推荐内容'
})

const heroEyebrow = computed(() => {
  if (heroMode.value === 'continue') return '继续观看'
  if (heroMode.value === 'featured') return '精选'
  return '今日概览'
})

const heroTitle = computed(() =>
  heroVideo.value ? heroVideo.value.title : '今天看点什么',
)

const heroChannelName = computed(() => {
  const subs = heroVideo.value?.subscriptions
  return subs?.[0]?.name || null
})

const heroSub = computed(() => {
  if (heroMode.value === 'continue' && heroVideo.value) {
    const parts: string[] = []
    if (heroChannelName.value) parts.push(heroChannelName.value)
    if (heroProgress.value) {
      parts.push(`已看 ${heroProgress.value.percent}%`)
      parts.push(heroProgress.value.remainingText)
    } else {
      const pos = Number(heroVideo.value.last_position || 0)
      if (pos > 0) parts.push(`看到 ${formatDuration(pos)}`)
    }
    const playedAt = 'played_at' in heroVideo.value ? heroVideo.value.played_at : null
    if (playedAt) parts.push(`上次 ${formatDate(playedAt)}`)
    return parts.length > 0 ? parts.join(' · ') : '从上次离开的位置继续'
  }

  if (heroMode.value === 'featured' && heroVideo.value) {
    const parts: string[] = []
    if (heroChannelName.value) parts.push(heroChannelName.value)
    const dur = Number(heroVideo.value.duration || 0)
    if (dur > 0) parts.push(formatDuration(dur))
    return parts.length > 0 ? parts.join(' · ') : '为你挑选的内容'
  }

  return '在右侧添加第一个订阅频道，开始建立你的观看队列。'
})

const heroCtaLabel = computed(() => {
  if (heroMode.value === 'continue') return '继续播放'
  if (heroMode.value === 'featured') return '立即播放'
  return '开始观看'
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

const loadFeaturedVideos = async () => {
  try {
    const items = await getFeaturedVideos()
    if (Array.isArray(items) && items.length > 0) {
      featuredVideos.value = items.slice(0, 5)
      writeCachedFeatured(featuredVideos.value)
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
  height: 2.5rem;
  padding: 0 1.15rem;
  border: 0;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 650;
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

/*
 * Hero is media tiles on the page canvas — not a nested surface card.
 * No tray background, border, or outer padding (that reads as a boxed section).
 */
.home-media-hero {
  position: relative;
  min-height: 0;
  overflow: visible;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.home-media-hero__inner {
  display: grid;
  /*
   * Equal columns + stretch: main is 16:9 and sets the row height; the side
   * 2×2 fills that same height. With equal column widths each side cell is
   * also ~16:9 ((W-g)/2) / ((H-g)/2) ≈ W/H = 16/9.
   */
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  align-items: stretch;
  gap: var(--space-3);
  min-height: 0;
  padding: 0;
}

.app-hero-main-card {
  position: relative;
  min-width: 0;
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: var(--radius-lg);
  background: hsl(var(--muted) / 0.55);
}

.app-hero-main-card__img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
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

/* Softer scrim: keep faces readable while anchoring text at the bottom. */
.app-hero-main-card__scrim {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  background:
    linear-gradient(
      to top,
      hsl(0 0% 0% / 0.86) 0%,
      hsl(0 0% 0% / 0.52) 34%,
      hsl(0 0% 0% / 0.16) 58%,
      transparent 78%
    ),
    linear-gradient(
      to right,
      hsl(0 0% 0% / 0.28) 0%,
      transparent 42%
    );
}

.app-hero-main-card--continue .app-hero-main-card__scrim {
  background:
    linear-gradient(
      to top,
      hsl(0 0% 0% / 0.9) 0%,
      hsl(0 0% 0% / 0.55) 36%,
      hsl(0 0% 0% / 0.18) 60%,
      transparent 80%
    ),
    linear-gradient(
      to right,
      hsl(0 0% 0% / 0.32) 0%,
      transparent 48%
    );
}

.app-hero-main-card__content {
  position: absolute;
  inset-inline: 0;
  bottom: 0;
  z-index: 3;
  display: grid;
  gap: 0;
  max-width: 40rem;
  padding: var(--space-5);
  pointer-events: none;
}

.app-hero-main-card__content > * {
  pointer-events: auto;
}

.home-media-hero__topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.375rem;
}

/* Status line — mode label, not a decorative section eyebrow. */
.home-media-hero__kicker {
  margin: 0;
  color: hsl(var(--primary));
  font-size: 0.75rem;
  font-weight: 650;
  line-height: 1.25;
}

.home-media-hero__skip {
  margin: 0;
  padding: 0.2rem 0.45rem;
  border: 0;
  border-radius: var(--radius-sm);
  background: hsl(0 0% 0% / 0.28);
  color: hsl(0 0% 100% / 0.72);
  font-size: 0.6875rem;
  font-weight: 550;
  line-height: 1.2;
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.home-media-hero__skip:hover {
  background: hsl(0 0% 0% / 0.42);
  color: hsl(0 0% 100% / 0.92);
}

.home-media-hero__skip:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.55);
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
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.home-media-hero__sub {
  margin: 0.5rem 0 0;
  max-width: 36rem;
  color: hsl(0 0% 100% / 0.78);
  font-size: 0.8125rem;
  line-height: 1.5;
  text-wrap: pretty;
}

.home-media-hero__progress {
  margin-top: 0.875rem;
  width: min(100%, 18rem);
  height: 0.25rem;
  overflow: hidden;
  border-radius: 999px;
  background: hsl(0 0% 100% / 0.18);
}

.home-media-hero__progress-fill {
  height: 100%;
  border-radius: inherit;
  background: hsl(var(--primary));
  transition: width var(--duration-base) var(--ease-default);
}

.home-media-hero__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem 1rem;
  margin-top: var(--space-4);
}

.home-media-hero__channel-link {
  margin: 0;
  padding: 0.25rem 0;
  border: 0;
  background: transparent;
  color: hsl(0 0% 100% / 0.78);
  font-size: 0.8125rem;
  font-weight: 550;
  line-height: 1.2;
  text-decoration: underline;
  text-decoration-color: hsl(0 0% 100% / 0.28);
  text-underline-offset: 0.18em;
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-default),
    text-decoration-color var(--duration-fast) var(--ease-default);
}

.home-media-hero__channel-link:hover {
  color: hsl(0 0% 100%);
  text-decoration-color: hsl(0 0% 100% / 0.55);
}

.home-media-hero__channel-link:focus-visible {
  outline: none;
  border-radius: var(--radius-sm);
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.55);
}

.app-hero-feature-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
  min-width: 0;
  min-height: 0;
  width: 100%;
  /* Stretch to the main card’s 16:9 height (parent row). */
  height: 100%;
  align-self: stretch;
}

.app-hero-feature-card {
  position: relative;
  min-width: 0;
  min-height: 0;
  width: 100%;
  height: 100%;
  /* Ratio comes from the equal-column + shared-height layout, not a local aspect-ratio. */
  padding: 0;
  overflow: hidden;
  border: 0;
  border-radius: var(--radius-lg);
  background: hsl(var(--muted) / 0.35);
  cursor: pointer;
  transition: transform var(--duration-fast) var(--ease-default);
}

.app-hero-feature-card:hover {
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
  object-position: center;
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
    align-items: start;
  }

  .app-hero-main-card {
    min-height: 0;
  }

  /* Stacked: no shared row height — restore intrinsic 16:9 on side cards. */
  .app-hero-feature-grid {
    height: auto;
    grid-template-rows: auto auto;
  }

  .app-hero-feature-card {
    height: auto;
    aspect-ratio: 16 / 9;
  }
}

@media (prefers-reduced-motion: reduce) {
  .app-hero-cta,
  .app-hero-feature-card,
  .app-hero-feature-card__img,
  .home-media-hero__progress-fill {
    transition: none;
  }

  .app-hero-feature-card:hover,
  .app-hero-feature-card:hover .app-hero-feature-card__img {
    transform: none;
  }
}
</style>
