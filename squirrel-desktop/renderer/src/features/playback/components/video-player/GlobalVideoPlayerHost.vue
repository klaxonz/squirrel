<template>
  <div ref="detachedHostRef" class="fixed -top-[9999px] -left-[9999px] w-px h-px overflow-hidden pointer-events-none" aria-hidden="true" />

  <Teleport v-if="isSessionActive && teleportTarget" :to="teleportTarget">
    <VideoPlayer
      v-if="isSessionActive"
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
      @auth="handleAuthRequired"
      @clipmarkerselect="handleClipMarkerSelect"
      @clipmarkersupdated="handleClipMarkersUpdated"
      @playlistSelect="handlePlaylistSelect"
      @enterpictureinpicture="session.setPictureInPicture(true)"
      @leavepictureinpicture="handleLeavePiP"
    />
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePlayerStore } from '@/features/playback/stores/player'
import { usePlaybackSession } from '@/features/playback/composables/usePlaybackSession'
import VideoPlayer from './VideoPlayer.vue'
import { BackendPlayerAdapter } from './core/BackendPlayerAdapter'
import { buildGlobalVideoPlayerProps } from './globalPlayerProps'
import type { VideoClipMarker } from '@/features/video/types/videoClipMarker'
import type { VideoPlayerHandle, VideoEndedEvent } from '@/features/playback/types/playerSession'

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

const playerProps = computed(() => buildGlobalVideoPlayerProps(
  session.facts,
  playerStore.adapter || backendAdapter.value,
))

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
const handleAuthRequired = () => playerStore.handlers.onAuthRequired?.()
const handleClipMarkerSelect = (t: number) => playerStore.handlers.onClipMarkerSelect?.(t)
const handleClipMarkersUpdated = (m: VideoClipMarker[]) => playerStore.handlers.onClipMarkersUpdated?.(m)
const handlePlaylistSelect = (index: number) => playerStore.handlers.onPlaylistSelect?.(index)

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
