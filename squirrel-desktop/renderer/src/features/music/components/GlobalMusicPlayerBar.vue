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
        'music-bar--collapsed': isCompactSidebarPlayer,
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

      <!-- Queue popover: one root, two mutually exclusive triggers (wide bar
           via MusicBarActions, mini bar via the queue button below). reka's
           provide/inject reaches PopoverTrigger inside both child branches. -->
      <PopoverRoot :open="showQueue" @update:open="showQueue = $event">
      <template v-if="isMusicPage">
        <div class="music-bar-progress-frame">
          <MusicProgressBar
            :current="store.currentTime"
            :total="store.duration"
            @seek="handleSeek"
          />
        </div>

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
          />
        </div>
      </template>

      <template v-else>
        <MusicProgressBar
          :current="store.currentTime"
          :total="store.duration"
          @seek="handleSeek"
        />

        <div v-if="isCompactSidebarPlayer" class="music-mini music-mini--compact">
          <Button
            text severity="secondary"
            size="sm" icon-only
            class="music-mini-compact-toggle"
            :disabled="store.resolvingUrl || isBuffering"
            :title="store.playing ? '暂停' : '播放'"
            :aria-label="store.playing ? '暂停' : '播放'"
            :aria-pressed="store.playing"
            @click="store.togglePlayback()"
          >
            <span class="music-mini-cover music-mini-cover--compact">
              <img v-if="store.currentTrack.cover" :src="store.currentTrack.cover" :alt="store.currentTrack.title || '封面'" />
              <AppIcon v-else name="playlistMusic" class="h-4 w-4" />
              <span class="music-mini-compact-icon" aria-hidden="true">
                <AppSpinner v-if="store.resolvingUrl || isBuffering" size="sm" />
                <AppIcon v-else-if="store.playing" name="pause" class="h-4 w-4" />
                <AppIcon v-else name="play" class="h-4 w-4" />
              </span>
            </span>
          </Button>
        </div>

        <div v-else class="music-mini">
          <Button
            text severity="secondary"
            class="music-mini-track"
            :title="needsRelogin ? '重新登录音乐账号' : '打开沉浸播放'"
            @click="handleMiniTrackClick"
          >
            <span class="music-mini-cover">
              <img v-if="store.currentTrack.cover" :src="store.currentTrack.cover" :alt="store.currentTrack.title || '封面'" />
              <AppIcon v-else name="playlistMusic" class="h-4 w-4" />
            </span>
            <span class="music-mini-text">
              <span class="music-mini-title-row">
                <span class="music-mini-title">{{ store.currentTrack.title || '未知歌曲' }}</span>
                <AppIcon
                  v-if="store.error"
                  name="error"
                  class="music-mini-error-indicator h-3 w-3"
                  :title="store.error"
                />
              </span>
              <span class="music-mini-artist">{{ store.currentTrack.artist || '未知歌手' }}</span>
            </span>
          </Button>

          <div class="music-mini-controls">
            <Button
              text severity="secondary" size="sm" icon-only
              class="music-mini-control"
              :disabled="!canStep"
              title="上一首"
              aria-label="上一首"
              @click="store.playPrevious()"
            >
              <AppIcon name="previous" class="h-3.5 w-3.5" />
            </Button>
            <Button
              size="sm" icon-only rounded
              class="music-mini-play"
              :disabled="store.resolvingUrl || isBuffering"
              :title="store.playing ? '暂停' : '播放'"
              :aria-label="store.playing ? '暂停' : '播放'"
              :aria-pressed="store.playing"
              @click="store.togglePlayback()"
            >
              <AppSpinner v-if="store.resolvingUrl || isBuffering" size="sm" />
              <AppIcon v-else-if="store.playing" name="pause" class="h-3.5 w-3.5" />
              <AppIcon v-else name="play" class="h-3.5 w-3.5" />
            </Button>
            <Button
              text severity="secondary" size="sm" icon-only
              class="music-mini-control"
              :disabled="!canStep"
              title="下一首"
              aria-label="下一首"
              @click="store.playNext()"
            >
              <AppIcon name="next" class="h-3.5 w-3.5" />
            </Button>
            <PopoverTrigger as-child>
              <Button
                text severity="secondary" size="sm" icon-only
                class="music-mini-control"
                title="播放队列"
                aria-label="播放队列"
              >
                <AppIcon name="playlistMusic" class="h-3.5 w-3.5" />
              </Button>
            </PopoverTrigger>
          </div>
        </div>
      </template>

      <PopoverContent
        side="top"
        align="end"
        :side-offset="8"
        class="music-queue-panel"
        aria-label="播放队列"
      >
        <MusicQueuePanel
          :queue="store.queue"
          :current-index="store.queueIndex"
          :playing="store.playing"
          @clear="store.clearQueue()"
          @play="playQueueItem"
          @remove="removeQueueItem"
          @drag-start="onDragStart"
          @drop="onDrop"
        />
      </PopoverContent>
      </PopoverRoot>
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
import { PopoverRoot, PopoverTrigger } from 'reka-ui'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Spinner as AppSpinner } from '@/shared/ui/skeleton'
import { Button } from '@/shared/ui/button'
import { PopoverContent } from '@/shared/ui/popover'
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

const onMiniErrorAction = () => {
  if (!needsRelogin.value) return
  void router.push({ name: 'Music', query: { view: 'profile' } })
}

