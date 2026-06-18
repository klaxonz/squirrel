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
    <!-- 暗角遮罩-->
    <div class="sp-vignette-overlay"></div>

    <VideoInfoOverlay
      :visible="showVideoInfo"
      :fullscreen="isFullscreen"
      :title="props.title"
      :uploader="props.uploader"
    />

    <SleepTimerBadge
      :fullscreen="isFullscreen"
      :visible="store.sleepTimerMinutes !== null"
      :remaining-text="formatSleepRemaining()"
    />

    <div v-if="store.abLoopActive" class="sp-abloop-indicator">
      <PlayerIcon name="loopAB" /> {{ t('abLoopActive') }}
      <span class="sp-abloop-times">{{ formatTime(store.loopAPoint ?? 0) }} - {{ formatTime(store.loopBPoint ?? 0) }}</span>
    </div>

    <UpNextOverlay
      :visible="showUpNext"
      :label="t('upNext')"
      :next-title="nextEpisodeTitle"
      :countdown="upNextCountdown"
      :start-now-label="t('startNow')"
      @start-now="handleStartNow"
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


    <!-- ???? -->
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

    <!-- ?????-->
    <Transition name="sp-loading-fade" @after-enter="onLoadingEnter" @after-leave="onLoadingLeave">
      <div v-if="showLoadingOverlay" class="sp-loading">
        <div class="sp-loader">
          <div class="sp-loader-ring"></div>
        </div>
        <div v-if="loadingStageText" class="sp-loading-text">{{ loadingStageText }}</div>
      </div>
    </Transition>

    <!-- Error overlay -->
    <Transition name="sp-loading-fade">
      <div v-if="errorState.show" class="sp-error-overlay" @click.stop>
        <div class="sp-error-content">
          <div class="sp-error-icon">
            <PlayerIcon name="error" class="sp-error-icon-svg" />
          </div>
          <div class="sp-error-title">{{ errorState.title || t('errorTitle') }}</div>
          <div class="sp-error-message">{{ errorState.message }}</div>
          <div class="sp-error-actions">
            <button v-if="errorState.canRetry" class="sp-error-retry-btn" @click.stop="handleRetry">
              {{ t('retry') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Stats overlay -->
    <StatsOverlay :get-stats="getStats" :visible="showStats" />

    <!-- Playlist panel -->
    <PlaylistPanel
      :visible="showPlaylist"
      :entries="playlistEntries"
      :active-index="playlistIndex"
      :is-playing="isPlaying"
      @close="showPlaylist = false"
      @select="handlePlaylistSelect"
    />

    <!-- ??????-->
    <transition name="sp-ui-fade">
      <div v-show="store.controlsVisible" class="sp-controls-wrapper" data-player-interactive>
        <!-- ?????? -->
        <div class="sp-gradient-overlay"></div>

        <div class="sp-controls-content">
          <!-- ????????-->
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
                  class="sp-chapter-marker"
                  :style="{ left: `${chapter.startPercent}%` }"
                  :title="chapter.title"
                  @pointerdown.stop="handleChapterClick(chapter.startTime)"
                ></button>
                <button
                  v-for="marker in normalizedClipMarkers"
                  :key="marker.id"
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
                      <button class="sp-clip-marker-tooltip__del" @click.stop="deleteMarkerFromPanel(marker)">×</button>
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
              <!-- ?????? -->
              <div v-if="previewTime !== null" class="sp-preview-hint" :style="{ left: `${previewPercent}%` }">
                <div v-if="thumbnailSpriteUrl" class="sp-preview-thumbnail" :style="thumbnailSpriteStyle"></div>
                <div class="sp-preview-hint-inner">
                  {{ formatTime(previewTime) }}
                </div>
              </div>
            </div>
          </div>

          <!-- ??????-->
          <div class="sp-controls-main">
            <div class="sp-controls-left">
              <button class="sp-icon-btn" @click="emit('prev')" :title="t('prev')" :disabled="!props.hasPrev" :aria-label="t('prev')">
                <PlayerIcon name="prev" />
              </button>
              <button class="sp-icon-btn sp-btn--play" @click="togglePlay" :title="isPlaying ? t('pause') : t('play')" :aria-label="isPlaying ? t('pause') : t('play')">
                <PlayerIcon :name="isPlaying ? 'pause' : 'play'" />
              </button>
              <button class="sp-icon-btn" @click="emit('next')" :title="t('next')" :disabled="!props.hasNext" :aria-label="t('next')">
                <PlayerIcon name="next" />
              </button>
              
              <div class="sp-volume-group" :class="{ 'is-active': isVolumeScrubbing }" @pointerenter="isVolumeHovered = true" @pointerleave="isVolumeHovered = false">
                <button class="sp-icon-btn" @click="toggleMute" :title="t('mute')" :aria-label="isMuted ? t('unmute') : t('mute')">
                  <PlayerIcon :name="volumeIconName" />
                </button>
                <div class="sp-volume-slider-wrap" 
                     @pointerdown.prevent="onVolumePointerDown"
                     @pointermove="onVolumePointerMove"
                     @pointerup="onVolumePointerUp">
                  <div class="sp-volume-bar">
                    <div class="sp-volume-fill" :style="{ width: `${isMuted ? 0 : volumeFillPercent}%` }">
                      <div class="sp-volume-glow"></div>
                    </div>
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
              <div
                v-if="displayedQualities.length > 0 && qualityTagLabel"
                class="sp-quality-tag"
                :class="{ 'is-active': showQualityMenu }"
                @click.stop="toggleQualityMenu"
                aria-haspopup="true"
                :aria-expanded="showQualityMenu"
                role="button"
              >
                {{ qualityTagLabel }}
              </div>
              <button v-if="subtitleTracks.length > 0" class="sp-icon-btn" @click.stop="toggleSubtitlesQuick" :title="t('subtitles')">
                <PlayerIcon :name="store.subtitlesEnabled ? 'subtitles' : 'subtitlesOff'" />
              </button>
              <button class="sp-icon-btn" :title="hasPendingSegment ? `保存片段` : t('markClip')" :disabled="isSavingMarker" @click.stop="hasPendingSegment ? finishSegmentCapture() : markCurrentPoint()">
                <PlayerIcon name="markClip" />
                <span v-if="hasPendingSegment" class="sp-marker-count sp-marker-count--capturing">●</span>
              </button>
              <button v-if="hasPlaylist" class="sp-icon-btn" @click.stop="showPlaylist = !showPlaylist" :title="'Playlist'">
                <PlayerIcon name="settings" />
              </button>
              <button v-if="isFullscreen" class="sp-icon-btn" @click.stop="captureScreenshot" :title="t('screenshot')">
                <PlayerIcon name="screenshot" />
              </button>
              <button v-if="isFullscreen" class="sp-icon-btn" @click.stop="settingsView = 'sleepTimer'; showSettingsMenu = true" :title="t('sleepTimer')">
                <PlayerIcon name="sleepTimer" />
              </button>
              <button v-if="isFullscreen" class="sp-icon-btn" @click.stop="handleLoopABToggle" :title="store.abLoopActive ? t('loopClearAB') : (store.loopAPoint !== null ? t('loopSetB') : t('loopSetA'))">
                <PlayerIcon name="loopAB" :style="{ opacity: store.loopAPoint !== null ? 1 : 0.5 }" />
              </button>
              <button class="sp-icon-btn" @click.stop="toggleSettingsMenu" :title="t('settings')" aria-haspopup="true" :aria-expanded="showSettingsMenu" :aria-label="t('settings')">
                <PlayerIcon name="settings" />
              </button>
              <button class="sp-icon-btn" @click="toggleWidescreen" :title="props.widescreen ? t('exitWidescreen') : t('widescreen')">
                <PlayerIcon :name="props.widescreen ? 'widescreenExit' : 'widescreen'" />
              </button>
              <button class="sp-icon-btn" @click="togglePictureInPicture" :title="store.pictureInPicture ? t('exitPictureInPicture') : t('pictureInPicture')">
                <PlayerIcon :name="store.pictureInPicture ? 'pipExit' : 'pip'" />
              </button>
              <button class="sp-icon-btn" @click="toggleFullscreen" :title="isFullscreen ? t('exitFullscreen') : t('fullscreen')">
                <PlayerIcon :name="isFullscreen ? 'fullscreenExit' : 'fullscreen'" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- ?????? -->
    <transition name="sp-ui-fade">
      <div v-if="showQualityMenu" class="sp-settings-pop sp-quality-pop" data-player-interactive role="menu">
        <div class="sp-menu-list">
          <div
            v-for="q in displayedQualities"
            :key="q.id"
            class="sp-menu-item"
            :class="{ 'is-active': isQualityActive(q) }"
            @click="handleQualitySelect(q)"
            role="menuitemradio"
            :aria-checked="isQualityActive(q)"
          >
            {{ q.label }}
          </div>
        </div>
      </div>
    </transition>

    <!-- ???? -->
    <SettingsMenu
      :visible="showSettingsMenu"
      :view="settingsView"
      :autoplay-next="store.autoplayNext"
      :loop="store.loop"
      :playback-rate="store.playbackRate"
      :rotation="videoRotation"
      :qualities="settingsQualities"
      :has-quality="displayedQualities.length > 0"
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
      :quality-value="qualityMenuLabel"
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
      :quality-label="t('quality')"
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
      @select-quality="settings.handleQualitySelect"
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
import { formatTime } from '@/utils/dateFormat'
import { usePlayer, type PlayerOptions } from './runtime/usePlayer'
import type { Chapter, MediaSource, SubtitleTrack } from './core'
import { getCodecFamily } from './core/codec'
import type { ThemeName } from './themes'
import type { VideoClipMarker } from '@/types/videoClipMarker'
import { usePlayerStore } from '@/stores/player'
import PlayerIcon from './PlayerIcon.vue'
import StatsOverlay from './StatsOverlay.vue'
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
    errorState.value = {
      show: true,
      title: t('errorTitle'),
      message: resolveErrorMessage(e.code, e.message),
      code: e.code,
      canRetry: true
    }
    emit('error', e)
  },
  onTimeUpdate: (time) => emit('timeupdate', time)
})

