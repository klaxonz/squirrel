<template>
  <Transition
    enter-active-class="transition-all duration-300 ease-out"
    leave-active-class="transition-all duration-200 ease-in"
    enter-from-class="translate-y-full opacity-0"
    leave-to-class="translate-y-full opacity-0"
  >
    <div
      v-if="store.currentTrack && (store.resolvingUrl || store.audioSrc || store.error)"
      class="music-bar"
      :class="{
        'music-bar--mini': !isMusicPage,
        'music-bar--immersive': showImmersive,
      }"
    >
      <audio
        ref="audioEl"
        preload="none"
        @play="store.syncPlayState()"
        @pause="store.syncPlayState()"
        @ended="store.handleEnded()"
        @error="handleAudioError"
        @timeupdate="store.syncAudioState()"
        @loadedmetadata="store.syncAudioState()"
        @waiting="isBuffering = true"
        @canplay="isBuffering = false"
        @playing="isBuffering = false"
      />

      <template v-if="isMusicPage">
        <MusicProgressBar
          :current="store.currentTime"
          :total="store.duration"
          @seek="handleSeek"
        />

        <div class="music-bar-inner">
          <MusicBarTrackInfo
            :track="store.currentTrack"
            :clickable="true"
            :error="store.error"
            @click="openImmersive"
          />

          <MusicBarControls
            :playing="store.playing"
            :shuffle="store.shuffle"
            :repeat="store.repeat"
            :can-step="canStep"
            :loading="store.resolvingUrl || isBuffering"
            @toggle="store.togglePlayback()"
            @previous="store.playPrevious()"
            @next="store.playNext()"
            @shuffle="store.shuffle = !store.shuffle"
            @repeat="cycleRepeat"
          >
            <template #time>
              <div class="music-bar-time-wrap">
                <span class="music-bar-time">{{ formatDuration(store.currentTime) }}</span>
                <span class="music-bar-time">{{ formatDuration(store.duration) }}</span>
              </div>
            </template>
          </MusicBarControls>

          <MusicBarActions
            :track="store.currentTrack"
            :liked="isTrackLiked"
            :volume="store.volume"
            :queue-count="store.queue.length"
            @like="toggleLike"
            @toggle-mute="toggleMute"
            @volume="store.setVolume"
            @queue="showQueue = !showQueue"
          />
        </div>
      </template>

      <div v-else class="music-mini">
        <button class="music-mini-track" title="打开沉浸播放" @click="openImmersive">
          <div class="music-mini-cover">
            <img v-if="store.currentTrack.cover" :src="store.currentTrack.cover" :alt="store.currentTrack.title || '封面'" />
            <AppIcon v-else name="playlistMusic" class="h-4 w-4" />
          </div>
          <div class="music-mini-text">
            <span class="music-mini-title">{{ store.currentTrack.title || '未知歌曲' }}</span>
            <span v-if="store.error" class="music-mini-error" :title="store.error">{{ store.error }}</span>
            <span v-else class="music-mini-artist">{{ store.currentTrack.artist || '未知歌手' }}</span>
          </div>
        </button>

        <div class="music-mini-controls">
          <button class="music-mini-btn" :disabled="!canStep" title="上一首" @click="store.playPrevious()">
            <AppIcon name="previous" class="h-4 w-4" />
          </button>
          <button
            class="music-mini-btn music-mini-btn--play"
            :disabled="store.resolvingUrl || isBuffering"
            title="播放/暂停"
            @click="store.togglePlayback()"
          >
            <AppIcon v-if="store.resolvingUrl || isBuffering" name="loadingSpinner" class="h-4 w-4 animate-spin" />
            <AppIcon v-else-if="store.playing" name="pause" class="h-4 w-4" />
            <AppIcon v-else name="play" class="h-4 w-4" />
          </button>
          <button class="music-mini-btn" :disabled="!canStep" title="下一首" @click="store.playNext()">
            <AppIcon name="next" class="h-4 w-4" />
          </button>
          <button class="music-mini-btn" title="播放队列" @click="showQueue = !showQueue">
            <AppIcon name="playlistMusic" class="h-4 w-4" />
          </button>
        </div>
      </div>

      <MusicQueuePanel
        :visible="showQueue"
        :queue="store.queue"
        :current-index="store.queueIndex"
        :playing="store.playing"
        @close="showQueue = false"
        @clear="store.clearQueue()"
        @play="playQueueItem"
        @remove="removeQueueItem"
        @drag-start="onDragStart"
        @drop="onDrop"
      />
    </div>
  </Transition>

  <MusicImmersivePlayer
    :visible="showImmersive"
    :track="store.currentTrack"
    :playing="store.playing"
    :loading="store.resolvingUrl"
    :shuffle="store.shuffle"
    :repeat="store.repeat"
    :can-step="canStep"
    :current-time="store.currentTime"
    :duration="store.duration"
    :audio-src="store.audioSrc"
    :error="store.error"
    :lyric-lines="store.lyricLines"
    :current-lyric-index="store.currentLyricIndex"
    :lyric-loading="store.lyricLoading"
    :lyric-error="store.lyricError"
    :comments="commentsState.comments.value"
    :comments-loading="commentsState.loading.value"
    :comments-error="commentsState.error.value"
    :comments-has-more="commentsState.hasMore.value"
    :comment-count="commentsState.count.value"
    @close="closeImmersive"
    @seek="store.seekTo"
    @seek-input="handleSeekInput"
    @toggle="store.togglePlayback()"
    @previous="store.playPrevious()"
    @next="store.playNext()"
    @toggle-shuffle="store.shuffle = !store.shuffle"
    @toggle-repeat="cycleRepeat"
    @switch-comments="switchToComments"
    @load-more-comments="loadMoreComments"
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import { formatPlaybackTime as formatDuration } from '@/features/music/lib/musicFormatters'
import MusicProgressBar from './player/MusicProgressBar.vue'
import MusicBarTrackInfo from './player/MusicBarTrackInfo.vue'
import MusicBarControls from './player/MusicBarControls.vue'
import MusicBarActions from './player/MusicBarActions.vue'
import MusicQueuePanel from './player/MusicQueuePanel.vue'
import MusicImmersivePlayer from './player/MusicImmersivePlayer.vue'
import { useMusicComments } from '@/features/music/composables/useMusicComments'
import { useMusicFavorites } from '@/features/music/composables/useMusicFavorites'
import { useImmersivePlayer } from '@/features/music/composables/useImmersivePlayer'
import { useAudioElementBridge } from '@/features/music/composables/useAudioElementBridge'
import { useQueueReorder } from '@/features/music/composables/useQueueReorder'

