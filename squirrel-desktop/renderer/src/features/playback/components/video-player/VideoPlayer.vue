<template>
  <div
    ref="containerRef"
    class="sp-player"
    :class="[`sp-theme-${theme}`, { 'is-active': store.controlsVisible }]"
    @pointerenter="onPointerEnter"
    @pointerleave="onPointerLeave"
    @pointermove="onPointerMove"
    @pointerdown="handlePointerDown"
    @click.self="handleVideoClick"
    @dblclick.self="toggleFullscreen"
    @focus="markPlayerActive"
    @keydown="handleKeyDown"
    tabindex="0"
  >
    <VideoInfoOverlay
      :visible="showVideoInfo && !showStats && !showPlaylist && !showChapterOverlay && !upNext.showUpNext.value"
      :fullscreen="isFullscreen"
      :title="props.title"
      :uploader="props.uploader"
    />

    <SleepTimerBadge
      :fullscreen="isFullscreen"
      :visible="store.sleepTimerMinutes !== null && !showPlaylist && !showChapterOverlay"
      :remaining-text="formatSleepRemaining()"
    />

    <div v-if="store.abLoopActive" class="sp-abloop-indicator">
      <PlayerIcon name="loopAB" /> {{ t('abLoopActive') }}
      <span class="sp-abloop-times">{{ formatTime(store.loopAPoint ?? 0) }} - {{ formatTime(store.loopBPoint ?? 0) }}</span>
    </div>

    <UpNextOverlay
      :visible="upNext.showUpNext.value"
      :label="t('upNext')"
      :next-title="upNext.nextEpisodeTitle.value"
      :countdown="upNext.upNextCountdown.value"
      :start-now-label="t('startNow')"
      @start-now="upNext.startNow"
    />

    <ChapterOverlay
      :visible="showChapterOverlay"
      :chapters="normalizedChapters"
      :chapters-label="t('chapters')"
      :current-time="currentTime"
      :duration="duration"
      @close="showChapterOverlay = false"
      @select="handleChapterClick"
    />


    <!-- 视频元素 -->
    <video
      ref="videoRef"
      class="sp-video"
      :style="videoRotationStyle"
      :muted="store.muted"
      :autoplay="store.autoplay"
      :loop="store.loop"
      crossorigin="anonymous"
      playsinline
      webkit-playsinline
      :class="{ 'sp-video--hidden': isAudioOnly }"
      @click="handleVideoClick"
      @dblclick="toggleFullscreen"
    />
    <div v-if="isAudioOnly" class="sp-audio-background">
      <div class="sp-audio-visual">
        <div v-for="n in 5" :key="n" class="sp-audio-dot" :class="{ 'is-active': isPlaying }"></div>
      </div>
    </div>
    <CentralHudOverlay :hud="centralHud" :shifted="showLoadingOverlay" />

    <!-- 加载遮罩 -->
    <LoadingOverlay :visible="showLoadingOverlay" :stage-text="loadingStageText" />

    <!-- Error overlay -->
    <ErrorOverlay
      :visible="errorState.show"
      :title="errorState.title"
      :message="errorState.message"
      :can-retry="errorState.canRetry"
      :fallback-title="t('errorTitle')"
      :retry-label="t('retry')"
      @retry="handleRetry"
    />

    <!-- Stats overlay -->
    <StatsOverlay :get-stats="getStats" :visible="showStats && !errorState.show" />

    <!-- Playlist panel -->
    <PlaylistPanel
      :visible="showPlaylist"
      :entries="playlistEntries"
      :active-index="playlistIndex"
      :is-playing="isPlaying"
      @close="showPlaylist = false"
      @select="handlePlaylistSelect"
    />

    <!-- 播放器控制栏 -->
    <transition name="sp-ui-fade">
      <div v-show="store.controlsVisible" class="sp-controls-wrapper" data-player-interactive>
        <!-- 底部渐变遮罩 -->
        <div class="sp-gradient-overlay"></div>

        <div class="sp-controls-content">
          <!-- 进度条容器 -->
          <div class="sp-progress-container">
            <div ref="progressAreaRef"
                 class="sp-progress-area" data-progress-area
                 @pointerdown.prevent="onProgressPointerDown"
                 @pointermove="onProgressPointerMove"
                 @pointerleave="onProgressPointerLeave"
                 @pointerup="onProgressPointerUp"
                 @pointercancel="onProgressPointerUp">
              <div class="sp-progress-rail">
                <div class="sp-progress-buffered" :style="{ width: `${store.bufferedProgress}%` }"></div>
                <button
                  v-for="chapter in normalizedChapters"
                  :key="chapter.id"
                  type="button"
                  class="sp-chapter-marker"
                  :style="{ left: `${chapter.startPercent}%` }"
                  :title="chapter.title"
                  @pointerdown.stop="handleChapterClick(chapter.startTime)"
                />
                <button
                  v-for="marker in normalizedClipMarkers"
                  :key="marker.id"
                  type="button"
                  :data-drag-id="marker.id"
                  class="sp-clip-marker"
                  :class="{ 'is-active': activeClipMarkerId === marker.id, 'is-point': marker.isPoint, 'is-dragging': draggingMarker?.markerId === marker.id }"
                  :style="{ left: `${marker.startPercent}%`, width: `${marker.widthPercent}%`, '--marker-color': marker.color }"
                  :title="getMarkerTitle(marker)"
                  @pointerdown.stop.prevent="onMarkerPointerDown($event, marker)"
                  @click.stop="handleClipMarkerSelect(marker)"
                  @mouseenter="hoveredMarkerId = marker.id"
                  @mouseleave="hoveredMarkerId = null"
                >
                  <span class="sp-clip-marker-track"></span>
                  <span class="sp-clip-marker-dot"></span>
                  <span class="sp-clip-marker-tooltip">
                    <span class="sp-clip-marker-tooltip__title">{{ getMarkerTitle(marker) }}</span>
                    <span class="sp-clip-marker-tooltip__time">{{ getMarkerTimeText(marker) }}</span>
                    <span class="sp-clip-marker-tooltip__actions">
                      <Button severity="danger" size="sm" icon-only class="sp-clip-marker-tooltip__del" @click.stop="deleteMarkerFromPanel(marker)">×</Button>
                    </span>
                  </span>
                </button>
                <!-- 捕获中预览区域 -->
                <div
                  v-if="hasPendingSegment && duration > 0"
                  class="sp-clip-marker sp-clip-marker--pending"
                  :style="{
                    left: `${Math.min((pendingSegmentStartTime! / duration) * 100, 100)}%`,
                    width: `${Math.max(((pendingSegmentPreviewEnd - pendingSegmentStartTime!) / duration) * 100, 0.1)}%`
                  }"
                  :title="`片段 ${formatTime(pendingSegmentStartTime!)} → ${formatTime(pendingSegmentPreviewEnd)}`"
                >
                  <span class="sp-clip-marker-track"></span>
                  <span class="sp-clip-marker-dot" style="right: 0; transform: translateY(-50%)"></span>
                </div>
                <div class="sp-progress-played" :style="{ width: `${progress}%` }">
                  <div class="sp-progress-dot"></div>
                </div>
              </div>
              <!-- 进度条悬停预览 -->
              <div v-if="previewTime !== null" class="sp-preview-hint" :style="{ left: `${previewPercent}%` }">
                <div v-if="thumbnailSpriteUrl" class="sp-preview-thumbnail" :style="thumbnailSpriteStyle"></div>
                <div class="sp-preview-hint-inner">
                  {{ formatTime(previewTime) }}
                </div>
              </div>
            </div>
          </div>

          <!-- 控制栏主行 -->
          <div class="sp-controls-main">
            <div class="sp-controls-left">
              <Button v-if="props.hasPrev" text severity="secondary" size="sm" icon-only class="sp-icon-btn" @click="emit('prev')" :title="t('prev')" :aria-label="t('prev')">
                <PlayerIcon name="prev" />
              </Button>
              <Button text severity="secondary" size="sm" icon-only class="sp-icon-btn sp-btn--play" @click="togglePlay" :title="isPlaying ? t('pause') : t('play')" :aria-label="isPlaying ? t('pause') : t('play')">
                <PlayerIcon :name="isPlaying ? 'pause' : 'play'" />
              </Button>
              <Button v-if="props.hasNext" text severity="secondary" size="sm" icon-only class="sp-icon-btn" @click="emit('next')" :title="t('next')" :aria-label="t('next')">
                <PlayerIcon name="next" />
              </Button>

              <div class="sp-volume-group" :class="{ 'is-active': isVolumeScrubbing }" @pointerenter="isVolumeHovered = true" @pointerleave="isVolumeHovered = false">
                <Button text severity="secondary" size="sm" icon-only class="sp-icon-btn" @click="toggleMute" :title="t('mute')" :aria-label="isMuted ? t('unmute') : t('mute')">
                  <PlayerIcon :name="volumeIconName" />
                </Button>
                <div ref="volumeRailRef"
                     class="sp-volume-slider-wrap"
                     @pointerdown.prevent="onVolumePointerDown"
                     @pointermove="onVolumePointerMove"
                     @pointerup="onVolumePointerUp"
                     @pointercancel="onVolumePointerUp">
                  <div class="sp-volume-bar">
                    <div class="sp-volume-fill" :style="{ width: `${isMuted ? 0 : volumeFillPercent}%` }" />
                  </div>
                </div>
                <span v-if="isVolumeScrubbing || isVolumeHovered" class="sp-volume-percent">{{ volumeText }}</span>
              </div>

              <div class="sp-time-display">
                <span class="sp-time-current">{{ formatTime(currentTime) }}</span>
                <span class="sp-time-separator">/</span>
                <span class="sp-time-total">{{ formatTime(duration) }}</span>
              </div>
            </div>

            <div class="sp-controls-right">
              <button
                v-if="displayedQualities.length > 0 && qualityTagLabel"
                type="button"
                class="sp-quality-tag"
                :class="{ 'is-active': showQualityMenu }"
                @click.stop="toggleQualityMenu"
                aria-haspopup="menu"
                :aria-expanded="showQualityMenu"
              >
                {{ qualityTagLabel }}
              </button>
              <Button v-if="subtitleTracks.length > 0" text severity="secondary" size="sm" icon-only class="sp-icon-btn" @click.stop="toggleSubtitlesQuick" :title="t('subtitles')" :aria-label="t('subtitles')">
                <PlayerIcon :name="store.subtitlesEnabled ? 'subtitles' : 'subtitlesOff'" />
              </Button>
              <Button text severity="secondary" size="sm" icon-only class="sp-icon-btn sp-control--optional" :title="hasPendingSegment ? `保存片段` : t('markClip')" :aria-label="hasPendingSegment ? `保存片段` : t('markClip')" :disabled="isSavingMarker" @click.stop="hasPendingSegment ? finishSegmentCapture() : markCurrentPoint()">
                <PlayerIcon name="markClip" />
                <span v-if="hasPendingSegment" class="sp-marker-count sp-marker-count--capturing">●</span>
              </Button>
              <Button v-if="hasPlaylist" text severity="secondary" size="sm" icon-only class="sp-icon-btn sp-control--optional" @click.stop="showPlaylist = !showPlaylist" title="播放列表" aria-label="播放列表">
                <PlayerIcon name="playlist" />
              </Button>
              <Button v-if="isFullscreen" text severity="secondary" size="sm" icon-only class="sp-icon-btn" @click.stop="captureScreenshot" :title="t('screenshot')" :aria-label="t('screenshot')">
                <PlayerIcon name="screenshot" />
              </Button>
              <Button v-if="isFullscreen" text severity="secondary" size="sm" icon-only class="sp-icon-btn" @click.stop="settingsView = 'sleepTimer'; showSettingsMenu = true" :title="t('sleepTimer')" :aria-label="t('sleepTimer')">
                <PlayerIcon name="sleepTimer" />
              </Button>
              <Button v-if="isFullscreen" text severity="secondary" size="sm" icon-only class="sp-icon-btn" @click.stop="handleLoopABToggle" :title="store.abLoopActive ? t('loopClearAB') : (store.loopAPoint !== null ? t('loopSetB') : t('loopSetA'))" :aria-label="store.abLoopActive ? t('loopClearAB') : (store.loopAPoint !== null ? t('loopSetB') : t('loopSetA'))">
                <PlayerIcon name="loopAB" :style="{ opacity: store.loopAPoint !== null ? 1 : 0.5 }" />
              </Button>
              <Button text severity="secondary" size="sm" icon-only class="sp-icon-btn" @click.stop="toggleSettingsMenu" :title="t('settings')" aria-haspopup="true" :aria-expanded="showSettingsMenu" :aria-label="t('settings')">
                <PlayerIcon name="settings" />
              </Button>
              <Button text severity="secondary" size="sm" icon-only class="sp-icon-btn sp-control--optional" @click="toggleWidescreen" :title="props.widescreen ? t('exitWidescreen') : t('widescreen')">
                <PlayerIcon :name="props.widescreen ? 'widescreenExit' : 'widescreen'" />
              </Button>
              <Button text severity="secondary" size="sm" icon-only class="sp-icon-btn sp-control--compact-hide" @click="togglePictureInPicture" :title="store.pictureInPicture ? t('exitPictureInPicture') : t('pictureInPicture')">
                <PlayerIcon :name="store.pictureInPicture ? 'pipExit' : 'pip'" />
              </Button>
              <Button text severity="secondary" size="sm" icon-only class="sp-icon-btn" @click="toggleFullscreen" :title="isFullscreen ? t('exitFullscreen') : t('fullscreen')">
                <PlayerIcon :name="isFullscreen ? 'fullscreenExit' : 'fullscreen'" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 设置菜单 -->
    <SettingsMenu
      :visible="showSettingsMenu"
      :quality-menu-visible="showQualityMenu"
      :view="settingsView"
      :autoplay-next="store.autoplayNext"
      :loop="store.loop"
      :playback-rate="store.playbackRate"
      :rotation="videoRotation"
      :qualities="settingsQualities"
      :has-subtitles="subtitleTracks.length > 0"
      :subtitle-tracks="subtitleTracks"
      :subtitles-enabled="store.subtitlesEnabled"
      :active-subtitle-id="currentSubtitle?.id ?? null"
      :subtitle-color="subtitleStyle.color || '#ffffff'"
      :subtitle-bg="subtitleStyle.backgroundColor || 'rgba(0,0,0,0.8)'"
      :subtitle-position="subtitleStyle.position || 'bottom'"
      :subtitle-offset="subtitleOffset"
      :bg-opacity="subtitleStyle.backgroundOpacity ?? 0.8"
      :current-font-size="subtitleStyle.fontSize || 'medium'"
      :current-preset-label="currentPresetLabel"
      :active-preset-id="settingsActivePresetId"
      :subtitle-presets="subtitlePresets"
      :color-options="settings.subtitleColorOptions"
      :bg-options="settings.subtitleBgOptions"
      :font-size-options="settings.fontSizeOptions"
      :font-size-value="settings.subtitleStyleLabel('fontSize', subtitleStyle.fontSize || 'medium', settings.fontSizeOptions)"
      :quality-menu-label="qualityTagLabel"
      :subtitle-value="subtitleMenuLabel"
      :speeds="settings.playbackRates"
      :rotations="settings.rotationOptions"
      :show-sleep-timer="true"
      :active-sleep-timer="store.sleepTimerMinutes"
      :sleep-timer-options="sleepTimerOptions"
      :sleep-timer-value="sleepTimerLabel"
      :autoplay-next-label="t('autoplayNext')"
      :loop-label="t('loop')"
      :speed-label="t('playbackSpeed')"
      :rotate-label="t('rotate')"
      :subtitle-label="t('subtitleSettings')"
      :subtitles-off-label="t('subtitlesOff')"
      :preset-label="t('preset')"
      :font-size-label="t('fontSize')"
      :font-color-label="t('fontColor')"
      :bg-color-label="t('backgroundColor')"
      :position-label="t('position')"
      :position-bottom-label="t('positionBottom')"
      :position-top-label="t('positionTop')"
      :opacity-label="t('opacity')"
      :offset-label="t('subtitleOffset')"
      :sleep-timer-label="t('sleepTimer')"
      :sleep-timer-off-label="t('sleepTimerOff')"
      :screenshot-label="t('screenshot')"
      :sleep-timer-mins-label="(mins: number) => t('sleepTimerMinutes', { minutes: mins })"
      @navigate="settingsView = $event"
      @toggle-autoplay-next="toggleAutoplayNext"
      @toggle-loop="toggleLoop"
      @screenshot="captureScreenshot"
      @select-speed="settings.handleSpeedSelect"
      @select-rotation="handleRotationSelect"
      @select-quality="handleQualitySelect"
      @disable-subtitles="settings.handleSubtitleDisable"
      @select-subtitle="settings.handleSubtitleSelect"
      @change-subtitle-style="settings.handleSubtitleStyleChange"
      @select-preset="settings.handlePresetSelect"
      @offset-change="settings.handleSubtitleOffsetChange"
      @update-opacity="settings.handleOpacityChange"
      @select-sleep-timer="sleepTimerSelect"
    />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { formatTime } from '@/shared/lib/dateFormat'