const playerStore = usePlayerStore()
const playlistEntries = computed(() => playerStore.session.playlist || [])
const playlistIndex = computed(() => playerStore.session.playlistIndex ?? -1)
const hasPlaylist = computed(() => playlistEntries.value.length > 1)

const handlePlaylistSelect = (index: number) => {
  if (index >= 0 && index < playlistEntries.value.length) {
    showPlaylist.value = false
    emit('playlistSelect', index)
  }
}

const videoRef = ref<HTMLVideoElement | null>(null)
const containerRef = ref<HTMLElement | null>(null)
const progressAreaRef = ref<HTMLElement | null>(null)

// Fullscreen feature state
const showVideoInfo = ref(true)
const showChapterOverlay = ref(false)
const showUpNext = ref(false)
const upNextCountdown = ref(5)
const nextEpisodeTitle = computed(() => {
  const entries = props.playlistEntries || []
  const nextIdx = (props.playlistIndex ?? -1) + 1
  if (nextIdx >= 0 && nextIdx < entries.length) {
    return entries[nextIdx].title || `Episode ${nextIdx + 1}`
  }
  return ''
})
let videoInfoTimer: ReturnType<typeof setTimeout> | null = null
let upNextTimer: ReturnType<typeof setInterval> | null = null

const { centralHud, showCentralHud } = useCentralHud()

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
const previewTime = ref<number | null>(null)
const previewPercent = ref(0)
const isScrubbing = ref(false)
const isVolumeScrubbing = ref(false)
const isVolumeHovered = ref(false)

const pendingUserVolumeHud = ref<number | null>(null)
const pendingWidescreenValue = ref<boolean | null>(null)
const shouldResumeAfterSourceSwap = ref(false)
const errorState = ref({ show: false, title: '', message: '', code: '', canRetry: true })

// 按 code 把引擎/插件产生的英文错误信息映射为中文。
// 这些 message 来自 core/error-recovery.ts、createPlayerEngine.ts、HlsPlugin/DashPlugin/ShakaDashPlugin，
// 在源头改会侵入多个插件并丢失原始信息，故在 UI 层统一翻译。
const resolveErrorMessage = (code: string, fallback: string): string => {
  const upper = String(code || '').toUpperCase()
  if (upper.includes('NETWORK') || upper.includes('TIMEOUT')) return t('errorNetwork')
  if (upper.includes('NOT_SUPPORTED') || upper.includes('CAPABILITY')) return t('errorNotSupported')
  if (upper.includes('DECODE')) return t('errorDecode')
  if (upper.includes('MEDIA') || upper.includes('HLS_') || upper.includes('DASH_')) return t('errorMedia')
  if (upper.includes('STALL')) return t('buffering')
  return fallback || t('errorUnknown')
}

const handleRetry = () => {
  errorState.value.show = false
  emit('retry')
}
const showLoadingOverlay = computed(() => (store.loading || props.externalLoading) && !errorState.value.show)
const isAudioOnly = computed(() => !!props.source?.audioOnly)
const loadingStageText = computed(() => {
  if (store.loadingStage === 'fetching') return t('loading')
  if (store.loadingStage === 'buffering') return t('buffering')
  return null
})
const videoRotation = ref(0)
const videoRotationScale = ref(1)
const videoRotationStyle = computed(() => ({
  transform: `rotate(${videoRotation.value}deg) scale(${videoRotationScale.value})`,
}))
let videoRotationResizeObserver: ResizeObserver | null = null
let rotationScaleRafId: number | null = null