const store = useMusicPlayerStore()
const route = useRoute()

// ponytail: the <audio> element <-> store bridge (ref registration + the
// imperative src/volume/play/error lifecycle on audioSrc change) lives in
// useAudioElementBridge. Isolating the imperative element lifecycle keeps the
// riskiest part of the player (forgotten load() / unhandled play() rejection)
// auditable in one place.
const { audioEl } = useAudioElementBridge({ store })

const isBuffering = ref(false)
const showQueue = ref(false)

// ponytail: HTML5 drag-and-drop queue reorder (drag source index + drop guard)
// lives in useQueueReorder. Any queue surface that wants drag-to-reorder can
// reuse it.
const { onDragStart, onDrop } = useQueueReorder({ store })

// ponytail: immersive overlay toggle + body-scroll-lock live in
// useImmersivePlayer. The lock is always released on close and on unmount.
const { showImmersive, openImmersive, closeImmersive } = useImmersivePlayer()

// ponytail: track-favorite (like) state + optimistic toggle + loading guard
// live in useMusicFavorites, keyed by album_audio_id. Any track surface that
// renders a heart can reuse it.
const { isTrackLiked, toggleLike } = useMusicFavorites({
  currentTrack: computed(() => store.currentTrack),
})

// ponytail: comments logic used to be hand-rolled inline (~50 lines mirroring
// useMusicComments). The composable now owns load/loadMore/count/switch/
// resetForNewTrack; we just drive it on track change.
const commentsState = useMusicComments()

const isMusicPage = computed(() => route.name === 'Music')
const canStep = computed(() => store.queue.length > 1)

// ponytail: formatDuration is the player-surface variant (zero-padded mm:ss)
// from the shared musicFormatters lib, deduped from 5 components.

function handleSeek(time: number) {
  store.seekTo(time)
}

function handleSeekInput(time: number) {
  store.seekTo(time)
}

function handleAudioError() {
  store.markPlaybackError('音频加载失败，当前歌曲可能不可播放')
}

function cycleRepeat() {
  if (store.repeat === 'none') store.repeat = 'all'
  else if (store.repeat === 'all') store.repeat = 'one'
  else store.repeat = 'none'
}

let previousVolume = 0.7

function toggleMute() {
  if (store.volume === 0) {
    store.setVolume(previousVolume || 0.7)
  } else {
    previousVolume = store.volume
    store.setVolume(0)
  }
}

function switchToComments() {
  const track = store.currentTrack
  if (!track?.album_audio_id) return
  commentsState.switchToComments(track.album_audio_id)
}

async function loadMoreComments() {
  const track = store.currentTrack
  if (!track?.album_audio_id) return
  await commentsState.loadMore(track.album_audio_id)
}

