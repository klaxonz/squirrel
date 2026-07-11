<template>
  <AppPageShell class="home-view-page" variant="compact" :fill="false">
    <div ref="contentRef" class="app-page-content app-page-content--media home-page-content">
      <div class="home-dashboard">
        <section class="home-focus" :aria-label="heroAriaLabel">
          <div
            class="home-stage"
            :class="{
              'home-stage--empty': heroMode === 'empty',
            }"
          >
            <img
              v-if="heroThumbnail"
              :key="heroVideoKey"
              :src="heroThumbnail"
              :alt="heroTitle"
              class="home-stage__image"
              loading="eager"
            />
            <button
              v-if="heroVideo"
              type="button"
              class="home-stage__cover-action"
              :aria-label="`${heroCtaLabel} ${heroTitle}`"
              @click="openVideo(heroVideo)"
            ></button>
            <div class="home-stage__scrim" aria-hidden="true" />

            <div class="home-stage__topbar">
              <span class="home-stage__mode">
                <AppIcon :name="heroMode === 'continue' ? 'history' : 'play'" class="size-3.5" />
                {{ heroEyebrow }}
              </span>
              <button
                v-if="heroMode === 'continue'"
                type="button"
                class="home-stage__shuffle"
                @click.stop="skipContinueHero"
              >
                <AppIcon name="shuffle" class="size-3.5" />
                换推荐
              </button>
            </div>

            <div class="home-stage__content">
              <h1 class="home-stage__title">{{ heroTitle }}</h1>
              <p v-if="heroSub" class="home-stage__meta">{{ heroSub }}</p>

              <div v-if="heroProgress" class="home-stage__progress-group">
                <div class="home-stage__progress-copy">
                  <span>观看进度</span>
                  <span>{{ heroProgress.percent }}%</span>
                </div>
                <div
                  class="home-stage__progress"
                  role="progressbar"
                  :aria-valuenow="heroProgress.percent"
                  aria-valuemin="0"
                  aria-valuemax="100"
                  :aria-label="`已观看 ${heroProgress.percent}%`"
                >
                  <div
                    class="home-stage__progress-fill"
                    :style="{ width: `${heroProgress.percent}%` }"
                  />
                </div>
              </div>

              <div class="home-stage__actions">
                <Button
                  v-if="heroVideo"
                  type="button"
                  variant="default"
                  class="home-stage__primary-action"
                  @click="openVideo(heroVideo)"
                >
                  <AppIcon name="play" class="app-play-icon size-4" />
                  {{ heroCtaLabel }}
                </Button>
                <Button
                  v-else
                  type="button"
                  variant="default"
                  class="home-stage__primary-action"
                  @click="scrollToFirstRail"
                >
                  <AppIcon name="chevronDown" class="size-4" />
                  开始探索
                </Button>
                <Button
                  v-if="heroChannelId"
                  type="button"
                  variant="ghost"
                  class="home-stage__channel-action"
                  @click.stop="openSubscription(heroChannelId)"
                >
                  查看频道
                  <AppIcon name="chevronRight" class="size-3.5" />
                </Button>
              </div>
            </div>
          </div>

          <aside class="home-queue" aria-label="推荐队列">
            <header class="home-queue__header">
              <h2 class="home-queue__title">{{ queueTitle }}</h2>
            </header>

            <div
              v-if="showQueueLoading"
              class="home-queue__list"
              aria-label="正在加载推荐队列"
            >
              <div v-for="index in 4" :key="index" class="home-queue-skeleton">
                <AppSkeleton
                  width="8.5rem"
                  height="4.78125rem"
                  rounded="var(--radius-md)"
                  shimmer
                />
                <div class="home-queue-skeleton__body">
                  <AppSkeleton height="0.875rem" rounded="var(--radius-sm)" shimmer />
                  <AppSkeleton
                    width="76%"
                    height="0.875rem"
                    rounded="var(--radius-sm)"
                    shimmer
                  />
                  <AppSkeleton
                    width="46%"
                    height="0.6875rem"
                    rounded="var(--radius-sm)"
                    shimmer
                  />
                </div>
              </div>
            </div>

            <div v-else-if="secondaryFeaturedVideos.length > 0" class="home-queue__list">
              <button
                v-for="video in secondaryFeaturedVideos"
                :key="video.id"
                type="button"
                class="home-queue-item"
                :aria-label="`播放 ${video.title}`"
                @click="openVideo(video)"
              >
                <span class="home-queue-item__media">
                  <img
                    :src="video.thumbnail || ''"
                    :alt="video.title"
                    class="home-queue-item__image"
                    loading="lazy"
                  />
                </span>
                <span class="home-queue-item__body">
                  <span class="home-queue-item__title">{{ video.title }}</span>
                  <span class="home-queue-item__meta">
                    <span class="home-queue-item__source">
                      {{ video.subscriptions?.[0]?.name || video.site || '未知来源' }}
                    </span>
                    <span v-if="video.duration">{{ formatDuration(video.duration) }}</span>
                  </span>
                </span>
              </button>
            </div>

            <div v-else class="home-queue__empty">
              <AppIcon name="inbox" class="size-5" />
              <span>暂无更多推荐</span>
            </div>
          </aside>
        </section>

        <div class="home-rails" aria-label="首页内容">
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
          <SpotlightRow
            ref="spotlightRef"
            @openModal="openVideo"
            @goToSubscription="openSubscription"
          />
        </div>
      </div>
    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onActivated, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import SpotlightRow from '@/features/video/components/feed/SpotlightRow.vue'