const updateVideoRotationScale = () => {
  if (rotationScaleRafId !== null) return
  rotationScaleRafId = requestAnimationFrame(() => {
    rotationScaleRafId = null
    const container = containerRef.value
    if (!container || videoRotation.value % 180 === 0) {
      videoRotationScale.value = 1
      return
    }

    const rect = container.getBoundingClientRect()
    if (rect.width <= 0 || rect.height <= 0) {
      videoRotationScale.value = 1
      return
    }

    videoRotationScale.value = Math.min(rect.width / rect.height, rect.height / rect.width)
  })
}

// Loading state control
const onLoadingEnter = () => {}
const onLoadingLeave = () => {}

watch(volume, (newVol, oldVol) => {
  if (Math.abs(newVol - oldVol) < 0.1) return
  const expectedVolume = pendingUserVolumeHud.value
  pendingUserVolumeHud.value = null
  if (expectedVolume === null || Math.abs(newVol - expectedVolume) > 0.1) return
  showCentralHud('volume', `${Math.round(newVol)}%`, volumeIconName.value, newVol)
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

const sourceChapters = computed(() => props.source?.chapters || [])
const normalizedChapters = computed(() => {
  if (!duration.value || duration.value <= 0) return []
  return sourceChapters.value.map((chapter: Chapter) => ({
    ...chapter,
    startPercent: Math.min((chapter.startTime / duration.value) * 100, 100),
  }))
})

const thumbnailSpriteUrl = computed(() => props.source?.thumbnailSpriteUrl || null)
const thumbnailSpriteColumns = computed(() => props.source?.thumbnailSpriteColumns || 10)
const thumbnailSpriteRows = computed(() => props.source?.thumbnailSpriteRows || 10)
const thumbnailSpriteInterval = computed(() => props.source?.thumbnailSpriteInterval || 10)
const thumbnailSpriteStyle = computed(() => {
  if (!thumbnailSpriteUrl.value || !duration.value) return {}
  const totalFrames = thumbnailSpriteColumns.value * thumbnailSpriteRows.value
  const frameIndex = Math.min(
    Math.floor((previewTime.value ?? 0) / thumbnailSpriteInterval.value),
    totalFrames - 1
  )
  const col = frameIndex % thumbnailSpriteColumns.value
  const row = Math.floor(frameIndex / thumbnailSpriteColumns.value)
  const frameW = 100 * thumbnailSpriteColumns.value
  const frameH = 100 * thumbnailSpriteRows.value
  return {
    backgroundImage: `url(${thumbnailSpriteUrl.value})`,
    backgroundPosition: `-${col * 100}% -${row * 100}%`,
    backgroundSize: `${frameW}% ${frameH}%`,
  }
})

const handleChapterClick = (time: number) => {
  seek(time)
}

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
const volumeIconName = computed(() => (isMuted.value || volume.value === 0) ? 'volumeOff' : volume.value < 50 ? 'volumeLow' : 'volumeHigh')
const volumeText = computed(() => isMuted.value ? 'Muted' : `${Math.round(volume.value)}%`)
const volumeFillPercent = computed(() => (isMuted.value ? 0 : Math.min(100, (volume.value / MAX_VOLUME) * 100)))
const visibleCodecFamily = computed(() => (
  selectedCodecFamily.value !== 'auto'
    ? selectedCodecFamily.value
    : currentCodecFamily.value
))
const isInternalQualityLabel = (label: string | null | undefined) => /^level[_\s-]?\d+$/i.test(String(label || '').trim())
const isAutoQualityLabel = (label: string | null | undefined) => ['auto', '??', '??'].includes(String(label || '').trim().toLowerCase())
const isDisplayableQualityLabel = (label: string | null | undefined) => !isInternalQualityLabel(label) && !isAutoQualityLabel(label)
const resolvedCurrentQuality = computed(() => {
  if (currentQualityId.value === null || currentQualityId.value === undefined) return null
  return qualities.value.find((quality) => String(quality.id) === String(currentQualityId.value)) || null
})
const getQualityBucketKey = (quality: { height?: number | null; label?: string | null; id?: string | number | null }) => {
  const height = Number(quality.height || 0)
  if (Number.isFinite(height) && height > 0) {
    return `height:${height}`
  }
  const label = String(quality.label || quality.id || '').trim().toLowerCase()
  return `label:${label}`
}
const scoreQualityForDisplay = (quality: { id?: string | number | null; codec?: string | null; height?: number | null; bitrate?: number | null }) => {
  let score = 0
  if (resolvedCurrentQuality.value && String(quality.id) === String(resolvedCurrentQuality.value.id)) {
    score += 1_000_000_000_000
  }

  const preferredCodecFamily = visibleCodecFamily.value
    || getCodecFamily(resolvedCurrentQuality.value?.codec)
    || currentCodecFamily.value
  if (preferredCodecFamily && getCodecFamily(quality.codec) === preferredCodecFamily) {
    score += 1_000_000_000
  }

  score += Math.max(0, Number(quality.height || 0)) * 1_000_000
  score += Math.max(0, Number(quality.bitrate || 0))
  return score
}
const displayedQualities = computed(() => {
  const codecMatchedQualities = visibleCodecFamily.value
    ? qualities.value.filter((quality) => getCodecFamily(quality.codec) === visibleCodecFamily.value)
    : qualities.value
  const sourceQualities = codecMatchedQualities.length > 0 ? codecMatchedQualities : qualities.value
  const dedupedQualities = new Map<string, typeof sourceQualities[number]>()

  sourceQualities.forEach((quality) => {
    const bucketKey = getQualityBucketKey(quality)
    const existing = dedupedQualities.get(bucketKey)
    if (!existing || scoreQualityForDisplay(quality) > scoreQualityForDisplay(existing)) {
      dedupedQualities.set(bucketKey, quality)
    }
  })

  return [...dedupedQualities.values()].sort((left, right) => {
    const heightDelta = (Number(right.height || 0) - Number(left.height || 0))
    if (heightDelta !== 0) return heightDelta
    return Number(right.bitrate || 0) - Number(left.bitrate || 0)
  })
})
const currentQualityText = computed(() => (
  resolvedCurrentQuality.value?.label
    || (isDisplayableQualityLabel(currentQualityLabel.value) ? (currentQualityLabel.value || '') : '')
))
const qualityTagLabel = computed(() => currentQualityText.value)
const qualityMenuLabel = computed(() => currentQualityText.value || t('quality'))
const subtitleMenuLabel = computed(() => {
  if (!store.subtitlesEnabled || !currentSubtitle.value) return t('subtitlesOff')
  return currentSubtitle.value.label
})
let removeInitialTimeListener: (() => void) | null = null
let removeResumeAfterSourceSwapListener: (() => void) | null = null
let initialTimeAppliedSourceKey: string | null = null

const clearInitialTimeListener = (): void => {
  if (!removeInitialTimeListener) return
  removeInitialTimeListener()
  removeInitialTimeListener = null
}

const clearResumeAfterSourceSwapListener = (): void => {
  if (!removeResumeAfterSourceSwapListener) return
  removeResumeAfterSourceSwapListener()
  removeResumeAfterSourceSwapListener = null
}

const getSourceIdentity = (source: MediaSource | null | undefined): string => {
  if (!source) return ''
  return String(source.key || source.src || '')
}

const applyInitialTime = (source: MediaSource | null | undefined, time: number | undefined): void => {
  const sourceKey = getSourceIdentity(source)
  if (!sourceKey || initialTimeAppliedSourceKey === sourceKey) return
  if (store.hasStartedPlayback || currentTime.value > 0.5) return

  const video = videoRef.value
  const nextTime = Number(time)
  if (!video || !Number.isFinite(nextTime) || nextTime <= 0) return

  clearInitialTimeListener()

  const applySeek = (): void => {
    const durationValue = Number(video.duration)
    const boundedTime = Number.isFinite(durationValue) && durationValue > 0
      ? Math.min(nextTime, durationValue)
      : nextTime

    if (boundedTime <= 0) return
    initialTimeAppliedSourceKey = sourceKey
    seek(Math.max(0, boundedTime))
  }

  if (video.readyState >= HTMLMediaElement.HAVE_METADATA) {
    applySeek()
    return
  }

  const onLoadedMetadata = (): void => {
    clearInitialTimeListener()
    applySeek()
  }

  video.addEventListener('loadedmetadata', onLoadedMetadata, { once: true })
  removeInitialTimeListener = () => {
    video.removeEventListener('loadedmetadata', onLoadedMetadata)
  }
}

const resumePlaybackAfterSourceSwap = (): void => {
  if (!shouldResumeAfterSourceSwap.value) return

  const video = videoRef.value
  if (!video) {
    shouldResumeAfterSourceSwap.value = false
    return
  }

  const resume = (): void => {
    clearResumeAfterSourceSwapListener()
    if (!shouldResumeAfterSourceSwap.value) return
    shouldResumeAfterSourceSwap.value = false
    void play()
  }

  if (video.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) {
    resume()
    return
  }

  clearResumeAfterSourceSwapListener()
  video.addEventListener('canplay', resume, { once: true })
  removeResumeAfterSourceSwapListener = () => {
    video.removeEventListener('canplay', resume)
  }
}

watch(videoRef, (el) => { videoElement.value = el }, { immediate: true })
watch(containerRef, (el) => { containerElement.value = el }, { immediate: true })
watch(() => props.source, (s, previousSource) => {
  const sourceChanged = getSourceIdentity(s) !== getSourceIdentity(previousSource)
  if (sourceChanged) {
    clearInitialTimeListener()
    clearResumeAfterSourceSwapListener()
    initialTimeAppliedSourceKey = null
    errorState.value.show = false
  }
  if (!s) {
    shouldResumeAfterSourceSwap.value = isPlaying.value
    clearResumeAfterSourceSwapListener()
    pause()
    return
  }
  loadSource(s)
  if (shouldResumeAfterSourceSwap.value) {
    if (props.autoplay) {
      shouldResumeAfterSourceSwap.value = false
    } else {
      resumePlaybackAfterSourceSwap()
    }
  }
  applyInitialTime(s, props.initialTime)
}, { immediate: true })
watch(() => props.initialTime, (initialTime) => {
  applyInitialTime(props.source, initialTime)
})
watch(() => props.subtitles, (ts) => { setSubtitleTracks(ts || []) }, { immediate: true, deep: true })

// 修复"视频在正常播放但错误遮罩仍盖在上面"的问题：
// 引擎的错误恢复链（HLS recoverMediaError / DASH attachSource / 重试）经常能在底层把播放救回来，
// 但 reportFatalError 已经触发过 onError → errorState.show=true。这里在视频真正重新进入播放态时兜底清除遮罩。
watch(() => store.playing, (playing) => {
  if (playing && errorState.value.show) {
    errorState.value.show = false
  }
})

const togglePlay = () => isPlaying.value ? pause() : play()
const rotateVideo = () => {
  videoRotation.value = (videoRotation.value + 90) % 360
  showCentralHud('rotation', `${videoRotation.value}°`, 'rotate')
}
const handleRotationSelect = (rotation: number) => {
  videoRotation.value = rotation
  showCentralHud('rotation', `${videoRotation.value}°`, 'rotate')
  closeMenus()
}
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
let hideTimer: ReturnType<typeof setTimeout>
const clearHideTimer = () => clearTimeout(hideTimer)
const hideControls = () => {
  clearHideTimer()
  store.setControlsVisible(false)
  previewTime.value = null
  closeMenus()
}
const syncHideTimer = () => {
  clearHideTimer()
  if (store.controlsVisible && isPlaying.value && !isScrubbing.value) {
    hideTimer = setTimeout(() => hideControls(), 3000)
  }
}
const showControls = () => {
  store.setControlsVisible(true)
  syncHideTimer()
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
let activeProgressPointerId: number | null = null

const updateProgressPreview = (e: PointerEvent) => {
  const progressArea = progressAreaRef.value
  if (!progressArea) return

  const rect = progressArea.getBoundingClientRect()
  if (rect.width <= 0) return

  const p = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
  previewPercent.value = p * 100
  previewTime.value = p * duration.value

  if (isScrubbing.value && !hasPendingSegment.value) {
    seek(previewTime.value)
  }
  if (isScrubbing.value) {
    pendingSegmentEndTime.value = previewTime.value
  }
}

const releaseProgressPointerCapture = () => {
  const progressArea = progressAreaRef.value
  if (!progressArea || activeProgressPointerId === null || typeof progressArea.hasPointerCapture !== 'function') return

  if (!progressArea.hasPointerCapture(activeProgressPointerId)) return

  try {
    progressArea.releasePointerCapture(activeProgressPointerId)
  } catch {
    // Ignore browsers that reject release when the capture is already gone.
  }
}

const addProgressScrubListeners = () => {
  window.addEventListener('pointermove', onWindowProgressPointerMove)
  window.addEventListener('pointerup', onWindowProgressPointerUp)
  window.addEventListener('pointercancel', onWindowProgressPointerUp)
}

const removeProgressScrubListeners = () => {
  window.removeEventListener('pointermove', onWindowProgressPointerMove)
  window.removeEventListener('pointerup', onWindowProgressPointerUp)
  window.removeEventListener('pointercancel', onWindowProgressPointerUp)
}

const stopProgressScrub = (pointerId?: number) => {
  if (activeProgressPointerId !== null && typeof pointerId === 'number' && pointerId !== activeProgressPointerId) return

  releaseProgressPointerCapture()
  removeProgressScrubListeners()
  activeProgressPointerId = null
  isScrubbing.value = false
}

const onWindowProgressPointerMove = (e: PointerEvent) => {
  if (!isScrubbing.value) return
  if (activeProgressPointerId !== null && e.pointerId !== activeProgressPointerId) return

  updateProgressPreview(e)
}

const onWindowProgressPointerUp = (e: PointerEvent) => {
  stopProgressScrub(e.pointerId)
}

const onProgressPointerDown = (e: PointerEvent) => {
  activeProgressPointerId = e.pointerId
  isScrubbing.value = true
  addProgressScrubListeners()
  const progressArea = progressAreaRef.value
  if (progressArea && typeof progressArea.setPointerCapture === 'function') {
    try {
      progressArea.setPointerCapture(e.pointerId)
    } catch {
      // Ignore browsers that do not support capturing this pointer.
    }
  }
  updateProgressPreview(e)
}
const onProgressPointerMove = (e: PointerEvent) => {
  if (isScrubbing.value) return
  updateProgressPreview(e)
}
const onProgressPointerUp = (e?: PointerEvent) => { stopProgressScrub(e?.pointerId) }
const onProgressPointerLeave = () => { if (!isScrubbing.value) previewTime.value = null }

const onVolumePointerDown = (e: PointerEvent) => { isVolumeScrubbing.value = true; updateVol(e) }
const onVolumePointerMove = (e: PointerEvent) => { if (isVolumeScrubbing.value) updateVol(e) }
const onVolumePointerUp = () => { isVolumeScrubbing.value = false }
const setUserVolume = (value: number) => {
  pendingUserVolumeHud.value = value
  setVolume(value)
}
const updateVol = (e: PointerEvent) => {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  setUserVolume(Math.max(0, Math.min(MAX_VOLUME, ((e.clientX - rect.left) / rect.width) * MAX_VOLUME)))
}

const isModifierKey = (e: KeyboardEvent): boolean =>
  e.metaKey || e.ctrlKey || e.altKey

const isInputFocused = (): boolean =>
  document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA'

const handleKeyDown = (e: KeyboardEvent) => {
  const ks = keyboardShortcuts
  if (!ks.enabled) return
  if (isModifierKey(e)) return

  const matches = (key: string): boolean => {
    if (e.key === key) return true
    if (key === ' ' && e.code === 'Space') return true
    return false
  }

  if (matches(ks.playPause)) { e.preventDefault(); togglePlay(); return }
  if (matches(ks.fullscreen)) { toggleFullscreen(); return }

  if (matches(ks.rotate)) {
    if (isInputFocused()) return
    e.preventDefault()
    rotateVideo()
    return
  }

  if (matches(ks.seekBackward)) { e.preventDefault(); seek(currentTime.value - 10); return }
  if (matches(ks.seekForward)) { e.preventDefault(); seek(currentTime.value + 10); return }
  if (matches(ks.volumeUp)) { e.preventDefault(); setUserVolume(Math.min(MAX_VOLUME, volume.value + 5)); return }
  if (matches(ks.volumeDown)) { e.preventDefault(); setUserVolume(Math.max(0, volume.value - 5)); return }

  if (matches(ks.markSegmentStart)) {
    if (isInputFocused()) return
    e.preventDefault()
    if (e.shiftKey) {
      if (hasPendingSegment.value) finishSegmentCapture()
      else startSegmentCapture()
      return
    }
    if (matches(ks.markPoint)) {
      markCurrentPoint()
      return
    }
  }

  if (matches(ks.markPoint)) {
    if (isInputFocused()) return
    e.preventDefault()
    markCurrentPoint()
    return
  }

  if (matches(ks.cancelSegment) && hasPendingSegment.value) {
    cancelSegmentCapture()
    return
  }

  if (matches(ks.toggleSubtitles)) {
    if (isInputFocused()) return
    e.preventDefault()
    toggleSubtitlesQuick()
    return
  }

  if (matches(ks.toggleStats)) {
    if (isInputFocused()) return
    e.preventDefault()
    showStats.value = !showStats.value
    return
  }

  if (matches(ks.screenshot) && isFullscreen.value) {
    e.preventDefault()
    captureScreenshot()
    return
  }

  if (matches(ks.speedUp)) {
    e.preventDefault()
    const nextIdx = playbackRates.indexOf(store.playbackRate) + 1
    if (nextIdx < playbackRates.length) handleSpeedSelect(playbackRates[nextIdx])
    return
  }

  if (matches(ks.speedDown)) {
    e.preventDefault()
    const prevIdx = playbackRates.indexOf(store.playbackRate) - 1
    if (prevIdx >= 0) handleSpeedSelect(playbackRates[prevIdx])
    return
  }

  if (matches(ks.setLoopA) && isFullscreen.value) {
    e.preventDefault()
    store.setAbLoopActive(false)
    store.setLoopAPoint(currentTime.value)
    store.setLoopBPoint(null)
    showCentralHud('loopAB', t('loopSetA'), 'skipBackward')
    return
  }

  if (matches(ks.setLoopB) && isFullscreen.value && store.loopAPoint !== null) {
    e.preventDefault()
    const bTime = currentTime.value
    if (bTime <= (store.loopAPoint ?? 0)) return
    store.setLoopBPoint(bTime)
    store.setAbLoopActive(true)
    showCentralHud('loopAB', t('abLoopActive'), 'loop')
    return
  }

  if (matches(ks.clearLoopAB) && isFullscreen.value && store.abLoopActive) {
    e.preventDefault()
    store.setAbLoopActive(false)
    store.setLoopAPoint(null)
    store.setLoopBPoint(null)
    showCentralHud('loopAB', t('loopClearAB'), 'loop')
    return
  }

  if (matches(ks.prevVideo) && props.hasPrev) {
    e.preventDefault()
    emit('prev')
    return
  }

  if (matches(ks.nextVideo) && props.hasNext) {
    e.preventDefault()
    emit('next')
    return
  }
}

const isQualityActive = (quality: { id: string | number }) => (
  resolvedCurrentQuality.value !== null
    && String(resolvedCurrentQuality.value.id) === String(quality.id)
)

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


const handleStartNow = () => {
  showUpNext.value = false
  if (upNextTimer) {
    clearInterval(upNextTimer)
    upNextTimer = null
  }
  emit('next')
}

const startUpNextCountdown = () => {
  const entries = props.playlistEntries || []
  const nextIdx = (props.playlistIndex ?? -1) + 1
  if (nextIdx < 0 || nextIdx >= entries.length) return
  const remaining = duration.value - currentTime.value
  if (remaining > 30 || remaining < 0) return
  showUpNext.value = true
  upNextCountdown.value = Math.min(5, Math.floor(remaining))
  upNextTimer = setInterval(() => {
    upNextCountdown.value--
    if (upNextCountdown.value <= 0) {
      handleStartNow()
    }
  }, 1000)
}

const clearUpNextCountdown = () => {
  showUpNext.value = false
  if (upNextTimer) {
    clearInterval(upNextTimer)
    upNextTimer = null
  }
}

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
    clearUpNextCountdown()
    return
  }
  const entries = props.playlistEntries || []
  const nextIdx = (props.playlistIndex ?? -1) + 1
  if (nextIdx < 0 || nextIdx >= entries.length || duration.value <= 0) return
  const remaining = duration.value - t
  if (remaining <= 30 && remaining > 0 && !showUpNext.value) {
    startUpNextCountdown()
  }
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

watch(videoRotation, updateVideoRotationScale)
watch(() => props.videoId, () => {
  videoRotation.value = 0
})
watch(containerRef, (container) => {
  videoRotationResizeObserver?.disconnect()
  videoRotationResizeObserver = null

  if (container) {
    videoRotationResizeObserver = new ResizeObserver(updateVideoRotationScale)
    videoRotationResizeObserver.observe(container)
  }

  updateVideoRotationScale()
}, { immediate: true })

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
  window.addEventListener('keydown', handleKeyDown)
  document.addEventListener('visibilitychange', handleVisibilityChange)
})
onUnmounted(() => {
  clearHideTimer()
  clearInitialTimeListener()
  clearResumeAfterSourceSwapListener()
  videoRotationResizeObserver?.disconnect()
  if (rotationScaleRafId !== null) cancelAnimationFrame(rotationScaleRafId)
  releaseMarkerPointerCapture()
  releaseProgressPointerCapture()
  removeMarkerDragListeners()
  removeProgressScrubListeners()
  window.removeEventListener('keydown', handleKeyDown)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  stopSleepTimer()
  clearUpNextCountdown()
  if (videoInfoTimer) clearTimeout(videoInfoTimer)
})