import { usePlayer, type PlayerOptions } from './runtime/usePlayer'
import type { MediaSource, SubtitleTrack } from './core'
import type { ThemeName } from './themes'
import type { VideoClipMarker } from '@/features/video/types/videoClipMarker'
import { usePlaybackSession } from '@/features/playback/composables/usePlaybackSession'
import PlayerIcon from './PlayerIcon.vue'
import StatsOverlay from './StatsOverlay.vue'
import LoadingOverlay from './LoadingOverlay.vue'
import ErrorOverlay from './ErrorOverlay.vue'
import PlaylistPanel from './PlaylistPanel.vue'
import CentralHudOverlay from './CentralHudOverlay.vue'
import VideoInfoOverlay from './VideoInfoOverlay.vue'
import SleepTimerBadge from './SleepTimerBadge.vue'
import ChapterOverlay from './ChapterOverlay.vue'
import UpNextOverlay from './UpNextOverlay.vue'
import SettingsMenu from './SettingsMenu.vue'
import { useClipMarkers } from './composables/useClipMarkers'
import { useSleepTimer } from './composables/useSleepTimer'
import { useCentralHud } from './composables/useCentralHud'
import { useSettingsMenu } from './composables/useSettingsMenu'
import { useQualityDisplay } from './composables/useQualityDisplay'
import { useUpNext } from './composables/useUpNext'
import { useVideoRotation } from './composables/useVideoRotation'
import { useProgressScrub } from './composables/useProgressScrub'
import { usePlayerKeyboard } from './composables/usePlayerKeyboard'
import { useSourceSync } from './composables/useSourceSync'
import { useControlAutoHide } from './composables/useControlAutoHide'
import { useVolumeScrub } from './composables/useVolumeScrub'
import { useChapterThumbnails } from './composables/useChapterThumbnails'
import { usePlayerError } from './composables/usePlayerError'
import { Button } from '@/shared/ui/button'