import ContinueWatching from '@/features/video/components/feed/ContinueWatching.vue'
import SpecialFollowVideos from '@/features/video/components/feed/SpecialFollowVideos.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
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

// ── Hero state ──
const featuredVideos = ref<VideoListItem[]>([])
const featuredLoading = ref(true)
let featuredRequestId = 0

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

const activeFeaturedVideo = computed(() => featuredVideos.value[0] ?? null)

const secondaryFeaturedVideos = computed(() => {
  // Continue mode keeps the full curated set available in the queue.
  // Featured mode removes the item already occupying the main stage.
  const continueId = isResumable(historyHero.value) ? historyHero.value.id : null

  return featuredVideos.value
    .filter((video, index) => {
      if (continueId != null && video.id === continueId) return false
      if (continueId == null && index === 0) return false
      return true
    })
    .slice(0, 4)
})
const showQueueLoading = computed(
  () => featuredLoading.value && featuredVideos.value.length === 0,
)

/**
 * Mode split is intentional:
 * - continue: unfinished history item owns the main stage
 * - featured: curated pool owns the main stage
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
const queueTitle = computed(() =>
  heroMode.value === 'continue' ? '接下来可以看' : '更多精选',
)

// ── Actions ──
const scrollToFirstRail = () => {
  const firstRail = contentRef.value?.querySelector('.home-feed-rail')
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
  const requestId = ++featuredRequestId
  featuredLoading.value = true

  try {
    const items = await getFeaturedVideos()
    if (requestId !== featuredRequestId) return

    if (Array.isArray(items)) {
      featuredVideos.value = items.slice(0, 5)
    }
  } catch (e) {
    if (requestId === featuredRequestId) {
      Logger.warn('Failed to load featured hero videos:', e)
    }
  } finally {
    if (requestId === featuredRequestId) {
      featuredLoading.value = false
    }
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
  loadFeaturedVideos()
})
</script>

<style scoped>
.home-view-page {
  --app-page-max-width: 1760px;
}

.home-page-content {
  position: relative;
  padding-top: var(--space-3);
  padding-bottom: var(--space-8);
}

.home-dashboard {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: var(--space-6);
}

.home-focus {
  display: grid;
  grid-template-columns: minmax(0, 5fr) minmax(30rem, 3fr);
  align-items: stretch;
  gap: var(--space-5);
  min-height: 0;
}

.home-stage {
  position: relative;
  min-width: 0;
  width: 100%;
  min-height: 24rem;
  max-height: 31rem;
  aspect-ratio: 2 / 1;
  overflow: hidden;
  border-radius: var(--app-card-radius);
  background: hsl(var(--background));
  isolation: isolate;
  color: hsl(var(--app-media-on-image));
}

.home-stage__image {
  display: block;
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
}

.home-stage__cover-action {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
}

.home-stage__cover-action:focus-visible {
  outline: none;
  box-shadow: inset 0 0 0 3px hsl(var(--ring) / 0.55);
}

.home-stage__scrim {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  background:
    linear-gradient(
      to top,
      hsl(var(--overlay) / 0.88) 0%,
      hsl(var(--overlay) / 0.58) 34%,
      hsl(var(--overlay) / 0.18) 64%,
      transparent 82%
    ),
    linear-gradient(
      to right,
      hsl(var(--overlay) / 0.36) 0%,
      transparent 54%
    );
}

.home-stage--empty {
  background:
    linear-gradient(135deg, hsl(var(--card)), hsl(var(--muted) / 0.45));
  color: hsl(var(--foreground));
}

.home-stage--empty .home-stage__scrim {
  background: linear-gradient(to top, var(--app-media-scrim-soft), transparent 72%);
}

.home-stage--empty .home-stage__mode,
.home-stage--empty .home-stage__title,
.home-stage--empty .home-stage__meta,
.home-stage--empty .home-stage__progress-copy,
.home-stage--empty .home-stage__channel-action {
  color: inherit;
  text-shadow: none;
}

.home-stage--empty .home-stage__mode {
  color: hsl(var(--muted-foreground));
}

.home-stage--empty .home-stage__meta,
.home-stage--empty .home-stage__progress-copy {
  color: hsl(var(--muted-foreground));
}

.home-stage--empty .home-stage__channel-action {
  color: hsl(var(--muted-foreground));
}

.home-stage--empty .home-stage__shuffle {
  border-color: hsl(var(--border) / 0.7);
  background: hsl(var(--card) / 0.9);
  color: hsl(var(--foreground));
}

.home-stage--empty .home-stage__shuffle:hover {
  background: hsl(var(--accent));
  color: hsl(var(--foreground));
}

.home-stage--empty .home-stage__progress {
  background: hsl(var(--foreground) / 0.12);
}

.home-stage--empty .home-stage__progress-fill {
  background: hsl(var(--primary));
}

.home-stage__topbar {
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
  left: var(--space-4);
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  pointer-events: none;
}

.home-stage__mode {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: hsl(var(--app-media-on-image) / 0.9);
  font-size: 0.6875rem;
  font-weight: 650;
  line-height: 1;
  text-shadow: 0 1px 3px hsl(var(--overlay) / 0.55);
}

.home-stage__shuffle {
  display: inline-flex;
  height: 1.875rem;
  align-items: center;
  gap: 0.4rem;
  border: 1px solid hsl(var(--app-media-on-image) / 0.16);
  border-radius: var(--radius-md);
  padding: 0 0.625rem;
  background: hsl(var(--overlay) / 0.46);
  color: hsl(var(--app-media-on-image) / 0.9);
  font-size: 0.6875rem;
  font-weight: 650;
  line-height: 1;
  pointer-events: auto;
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.home-stage__shuffle:hover {
  background: hsl(var(--overlay) / 0.66);
  color: hsl(var(--app-media-on-image));
}

.home-stage__shuffle:focus-visible {
  outline: none;
  box-shadow:
    0 0 0 2px hsl(var(--background)),
    0 0 0 4px hsl(var(--ring) / 0.55);
}

.home-stage__content {
  position: absolute;
  right: var(--space-6);
  bottom: var(--space-6);
  left: var(--space-6);
  z-index: 3;
  max-width: 44rem;
  pointer-events: none;
}

.home-stage__content > * {
  pointer-events: auto;
}

.home-stage__title {
  margin: 0;
  max-width: 42rem;
  overflow: hidden;
  color: hsl(var(--app-media-on-image));
  font-family: var(--app-heading-font);
  font-size: clamp(1.5rem, 2.2vw, 1.875rem);
  font-weight: 680;
  line-height: 1.16;
  letter-spacing: -0.02em;
  text-wrap: balance;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  text-shadow: 0 1px 2px hsl(var(--overlay) / 0.4);
}

.home-stage__meta {
  margin: 0.625rem 0 0;
  max-width: 40rem;
  color: hsl(var(--app-media-on-image-muted) / 0.92);
  font-size: 0.8125rem;
  line-height: 1.5;
  text-wrap: pretty;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.home-stage__progress-group {
  width: min(100%, 20rem);
  margin-top: var(--space-4);
}

.home-stage__progress-copy {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.375rem;
  color: hsl(var(--app-media-on-image-muted) / 0.88);
  font-size: 0.6875rem;
  font-weight: 550;
  font-variant-numeric: tabular-nums;
}

.home-stage__progress {
  height: 0.25rem;
  overflow: hidden;
  border-radius: 999px;
  background: hsl(var(--app-media-on-image) / 0.18);
}

.home-stage__progress-fill {
  height: 100%;
  border-radius: inherit;
  background: hsl(var(--primary));
}

.home-stage__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-4);
}

/* Comfort 40px CTA — brand primary (Spec 2: one solid primary per view) */
.home-stage__primary-action {
  height: 2.5rem;
  gap: 0.5rem;
  padding-inline: 1rem;
  font-weight: 650;
}

