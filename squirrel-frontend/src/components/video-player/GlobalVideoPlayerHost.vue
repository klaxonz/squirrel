<template>
  <div ref="detachedHostRef" class="fixed -top-[9999px] -left-[9999px] w-px h-px overflow-hidden pointer-events-none" aria-hidden="true" />

  <Teleport v-if="isSessionActive && teleportTarget" :to="teleportTarget">
    <VideoPlayer
      v-if="session.facts.source || session.facts.externalLoading || session.facts.externalError"
      ref="playerRef"
      v-bind="playerProps"
      :i18n-options="{ persist: true, storageKey: 'sp-locale', applyToDocument: true, useGlobal: true }"
      :enable-global-shortcuts="true"
      :enable-click-outside-close-menu="true"
      :enable-window-resize="true"
      @play="handlePlay"
      @pause="handlePause"
      @ended="handleEnded"
      @timeupdate="handleTimeUpdate"
      @prev="handlePrev"
      @next="handleNext"
      @widescreenChange="handleWidescreenChange"
      @retry="handleRetry"
      @clipmarkerselect="handleClipMarkerSelect"
      @clipmarkersupdated="handleClipMarkersUpdated"
      @enterpictureinpicture="session.setPictureInPicture(true)"
      @leavepictureinpicture="handleLeavePiP"
    />
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePlayerStore } from '@/stores/player'
import { usePlaybackSession } from '@/composables/usePlaybackSession'
import VideoPlayer from './VideoPlayer.vue'
import { BackendPlayerAdapter } from './core/BackendPlayerAdapter'
import type { ThemeName } from './themes'
import type { VideoClipMarker } from '@/types/videoClipMarker'
import type { VideoPlayerHandle, VideoEndedEvent } from '@/types/playerSession'

// ponytail: ADR-0002 — the 22-field `playerStore.session` bag moved to
// PlaybackSession (`session.facts`). The host reads facts from the session
// singleton and wiring state (target / adapter / handlers) from the slimmed
// Pinia store. The `active` flag is gone: the session is always app-scoped, so
// "is there a user-facing video?" is now `facts.videoId !== ''`.
const playerStore = usePlayerStore()
const session = usePlaybackSession()
const detachedHostRef = ref<HTMLElement | null>(null)
const playerRef = ref<VideoPlayerHandle | null>(null)
const route = useRoute()
const router = useRouter()

const backendAdapter = shallowRef<BackendPlayerAdapter | null>(null)

const teleportTarget = computed(() => playerStore.target || detachedHostRef.value)
const isSessionActive = computed(() => !!session.facts.videoId)

const playerProps = computed(() => ({
  source: session.facts.source,
  subtitles: session.facts.subtitles,
  clipMarkers: session.facts.clipMarkers as unknown as VideoClipMarker[],
  videoId: session.facts.videoId || null,
  title: session.facts.title,
  uploader: session.facts.uploader,
  initialTime: session.facts.initialTime,
  hasPrev: session.facts.hasPrev,
  hasNext: session.facts.hasNext,
  externalError: session.facts.externalError,
  widescreen: session.facts.widescreen,
  externalLoading: session.facts.externalLoading,
  adapter: playerStore.adapter || backendAdapter.value,
  theme: (session.facts.theme || 'dark') as ThemeName,
  playlistEntries: session.facts.playlist || [],
  playlistIndex: session.facts.playlistIndex ?? -1,
}))

watch(() => session.facts.videoId, (videoId) => {
  if (videoId && !playerStore.adapter && !backendAdapter.value) {
    backendAdapter.value = new BackendPlayerAdapter()
  }
}, { immediate: true })

onUnmounted(() => {
  backendAdapter.value?.destroy()
})

// Event Handlers with safety checks
const handlePlay = () => playerStore.handlers.onPlay?.()
const handlePause = () => playerStore.handlers.onPause?.()
const handleEnded = (e: VideoEndedEvent) => playerStore.handlers.onEnded?.(e)
const handleTimeUpdate = (t: number) => playerStore.handlers.onTimeUpdate?.(t)
const handlePrev = () => playerStore.handlers.onPrev?.()
const handleNext = () => playerStore.handlers.onNext?.()
const handleWidescreenChange = (v: boolean) => playerStore.handlers.onWidescreenChange?.(v)
const handleRetry = () => playerStore.handlers.onRetry?.()
const handleClipMarkerSelect = (t: number) => playerStore.handlers.onClipMarkerSelect?.(t)
const handleClipMarkersUpdated = (m: VideoClipMarker[]) => playerStore.handlers.onClipMarkersUpdated?.(m)

watch(playerRef, (instance) => {
  playerStore.playerRef = instance
}, { immediate: true })

async function handleLeavePiP() {
  session.setPictureInPicture(false)
  const vid = session.facts.videoId
  if (vid && !playerStore.target && route.name !== 'VideoPlay') {
    router.push({ name: 'VideoPlay', params: { videoId: vid } })
  }
}
</script>