import './themes/variables.css'
import './themes/dark.css'
import './themes/light.css'

interface Props {
  source?: MediaSource | null
  videoId?: string | number | null
  subtitles?: SubtitleTrack[]
  clipMarkers?: VideoClipMarker[]
  title?: string
  uploader?: string
  autoplay?: boolean
  adapter?: PlayerOptions['adapter'] | null
  i18nOptions?: PlayerOptions['i18nOptions']
  theme?: ThemeName
  initialTime?: number
  widescreen?: boolean
  externalLoading?: boolean
  hasPrev?: boolean
  hasNext?: boolean
  playlistEntries?: Array<{ title: string; source: MediaSource | null }>
  playlistIndex?: number
}

const props = withDefaults(defineProps<Props>(), {
  source: null,
  videoId: null,
  subtitles: () => [],
  clipMarkers: () => [],
  title: '',
  uploader: '',
  autoplay: true,
  adapter: null,
  i18nOptions: undefined,
  theme: 'dark',
  widescreen: false,
  externalLoading: false,
  hasPrev: false,
  hasNext: false,
  playlistEntries: () => [],
  playlistIndex: -1,
})

const emit = defineEmits([
  'play',
  'pause',
  'ended',
  'timeupdate',
  'error',
  'fullscreenChange',
  'retry',
  'widescreenChange',
  'enterpictureinpicture',
  'leavepictureinpicture',
  'clipmarkerselect',
  'clipmarkersupdated',
  'prev',
  'next',
  'playlistSelect',
])

const MAX_VOLUME = 200

