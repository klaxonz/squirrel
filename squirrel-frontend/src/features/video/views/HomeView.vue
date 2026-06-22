<template>
  <AppPageShell class="home-view-page" variant="compact" :fill="false">
    <div ref="contentRef" class="app-page-content app-page-content--cinema">

      <header class="app-cinema-hero-pro">
        <div
          v-if="heroBackdropUrl"
          class="app-cinema-hero-pro__backdrop"
          :style="{ backgroundImage: `url('${heroBackdropUrl}')`, opacity: heroLoaded ? 1 : 0 }"
        />
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
              继续观看
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
import { computed, onActivated, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import SpotlightRow from '@/features/video/components/feed/SpotlightRow.vue'
import ContinueWatching from '@/features/video/components/feed/ContinueWatching.vue'
import SpecialFollowVideos from '@/features/video/components/feed/SpecialFollowVideos.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { formatDuration } from '@/shared/lib/dateFormat'
import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import type { VideoHistoryEntry } from '@/features/video/types/video'

// Home view: recommendation rows + cinematic hero. The full tabbed feed lives in VideosView (/videos).
defineOptions({ name: 'HomeView' })

const router = useRouter()

// feed rows share a refresh() surface via defineExpose; minimal interface
// avoids coupling the parent to specific component instances.
const spotlightRef = ref<{ refresh?: () => void } | null>(null)
const continueWatchingRef = ref<{ refresh?: () => void } | null>(null)
const specialFollowRef = ref<{ refresh?: () => void } | null>(null)

const heroVideo = ref<VideoHistoryEntry | null>(null)
const heroLoaded = ref(false)

const handleHeroChange = (video: VideoHistoryEntry | null) => {
  if (video?.id === heroVideo.value?.id) return
  heroLoaded.value = false
  heroVideo.value = video
}

const heroBackdropUrl = computed(() => heroVideo.value?.thumbnail || '')

watch(heroBackdropUrl, (url) => {
  heroLoaded.value = false
  if (!url) return
  const img = new Image()
  img.onload = () => { heroLoaded.value = true }
  img.onerror = () => { heroLoaded.value = true }
  img.src = url
}, { immediate: true })

const heroEyebrow = computed(() =>
  heroVideo.value ? '归仓 · 继续观看' : '归仓 · 你的影音仓',
)
const heroTitle = computed(() =>
  heroVideo.value ? heroVideo.value.title : '今天看点什么',
)
const heroSub = computed(() => {
  if (heroVideo.value) {
    const who = heroVideo.value.subscriptions?.[0]?.name
    return who ? `来自 ${who} · 从你离开的地方继续` : '从你离开的地方继续这段旅程'
  }
  return '从你订阅的频道精选、未看完的内容,以及特别关注的更新中,挑出今天的观看清单。'
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
  ]).finally(() => {
    lastRefreshedAt = Date.now()
  })
}

// HomeView is kept-alive at the app root; refresh recommendation rows when
// returning to the home page, throttled to avoid hammering the API on rapid nav.
onActivated(() => {
  const now = Date.now()
  if (now - lastRefreshedAt < 30_000) return
  refresh()
})

onMounted(() => {
  // Initial load is handled by each row's onMounted; just stamp the timestamp.
  lastRefreshedAt = Date.now()
})
</script>

<style scoped>
.home-view-page {
  --app-page-max-width: 2400px;
}

.app-page-content--cinema {
  padding-top: 0;
}

.app-hero-cta {
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  height: 2.5rem;
  padding: 0 1.25rem;
  border: 0;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
  color: hsl(var(--primary-foreground));
  background: var(--brand-gradient);
  box-shadow: inset 0 0 0 1px hsl(var(--primary) / 0.35), 0 6px 18px hsl(var(--primary) / 0.18);
  transition: transform var(--duration-fast) var(--ease-spring),
              box-shadow var(--duration-fast) var(--ease-default);
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
  font-size: 0.75rem;
  font-weight: 500;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  opacity: 0.85;
}
.app-hero-cta--ghost {
  background: hsl(var(--background) / 0.72);
  color: hsl(var(--foreground) / 0.9);
  box-shadow: inset 0 0 0 1px hsl(var(--border) / 0.95), 0 4px 14px hsl(var(--foreground) / 0.08);
  backdrop-filter: blur(8px);
}
.app-hero-cta--ghost:hover {
  background: hsl(var(--background) / 0.86);
  box-shadow: inset 0 0 0 1px hsl(var(--foreground) / 0.18), 0 4px 14px hsl(var(--foreground) / 0.1);
}

.app-cinema-hero-pro__backdrop--fallback {
  background: radial-gradient(ellipse 60% 80% at 30% 40%,
    hsl(38 92% 56% / 0.12) 0%,
    hsl(28 88% 50% / 0.06) 40%,
    transparent 70%);
  filter: none;
  transform: none;
}
</style>