const handleMiniTrackClick = () => {
  if (needsRelogin.value) {
    onMiniErrorAction()
    return
  }
  openImmersive()
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
const isCompactSidebarPlayer = computed(() => !isMusicPage.value && !isSidebarOpen.value)
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

watch(isCompactSidebarPlayer, (compact) => {
  if (compact) showQueue.value = false
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
/* Queue popover container — lives on shared PopoverContent (sq-popover);
   padding 0 keeps the panel header flush like the old fixed panel. */
.music-queue-panel {
  width: 24rem;
  max-height: 28rem;
  padding: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.music-bar {
  position: fixed;
  right: 0;
  bottom: 0;
  left: var(--workspace-offset, 0px);
  z-index: var(--z-sidebar);
  display: flex;
  width: auto;
  height: var(--app-music-player-height);
  flex-direction: column;
  overflow: hidden;
  border-top: 1px solid hsl(var(--border));
  background: hsl(var(--card));
  transition:
    left var(--duration-base) var(--ease-out),
    border-color var(--duration-fast) var(--ease-default);
}

.music-bar--immersive {
  visibility: hidden;
  pointer-events: none;
}

.music-bar--mini {
  right: auto;
  left: 0;
  bottom: var(--sidebar-footer-height);
  z-index: var(--z-header);
  width: var(--sidebar-expanded-width);
  height: var(--sidebar-player-height);
  max-width: none;
  border: 0;
  border-top: 1px solid hsl(var(--border));
  border-right: 1px solid hsl(var(--border));
  border-radius: 0;
  background: hsl(var(--sidebar));
  box-shadow: none;
  overflow: hidden;
}

.music-bar--collapsed {
  width: var(--sidebar-collapsed-width);
}

@media (prefers-reduced-motion: reduce) {
  .music-bar {
    transition: none;
  }
}

.music-bar-inner {
  display: grid;
  width: 100%;
  max-width: var(--app-content-media-max);
  height: 100%;
  min-height: 0;
  align-items: center;
  grid-template-columns: minmax(13rem, 1fr) auto minmax(13rem, 1fr);
  gap: clamp(var(--space-4), 2vw, var(--space-7));
  margin-inline: auto;
  padding: 0.25rem var(--app-content-media-gutter) 0.125rem;
}

/* Keep the full player and its scrubber on the same centered media boundary as
   the music page. The mini player still owns the full width of the sidebar. */
.music-bar-progress-frame {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  z-index: 1;
  width: 100%;
  max-width: var(--app-content-media-max);
  margin: 0;
  margin-inline: auto;
  padding-inline: var(--app-content-media-gutter);
}

.music-bar-progress-frame :deep(.music-progress-bar),
.music-bar--mini :deep(.music-progress-bar) {
  width: 100%;
  margin: 0;
  padding: 0;
}

.music-bar--mini :deep(.music-progress-bar) {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 1;
}

.music-bar-inner :deep(.music-bar-track-info),
.music-bar-inner :deep(.music-bar-controls),
.music-bar-inner :deep(.music-bar-actions) {
  width: 100%;
  min-width: 0;
}

.music-bar-inner :deep(.music-bar-track-info) {
  max-width: 24rem;
}

.music-bar-inner :deep(.music-bar-actions) {
  max-width: 18rem;
  margin-left: auto;
}

@media (max-width: 900px) {
  .music-bar-inner {
    grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
    gap: var(--space-2);
    padding-inline: var(--space-3);
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
  display: grid;
  grid-template-rows: 2.125rem 1.75rem;
  align-items: center;
  align-content: center;
  gap: 0.125rem;
  height: 100%;
  padding: 0.3125rem 0.625rem 0.1875rem;
}

.music-mini--compact {
  display: flex;
  justify-content: center;
  padding: 0.375rem;
}

.music-mini-track {
  min-width: 0;
  width: 100%;
  height: 2.125rem;
  gap: 0.4375rem;
  padding: 0;
  justify-content: flex-start;
}

.music-mini-track :deep(.sq-button__content) {
  width: 100%;
  justify-content: flex-start;
}

.music-mini-cover {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
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
  display: block;
  min-width: 0;
  flex: 1 1 auto;
  text-align: left;
}

.music-mini-title-row,
.music-mini-title,
.music-mini-artist {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-mini-title-row {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.music-mini-title {
  display: block;
  font-size: var(--app-text-sm);
  font-weight: 650;
  color: hsl(var(--foreground));
}

.music-mini-artist {
  display: block;
  margin-top: 0.0625rem;
  font-size: var(--app-text-badge-size);
  color: hsl(var(--muted-foreground));
}

.music-mini-error-indicator {
  flex: 0 0 auto;
  color: hsl(var(--destructive));
}

.music-mini-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  padding-inline: 1.125rem;
}

.music-mini-control {
  --sq-button-height: 1.625rem;
}

.music-mini-play {
  --sq-button-height: 1.875rem;
}

.music-mini-compact-toggle {
  --sq-button-height: 2.5rem;
  padding: 0;
}

.music-mini-cover--compact {
  width: 2.25rem;
  height: 2.25rem;
}

.music-mini-cover--compact img {
  opacity: 0.72;
}

.music-mini-compact-icon {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: inherit;
  background: var(--app-media-scrim-soft);
  color: hsl(var(--app-media-on-image));
  filter: drop-shadow(0 1px 1px hsl(var(--overlay) / 0.5));
}

.music-bar--mini :deep(.music-progress-fill) {
  background: hsl(var(--primary));
}

.music-bar--mini :deep(.music-progress-tooltip) {
  display: none;
}

</style>