const {
  store, videoElement, containerElement, isPlaying, currentTime, duration, volume, isMuted, isFullscreen,
  play, pause, seek, setVolume, toggleMute, setPlaybackRate, toggleFullscreen,
  togglePictureInPicture,
  subtitleTracks, currentSubtitle, subtitleStyle, subtitlePresets, subtitleOffset,
  setSubtitle, setSubtitleTracks, setSubtitleStyle, applySubtitlePreset, setSubtitleOffset,
  loadSource, theme, t, getStats, keyboardShortcuts,
  qualities, selectedCodecFamily, currentCodecFamily,
  currentQualityLabel, currentQualityId, setQuality
} = usePlayer({
  autoplay: props.autoplay,
  adapter: props.adapter ?? undefined,
  theme: props.theme,
  i18nOptions: props.i18nOptions,

  onPlay: () => emit('play'),
  onPause: () => emit('pause'),
  onEnded: () => emit('ended'),
  onError: (e) => {
    playerError.reportError(e.code, e.message)
    emit('error', e)
  },
  onTimeUpdate: (time) => emit('timeupdate', time)
})

// ponytail: error-overlay state + code→message translation live in
// usePlayerError. The onError callback above closes over `playerError` lazily
// (it only fires after setup completes), so declaring it here after usePlayer
// is safe. `errorState`/`handleRetry` are aliased for the template binding.
const playerError = usePlayerError({
  t: t as (key: string, params?: Record<string, string | number>) => string,
  onRetry: () => emit('retry'),
})
const { errorState, handleRetry } = playerError

const playbackSession = usePlaybackSession()
const playlistEntries = computed(() => playbackSession.facts.playlist || [])
const playlistIndex = computed(() => playbackSession.facts.playlistIndex ?? -1)
const hasPlaylist = computed(() => playlistEntries.value.length > 1)

const handlePlaylistSelect = (index: number) => {
  if (index >= 0 && index < playlistEntries.value.length) {
    showPlaylist.value = false
    emit('playlistSelect', index)
  }
}

const videoRef = ref<HTMLVideoElement | null>(null)
const containerRef = ref<HTMLElement | null>(null)

// Fullscreen feature state
const showVideoInfo = ref(true)
const showChapterOverlay = ref(false)
let videoInfoTimer: ReturnType<typeof setTimeout> | null = null

const { centralHud, showCentralHud } = useCentralHud()

const upNext = useUpNext({
  playlistEntries: computed(() => props.playlistEntries || []),
  playlistIndex: computed(() => props.playlistIndex ?? -1),
  onNext: () => emit('next'),
})

const clipMarkersState = useClipMarkers({
  clipMarkers: computed(() => props.clipMarkers),
  videoId: computed(() => props.videoId),
  source: computed(() => props.source),
  currentTime,
  duration,
  seek,
  showCentralHud,
  onClipMarkerSelect: (time) => emit('clipmarkerselect', time),
  onClipMarkersUpdated: (markers) => emit('clipmarkersupdated', markers),
})

const {
  sleepTimerOptions,
  sleepTimerLabel,
  formatSleepRemaining,
  handleSleepTimerSelect,
  stopSleepTimer,
} = useSleepTimer({ store, pause, showCentralHud, t: t as (key: string, params?: Record<string, string | number>) => string })

const showStats = ref(false)
const showPlaylist = ref(false)

const pendingWidescreenValue = ref<boolean | null>(null)

const showLoadingOverlay = computed(() => (store.loading || props.externalLoading) && !playerError.errorState.value.show)
const isAudioOnly = computed(() => !!props.source?.audioOnly)
const loadingStageText = computed(() => {
  if (store.loadingStage === 'fetching') return t('loading')
  if (store.loadingStage === 'buffering') return t('buffering')
  return null
})

// ponytail: settings menu state + handlers + option arrays live in
// useSettingsMenu; VideoPlayer keeps only the quality-pipeline computeds it
// shares with the rest of the controls (displayedQualities / isQualityActive /
// qualityMenuLabel / subtitleMenuLabel / currentPresetLabel).
const settings = useSettingsMenu({
  subtitleStyle,
  subtitleOffset,
  setPlaybackRate,
  setQuality,
  setSubtitle,
  setSubtitleStyle,
  setSubtitleOffset,
  applySubtitlePreset,
})
// destructure the refs + the symbols still referenced by bare name elsewhere
// in VideoPlayer (controls bar buttons, quality quick-popup, hideControls,
// keyboard speed shortcuts). The rest are accessed via `settings.*`.
const {
  showSettingsMenu,
  showQualityMenu,
  settingsView,
  closeMenus,
  toggleSettingsMenu,
  toggleQualityMenu,
  handleSpeedSelect,
  handleQualitySelect,
  playbackRates,
} = settings

const {
  videoRotation,
  videoRotationStyle,
  rotateVideo,
  handleRotationSelect,
} = useVideoRotation({
  containerRef,
  videoId: computed(() => props.videoId),
  showCentralHud,
  closeMenus,
})

// ponytail: SettingsMenu expects qualities as {id,label,active}; map the shared
// displayedQualities + isQualityActive into that shape instead of duplicating.
const settingsQualities = computed(() =>
  displayedQualities.value.map((q) => ({ id: q.id, label: q.label, active: isQualityActive(q) })),
)
const settingsActivePresetId = computed(() => {
  const active = subtitlePresets.find((p) => settings.isPresetActive(p))
  return active ? active.id : null
})
const progress = computed(() => duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0)

const {
  hoveredMarkerId,
  hasPendingSegment,
  pendingSegmentStartTime,
  pendingSegmentEndTime,
  pendingSegmentPreviewEnd,
  isSavingMarker,
  draggingMarker,
  normalizedClipMarkers,
  activeClipMarkerId,
  getMarkerTitle,
  getMarkerTimeText,
  markCurrentPoint,
  startSegmentCapture,
  finishSegmentCapture,
  cancelSegmentCapture,
  deleteMarkerFromPanel,
  onMarkerPointerDown,
  handleClipMarkerSelect,
  captureCurrentFrameDataUrl,
  releaseMarkerPointerCapture,
  removeMarkerDragListeners,
} = clipMarkersState

// ponytail: progress-rail pointer scrub (preview + seek + marker-segment sync)
// lives in useProgressScrub; VideoPlayer keeps only the `isScrubbing` watch that
// suppresses control auto-hide during a drag, and hideControls() clearing the
// preview via clearPreview().
const {
  progressAreaRef,
  previewTime,
  previewPercent,
  isScrubbing,
  onProgressPointerDown,
  onProgressPointerMove,
  onProgressPointerUp,
  onProgressPointerLeave,
  clearPreview,
  cleanup: cleanupProgressScrub,
} = useProgressScrub({
  duration,
  pendingSegmentEndTime,
  hasPendingSegment,
  seek,
})

// ponytail: chapter normalisation + thumbnail-sprite frame math live in
// useChapterThumbnails. Declared after useProgressScrub because the sprite
// frame depends on the scrub `previewTime`.
const {
  normalizedChapters,
  thumbnailSpriteUrl,
  thumbnailSpriteStyle,
  handleChapterClick,
} = useChapterThumbnails({
  source: computed(() => props.source),
  duration,
  previewTime,
  seek,
})

