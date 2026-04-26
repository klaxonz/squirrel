<template>
  <div ref="detachedHostRef" class="fixed -top-[9999px] -left-[9999px] w-px h-px overflow-hidden pointer-events-none" aria-hidden="true" />

  <Teleport v-if="playerStore.session.active && teleportTarget" :to="teleportTarget">
    <VideoPlayer
      v-if="playerStore.session.source || playerStore.session.externalLoading || playerStore.session.externalError"
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
      @enterpictureinpicture="playerStore.session.pictureInPicture = true"
      @leavepictureinpicture="handleLeavePiP"
    />
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePlayerStore } from '@/stores/player'
import VideoPlayer from './VideoPlayer.vue'
import type { ThemeName } from './themes'

const playerStore = usePlayerStore()
const detachedHostRef = ref<HTMLElement | null>(null)
const playerRef = ref(null)
const route = useRoute()
const router = useRouter()

const teleportTarget = computed(() => playerStore.session.target || detachedHostRef.value)

const playerProps = computed(() => ({
  source: playerStore.session.source as any,
  subtitles: playerStore.session.subtitles as any[],
  clipMarkers: playerStore.session.clipMarkers as any[],
  videoId: playerStore.session.currentVideoId || null,
  title: playerStore.session.title,
  initialTime: playerStore.session.initialTime,
  hasPrev: playerStore.session.hasPrev,
  hasNext: playerStore.session.hasNext,
  externalError: playerStore.session.externalError,
  widescreen: playerStore.session.widescreen,
  externalLoading: playerStore.session.externalLoading,
  adapter: playerStore.session.adapter as any,
  theme: (playerStore.session.theme || 'dark') as ThemeName
}))

// Event Handlers with safety checks
const handlePlay = () => playerStore.session.handlers.onPlay?.()
const handlePause = () => playerStore.session.handlers.onPause?.()
const handleEnded = (e: any) => playerStore.session.handlers.onEnded?.(e)
const handleTimeUpdate = (t: number) => playerStore.session.handlers.onTimeUpdate?.(t)
const handlePrev = () => playerStore.session.handlers.onPrev?.()
const handleNext = () => playerStore.session.handlers.onNext?.()
const handleWidescreenChange = (v: boolean) => playerStore.session.handlers.onWidescreenChange?.(v)
const handleRetry = () => playerStore.session.handlers.onRetry?.()
const handleClipMarkerSelect = (t: number) => playerStore.session.handlers.onClipMarkerSelect?.(t)
const handleClipMarkersUpdated = (m: any[]) => playerStore.session.handlers.onClipMarkersUpdated?.(m)

watch(playerRef, (instance) => {
  playerStore.playerRef = instance
}, { immediate: true })

async function handleLeavePiP() {
  playerStore.session.pictureInPicture = false
  const vid = playerStore.session.currentVideoId
  if (vid && !playerStore.session.target && route.name !== 'VideoPlay') {
    router.push({ name: 'VideoPlay', params: { videoId: vid } })
  }
}
</script>