defineExpose({ play, pause, seek, toggleFullscreen, togglePictureInPicture })
</script>

<style scoped>
.sp-player {
  position: absolute;
  inset: 0;
  background: #000;
  border: none;
  outline: none;
  box-shadow: none;
  overflow: hidden;
  cursor: none;
  font-family: var(--sp-font-family);
  user-select: none;
  letter-spacing: 0.015em;
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
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
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

/* ????????*/
.sp-vignette-overlay {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle, transparent 50%, rgba(0,0,0,0.4) 100%);
  pointer-events: none;
  z-index: 5;
}

/* ?? HUD ????*/
.sp-central-hud {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 100;
  pointer-events: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  /* smooth repositioning when shifting out of the spinner's way */
  transition: transform var(--duration-slow) var(--ease-default);
}

/* When the buffering spinner is showing, nudge the HUD up so they don't overlap. */
.sp-central-hud--shifted {
  transform: translate(-50%, -240%);
}

/* ====================== Volume capsule bar ====================== */
.sp-vol-capsule {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 16px;
  border-radius: var(--sp-radius-full);
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid var(--sp-border);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.sp-vol-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
}

.sp-vol-icon {
  width: 22px;
  height: 22px;
  color: #fff;
  filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.5));
}

.sp-vol-track {
  position: relative;
  width: 160px;
  height: 6px;
  border-radius: var(--sp-radius-full);
  background: rgba(255, 255, 255, 0.15);
  overflow: visible;
  flex-shrink: 0;
}