// ponytail: volume display computeds + pointer-scrub + user-HUD suppression
// live in useVolumeScrub. `setUserVolume` is also consumed by the keyboard
// shortcut table, so it stays destructured here.
const {
  volumeRailRef,
  cleanup: cleanupVolumeScrub,
  isVolumeScrubbing,
  isVolumeHovered,
  volumeIconName,
  volumeText,
  volumeFillPercent,
  setUserVolume,
  onVolumePointerDown,
  onVolumePointerMove,
  onVolumePointerUp,
} = useVolumeScrub({
  volume,
  isMuted,
  setVolume,
  showCentralHud,
  maxVolume: MAX_VOLUME,
})

// ponytail: quality display pipeline (codec matching, dedup/score, active
// check, labels) lives in useQualityDisplay; VideoPlayer just consumes the
// derived values. Behavior is byte-identical to the former inline block.
const {
  displayedQualities,
  qualityTagLabel,
  qualityMenuLabel: _qualityMenuLabel,
  isQualityActive,
} = useQualityDisplay({
  qualities,
  selectedCodecFamily,
  currentCodecFamily,
  currentQualityId,
  currentQualityLabel,
  t: t as (key: string, params?: Record<string, string | number>) => string,
})
const subtitleMenuLabel = computed(() => {
  if (!store.subtitlesEnabled || !currentSubtitle.value) return t('subtitlesOff')
  return currentSubtitle.value.label
})

// ponytail: source/initialTime/resume-after-swap sync lives in useSourceSync.
// VideoPlayer keeps the videoRef<->videoElement + containerRef<->containerElement
// bridge watches (those are usePlayer wiring, not source logic) and only injects
// a small onSourceChange callback to clear the error overlay when the source
// identity changes.
const { cleanup: cleanupSourceSync } = useSourceSync({
  videoRef,
  source: computed(() => props.source),
  initialTime: computed(() => props.initialTime),
  autoplay: computed(() => props.autoplay),
  currentTime,
  isPlaying,
  hasStartedPlayback: computed(() => store.hasStartedPlayback),
  loadSource,
  play,
  pause,
  seek,
  onSourceChange: () => { playerError.clear() },
})

watch(videoRef, (el) => { videoElement.value = el }, { immediate: true })
watch(containerRef, (el) => { containerElement.value = el }, { immediate: true })
watch(() => props.subtitles, (ts) => { setSubtitleTracks(ts || []) }, { immediate: true, deep: true })

// 修复"视频在正常播放但错误遮罩仍盖在上面"的问题：
// 引擎的错误恢复链（HLS recoverMediaError / DASH attachSource / 重试）经常能在底层把播放救回来，
// 但 reportFatalError 已经触发过 onError → error overlay shown。这里在视频真正重新进入播放态时兜底清除遮罩。
watch(() => store.playing, (playing) => {
  if (playing && errorState.value.show) {
    playerError.clear()
  }
})

const togglePlay = () => isPlaying.value ? pause() : play()
const currentPresetLabel = computed(() => {
  const active = subtitlePresets.find((p) => settings.isPresetActive(p))
  return active ? active.label : t('custom')
})
const toggleWidescreen = async () => {
  const nextWidescreen = !props.widescreen

  if (isFullscreen.value) {
    pendingWidescreenValue.value = nextWidescreen
    await toggleFullscreen()

    if (pendingWidescreenValue.value !== null && typeof document !== 'undefined' && !document.fullscreenElement) {
      const resolvedWidescreen = pendingWidescreenValue.value
      pendingWidescreenValue.value = null
      emit('widescreenChange', resolvedWidescreen)
    }

    return
  }

  emit('widescreenChange', nextWidescreen)
}
const toggleAutoplayNext = () => store.setAutoplayNext(!store.autoplayNext)
const toggleLoop = () => store.setLoop(!store.loop)
const toggleSubtitlesQuick = () => {
  if (store.subtitlesEnabled) {
    setSubtitle(null)
    return
  }

  const nextTrack = currentSubtitle.value
    || subtitleTracks.value.find((track) => track.default)
    || subtitleTracks.value[0]
    || null

  setSubtitle(nextTrack)
}
// ponytail: the 3s idle auto-hide timer + show/hide/sync contract lives in
// useControlAutoHide. showControls additionally drives the fullscreen
// info-overlay auto-fade (a video-info concern, not control visibility), so we
// wrap it here to keep that side-effect co-located with the overlay it owns.
const { showControls: showControlsBase, hideControls, syncHideTimer, clearHideTimer } = useControlAutoHide({
  store,
  isPlaying,
  isScrubbing,
  clearPreview,
  closeMenus,
})
const showControls = () => {
  showControlsBase()
  if (isFullscreen.value) {
    showVideoInfo.value = true
    if (videoInfoTimer) clearTimeout(videoInfoTimer)
    videoInfoTimer = setTimeout(() => { showVideoInfo.value = false }, 5000)
  }
}
const handleVideoClick = () => {
  togglePlay()
}
const onPointerEnter = () => {
  showControls()
}

const onPointerMove = (event: PointerEvent) => {
  showControls()
  if (isFullscreen.value && containerRef.value) {
    const rect = containerRef.value.getBoundingClientRect()
    const y = event.clientY - rect.top
    if (y < 60) {
      showChapterOverlay.value = true
    } else if (y > 200) {
      showChapterOverlay.value = false
    }
  }
}

const onPointerLeave = () => {
  if (!isScrubbing.value) hideControls()
}

const markPlayerActive = () => {}
const handlePointerDown = () => {}

// ===== Fullscreen features =====

const sleepTimerSelect = (mins: number | null) => {
  handleSleepTimerSelect(mins)
  settingsView.value = 'main'
  showSettingsMenu.value = false
}

const captureScreenshot = () => {
  const dataUrl = captureCurrentFrameDataUrl(videoRef)
  if (!dataUrl) {
    showCentralHud('error', t('errorMedia'), 'play')
    return
  }
  const link = document.createElement('a')
  link.download = `screenshot-${Date.now()}.jpg`
  link.href = dataUrl
  link.click()
  showCentralHud('screenshot', t('screenshotSaved'), 'check')
}

const handleLoopABToggle = () => {
  if (store.abLoopActive) {
    store.setAbLoopActive(false)
    store.setLoopAPoint(null)
    store.setLoopBPoint(null)
    showCentralHud('loopAB', t('loopClearAB'), 'loop')
    return
  }
  if (store.loopAPoint === null) {
    store.setLoopAPoint(currentTime.value)
    showCentralHud('loopAB', t('loopSetA'), 'skipBackward')
    return
  }
  if (store.loopAPoint !== null && store.loopBPoint === null) {
    const bTime = currentTime.value
    if (bTime <= store.loopAPoint) {
      showCentralHud('error', 'B must be after A', 'play')
      return
    }
    store.setLoopBPoint(bTime)
    store.setAbLoopActive(true)
    showCentralHud('loopAB', t('abLoopActive'), 'loop')
    return
  }
}