.home-stage__channel-action {
  height: 2.5rem;
  gap: 0.25rem;
  padding-inline: 0.75rem;
  border-color: transparent;
  background: transparent;
  color: hsl(var(--app-media-on-image) / 0.78);
  box-shadow: none;
  font-size: 0.8125rem;
  font-weight: 600;
}

.home-stage__channel-action:hover {
  border-color: hsl(var(--app-media-on-image) / 0.12);
  background: hsl(var(--app-media-on-image) / 0.1);
  color: hsl(var(--app-media-on-image));
  box-shadow: none;
}

.home-stage__channel-action:focus-visible {
  box-shadow:
    0 0 0 2px hsl(var(--background)),
    0 0 0 4px hsl(var(--ring) / 0.5);
}

.home-queue {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-width: 0;
  min-height: 0;
  height: 100%;
  align-self: stretch;
  border-left: 1px solid hsl(var(--border) / 0.72);
  padding-left: var(--space-5);
}

.home-queue__header {
  padding: 0.125rem 0 var(--space-3);
}

.home-queue__title {
  margin: 0;
  color: hsl(var(--foreground));
  font-family: var(--app-heading-font);
  font-size: 1.125rem;
  font-weight: 650;
  line-height: 1.3;
}

.home-queue__list {
  display: grid;
  grid-template-rows: repeat(4, minmax(0, 1fr));
  min-width: 0;
  min-height: 0;
}