.sp-vol-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  border-radius: var(--sp-radius-full);
  background: var(--sp-primary);
  box-shadow: 0 0 8px rgba(var(--sp-primary-rgb), 0.6);
  transition: width var(--duration-normal) var(--ease-default);
}

.sp-vol-thumb {
  position: absolute;
  top: 50%;
  width: 14px;
  height: 14px;
  border-radius: var(--sp-radius-full);
  background: #fff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
  transform: translate(-50%, -50%);
  transition: left var(--duration-normal) var(--ease-default);
}

.sp-vol-percent {
  color: #fff;
  font-family: var(--sp-font-mono);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.02em;
  min-width: 40px;
  text-align: right;
  flex-shrink: 0;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.6);
}

/* ====================== Generic notice ====================== */
.sp-notice-badge {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--sp-radius-full);
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid var(--sp-border);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.sp-notice-icon {
  width: 28px;
  height: 28px;
  color: #fff;
}

.sp-notice-text {
  color: #fff;
  font-family: var(--sp-font-mono);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.6);
  padding: 3px 14px;
  border-radius: var(--sp-radius-full);
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

/* enter/leave only drive opacity on the root — transform is reserved for
   centering + shift, so transitions never clobber each other */
.sp-hud-fade-enter-active,
.sp-hud-fade-leave-active {
  transition: opacity var(--duration-normal) var(--ease-default);
}