// ponytail: keyboard-shortcut dispatch table + its window keydown listener
// lifecycle live in usePlayerKeyboard. VideoPlayer only injects the action
// surface (transport, volume, markers, speed, loop, playlist nav). Declared
// after captureScreenshot/handleSpeedSelect/etc. so all action consts are past
// their TDZ at call time.
const { handleKeyDown } = usePlayerKeyboard({
  keyboardShortcuts,
  currentTime,
  volume,
  isFullscreen,
  hasPendingSegment,
  hasPrev: computed(() => props.hasPrev),
  hasNext: computed(() => props.hasNext),
  store,
  playbackRates,
  t: t as (key: string, params?: Record<string, string | number>) => string,
  showCentralHud,
  toggleStats: () => { showStats.value = !showStats.value },
  togglePlay,
  toggleFullscreen,
  rotateVideo,
  seek,
  setUserVolume,
  toggleSubtitlesQuick,
  captureScreenshot,
  startSegmentCapture,
  finishSegmentCapture,
  cancelSegmentCapture,
  markCurrentPoint,
  handleSpeedSelect,
  onPrev: () => emit('prev'),
  onNext: () => emit('next'),
  maxVolume: MAX_VOLUME,
})


watch(isPlaying, (playing) => {
  if (!playing) {
    showControls()
    return
  }

  showControls()
})

// AB loop check
watch(() => currentTime.value, (t) => {
  if (!store.abLoopActive || store.loopBPoint === null) return
  if (t >= store.loopBPoint) {
    seek(store.loopAPoint ?? 0)
  }
})

// Up next countdown
watch(() => currentTime.value, (t) => {
  if (!isFullscreen.value || !isPlaying.value) {
    upNext.clear()
    return
  }
  if (duration.value <= 0) return
  upNext.maybeStart(duration.value - t)
})

// Video info timer
watch(showVideoInfo, (v) => {
  if (!v) return
  if (videoInfoTimer) clearTimeout(videoInfoTimer)
  videoInfoTimer = setTimeout(() => { showVideoInfo.value = false }, 5000)
})

watch(isFullscreen, (fullscreen) => {
  emit('fullscreenChange', fullscreen)

  if (fullscreen) {
    showVideoInfo.value = true
    if (videoInfoTimer) clearTimeout(videoInfoTimer)
    videoInfoTimer = setTimeout(() => { showVideoInfo.value = false }, 5000)
  } else {
    showVideoInfo.value = false
    if (videoInfoTimer) clearTimeout(videoInfoTimer)
    showChapterOverlay.value = false
  }

  if (fullscreen || pendingWidescreenValue.value === null) return

  const nextWidescreen = pendingWidescreenValue.value
  pendingWidescreenValue.value = null
  emit('widescreenChange', nextWidescreen)
})

watch(() => store.pictureInPicture, (inPictureInPicture, previousValue) => {
  if (inPictureInPicture === previousValue) return
  emit(inPictureInPicture ? 'enterpictureinpicture' : 'leavepictureinpicture')
})

watch(isScrubbing, (scrubbing) => {
  if (scrubbing) {
    clearHideTimer()
    return
  }

  syncHideTimer()
})

// When the window regains visibility (e.g. after Alt-Tab or minimize), the
// <video> element may have dropped its last decoded frame during background
// throttling and render black even though playback continues. Nudge it by
// re-seeking to the current time to force a fresh frame paint.
const handleVisibilityChange = () => {
  if (document.hidden) return
  const video = videoRef.value
  if (!video || video.paused || video.ended) return
  const t = video.currentTime
  if (!Number.isFinite(t)) return
  // Re-assigning currentTime (even to the same value) triggers a seek that
  // forces the decoder to repaint the current frame.
  video.currentTime = t
}

onMounted(() => {
  document.addEventListener('visibilitychange', handleVisibilityChange)
})
onUnmounted(() => {
  clearHideTimer()
  cleanupSourceSync()
  releaseMarkerPointerCapture()
  cleanupProgressScrub()
  cleanupVolumeScrub()
  removeMarkerDragListeners()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  stopSleepTimer()
  upNext.clear()
  if (videoInfoTimer) clearTimeout(videoInfoTimer)
})

defineExpose({ play, pause, seek, toggleFullscreen, togglePictureInPicture })
</script>

<style scoped>
.sp-player {
  position: absolute;
  inset: 0;
  container-name: video-player;
  container-type: inline-size;
  background: #000;
  border: none;
  outline: none;
  box-shadow: none;
  overflow: hidden;
  cursor: none;
  font-family: var(--sp-font-family);
  user-select: none;
  letter-spacing: 0;
}

.sp-player:focus,
.sp-player:focus-visible {
  outline: none;
  box-shadow: none;
}

.sp-player.is-active {
  cursor: pointer;
}

.sp-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  transform-origin: center center;
  transition: transform var(--duration-normal) var(--ease-default);
}

.sp-video--hidden {
  opacity: 0;
  pointer-events: none;
}

.sp-audio-background {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #101010;
  z-index: 1;
}

.sp-audio-visual {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 8px;
  height: 60px;
}

.sp-audio-dot {
  width: 6px;
  height: 20px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
  transition: height var(--duration-normal) ease;
}

.sp-audio-dot.is-active {
  background: var(--sp-primary, #d3d4d8);
  animation: audio-bar-bounce 1.2s ease-in-out infinite;
}

.sp-audio-dot:nth-child(1).is-active { animation-delay: 0s; }
.sp-audio-dot:nth-child(2).is-active { animation-delay: 0.1s; }
.sp-audio-dot:nth-child(3).is-active { animation-delay: 0.2s; }
.sp-audio-dot:nth-child(4).is-active { animation-delay: 0.3s; }
.sp-audio-dot:nth-child(5).is-active { animation-delay: 0.4s; }

@keyframes audio-bar-bounce {
  0%, 100% { height: 12px; }
  50% { height: 36px; }
}

/* HUD 角标覆盖层 */
.sp-hud-overlay {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 10;
  pointer-events: none;
}

.sp-hud-tag {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  background: rgba(0, 0, 0, 0.55);
  border: 1px solid rgba(var(--sp-primary-rgb), 0.25);
  border-radius: 4px;
}

.sp-hud-dot {
  width: 6px;
  height: 6px;
  background: var(--sp-primary);
  border-radius: 50%;
}

.sp-hud-dot.is-pulsing {
  animation: hud-pulse 1.5s infinite;
}

@keyframes hud-pulse {
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.4); opacity: 0.6; }
  100% { transform: scale(1); opacity: 1; }
}

.sp-hud-text {
  color: var(--sp-primary);
  font-size: var(--app-text-badge-size);
  font-family: var(--sp-font-mono);
  letter-spacing: 0;
  font-weight: 700;
}

.sp-hud-separator {
  opacity: 0.2;
  color: #fff;
  font-size: var(--app-text-badge-size);
}

.sp-hud-code {
  color: rgba(255, 255, 255, 0.6);
  font-family: var(--sp-font-mono);
  font-size: var(--app-text-badge-size);
  width: 60px;
}

/* A single quiet readability layer keeps controls legible without turning the
   bottom third of the video into a separate black toolbar. */
.sp-gradient-overlay {
  position: absolute;
  inset: auto 0 0 0;
  height: 9rem;
  background: linear-gradient(to top, rgb(0 0 0 / 0.9) 0%, rgb(0 0 0 / 0.52) 42%, transparent 100%);
  pointer-events: none;
  z-index: 15;
}