watch(() => store.currentTrack?.album_audio_id, async (newId) => {
  if (!newId) return
  commentsState.resetForNewTrack()
  const track = store.currentTrack
  if (track?.hash) {
    await commentsState.loadCount(track.hash)
  }
})

function playQueueItem(index: number) {
  if (store.queueIndex === index) {
    store.togglePlayback()
  } else {
    const track = store.queue[index]
    if (track) {
      store.playTrack(track)
    }
  }
}

function removeQueueItem(index: number) {
  const track = store.queue[index]
  if (track) {
    store.removeFromQueue(track.hash)
  }
}
</script>

<style scoped>
.music-bar {
  position: fixed;
  bottom: 0.875rem;
  left: 1rem;
  right: 1rem;
  z-index: 60;
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 0.75rem;
  background: hsl(var(--background) / 0.94);
  backdrop-filter: blur(18px) saturate(160%);
  -webkit-backdrop-filter: blur(18px) saturate(160%);
  transition: left 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 10px 32px hsl(var(--foreground) / 0.1);
  overflow: hidden;
}

.music-bar--immersive {
  visibility: hidden;
  pointer-events: none;
}

.music-bar--mini {
  left: 0;
  right: auto;
  bottom: 0;
  width: var(--sidebar-width, 14rem);
  max-width: none;
  border-top: 1px solid hsl(var(--border) / 0.5);
  border-right: 1px solid hsl(var(--border));
  border-radius: 0;
  background: hsl(var(--background) / 0.82);
  box-shadow: none;
  overflow: hidden;
}

@media (min-width: 768px) {
  .music-bar {
    left: calc(var(--sidebar-width, 240px) + 2rem);
    right: 2rem;
    max-width: 1480px;
  }

  .music-bar--mini {
    left: 0;
  }
}

.music-bar-inner {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 0.875rem;
  min-height: 2.75rem;
  padding: 0.25rem 0.875rem 0.5rem;
}

.music-bar :deep(.music-progress-bar) {
  width: calc(100% - 1.75rem);
  margin: 0.375rem auto 0;
  padding: 0;
}

.music-bar-time-wrap {
  display: flex;
  gap: 0.25rem;
  align-items: center;
  justify-content: center;
}

.music-bar-time-wrap::after {
  content: '/';
  order: 1;
  color: hsl(var(--muted-foreground) / 0.45);
  font-size: 0.625rem;
}

.music-bar-time {
  font-size: 0.625rem;
  color: hsl(var(--muted-foreground) / 0.7);
  min-width: 2.25rem;
  text-align: center;
  font-variant-numeric: tabular-nums;
  font-weight: 500;
}

.music-bar-time:first-child {
  order: 0;
  text-align: right;
}

.music-bar-time:last-child {
  order: 2;
  text-align: left;
}

.music-mini {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem 0.625rem;
}

.music-mini-track {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
  min-width: 0;
  border: none;
  background: none;
  color: inherit;
  text-align: left;
  cursor: pointer;
  border-radius: 0.375rem;
  padding: 0.125rem;
}

.music-mini-track:hover {
  background: hsl(var(--muted) / 0.45);
}

.music-mini-cover {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.875rem;
  height: 1.875rem;
  flex-shrink: 0;
  border-radius: 0.375rem;
  overflow: hidden;
  background: hsl(var(--muted) / 0.5);
  color: hsl(var(--muted-foreground));
}

.music-mini-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-mini-text {
  min-width: 0;
  flex: 1;
}

.music-mini-title,
.music-mini-artist {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-mini-title {
  font-size: 0.75rem;
  font-weight: 650;
  color: hsl(var(--foreground));
}

.music-mini-artist {
  margin-top: 0.0625rem;
  font-size: 0.625rem;
  color: hsl(var(--muted-foreground));
}

.music-mini-error {
  display: block;
  margin-top: 0.0625rem;
  overflow: hidden;
  color: hsl(var(--destructive));
  font-size: 0.625rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-mini-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  width: 100%;
  flex-shrink: 0;
}

.music-mini-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.625rem;
  height: 1.625rem;
  border: none;
  border-radius: 0.375rem;
  background: none;
  color: hsl(var(--foreground) / 0.64);
  cursor: pointer;
}

.music-mini-btn:hover {
  background: hsl(var(--muted) / 0.65);
  color: hsl(var(--foreground));
}

.music-mini-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.music-mini-btn--play {
  border-radius: 9999px;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
}

.music-mini-btn--play:hover {
  background: hsl(var(--primary) / 0.9);
  color: hsl(var(--primary-foreground));
}


</style>