.sp-hud-fade-enter-from,
.sp-hud-fade-leave-to {
  opacity: 0;
}

/* HUD ?????*/
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
  backdrop-filter: blur(8px);
  border: 1px solid rgba(var(--sp-primary-rgb), 0.25);
  border-radius: 4px;
}

.sp-hud-dot {
  width: 6px;
  height: 6px;
  background: var(--sp-primary);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--sp-primary);
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
  font-size: 10px;
  font-family: var(--sp-font-mono);
  letter-spacing: 0.1em;
  font-weight: 700;
  text-shadow: 0 0 4px rgba(var(--sp-primary-rgb), 0.4);
}

.sp-hud-separator {
  opacity: 0.2;
  color: #fff;
  font-size: 10px;
}

.sp-hud-code {
  color: rgba(255, 255, 255, 0.6);
  font-family: var(--sp-font-mono);
  font-size: 10px;
  width: 60px;
}

/* ?????? */
.sp-gradient-overlay {
  position: absolute;
  inset: auto 0 0 0;
  height: 120px;
  background: linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.4) 40%, transparent 100%);
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
  padding: 0 10px 6px;
  margin: 0;
  position: relative;
  z-index: 25;
  pointer-events: auto;
}

/* ??????*/
.sp-progress-container {
  padding: 6px 0;
  margin: 0 -4px;
  cursor: pointer;
  position: relative;
}

.sp-progress-area {
  position: relative;
  height: 4px;
  display: flex;
  align-items: center;
}

.sp-progress-rail {
  width: 100%;
  height: 2px;
  background: rgba(255, 255, 255, 0.12);
  transition:
    height var(--duration-normal) var(--ease-default);
  border-radius: 2px;
  overflow: hidden;
  position: relative;
}

.sp-progress-container:hover .sp-progress-rail {
  height: 4px;
}

.sp-progress-buffered {
  position: absolute;
  height: 100%;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
}

.sp-progress-played {
  position: absolute;
  height: 100%;
  background: var(--sp-primary, #d3d4d8);
  box-shadow: 0 0 10px rgba(var(--sp-primary-rgb), 0.5);
  border-radius: 2px;
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
  box-shadow: 0 0 10px hsla(0, 84%, 60%, 0.5);
}

.sp-clip-marker--pending .sp-clip-marker-dot {
  background: hsl(0, 84%, 60%);
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.5), 0 0 10px hsl(0, 84%, 60%);
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
  box-shadow: 0 0 8px color-mix(in srgb, var(--marker-color, hsl(24 100% 50%)) 30%, transparent);
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
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.55), 0 0 6px color-mix(in srgb, var(--marker-color, hsl(24 100% 50%)) 50%, transparent);
  transition:
    transform var(--duration-fast) var(--ease-default),
    box-shadow var(--duration-normal) var(--ease-default);
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
  box-shadow: 0 0 14px color-mix(in srgb, var(--marker-color, hsl(24 100% 50%)) 50%, transparent);
}