.sp-controls-wrapper {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  z-index: 20;
  pointer-events: none;
}

.sp-controls-content {
  padding: 0 18px 12px;
  margin: 0;
  position: relative;
  z-index: 25;
  pointer-events: auto;
}

/* 进度条容器 */
.sp-progress-container {
  padding: 8px 0 7px;
  margin: 0;
  cursor: pointer;
  position: relative;
}

.sp-progress-area {
  position: relative;
  height: 8px;
  display: flex;
  align-items: center;
}

.sp-progress-rail {
  width: 100%;
  height: 3px;
  background: rgba(255, 255, 255, 0.2);
  transition:
    height var(--duration-normal) var(--ease-default);
  border-radius: 999px;
  overflow: hidden;
  position: relative;
}

.sp-progress-container:hover .sp-progress-rail {
  height: 5px;
}

.sp-progress-buffered {
  position: absolute;
  height: 100%;
  background: rgba(255, 255, 255, 0.28);
  border-radius: inherit;
}

.sp-progress-played {
  position: absolute;
  height: 100%;
  background: var(--sp-primary, #d3d4d8);
  border-radius: inherit;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.sp-clip-marker {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  min-width: 4px;
  height: 18px;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: grab;
  z-index: 1;
}

.sp-clip-marker.is-dragging {
  cursor: grabbing;
  z-index: 2;
}

.sp-clip-marker--pending {
  cursor: default;
  animation: pending-pulse 1.5s ease-in-out infinite;
}

@keyframes pending-pulse {
  0%, 100% { opacity: 0.75; }
  50% { opacity: 1; }
}

.sp-clip-marker--pending .sp-clip-marker-track {
  background: hsla(0, 84%, 60%, 0.45);
}

.sp-clip-marker--pending .sp-clip-marker-dot {
  background: hsl(0, 84%, 60%);
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.55);
  animation: pending-dot-pulse 1s ease-in-out infinite;
}

@keyframes pending-dot-pulse {
  0%, 100% { transform: translateY(-50%) scale(1); }
  50% { transform: translateY(-50%) scale(1.3); }
}

.sp-clip-marker-track {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 5px;
  transform: translateY(-50%);
  border-radius: 999px;
  background: color-mix(in srgb, var(--marker-color, hsl(24 100% 50%)) 40%, transparent);
  transition:
    height var(--duration-fast) var(--ease-default),
    background var(--duration-normal) var(--ease-default);
}

.sp-clip-marker:hover .sp-clip-marker-track {
  height: 7px;
  background: color-mix(in srgb, var(--marker-color, hsl(24 100% 50%)) 60%, transparent);
}

.sp-clip-marker-dot {
  position: absolute;
  top: 50%;
  right: 0;
  width: 8px;
  height: 8px;
  transform: translate(50%, -50%);
  border-radius: 999px;
  background: var(--marker-color, hsl(24 100% 50%));
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.55);
  transition: transform var(--duration-fast) var(--ease-default);
}

.sp-clip-marker:hover .sp-clip-marker-dot {
  transform: translate(50%, -50%) scale(1.2);
}

.sp-clip-marker.is-point .sp-clip-marker-track {
  left: 50%;
  right: auto;
  width: 2px;
  transform: translate(-50%, -50%);
}

.sp-clip-marker.is-point .sp-clip-marker-dot {
  right: 50%;
  transform: translate(50%, -50%);
}

.sp-clip-marker.is-active .sp-clip-marker-track {
  background: color-mix(in srgb, var(--marker-color, hsl(24 100% 50%)) 85%, transparent);
}

.sp-clip-marker.is-active .sp-clip-marker-dot {
  background: var(--marker-color, hsl(24 100% 50%));
  box-shadow: 0 0 0 2px rgba(255,255,255,0.88);
}

.sp-clip-marker-tooltip {
  position: absolute;
  bottom: calc(100% + 10px);
  left: 50%;
  transform: translateX(-50%) translateY(4px);
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  background: hsl(0 0% 8% / 0.95);
  border: 1px solid color-mix(in srgb, var(--marker-color, hsl(24 100% 50%)) 40%, transparent);
  border-radius: 6px;
  color: #fff;
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  white-space: nowrap;
  opacity: 0;
  transition:
    opacity var(--duration-normal) var(--ease-default),
    transform var(--duration-normal) var(--ease-default);
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  z-index: 10;
  pointer-events: none;
}

.sp-clip-marker:hover .sp-clip-marker-tooltip {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
  pointer-events: auto;
}

.sp-clip-marker-tooltip__title {
  font-weight: 600;
  color: #fff;
}

.sp-clip-marker-tooltip__time {
  color: rgba(255,255,255,0.6);
  font-size: var(--app-text-badge-size);
}

.sp-clip-marker-tooltip__actions {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-left: 2px;
}

.sp-clip-marker-tooltip__del {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border: none;
  border-radius: 3px;
  background: rgba(255, 99, 99, 0.15);
  color: hsl(0 72% 64%);
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-default);
}

.sp-clip-marker-tooltip__del:hover {
  background: rgba(255, 99, 99, 0.3);
}

/* 标记数量徽章 */
.sp-marker-count {
  position: absolute;
  top: 1px;
  right: 1px;
  min-width: 14px;
  height: 14px;
  padding: 0 3px;
  background: var(--sp-primary);
  color: #fff;
  font-size: var(--app-text-badge-size);
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  pointer-events: none;
}

.sp-marker-count--capturing {
  background: hsl(0 84% 60%);
  font-size: var(--app-text-badge-size);
  animation: capture-blink 1s ease-in-out infinite;
}

@keyframes capture-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.sp-progress-dot {
  top: 50%;
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: var(--sp-primary);
  box-shadow: 0 0 0 2px rgb(255 255 255 / 0.9), 0 1px 4px rgb(0 0 0 / 0.45);
  position: absolute;
  right: 0;
  transform: translate(50%, -50%) scale(0);
  transition: transform var(--duration-normal) var(--ease-default);
}

.sp-progress-container:hover .sp-progress-dot {
  transform: translate(50%, -50%) scale(1);
}

/* 进度条悬停预览 */
.sp-preview-hint {
  position: absolute;
  bottom: 24px;
  transform: translateX(-50%);
  pointer-events: none;
  animation: hint-fade var(--duration-normal) var(--ease-default);
}

