<template>
  <div ref="detachedHostRef" class="global-video-player-detached-host" aria-hidden="true"></div>

  <Teleport v-if="globalVideoPlayerSession.active && teleportTarget" :to="teleportTarget">
    <VideoPlayer
      v-if="globalVideoPlayerSession.source || globalVideoPlayerSession.externalLoading || globalVideoPlayerSession.externalError"
      ref="playerRef"
      :source="globalVideoPlayerSession.source"
      :subtitles="globalVideoPlayerSession.subtitles"
      :poster="globalVideoPlayerSession.poster"
      :title="globalVideoPlayerSession.title"
      :initialTime="globalVideoPlayerSession.initialTime"
      :has-prev="globalVideoPlayerSession.hasPrev"
      :has-next="globalVideoPlayerSession.hasNext"
      :external-error="globalVideoPlayerSession.externalError"
      :widescreen="globalVideoPlayerSession.widescreen"
      :external-loading="globalVideoPlayerSession.externalLoading"
      :external-loading-text="globalVideoPlayerSession.externalLoadingText"
      :adapter="globalVideoPlayerSession.adapter"
      :theme="globalVideoPlayerSession.theme"
      :i18n-options="{ persist: true, storageKey: 'sp-locale', applyToDocument: true, useGlobal: true }"
      :enable-global-shortcuts="true"
      :enable-click-outside-close-menu="true"
      :enable-window-resize="true"
      @play="globalVideoPlayerSession.handlers.onPlay?.()"
      @pause="globalVideoPlayerSession.handlers.onPause?.()"
      @ended="globalVideoPlayerSession.handlers.onEnded?.($event)"
      @timeupdate="globalVideoPlayerSession.handlers.onTimeUpdate?.($event)"
      @prev="globalVideoPlayerSession.handlers.onPrev?.()"
      @next="globalVideoPlayerSession.handlers.onNext?.()"
      @widescreenChange="globalVideoPlayerSession.handlers.onWidescreenChange?.($event)"
      @retry="globalVideoPlayerSession.handlers.onRetry?.()"
      @enterpictureinpicture="handleEnterPictureInPicture"
      @leavepictureinpicture="handleLeavePictureInPicture"
    />
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useGlobalVideoPlayer } from '@/composables/useGlobalVideoPlayer'
import VideoPlayer from './VideoPlayer.vue'

const detachedHostRef = ref(null)
const playerRef = ref(null)

const route = useRoute()
const router = useRouter()

const {
  globalVideoPlayerSession,
  registerGlobalVideoPlayerInstance,
  setGlobalVideoPlayerPictureInPicture,
} = useGlobalVideoPlayer()

const teleportTarget = computed(() => globalVideoPlayerSession.target || detachedHostRef.value)

watch(playerRef, (instance) => {
  registerGlobalVideoPlayerInstance(instance)
}, { immediate: true })

const handleEnterPictureInPicture = () => {
  setGlobalVideoPlayerPictureInPicture(true)
}

const handleLeavePictureInPicture = async () => {
  setGlobalVideoPlayerPictureInPicture(false)

  const currentVideoId = String(globalVideoPlayerSession.currentVideoId || '')
  if (!currentVideoId || globalVideoPlayerSession.target) {
    return
  }

  if (route.name === 'VideoPlay' && String(route.params.videoId || '') === currentVideoId) {
    return
  }

  try {
    await router.push({ name: 'VideoPlay', params: { videoId: currentVideoId } })
  } catch {}
}
</script>

<style scoped>
.global-video-player-detached-host {
  position: fixed;
  top: -9999px;
  left: -9999px;
  width: 1px;
  height: 1px;
  overflow: hidden;
  pointer-events: none;
}
</style>