.sp-clip-marker.is-active .sp-clip-marker-dot {
  background: var(--marker-color, hsl(24 100% 50%));
  box-shadow: 0 0 0 2px rgba(255,255,255,0.88), 0 0 10px var(--marker-color, hsl(24 100% 50%));
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
  backdrop-filter: blur(8px);
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
  font-size: 10px;
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
  font-size: 9px;
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
  font-size: 6px;
  animation: capture-blink 1s ease-in-out infinite;
}

@keyframes capture-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.sp-progress-dot {
  width: 10px;
  height: 100%;
  background: #fff;
  position: absolute;
  right: 0;
  transform: scaleX(0);
  transform-origin: right;
  transition: transform var(--duration-normal) var(--ease-default);
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.8);
}

.sp-progress-container:hover .sp-progress-dot {
  transform: scaleX(1);
  width: 2px;
}

/* ?????? */
.sp-preview-hint {
  position: absolute;
  bottom: 20px;
  transform: translateX(-50%);
  pointer-events: none;
  animation: hint-fade var(--duration-normal) var(--ease-default);
}

@keyframes hint-fade {
  from { opacity: 0; transform: translateX(-50%) translateY(5px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

.sp-preview-hint-inner {
  padding: 3px 8px;
  background: rgba(10, 10, 10, 0.95);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(var(--sp-primary-rgb), 0.25);
  color: #fff;
  font-size: 10px;
  font-family: var(--sp-font-mono);
  border-radius: 4px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.6);
}

.sp-preview-thumbnail {
  width: 120px;
  height: 68px;
  margin-bottom: 4px;
  border-radius: 3px;
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

/* ????????*/
.sp-controls-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 36px;
  margin-top: 0;
}

.sp-controls-left, .sp-controls-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ???? */
.sp-quality-tag {
  font-family: var(--sp-font-mono);
  font-size: 10px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.7);
  padding: 2px 6px;
  border: 1px solid transparent;
  border-radius: 3px;
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-default);
  background: transparent;
  letter-spacing: 0.05em;
  margin-right: 4px;
}

.sp-quality-tag:hover,
.sp-quality-tag.is-active {
  color: var(--sp-primary, #d3d4d8);
  border-color: var(--sp-border);
  background: var(--sp-bg-hover);
}

/* ?????? */
.sp-icon-btn {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-slow) var(--ease-out);
  position: relative;
}

.sp-icon-btn::after {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--sp-bg-hover);
  border: 1px solid var(--sp-border);
  border-radius: 6px;
  transform: scale(0.85);
  opacity: 0;
  transition: all var(--duration-normal) var(--ease-default);
}

.sp-icon-btn:hover {
  color: var(--sp-primary, #d3d4d8);
  transform: translateY(-1px);
}

.sp-icon-btn:hover::after {
  transform: scale(1);
  opacity: 1;
}

.sp-icon-btn :deep(svg) {
  width: 18px;
  height: 18px;
  filter: drop-shadow(0 0 4px rgba(0,0,0,0.4));
}

/* ???? */
.sp-time-display {
  font-family: var(--sp-font-mono);
  font-size: 12px;
  color: #fff;
  display: flex;
  align-items: center;
  padding-left: 6px;
  letter-spacing: 0.02em;
  font-weight: 700;
}

.sp-time-separator {
  margin: 0 6px;
  opacity: 0.2;
}

.sp-time-total {
  opacity: 0.4;
}

/* ???? */
.sp-volume-group {
  display: flex;
  align-items: center;
  gap: 2px;
}

.sp-volume-slider-wrap {
  width: 0;
  overflow: hidden;
  opacity: 0;
  transition: all var(--duration-slow) var(--ease-out);
  height: 32px;
  display: flex;
  align-items: center;
}

.sp-volume-group:hover .sp-volume-slider-wrap,
.sp-volume-group.is-active .sp-volume-slider-wrap {
  width: 76px;
  opacity: 1;
  padding: 0 8px;
}

.sp-volume-bar {
  width: 100%;
  height: 3px;
  background: rgba(255, 255, 255, 0.12);
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

.sp-volume-glow {
  position: absolute;
  top: 0;
  right: 0;
  height: 100%;
  width: 100%;
  box-shadow: 0 0 10px rgba(var(--sp-primary-rgb), 0.6);
}

.sp-volume-percent {
  font-family: var(--sp-font-mono);
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  min-width: 36px;
  text-align: right;
  flex-shrink: 0;
}

/* ????????*/
.sp-settings-pop {
  position: absolute;
  bottom: 52px;
  right: 12px;
  width: 220px;
  background: var(--sp-menu-bg);
  backdrop-filter: blur(24px);
  border: 1px solid var(--sp-menu-border);
  border-radius: 8px;
  padding: 6px;
  z-index: 100;
  box-shadow: var(--sp-menu-shadow);
  overflow: hidden;
}

.sp-settings-pop::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(var(--sp-primary-rgb), 0.05) 50%);
  background-size: 100% 4px;
  pointer-events: none;
  opacity: 0.2;
}

.sp-menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  color: var(--sp-text-secondary);
  font-size: 12px;
  font-family: var(--sp-font-family);
  border-radius: 6px;
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-default);
  position: relative;
  z-index: 1;
  letter-spacing: 0.03em;
}

.sp-menu-item:hover {
  background: var(--sp-menu-item-hover-bg);
  color: var(--sp-text-strong);
}

.sp-menu-item.is-active {
  color: var(--sp-primary);
  background: var(--sp-menu-item-active-bg);
}

.sp-menu-val {
  font-size: 11px;
  opacity: 0.6;
  font-family: var(--sp-font-mono);
}

.sp-simple-switch {
  width: 30px;
  height: 16px;
  background: var(--sp-switch-bg);
  border-radius: 8px;
  position: relative;
  transition: background var(--duration-normal) var(--ease-default);
  border: 1px solid var(--sp-border);
}

.sp-simple-switch.is-on { 
  background: var(--sp-primary);
  border-color: rgba(var(--sp-primary-rgb), 0.5);
}

.sp-simple-switch::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 10px;
  height: 10px;
  background: #fff;
  border-radius: 50%;
  transition: transform var(--duration-normal) var(--ease-default);
}

.sp-simple-switch.is-on::after { transform: translateX(14px); }

/* ?????? */
.sp-subtitle-color-preview {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  border: 1px solid rgba(255,255,255,0.2);
  flex-shrink: 0;
}

/* ?????? */
.sp-subtitle-color-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 6px;
  padding: 8px 14px;
}

.sp-subtitle-color-swatch {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all var(--duration-normal) var(--ease-default);
  margin: 0 auto;
}

.sp-subtitle-color-swatch:hover {
  transform: scale(1.15);
  box-shadow: 0 0 6px rgba(255,255,255,0.3);
}

.sp-subtitle-color-swatch.is-active {
  border-color: var(--sp-primary);
  box-shadow: 0 0 8px rgba(var(--sp-primary-rgb), 0.5);
}