.home-queue-skeleton {
  display: grid;
  grid-template-columns: 8.5rem minmax(0, 1fr);
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-3) 0;
  border-top: 1px solid hsl(var(--border) / 0.5);
}

.home-queue-skeleton__body {
  display: grid;
  min-width: 0;
  gap: 0.5rem;
}

.home-queue__empty {
  display: flex;
  min-height: 0;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  font-weight: 550;
}

.home-queue-item {
  display: grid;
  grid-template-columns: 8.5rem minmax(0, 1fr);
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
  margin: 0;
  padding: var(--space-3) 0;
  border: 0;
  border-top: 1px solid hsl(var(--border) / 0.5);
  background: transparent;
  color: hsl(var(--foreground));
  text-align: left;
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-default);
}

.home-queue-item:hover {
  color: hsl(var(--foreground));
}

.home-queue-item:hover .home-queue-item__title {
  color: hsl(var(--foreground));
}

.home-queue-item:focus-visible {
  border-radius: var(--radius-md);
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.45);
}

.home-queue-item__media {
  display: block;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: var(--radius-md);
  background: hsl(var(--muted));
}

.home-queue-item__image {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
}

.home-queue-item__body {
  display: grid;
  min-width: 0;
  gap: 0.45rem;
}

.home-queue-item__title {
  display: -webkit-box;
  overflow: hidden;
  min-width: 0;
  color: currentColor;
  font-size: 0.8125rem;
  font-weight: 620;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.home-queue-item__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  min-width: 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 500;
  line-height: 1.3;
  font-variant-numeric: tabular-nums;
}

.home-queue-item__source {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.home-rails {
  display: grid;
  gap: var(--space-8);
}

:deep(.home-feed-rail) {
  min-width: 0;
  margin: 0;
  padding: 0;
  overflow: visible;
}

@media (max-width: 1360px) {
  .home-focus {
    grid-template-columns: 1fr;
  }

  .home-stage {
    min-height: 26rem;
    max-height: none;
  }

  .home-queue {
    height: auto;
    border-top: 1px solid hsl(var(--border) / 0.72);
    border-left: 0;
    padding-top: var(--space-5);
    padding-left: 0;
  }

  .home-queue__list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-template-rows: repeat(2, minmax(0, 1fr));
    column-gap: var(--space-6);
  }
}

@media (prefers-reduced-motion: reduce) {
  .home-stage__shuffle,
  .home-stage__channel-action,
  .home-queue-item {
    transition: none;
  }
}
</style>