@keyframes hint-fade {
  from { opacity: 0; transform: translateX(-50%) translateY(5px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

.sp-preview-hint-inner {
  padding: 4px 8px;
  background: rgb(18 18 18 / 0.96);
  border: 1px solid rgb(255 255 255 / 0.1);
  color: #fff;
  font-size: var(--app-text-badge-size);
  font-family: var(--sp-font-mono);
  border-radius: 6px;
  box-shadow: 0 8px 20px rgb(0 0 0 / 0.5);
}

.sp-preview-thumbnail {
  width: 120px;
  height: 68px;
  margin-bottom: 4px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background-color: #000;
  background-repeat: no-repeat;
  box-shadow: 0 2px 8px rgba(0,0,0,0.5);
}

/* Chapter markers */
.sp-chapter-marker {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 3px;
  height: 10px;
  padding: 0;
  border: 0;
  background: rgba(255, 255, 255, 0.35);
  border-radius: 2px;
  cursor: pointer;
  z-index: 1;
  transition: height var(--duration-fast), background var(--duration-fast);
}

.sp-chapter-marker:hover {
  height: 14px;
  background: var(--sp-primary, #d3d4d8);
}

/* 控制栏主行 */
.sp-controls-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 38px;
  margin-top: 0;
}

.sp-controls-left,
.sp-controls-right {
  display: flex;
  align-items: center;
  gap: 2px;
}

.sp-controls-left {
  min-width: 0;
}

.sp-controls-right {
  justify-content: flex-end;
}

/* 质量标签 */
.sp-quality-tag {
  appearance: none;
  font-family: var(--sp-font-mono);
  min-height: 1.75rem;
  padding: 0.25rem 0.5rem;
  border: 1px solid rgb(255 255 255 / 0.13);
  border-radius: 6px;
  color: rgb(255 255 255 / 0.78);
  font-size: var(--app-text-badge-size);
  font-weight: 650;
  cursor: pointer;
  transition:
    color var(--duration-normal) var(--ease-default),
    border-color var(--duration-normal) var(--ease-default),
    background-color var(--duration-normal) var(--ease-default);
  background: rgb(0 0 0 / 0.18);
  letter-spacing: 0;
  margin-right: 6px;
}

.sp-quality-tag:hover,
.sp-quality-tag.is-active {
  color: #fff;
  border-color: rgb(255 255 255 / 0.24);
  background: rgb(255 255 255 / 0.1);
}

/* 控制按钮 */
.sp-icon-btn {
  background: transparent;
  border: none;
  color: rgb(255 255 255 / 0.78);
  cursor: pointer;
  width: 34px;
  height: 34px;
  min-width: 34px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 1;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    transform var(--duration-fast) var(--ease-default);
  position: relative;
}

.sp-icon-btn:hover {
  color: #fff;
  background: rgb(255 255 255 / 0.1);
}

.sp-icon-btn:focus-visible,
.sp-quality-tag:focus-visible {
  color: #fff;
  outline: 2px solid rgb(255 255 255 / 0.82);
  outline-offset: -2px;
}

.sp-icon-btn:active {
  transform: scale(0.92);
}

.sp-icon-btn :deep(svg) {
  width: 17px;
  height: 17px;
}

.sp-btn--play {
  width: 36px;
  height: 36px;
  min-width: 36px;
  margin-inline: 2px;
  border-radius: 999px;
  background: var(--sp-primary);
  color: #fff;
  box-shadow: 0 4px 14px hsl(var(--primary) / 0.28);
}

.sp-btn--play:hover {
  background: var(--sp-primary-hover);
  color: #fff;
}

.sp-btn--play :deep(svg) {
  width: 18px;
  height: 18px;
}

/* 时间显示 */
.sp-time-display {
  font-family: var(--sp-font-mono);
  min-width: 0;
  padding-left: 8px;
  color: rgb(255 255 255 / 0.92);
  font-size: 11px;
  display: flex;
  align-items: center;
  letter-spacing: 0;
  font-weight: 600;
}

.sp-time-separator {
  margin-inline: 5px;
  opacity: 0.34;
}

.sp-time-total {
  opacity: 0.62;
}

/* 音量控制 */
.sp-volume-group {
  position: relative;
  display: flex;
  align-items: center;
  gap: 1px;
}

.sp-volume-slider-wrap {
  width: 68px;
  padding-inline: 7px;
  overflow: visible;
  opacity: 1;
  height: 32px;
  display: flex;
  align-items: center;
}

.sp-volume-bar {
  width: 100%;
  height: 3px;
  background: rgb(255 255 255 / 0.22);
  border-radius: 1.5px;
  position: relative;
  cursor: pointer;
}

.sp-volume-fill {
  height: 100%;
  background: var(--sp-primary);
  border-radius: 1.5px;
  position: relative;
}

.sp-volume-percent {
  position: absolute;
  bottom: calc(100% + 0.375rem);
  left: 50%;
  z-index: 2;
  min-width: 2.75rem;
  padding: 0.25rem 0.375rem;
  transform: translateX(-50%);
  border: 1px solid rgb(255 255 255 / 0.1);
  border-radius: 6px;
  background: rgb(18 18 18 / 0.96);
  box-shadow: 0 8px 20px rgb(0 0 0 / 0.38);
  font-family: var(--sp-font-mono);
  font-size: 11px;
  color: rgb(255 255 255 / 0.86);
  text-align: center;
  pointer-events: none;
}

.sp-ui-fade-enter-active, .sp-ui-fade-leave-active {
  transition:
    opacity var(--duration-slow) var(--ease-out),
    transform var(--duration-slow) var(--ease-out);
}

.sp-ui-fade-enter-from, .sp-ui-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

.sp-icon-btn:disabled {
  opacity: 0.28;
  cursor: not-allowed;
  filter: grayscale(1);
}

@container video-player (max-width: 760px) {
  .sp-controls-content {
    padding-inline: 12px;
  }

  .sp-volume-slider-wrap,
  .sp-volume-percent {
    display: none;
  }

  .sp-control--optional {
    display: none;
  }
}

@container video-player (max-width: 560px) {
  .sp-controls-content {
    padding: 0 8px 7px;
  }

  .sp-progress-container {
    padding-block: 6px;
  }

  .sp-icon-btn {
    width: 32px;
    height: 32px;
    min-width: 32px;
  }

  .sp-btn--play {
    width: 34px;
    height: 34px;
    min-width: 34px;
  }

  .sp-control--compact-hide,
  .sp-quality-tag,
  .sp-time-total,
  .sp-time-separator {
    display: none;
  }

  .sp-time-display {
    padding-left: 4px;
  }
}

/* Viewport fallbacks for environments without container-query support. */
@supports not (container-type: inline-size) {
  @media (max-width: 860px) {
    .sp-volume-slider-wrap,
    .sp-volume-percent,
    .sp-control--optional {
      display: none;
    }
  }

  @media (max-width: 620px) {
    .sp-control--compact-hide,
    .sp-quality-tag,
    .sp-time-total,
    .sp-time-separator {
      display: none;
    }
  }
}

/* ===== Fullscreen Features CSS ===== */

/* AB loop indicator */
.sp-abloop-indicator {
  position: absolute;
  bottom: 56px;
  left: 16px;
  z-index: 30;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: var(--sp-menu-bg);
  border: 1px solid var(--sp-menu-border);
  border-radius: var(--sp-radius-md);
  box-shadow: var(--sp-menu-shadow);
  color: var(--sp-primary);
  font-family: var(--sp-font-mono);
  font-size: 11px;
  font-weight: 700;
}

.sp-abloop-indicator :deep(svg) {
  width: 14px;
  height: 14px;
}

.sp-abloop-times {
  opacity: 0.6;
  font-weight: 400;
}

</style>