/* ????????*/
.sp-subtitle-opacity-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
}

.sp-subtitle-opacity-label {
  font-size: 12px;
  color: var(--sp-text-secondary);
  width: 52px;
  flex-shrink: 0;
}

.sp-subtitle-opacity-slider {
  flex: 1;
}

.sp-opacity-rail {
  position: relative;
  height: 3px;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 1.5px;
  cursor: pointer;
}

.sp-opacity-fill {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  background: var(--sp-primary);
  border-radius: 1.5px;
}

.sp-opacity-thumb {
  position: absolute;
  top: 50%;
  width: 12px;
  height: 12px;
  background: #fff;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 4px rgba(0,0,0,0.4);
  cursor: grab;
}

.sp-opacity-thumb:active {
  cursor: grabbing;
  transform: translate(-50%, -50%) scale(1.2);
}

.sp-subtitle-opacity-val {
  font-size: 11px;
  color: var(--sp-text-secondary);
  font-family: var(--sp-font-mono);
  width: 32px;
  text-align: right;
  flex-shrink: 0;
}

/* Subtitle offset controls */
.sp-offset-controls {
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: var(--sp-font-mono);
}

.sp-offset-btn {
  padding: 2px 6px;
  background: var(--sp-bg-hover);
  border: 1px solid var(--sp-border);
  border-radius: 3px;
  color: var(--sp-text-secondary);
  font-size: 11px;
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-default);
  font-family: var(--sp-font-mono);
}

.sp-offset-btn:hover {
  color: var(--sp-primary);
  border-color: var(--sp-primary);
}

.sp-offset-value {
  font-size: 11px;
  color: var(--sp-text-strong);
  min-width: 36px;
  text-align: center;
}

/* ???? */
.sp-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  z-index: 50;
  /* Loading overlay is purely presentational; let pointer events (click/dblclick)
     pass through to the video/container underneath so fullscreen toggling still
     works while the video is loading. */
  pointer-events: none;
}

.sp-loader {
  width: 28px;
  height: 28px;
  position: relative;
}

.sp-loader-ring {
  position: absolute;
  inset: 0;
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-top-color: rgba(255, 255, 255, 0.6);
  border-radius: 50%;
  animation: sp-loader-spin 0.8s linear infinite;
}

.sp-loading-text {
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  font-family: var(--sp-font-family);
  margin-top: 8px;
}

@keyframes sp-loader-spin {
  to { transform: rotate(360deg); }
}

/* ?????????*/
.sp-loading-fade-enter-active,
.sp-loading-fade-leave-active {
  transition: opacity var(--duration-slow) var(--ease-default);
}

.sp-loading-fade-enter-from,
.sp-loading-fade-leave-to {
  opacity: 0;
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
  opacity: 0.35;
  cursor: not-allowed;
  filter: grayscale(1);
}

/* Error overlay */
.sp-error-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 60;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
}

.sp-error-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 32px 24px;
  max-width: 320px;
  text-align: center;
}

.sp-error-icon-svg {
  width: 36px;
  height: 36px;
  color: var(--sp-primary, #d3d4d8);
  opacity: 0.7;
}

.sp-error-title {
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.sp-error-message {
  color: rgba(255, 255, 255, 0.55);
  font-size: 12px;
  line-height: 1.5;
}

.sp-error-actions {
  margin-top: 4px;
}

.sp-error-retry-btn {
  padding: 6px 18px;
  background: var(--sp-primary, #d3d4d8);
  color: #000;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity var(--duration-fast) var(--ease-default);
  letter-spacing: 0.03em;
}

.sp-error-retry-btn:hover {
  opacity: 0.85;
}

/* ===== Fullscreen Features CSS ===== */

/* Video info overlay */
.sp-video-info-overlay {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 30;
  max-width: 50%;
  pointer-events: none;
}

.sp-video-info-title {
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  font-family: var(--sp-font-family);
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.8);
  line-height: 1.3;
  margin-bottom: 4px;
}

.sp-video-info-meta {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  font-family: var(--sp-font-mono);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6);
}

.sp-info-fade-enter-active,
.sp-info-fade-leave-active {
  transition: opacity 0.4s ease;
}

.sp-info-fade-enter-from,
.sp-info-fade-leave-to {
  opacity: 0;
}

/* Sleep timer badge */
.sp-sleep-badge {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 30;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(var(--sp-primary-rgb), 0.25);
  border-radius: 16px;
  color: var(--sp-primary);
  font-family: var(--sp-font-mono);
  font-size: 12px;
  font-weight: 700;
}

.sp-sleep-badge :deep(svg) {
  width: 14px;
  height: 14px;
}

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
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(var(--sp-primary-rgb), 0.4);
  border-radius: 16px;
  color: var(--sp-primary);
  font-family: var(--sp-font-mono);
  font-size: 11px;
  font-weight: 700;
  animation: abloop-pulse 2s ease-in-out infinite;
}

.sp-abloop-indicator :deep(svg) {
  width: 14px;
  height: 14px;
}

.sp-abloop-times {
  opacity: 0.6;
  font-weight: 400;
}

@keyframes abloop-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

/* Up next overlay */
.sp-upnext-overlay {
  position: absolute;
  bottom: 64px;
  right: 16px;
  z-index: 30;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(12px);
  border: 1px solid var(--sp-border);
  border-radius: 8px;
  min-width: 200px;
  cursor: default;
}

.sp-upnext-label {
  color: rgba(255, 255, 255, 0.5);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-family: var(--sp-font-mono);
  margin-bottom: 4px;
}

.sp-upnext-title {
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  line-height: 1.3;
}

.sp-upnext-countdown {
  color: var(--sp-primary);
  font-size: 11px;
  font-family: var(--sp-font-mono);
  margin-bottom: 8px;
}

.sp-upnext-btn {
  width: 100%;
  padding: 6px 0;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
  transition: background var(--duration-fast);
}

.sp-upnext-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

/* Chapter overlay */
.sp-chapter-overlay {
  position: absolute;
  top: 0;
  right: 16px;
  z-index: 35;
  max-height: 60vh;
  width: 240px;
  overflow-y: auto;
  padding: 8px;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(12px);
  border: 1px solid var(--sp-border);
  border-radius: 0 0 8px 8px;
}

.sp-chapter-overlay-title {
  color: rgba(255, 255, 255, 0.5);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-family: var(--sp-font-mono);
  padding: 4px 8px 6px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  margin-bottom: 4px;
}

.sp-chapter-overlay-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: background var(--duration-fast);
}

.sp-chapter-overlay-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.sp-chapter-overlay-item.is-active {
  background: rgba(var(--sp-primary-rgb), 0.15);
}

.sp-chapter-overlay-time {
  color: var(--sp-primary);
  font-family: var(--sp-font-mono);
  font-size: 11px;
  min-width: 50px;
  flex-shrink: 0;
}

.sp-chapter-overlay-name {
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

</style>
