<template>
  <Transition
    enter-active-class="transition-[transform,opacity] duration-300 ease-out"
    leave-active-class="transition-[transform,opacity] duration-200 ease-in"
    enter-from-class="translate-y-full opacity-0"
    leave-to-class="translate-y-full opacity-0"
  >
    <div
      v-if="store.currentTrack && (store.resolvingUrl || store.audioSrc || store.error)"
      class="music-bar"
      :class="{
        'music-bar--mini': !isMusicPage,
        'music-bar--dock': !isMusicPage && !isSidebarOpen,
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
            :volume="store.volume"
            :queue-count="store.queue.length"
            @toggle-mute="toggleMute"
            @volume="store.setVolume"
            @queue="showQueue = !showQueue"
          />
        </div>
      </template>

      <div v-else class="music-mini">
        <Button text severity="secondary" class="music-mini-track" title="打开沉浸播放" @click="openImmersive">
          <div class="music-mini-cover">
            <img v-if="store.currentTrack.cover" :src="store.currentTrack.cover" :alt="store.currentTrack.title || '封面'" />
            <AppIcon v-else name="playlistMusic" class="h-4 w-4" />
          </div>
          <div class="music-mini-text">
            <span class="music-mini-title">{{ store.currentTrack.title || '未知歌曲' }}</span>
            <span
              v-if="store.error"
              class="music-mini-error"
              :class="{ 'music-mini-error--action': needsRelogin }"
              :title="store.error"
              :role="needsRelogin ? 'link' : undefined"
              @click.stop="onMiniErrorAction"
            >{{ shortMiniError }}</span>
            <span v-else class="music-mini-artist">{{ store.currentTrack.artist || '未知歌手' }}</span>
          </div>
        </Button>

        <div class="music-mini-controls">
          <Button text severity="secondary" size="sm" icon-only :disabled="!canStep" title="上一首" aria-label="上一首" @click="store.playPrevious()">
            <AppIcon name="previous" class="h-4 w-4" />
          </Button>
          <Button

            size="sm" icon-only
            class="rounded-full"
            :disabled="store.resolvingUrl || isBuffering"
            :title="store.playing ? '暂停' : '播放'"
            :aria-label="store.playing ? '暂停' : '播放'"
            :aria-pressed="store.playing"
            @click="store.togglePlayback()"
          >
            <AppSpinner v-if="store.resolvingUrl || isBuffering" size="sm" />
            <AppIcon v-else-if="store.playing" name="pause" class="h-4 w-4" />
            <AppIcon v-else name="play" class="h-4 w-4" />
          </Button>
          <Button text severity="secondary" size="sm" icon-only :disabled="!canStep" title="下一首" aria-label="下一首" @click="store.playNext()">
            <AppIcon name="next" class="h-4 w-4" />
          </Button>
          <Button text severity="secondary" size="sm" icon-only title="播放队列" aria-label="播放队列" @click="showQueue = !showQueue">
            <AppIcon name="playlistMusic" class="h-4 w-4" />
          </Button>
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
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import { Button } from '@/shared/ui/button'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import { formatPlaybackTime as formatDuration } from '@/features/music/lib/musicFormatters'
import MusicProgressBar from './player/MusicProgressBar.vue'
import MusicBarTrackInfo from './player/MusicBarTrackInfo.vue'
import MusicBarControls from './player/MusicBarControls.vue'
import MusicBarActions from './player/MusicBarActions.vue'
import MusicQueuePanel from './player/MusicQueuePanel.vue'
import MusicImmersivePlayer from './player/MusicImmersivePlayer.vue'
import { useMusicComments } from '@/features/music/composables/useMusicComments'
import { useImmersivePlayer } from '@/features/music/composables/useImmersivePlayer'
import { useAudioElementBridge } from '@/features/music/composables/useAudioElementBridge'
import { useQueueReorder } from '@/features/music/composables/useQueueReorder'
import { useUIStore } from '@/shared/stores/ui'

const store = useMusicPlayerStore()
const uiStore = useUIStore()
const route = useRoute()
const router = useRouter()

// ponytail: the <audio> element <-> store bridge (ref registration + the
// imperative src/volume/play/error lifecycle on audioSrc change) lives in
// useAudioElementBridge. Isolating the imperative element lifecycle keeps the
// riskiest part of the player (forgotten load() / unhandled play() rejection)
// auditable in one place.
const { audioEl } = useAudioElementBridge({ store })

const isBuffering = ref(false)
const showQueue = ref(false)

const needsRelogin = computed(() => /登录|会话|鉴权|auth|login|token/i.test(String(store.error || '')))

const shortMiniError = computed(() => {
  const raw = String(store.error || '').trim()
  if (!raw) return ''
  // Recoverable path — short label + click-through login.
  if (needsRelogin.value) return '需重新登录'
  if (/网络|timeout|fetch|连接/i.test(raw)) return '网络异常'
  if (raw.length <= 16) return raw
  return '播放失败'
})

const onMiniErrorAction = () => {
  if (!needsRelogin.value) return
  void router.push({ name: 'Music', query: { view: 'profile' } })
}

// ponytail: HTML5 drag-and-drop queue reorder (drag source index + drop guard)
// lives in useQueueReorder. Any queue surface that wants drag-to-reorder can
// reuse it.
const { onDragStart, onDrop } = useQueueReorder({ store })

// ponytail: immersive overlay toggle + body-scroll-lock live in
// useImmersivePlayer. The lock is always released on close and on unmount.
const { showImmersive, openImmersive, closeImmersive } = useImmersivePlayer()

// ponytail: comments logic used to be hand-rolled inline (~50 lines mirroring
// useMusicComments). The composable now owns load/loadMore/count/switch/
// resetForNewTrack; we just drive it on track change.
const commentsState = useMusicComments()

const isMusicPage = computed(() => route.name === 'Music')
const isSidebarOpen = computed(() => uiStore.isSidebarOpen)
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
  right: 0;
  bottom: 0;
  left: 0;
  z-index: var(--z-sidebar);
  display: flex;
  width: auto;
  height: var(--app-music-player-height);
  flex-direction: column;
  overflow: hidden;
  border-top: 1px solid var(--app-hairline);
  background: hsl(var(--background) / 0.96);
  transition:
    border-color var(--duration-fast) var(--ease-default);
}

.music-bar--immersive {
  visibility: hidden;
  pointer-events: none;
}

.music-bar--mini {
  right: auto;
  left: 0;
  bottom: 0;
  z-index: var(--z-header);
  width: var(--sidebar-expanded-width);
  height: auto;
  max-width: none;
  border: 0;
  border-top: 1px solid var(--app-hairline);
  border-right: 1px solid var(--app-hairline);
  border-radius: 0;
  background: hsl(var(--background) / 0.92);
  box-shadow: none;
  overflow: hidden;
}

/*
  When the app rail is collapsed, mini controls must stay reachable.
  Dock to the workspace bottom-left instead of the inert sidebar slot.
*/
.music-bar--dock {
  right: auto;
  left: var(--space-3);
  bottom: var(--space-3);
  z-index: var(--z-header);
  width: min(22rem, calc(100vw - 1.5rem));
  transform: none;
  border: 1px solid var(--app-hairline);
  border-radius: var(--app-surface-radius);
  background: hsl(var(--background) / 0.96);
  box-shadow: var(--app-panel-shadow);
}

@media (min-width: 768px) {
  .music-bar--mini {
    left: 0;
    width: var(--sidebar-expanded-width);
  }

  .music-bar--dock {
    left: var(--space-3);
    width: min(22rem, calc(100vw - var(--workspace-offset) - 1.5rem));
  }
}

@media (prefers-reduced-motion: reduce) {
  .music-bar {
    transition: none;
  }
}

.music-bar-inner {
  display: grid;
  height: 100%;
  min-height: 0;
  align-items: center;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  padding: 2px 10vw 0;
}

/* Progress stays glued to the top edge of the full-width bar with a larger
   invisible hit target; the visual hairline is centered inside that target. */
.music-bar :deep(.music-progress-bar) {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 1;
  width: 100%;
  margin: 0;
  padding: 0;
}

.music-bar-inner :deep(.music-bar-track-info),
.music-bar-inner :deep(.music-bar-controls),
.music-bar-inner :deep(.music-bar-actions) {
  width: 100%;
  min-width: 0;
}

@media (max-width: 1336px) {
  .music-bar-inner {
    padding-inline: 5vw;
  }
}

@media (max-width: 900px) {
  .music-bar-inner {
    gap: var(--space-1);
    padding-inline: var(--space-2);
  }

  .music-bar .music-bar-time-wrap,
  .music-bar-inner :deep(.music-bar-range) {
    display: none;
  }
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
  font-size: var(--app-text-badge-size);
}

.music-bar-time {
  font-size: var(--app-text-badge-size);
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
  width: 100%;
  min-width: 0;
  padding: 0.125rem;
  justify-content: flex-start;
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
  font-size: var(--app-text-badge-size);
  color: hsl(var(--muted-foreground));
}

.music-mini-error {
  display: block;
  margin-top: 0.0625rem;
  overflow: hidden;
  color: hsl(var(--destructive));
  font-size: var(--app-text-badge-size);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-mini-error--action {
  text-decoration: underline;
  text-underline-offset: 0.1rem;
  cursor: pointer;
}

.music-mini-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  width: 100%;
  flex-shrink: 0;
}

</style>
