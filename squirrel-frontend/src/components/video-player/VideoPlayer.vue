<template>
  <div 
    ref="containerRef"
    class="sp-player"
    :class="[`sp-theme-${theme}`, { 'is-active': store.controlsVisible }]"
    @pointerenter="onPointerEnter"
    @pointerleave="onPointerLeave"
    @pointermove="onPointerMove"
    @pointerdown="handlePointerDown"
    @focus="markPlayerActive"
    @keydown="handleKeyDown"
    tabindex="0"
  >
    <!-- ????????-->
    <div class="sp-vignette-overlay"></div>

    <!-- ???? -->
    <video
      ref="videoRef"
      class="sp-video"
      :muted="store.muted"
      :autoplay="store.autoplay"
      :loop="store.loop"
      crossorigin="anonymous"
      playsinline
      webkit-playsinline
      @click="handleVideoClick"
      @dblclick="toggleFullscreen"
    />
    <!-- ?? HUD ????-->
    <transition name="sp-hud-fade">
      <div v-if="centralHud.visible" class="sp-central-hud">
        <div class="sp-central-hud-content">
          <PlayerIcon :name="centralHud.icon" class="sp-central-hud-icon" />
          <div class="sp-central-hud-value">{{ centralHud.value }}</div>
        </div>
      </div>
    </transition>

    <!-- ?????-->
    <Transition name="sp-loading-fade" @after-enter="onLoadingEnter" @after-leave="onLoadingLeave">
      <div v-if="showLoadingOverlay" class="sp-loading">
        <div class="sp-loader">
          <div class="sp-loader-ring"></div>
        </div>
      </div>
    </Transition>

    <!-- ??????-->
    <transition name="sp-ui-fade">
      <div v-show="store.controlsVisible" class="sp-controls-wrapper" data-player-interactive>
        <!-- ?????? -->
        <div class="sp-gradient-overlay"></div>

        <div class="sp-controls-content">
          <!-- ????????-->
          <div class="sp-progress-container">
            <div ref="progressAreaRef"
                 class="sp-progress-area" 
                 @pointerdown.prevent="onProgressPointerDown"
                 @pointermove="onProgressPointerMove"
                 @pointerleave="onProgressPointerLeave"
                 @pointerup="onProgressPointerUp"
                 @pointercancel="onProgressPointerUp">
              <div class="sp-progress-rail">
                <div class="sp-progress-buffered" :style="{ width: `${store.bufferedProgress}%` }"></div>
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
                      <button class="sp-clip-marker-tooltip__del" @click.stop="deleteMarkerFromPanel(marker)">?</button>
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
                <div class="sp-preview-hint-inner">
                  {{ formatTime(previewTime) }}
                </div>
              </div>
            </div>
          </div>

          <!-- ??????-->
          <div class="sp-controls-main">
            <div class="sp-controls-left">
              <button class="sp-icon-btn" @click="emit('prev')" :title="t('prev')" :disabled="!props.hasPrev">
                <PlayerIcon name="prev" />
              </button>
              <button class="sp-icon-btn sp-btn--play" @click="togglePlay" :title="isPlaying ? t('pause') : t('play')">
                <PlayerIcon :name="isPlaying ? 'pause' : 'play'" />
              </button>
              <button class="sp-icon-btn" @click="emit('next')" :title="t('next')" :disabled="!props.hasNext">
                <PlayerIcon name="next" />
              </button>
              
              <div class="sp-volume-group" :class="{ 'is-active': isVolumeScrubbing }">
                <button class="sp-icon-btn" @click="toggleMute" :title="t('mute')">
                  <PlayerIcon :name="volumeIconName" />
                </button>
                <div class="sp-volume-slider-wrap" 
                     @pointerdown.prevent="onVolumePointerDown"
                     @pointermove="onVolumePointerMove"
                     @pointerup="onVolumePointerUp">
                  <div class="sp-volume-bar">
                    <div class="sp-volume-fill" :style="{ width: `${isMuted ? 0 : volume}%` }">
                      <div class="sp-volume-glow"></div>
                    </div>
                  </div>
                </div>
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
              <button class="sp-icon-btn" @click.stop="toggleSettingsMenu" :title="t('settings')">
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
      <div v-if="showQualityMenu" class="sp-settings-pop sp-quality-pop" data-player-interactive>
        <div class="sp-menu-list">
          <div
            v-for="q in displayedQualities"
            :key="q.id"
            class="sp-menu-item"
            :class="{ 'is-active': isQualityActive(q) }"
            @click="handleQualitySelect(q)"
          >
            {{ q.label }}
          </div>
        </div>
      </div>
    </transition>

    <!-- ???? -->
    <transition name="sp-ui-fade">
      <div v-if="showSettingsMenu" class="sp-settings-pop" ref="settingsPopupRef" data-player-interactive>
        <template v-if="settingsView === 'main'">
          <div class="sp-menu-list">
            <div class="sp-menu-item" @click="toggleAutoplayNext">
              <span>{{ t('autoplayNext') }}</span>
              <div class="sp-simple-switch" :class="{ 'is-on': store.autoplayNext }"></div>
            </div>
            <div class="sp-menu-item" @click="toggleLoop">
              <span>{{ t('loop') }}</span>
              <div class="sp-simple-switch" :class="{ 'is-on': store.loop }"></div>
            </div>
            <div class="sp-menu-item" @click="settingsView = 'speed'">
              <span>{{ t('playbackSpeed') }}</span>
              <span class="sp-menu-val">{{ store.playbackRate }}x</span>
            </div>
            <div v-if="displayedQualities.length > 0" class="sp-menu-item" @click="settingsView = 'quality'">
              <span>{{ t('quality') }}</span>
              <span class="sp-menu-val">{{ qualityMenuLabel }}</span>
            </div>
            <div v-if="subtitleTracks.length > 0" class="sp-menu-item" @click="settingsView = 'subtitleStyle'">
              <span>{{ t('subtitleSettings') }}</span>
              <span class="sp-menu-val">{{ subtitleMenuLabel }}</span>
            </div>
          </div>
        </template>
        <template v-else-if="settingsView === 'speed'">
          <div class="sp-menu-item" style="opacity: 0.5" @click="settingsView = 'main'">
            <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ t('playbackSpeed') }}
          </div>
          <div class="sp-menu-list">
            <div v-for="rate in playbackRates" :key="rate" 
                 class="sp-menu-item" :class="{ 'is-active': store.playbackRate === rate }"
                 @click="handleSpeedSelect(rate)">
              {{ rate }}x
            </div>
          </div>
        </template>
        <template v-else-if="settingsView === 'quality'">
          <div class="sp-menu-item" style="opacity: 0.5" @click="settingsView = 'main'">
            <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ t('quality') }}
          </div>
          <div class="sp-menu-list">
            <div v-for="q in displayedQualities" :key="q.id" 
                 class="sp-menu-item" :class="{ 'is-active': isQualityActive(q) }"
                 @click="handleQualitySelect(q)">
              {{ q.label }}
            </div>
          </div>
        </template>
        <template v-else-if="settingsView === 'subtitles'">
          <div class="sp-menu-item" style="opacity: 0.5" @click="settingsView = 'main'">
            <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ t('subtitleSettings') }}
          </div>
          <div class="sp-menu-list">
            <div
              class="sp-menu-item"
              :class="{ 'is-active': !store.subtitlesEnabled || !currentSubtitle }"
              @click="handleSubtitleDisable"
            >
              {{ t('subtitlesOff') }}
            </div>
            <div
              v-for="track in subtitleTracks"
              :key="track.id"
              class="sp-menu-item"
              :class="{ 'is-active': store.subtitlesEnabled && currentSubtitle?.id === track.id }"
              @click="handleSubtitleSelect(track)"
            >
              {{ track.label }}
            </div>
          </div>
        </template>
        <template v-else-if="settingsView === 'subtitleStyle'">
          <div class="sp-menu-item" style="opacity: 0.5" @click="settingsView = 'subtitles'">
            <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ t('subtitleSettings') }}
          </div>
          <div class="sp-menu-list">
            <!-- ?? -->
            <div class="sp-menu-item" @click="settingsView = 'subtitlePreset'">
              <span>{{ t('preset') }}</span>
              <span class="sp-menu-val">{{ currentPresetLabel }}</span>
            </div>
            <!-- ???? -->
            <div class="sp-menu-item" @click="settingsView = 'subtitleFontSize'">
              <span>{{ t('fontSize') }}</span>
              <span class="sp-menu-val">{{ subtitleStyleLabel('fontSize', subtitleStyle.fontSize || 'medium', fontSizeOptions) }}</span>
            </div>
            <!-- ???? -->
            <div class="sp-menu-item" @click="settingsView = 'subtitleColor'">
              <span>{{ t('fontColor') }}</span>
              <span class="sp-subtitle-color-preview" :style="{ background: subtitleStyle.color || '#ffffff' }"></span>
            </div>
            <!-- ???? -->
            <div class="sp-menu-item" @click="settingsView = 'subtitleBg'">
              <span>{{ t('backgroundColor') }}</span>
              <span class="sp-subtitle-color-preview" :style="{ background: subtitleStyle.backgroundColor || 'rgba(0,0,0,0.8)' }"></span>
            </div>
            <!-- ???? -->
            <div class="sp-menu-item" @click="settingsView = 'subtitlePosition'">
              <span>{{ t('position') }}</span>
              <span class="sp-menu-val">{{ subtitleStyle.position === 'top' ? t('positionTop') : t('positionBottom') }}</span>
            </div>
          </div>
        </template>
        <template v-else-if="settingsView === 'subtitleFontSize'">
          <div class="sp-menu-item" style="opacity: 0.5" @click="settingsView = 'subtitleStyle'">
            <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ t('fontSize') }}
          </div>
          <div class="sp-menu-list">
            <div
              v-for="opt in fontSizeOptions"
              :key="opt.value"
              class="sp-menu-item"
              :class="{ 'is-active': (subtitleStyle.fontSize || 'medium') === opt.value }"
              @click="handleSubtitleStyleChange('fontSize', opt.value)"
            >
              {{ opt.label }}
            </div>
          </div>
        </template>
        <template v-else-if="settingsView === 'subtitleColor'">
          <div class="sp-menu-item" style="opacity: 0.5" @click="settingsView = 'subtitleStyle'">
            <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ t('fontColor') }}
          </div>
          <div class="sp-subtitle-color-grid">
            <div
              v-for="c in subtitleColorOptions"
              :key="c.value"
              class="sp-subtitle-color-swatch"
              :class="{ 'is-active': subtitleStyle.color === c.value }"
              :style="{ background: c.value }"
              :title="c.label"
              @click="handleSubtitleStyleChange('color', c.value)"
            ></div>
          </div>
        </template>
        <template v-else-if="settingsView === 'subtitleBg'">
          <div class="sp-menu-item" style="opacity: 0.5" @click="settingsView = 'subtitleStyle'">
            <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ t('backgroundColor') }}
          </div>
          <div class="sp-subtitle-color-grid">
            <div
              v-for="c in subtitleBgOptions"
              :key="c.value"
              class="sp-subtitle-color-swatch"
              :class="{ 'is-active': subtitleStyle.backgroundColor === c.value }"
              :style="{ background: c.value }"
              :title="c.label"
              @click="handleSubtitleStyleChange('backgroundColor', c.value)"
            ></div>
          </div>
          <div class="sp-subtitle-opacity-row">
            <span class="sp-subtitle-opacity-label">{{ t('opacity') }}</span>
            <div class="sp-subtitle-opacity-slider">
              <div class="sp-opacity-rail" ref="opacityRailRef" @pointerdown="onOpacityPointerDown">
                <div class="sp-opacity-fill" :style="{ width: `${(subtitleStyle.backgroundOpacity ?? 0.8) * 100}%` }"></div>
                <div class="sp-opacity-thumb" :style="{ left: `${(subtitleStyle.backgroundOpacity ?? 0.8) * 100}%` }"></div>
              </div>
            </div>
            <span class="sp-subtitle-opacity-val">{{ Math.round((subtitleStyle.backgroundOpacity ?? 0.8) * 100) }}%</span>
          </div>
        </template>
        <template v-else-if="settingsView === 'subtitlePreset'">
          <div class="sp-menu-item" style="opacity: 0.5" @click="settingsView = 'subtitleStyle'">
            <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ t('preset') }}
          </div>
          <div class="sp-menu-list">
            <div
              v-for="preset in subtitlePresets"
              :key="preset.id"
              class="sp-menu-item"
              :class="{ 'is-active': isPresetActive(preset) }"
              @click="handlePresetSelect(preset.id)"
            >
              {{ preset.label }}
            </div>
          </div>
        </template>
        <template v-else-if="settingsView === 'subtitlePosition'">
          <div class="sp-menu-item" style="opacity: 0.5" @click="settingsView = 'subtitleStyle'">
            <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ t('position') }}
          </div>
          <div class="sp-menu-list">
            <div
              class="sp-menu-item"
              :class="{ 'is-active': subtitleStyle.position === 'bottom' }"
              @click="handleSubtitleStyleChange('position', 'bottom')"
            >
              {{ t('positionBottom') }}
            </div>
            <div
              class="sp-menu-item"
              :class="{ 'is-active': subtitleStyle.position === 'top' }"
              @click="handleSubtitleStyleChange('position', 'top')"
            >
              {{ t('positionTop') }}
            </div>
          </div>
        </template>
      </div>
    </transition>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { formatTime } from '@/utils/dateFormat'
import { usePlayer, type PlayerOptions } from './runtime/usePlayer'
import {
  getNextControlsVisibilityOnTouchTap,
  shouldHandlePointerVisibility,
  shouldAutoHideControls,
  shouldTogglePlayOnVideoClick
} from './runtime/mobileControls'
import {
  createPointMarkerDraft,
  createSegmentMarkerDraft,
  isClipMarkerActive,
  isPointMarker,
  resolveClipMarkerVideoId,
} from './runtime/clipMarkers'
import type { MediaSource, SubtitleTrack } from './core'
import type { ThemeName } from './themes'
import type { IconName } from './core/useIcons'
import type { VideoClipMarker } from '@/types/videoClipMarker'
import { createVideoClipMarker, deleteVideoClipMarker, updateVideoClipMarker, uploadVideoClipMarkerPreview } from '@/api/videoClipMarkers'
import PlayerIcon from './PlayerIcon.vue'

// ????????import './themes/variables.css'
import './themes/dark.css'
import './themes/light.css'

interface Props {
  source?: MediaSource | null
  videoId?: string | number | null
  subtitles?: SubtitleTrack[]
  clipMarkers?: VideoClipMarker[]
  title?: string
  autoplay?: boolean
  adapter?: PlayerOptions['adapter'] | null
  i18nOptions?: PlayerOptions['i18nOptions']
  theme?: ThemeName
  initialTime?: number
  widescreen?: boolean
  externalLoading?: boolean
  hasPrev?: boolean
  hasNext?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  source: null,
  videoId: null,
  subtitles: () => [],
  clipMarkers: () => [],
  title: '',
  autoplay: true,
  adapter: null,
  i18nOptions: undefined,
  theme: 'dark',
  widescreen: false,
  externalLoading: false,
  hasPrev: false,
  hasNext: false,
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
])

const {
  store, videoElement, containerElement, isPlaying, currentTime, duration, volume, isMuted, isFullscreen,
  play, pause, seek, setVolume, toggleMute, setPlaybackRate, toggleFullscreen,
  togglePictureInPicture,
  subtitleTracks, currentSubtitle, subtitleStyle, subtitlePresets, setSubtitle, setSubtitleTracks, setSubtitleStyle, applySubtitlePreset, loadSource, theme, t,
  qualities, selectedCodecFamily, currentCodecFamily,
  currentQualityLabel, currentQualityId, setQuality
} = usePlayer({
  autoplay: props.autoplay,
  adapter: props.adapter ?? undefined,
  theme: props.theme,
  i18nOptions: props.i18nOptions,
  onTouchTap: () => {
    toggleControls(getNextControlsVisibilityOnTouchTap(store.controlsVisible))
  },
  onPlay: () => emit('play'),
  onPause: () => emit('pause'),
  onEnded: () => emit('ended'),
  onError: (e) => emit('error', e),
  onTimeUpdate: (time) => emit('timeupdate', time)
})

const videoRef = ref<HTMLVideoElement | null>(null)
const containerRef = ref<HTMLElement | null>(null)
const progressAreaRef = ref<HTMLElement | null>(null)
const settingsPopupRef = ref<HTMLElement | null>(null)
const opacityRailRef = ref<HTMLElement | null>(null)

// Clip Markers state
const localClipMarkers = ref<VideoClipMarker[]>([])
const clipMarkerVideoId = ref<string | number | null>(null)
const hoveredMarkerId = ref<number | null>(null)
const pendingSegmentStartTime = ref<number | null>(null)
const pendingSegmentEndTime = ref<number | null>(null)
const pendingSegmentPreviewImageDataUrl = ref<string | null>(null)

const hasPendingSegment = computed(() => pendingSegmentStartTime.value !== null)
const isSavingMarker = ref(false)
const pendingSegmentPreviewEnd = computed(() => {
  const end = pendingSegmentEndTime.value
  if (end === null) return currentTime.value
  if (pendingSegmentStartTime.value !== null && end < pendingSegmentStartTime.value) {
    return pendingSegmentStartTime.value
  }
  return end
})
const draggingMarker = ref<{
  markerId: number
  pointerId: number
  dragType: 'start' | 'end' | 'move'
  startX: number
  originalStart: number
  originalEnd: number
  previewStart: number
  previewEnd: number
  moved: boolean
} | null>(null)
let activeMarkerPointerTarget: HTMLElement | null = null
let suppressMarkerClickUntil = 0

const handleOverlaySeek = (time: number) => {
  seek(time)
  emit('clipmarkerselect', time)
}

const syncLocalClipMarkers = (markers: VideoClipMarker[]) => {
  localClipMarkers.value = [...markers].sort((a, b) => a.start_time - b.start_time)
  emit('clipmarkersupdated', localClipMarkers.value)
}

const captureCurrentFrameDataUrl = (): string | null => {
  const video = videoRef.value
  if (
    !video
    || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA
    || video.videoWidth <= 0
    || video.videoHeight <= 0
  ) {
    return null
  }

  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  const context = canvas.getContext('2d')
  if (!context) return null

  try {
    context.drawImage(video, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL('image/jpeg', 0.82)
  } catch {
    return null
  }
}

const uploadMarkerPreviewIfAvailable = async (marker: VideoClipMarker, imageDataUrl: string | null): Promise<VideoClipMarker> => {
  if (!imageDataUrl) return marker

  const { data, error } = await uploadVideoClipMarkerPreview(marker.id, {
    image_data_url: imageDataUrl,
  })

  if (error || !data) {
    return marker
  }

  return data
}

const markCurrentPoint = async () => {
  if (!clipMarkerVideoId.value || isSavingMarker.value) return
  const t = currentTime.value
  const previewImageDataUrl = captureCurrentFrameDataUrl()
  isSavingMarker.value = true
  try {
    const { data, error } = await createVideoClipMarker({
      video_id: clipMarkerVideoId.value,
      start_time: t,
      end_time: t,
    })

    isSavingMarker.value = false
    if (error || !data) {
      showCentralHud('error', error?.message || '标记失败', 'play')
      return
    }

    const markerWithPreview = await uploadMarkerPreviewIfAvailable(data, previewImageDataUrl)
    syncLocalClipMarkers([...localClipMarkers.value, markerWithPreview])
    showCentralHud('marker', `标记 ${formatTime(t)}`, 'play')
  } finally {
    isSavingMarker.value = false
  }
}

const startSegmentCapture = () => {
  if (isSavingMarker.value) return
  const t = currentTime.value
  if (!isFinite(t) || t < 0 || !duration.value) return
  const draft = createPointMarkerDraft({ currentTime: t, duration: duration.value })
  pendingSegmentStartTime.value = draft.startTime
  pendingSegmentPreviewImageDataUrl.value = captureCurrentFrameDataUrl()
  showCentralHud('marker', `起点 ${formatTime(draft.startTime)}`, 'skipBackward')
}

const finishSegmentCapture = async () => {
  if (!clipMarkerVideoId.value || pendingSegmentStartTime.value === null || isSavingMarker.value) return
  const startTime = pendingSegmentStartTime.value
  const endTime = pendingSegmentEndTime.value ?? currentTime.value
  const draft = createSegmentMarkerDraft({
    startTime,
    currentTime: endTime,
    duration: duration.value,
  })
  pendingSegmentEndTime.value = null
  const previewImageDataUrl = pendingSegmentPreviewImageDataUrl.value
  isSavingMarker.value = true

  try {
    const { data, error } = await createVideoClipMarker({
      video_id: clipMarkerVideoId.value,
      start_time: draft.startTime,
      end_time: draft.endTime,
    })

    if (error || !data) {
      pendingSegmentStartTime.value = null
      showCentralHud('error', error?.message || '保存失败', 'play')
      return
    }

    pendingSegmentStartTime.value = null
    pendingSegmentPreviewImageDataUrl.value = null
    const markerWithPreview = await uploadMarkerPreviewIfAvailable(data, previewImageDataUrl)
    syncLocalClipMarkers([...localClipMarkers.value, markerWithPreview])
    showCentralHud('segment', `片段 ${formatTime(draft.startTime)}`, 'skipForward')
  } finally {
    isSavingMarker.value = false
  }
}

const cancelSegmentCapture = () => {
  pendingSegmentStartTime.value = null
  pendingSegmentEndTime.value = null
  pendingSegmentPreviewImageDataUrl.value = null
  showCentralHud('seek', '已取消', 'play')
}

const deleteMarkerFromPanel = async (marker: { id: number }) => {
  const { error } = await deleteVideoClipMarker(marker.id)
  if (error) {
    showCentralHud('error', error.message || '删除失败', 'play')
    return
  }
  syncLocalClipMarkers(localClipMarkers.value.filter((item) => item.id !== marker.id))
  hoveredMarkerId.value = null
}

// ---- Marker drag ----
const getProgressRect = () => progressAreaRef.value?.getBoundingClientRect()

const getTimeFromPointerX = (clientX: number) => {
  const rect = getProgressRect()
  if (!rect || !duration.value) return null
  const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
  return ratio * duration.value
}

const onMarkerPointerDown = (e: PointerEvent, marker: ReturnType<typeof normalizedClipMarkers.value.find>) => {
  if (isSavingMarker.value || !marker) return
  const rect = getProgressRect()
  if (!rect) return
  const ratio = (e.clientX - rect.left) / rect.width
  const markerStartRatio = marker.startPercent / 100
  const markerEndRatio = (marker.startPercent + marker.widthPercent) / 100

  let dragType: 'start' | 'end' | 'move' = 'move'
  if (!marker.isPoint && marker.widthPercent > 0.5) {
    const startDist = Math.abs(ratio - markerStartRatio)
    const endDist = Math.abs(ratio - markerEndRatio)
    if (startDist < endDist) dragType = 'start'
    else if (endDist < startDist) dragType = 'end'
  }

  draggingMarker.value = {
    markerId: marker.id,
    pointerId: e.pointerId,
    dragType,
    startX: e.clientX,
    originalStart: marker.startTime,
    originalEnd: marker.endTime,
    previewStart: marker.startTime,
    previewEnd: marker.endTime,
    moved: false,
  }

  if (e.currentTarget instanceof HTMLElement && typeof e.currentTarget.setPointerCapture === 'function') {
    try {
      e.currentTarget.setPointerCapture(e.pointerId)
      activeMarkerPointerTarget = e.currentTarget
    } catch {
      activeMarkerPointerTarget = null
    }
  }
}

const onPointerMove = (event: PointerEvent) => {
  if (!shouldHandlePointerVisibility(event.pointerType)) return
  showControls()
}

const releaseMarkerPointerCapture = () => {
  const markerPointerId = draggingMarker.value?.pointerId
  if (!activeMarkerPointerTarget || markerPointerId === undefined || markerPointerId === null) {
    activeMarkerPointerTarget = null
    return
  }
  if (typeof activeMarkerPointerTarget.hasPointerCapture !== 'function') {
    activeMarkerPointerTarget = null
    return
  }
  if (!activeMarkerPointerTarget.hasPointerCapture(markerPointerId)) {
    activeMarkerPointerTarget = null
    return
  }

  try {
    activeMarkerPointerTarget.releasePointerCapture(markerPointerId)
  } catch {
    // Ignore browsers that reject release when capture is already gone.
  }

  activeMarkerPointerTarget = null
}

const updateDragPreview = (deltaTime: number) => {
  const d = draggingMarker.value
  if (!d) return
  const rect = getProgressRect()
  if (!rect || !duration.value) return

  const rawStart = d.originalStart + deltaTime
  const rawEnd = d.originalEnd + deltaTime

  let newStart: number, newEnd: number
  if (d.dragType === 'move') {
    const span = d.originalEnd - d.originalStart
    newStart = Math.max(0, Math.min(duration.value - span, rawStart))
    newEnd = newStart + span
  } else if (d.dragType === 'start') {
    newStart = Math.max(0, Math.min(d.originalEnd - 0.1, rawStart))
    newEnd = d.originalEnd
  } else {
    newStart = d.originalStart
    newEnd = Math.min(duration.value, Math.max(d.originalStart + 0.1, rawEnd))
  }

  d.previewStart = newStart
  d.previewEnd = newEnd
  d.moved = d.moved
    || Math.abs(newStart - d.originalStart) > 0.01
    || Math.abs(newEnd - d.originalEnd) > 0.01

  showCentralHud('seek', `${formatTime(newStart)} → ${formatTime(newEnd)}`, 'skipForward')
}

const commitDrag = () => {
  const d = draggingMarker.value
  if (!d) return
  const normMarker = normalizedClipMarkers.value.find((m) => m.id === d.markerId)
  if (!normMarker || !duration.value) {
    releaseMarkerPointerCapture()
    draggingMarker.value = null
    return
  }

  const newStart = Math.max(0, Math.min(duration.value, d.previewStart))
  const newEnd = Math.max(newStart, Math.min(duration.value, d.previewEnd))

  releaseMarkerPointerCapture()
  draggingMarker.value = null
  if (d.moved) {
    suppressMarkerClickUntil = Date.now() + 250
  }

  if (normMarker.isPoint || Math.abs(newStart - newEnd) < 0.1) {
    updateVideoClipMarker(d.markerId, { start_time: newStart, end_time: newStart }).then(({ data, error }) => {
      if (error || !data) {
        showCentralHud('error', error?.message || '更新失败', 'play')
        return
      }
      syncLocalClipMarkers(localClipMarkers.value.map((m) => m.id === d.markerId ? data : m))
      showCentralHud('marker', `标记 ${formatTime(newStart)}`, 'skipForward')
    })
    return
  }

  updateVideoClipMarker(d.markerId, { start_time: newStart, end_time: newEnd }).then(({ data, error }) => {
    if (error || !data) {
      showCentralHud('error', error?.message || '更新失败', 'play')
      return
    }
    syncLocalClipMarkers(localClipMarkers.value.map((m) => m.id === d.markerId ? data : m))
    showCentralHud('segment', `${formatTime(newStart)} → ${formatTime(newEnd)}`, 'skipForward')
  })
}

const onWindowMarkerPointerMove = (event: PointerEvent) => {
  if (!draggingMarker.value) return
  if (event.pointerId !== draggingMarker.value.pointerId) return

  const rect = getProgressRect()
  if (!rect || !duration.value) return

  const deltaX = event.clientX - draggingMarker.value.startX
  const deltaTime = (deltaX / rect.width) * duration.value
  updateDragPreview(deltaTime)
}

const onWindowMarkerPointerUp = (event: PointerEvent) => {
  if (!draggingMarker.value) return
  if (event.pointerId !== draggingMarker.value.pointerId) return
  commitDrag()
}
// ---- end marker drag ----

// Sync local markers from prop
watch(() => props.clipMarkers, (markers) => {
  localClipMarkers.value = Array.isArray(markers) ? [...markers] : []
}, { immediate: true, deep: true })

watch(() => [props.videoId, props.source] as const, ([videoId, source]) => {
  clipMarkerVideoId.value = resolveClipMarkerVideoId(videoId, source as any)
}, { immediate: true })

const showSettingsMenu = ref(false)
const showQualityMenu = ref(false)
const settingsView = ref('main')
const previewTime = ref<number | null>(null)
const previewPercent = ref(0)
const isScrubbing = ref(false)
const isVolumeScrubbing = ref(false)
const lastPointerType = ref('mouse')
const pendingWidescreenValue = ref<boolean | null>(null)
const shouldResumeAfterSourceSwap = ref(false)
const errorState = ref({ show: false, title: '', message: '', code: '', canRetry: true })
const centralHud = ref<{ visible: boolean; type: string; value: string; icon: IconName; percent: number }>({ 
  visible: false, type: '', value: '', icon: 'play', percent: 0 
})
const showLoadingOverlay = computed(() => (store.loading || props.externalLoading) && !errorState.value.show)

// Loading state control
const onLoadingEnter = () => {}
const onLoadingLeave = () => {}

let centralHudTimer: any
const showCentralHud = (type: string, value: string, icon: IconName, percent: number = 0) => {
  clearTimeout(centralHudTimer)
  centralHud.value = { visible: true, type, value, icon, percent }
  centralHudTimer = setTimeout(() => { centralHud.value.visible = false }, 1500)
}

watch(volume, (newVol, oldVol) => {
  if (Math.abs(newVol - oldVol) < 0.1) return
  showCentralHud('volume', `${Math.round(newVol)}%`, volumeIconName.value, newVol)
})

const playbackRates = [0.5, 0.75, 1, 1.25, 1.5, 2]
const fontSizeOptions = [
  { value: 'small', label: '1' },
  { value: 'medium', label: '2' },
  { value: 'large', label: '3' },
  { value: 'xlarge', label: '4' },
]
const subtitleColorOptions = [
  { value: '#ffffff', label: 'White' },
  { value: '#ffff00', label: 'Yellow' },
  { value: '#00ff00', label: 'Green' },
  { value: '#00ffff', label: 'Cyan' },
  { value: '#ff55ff', label: 'Pink' },
  { value: '#ff5500', label: 'Orange' },
]
const subtitleBgOptions = [
  { value: 'rgba(0,0,0,0.8)', label: 'Black' },
  { value: 'rgba(0,0,0,0.5)', label: 'Dark' },
  { value: 'rgba(0,0,128,0.8)', label: 'Blue' },
  { value: 'rgba(0,80,0,0.8)', label: 'Green' },
  { value: 'rgba(80,0,0,0.8)', label: 'Red' },
  { value: 'transparent', label: 'None' },
]
const subtitleStyleLabel = (key: string, value: string, options: any[]) => {
  const opt = options.find((o) => o.value === value)
  return opt ? opt.label : value
}
const progress = computed(() => duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0)
const COLORS = [
  'hsl(24 100% 50%)',
  'hsl(186 100% 50%)',
  'hsl(145 70% 50%)',
  'hsl(280 80% 60%)',
  'hsl(38 92% 55%)',
]
const normalizedClipMarkers = computed(() => {
  if (!duration.value || duration.value <= 0) return []

  return localClipMarkers.value.map((marker, index) => {
    const dragPreview = draggingMarker.value?.markerId === marker.id
      ? {
          startTime: draggingMarker.value.previewStart,
          endTime: draggingMarker.value.previewEnd,
        }
      : null
    const startTime = Math.max(
      Number(dragPreview?.startTime ?? marker.start_time) || 0,
      0
    )
    const rawEndTime = Number(dragPreview?.endTime ?? marker.end_time)
    const endTime = Number.isFinite(rawEndTime) ? Math.max(rawEndTime, startTime) : startTime
    const isPoint = isPointMarker({ startTime, endTime })
    const startPercent = Math.min((startTime / duration.value) * 100, 100)
    const widthPercent = isPoint ? 0.001 : Math.max(((endTime - startTime) / duration.value) * 100, 0.35)

    return {
      id: marker.id,
      title: marker.title,
      startTime,
      endTime,
      isPoint,
      startPercent,
      widthPercent,
      color: COLORS[index % COLORS.length],
    }
  })
})
const markerColorById = computed(() => Object.fromEntries(
  normalizedClipMarkers.value.map((marker) => [marker.id, marker.color])
))
const activeClipMarkerId = computed(() => {
  const activeMarker = normalizedClipMarkers.value.find((marker) => isClipMarkerActive(marker, currentTime.value))
  return activeMarker?.id ?? null
})
const getMarkerTitle = (marker: { title?: string | null; start_time?: number; startTime?: number; end_time?: number; endTime?: number }) => {
  if (marker.title) return marker.title
  const startTime = Number(marker.start_time ?? marker.startTime ?? 0)
  return isPointMarker(marker) ? `?? ${formatTime(startTime)}` : `?? ${formatTime(startTime)}`
}
const getMarkerTimeText = (marker: { start_time?: number; startTime?: number; end_time?: number; endTime?: number }) => {
  const startTime = Number(marker.start_time ?? marker.startTime ?? 0)
  const endTime = Number(marker.end_time ?? marker.endTime ?? startTime)
  return isPointMarker(marker)
    ? `????${formatTime(startTime)}`
    : `${formatTime(startTime)} ??${formatTime(endTime)}`
}
const volumeIconName = computed(() => (isMuted.value || volume.value === 0) ? 'volumeOff' : volume.value < 50 ? 'volumeLow' : 'volumeHigh')
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

const closeMenus = () => {
  showSettingsMenu.value = false
  showQualityMenu.value = false
  settingsView.value = 'main'
}

const togglePlay = () => isPlaying.value ? pause() : play()
const toggleSettingsMenu = () => {
  const nextVisible = !showSettingsMenu.value
  showQualityMenu.value = false
  showSettingsMenu.value = nextVisible
  settingsView.value = 'main'
}
const toggleQualityMenu = () => {
  const nextVisible = !showQualityMenu.value
  showSettingsMenu.value = false
  showQualityMenu.value = nextVisible
}
const handleSpeedSelect = (rate: number) => { setPlaybackRate(rate); closeMenus() }
const handleQualitySelect = (q: any) => { setQuality(q.id); closeMenus() }
const handleSubtitleSelect = (track: SubtitleTrack) => { setSubtitle(track); closeMenus() }
const handleSubtitleDisable = () => { setSubtitle(null); closeMenus() }
const handleSubtitleStyleChange = (key: string, value: any) => { setSubtitleStyle({ [key]: value }) }
const handlePresetSelect = (presetId: string) => { applySubtitlePreset(presetId); closeMenus() }
const handleOpacityChange = (e: PointerEvent) => {
  if (!opacityRailRef.value) return
  const rect = opacityRailRef.value.getBoundingClientRect()
  const p = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
  setSubtitleStyle({ backgroundOpacity: Math.round(p * 10) / 10 })
}
const onOpacityPointerDown = (e: PointerEvent) => {
  handleOpacityChange(e)
  const onMove = (ev: PointerEvent) => handleOpacityChange(ev)
  const onUp = () => {
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
  }
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
}
const isPresetActive = (preset: any) => {
  const s = preset.style
  const current = subtitleStyle.value
  return (
    (current.fontSize || 'medium') === (s.fontSize || 'medium') &&
    (current.color || '#ffffff') === (s.color || '#ffffff') &&
    (current.backgroundColor || 'rgba(0,0,0,0.8)') === (s.backgroundColor || 'rgba(0,0,0,0.8)') &&
    (current.backgroundOpacity ?? 0.8) === (s.backgroundOpacity ?? 0.8) &&
    (current.position || 'bottom') === (s.position || 'bottom') &&
    (current.textShadow ?? true) === (s.textShadow ?? true)
  )
}
const currentPresetLabel = computed(() => {
  const active = subtitlePresets.find(p => isPresetActive(p))
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
let hideTimer: any
const clearHideTimer = () => clearTimeout(hideTimer)
const hideControls = () => {
  clearHideTimer()
  store.setControlsVisible(false)
  previewTime.value = null
  closeMenus()
}
const syncHideTimer = () => {
  clearHideTimer()
  if (shouldAutoHideControls({
    controlsVisible: store.controlsVisible,
    isPlaying: isPlaying.value,
    isScrubbing: isScrubbing.value
  })) {
    hideTimer = setTimeout(() => hideControls(), 3000)
  }
}
const showControls = () => {
  store.setControlsVisible(true)
  syncHideTimer()
}
const toggleControls = (nextVisible = !store.controlsVisible) => {
  if (nextVisible) {
    showControls()
    return
  }

  hideControls()
}
const handleVideoClick = () => {
  if (!shouldTogglePlayOnVideoClick(lastPointerType.value)) return
  togglePlay()
}
const handleClipMarkerSelect = (marker: { id: number; startTime: number }) => {
  if (Date.now() < suppressMarkerClickUntil) return
  seek(marker.startTime)
  emit('clipmarkerselect', marker.startTime)
}

const onPointerEnter = (event: PointerEvent) => {
  if (!shouldHandlePointerVisibility(event.pointerType)) return
  showControls()
}
const onPointerLeave = (event: PointerEvent) => {
  if (!shouldHandlePointerVisibility(event.pointerType)) return
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

const stopProgressScrub = (pointerId?: number) => {
  if (activeProgressPointerId !== null && typeof pointerId === 'number' && pointerId !== activeProgressPointerId) return

  releaseProgressPointerCapture()
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
const updateVol = (e: PointerEvent) => {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  setVolume(Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100)))
}

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === ' ') { e.preventDefault(); togglePlay() }
  if (e.key === 'f') toggleFullscreen()
  if (e.key === 'ArrowLeft') { seek(currentTime.value - 10); showCentralHud('seek', '-10s', 'skipBackward') }
  if (e.key === 'ArrowRight') { seek(currentTime.value + 10); showCentralHud('seek', '+10s', 'skipForward') }
  if (e.key === 'ArrowUp') { setVolume(Math.min(100, volume.value + 5)) }
  if (e.key === 'ArrowDown') { setVolume(Math.max(0, volume.value - 5)) }
  if (e.key === 'm' || e.key === 'M') {
    if (document.activeElement?.tagName === 'INPUT') return
    e.preventDefault()
    if (e.shiftKey) {
      if (hasPendingSegment.value) {
        finishSegmentCapture()
      } else {
        startSegmentCapture()
      }
      return
    }
    markCurrentPoint()
  }
  if (e.key === 'Escape' && hasPendingSegment.value) {
    cancelSegmentCapture()
  }
  if ((e.key === 'p' || e.key === 'P') && props.hasPrev) {
    e.preventDefault()
    emit('prev')
  }
  if ((e.key === 'n' || e.key === 'N') && props.hasNext) {
    e.preventDefault()
    emit('next')
  }
}

const getCodecFamily = (codec: string | null | undefined) => {
  if (!codec) return null
  const normalized = String(codec).toLowerCase()
  if (normalized.includes('av01') || normalized.includes('av1')) return 'av1'
  if (normalized.includes('vp09') || normalized.includes('vp9')) return 'vp9'
  if (normalized.includes('avc1') || normalized.includes('avc') || normalized.includes('h264')) return 'avc'
  return normalized
}

const formatCodecFamilyLabel = (codecFamily: string | null | undefined) => {
  if (!codecFamily) return t('codec')
  const normalized = String(codecFamily).toLowerCase()
  if (normalized === 'av1') return 'AV1'
  if (normalized === 'vp9') return 'VP9'
  if (normalized === 'avc') return 'AVC'
  return normalized.toUpperCase()
}

const isQualityActive = (quality: { id: string | number }) => (
  resolvedCurrentQuality.value !== null
    && String(resolvedCurrentQuality.value.id) === String(quality.id)
)

const markPlayerActive = () => {}
const handlePointerDown = (event: PointerEvent) => {
  lastPointerType.value = event.pointerType || 'mouse'
}

watch(isPlaying, (playing) => {
  if (!playing) {
    showControls()
    return
  }

  syncHideTimer()
})

watch(isFullscreen, (fullscreen) => {
  emit('fullscreenChange', fullscreen)

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

onMounted(() => { window.addEventListener('keydown', handleKeyDown) })
onMounted(() => {
  window.addEventListener('pointermove', onWindowMarkerPointerMove)
  window.addEventListener('pointerup', onWindowMarkerPointerUp)
  window.addEventListener('pointercancel', onWindowMarkerPointerUp)
  window.addEventListener('pointermove', onWindowProgressPointerMove)
  window.addEventListener('pointerup', onWindowProgressPointerUp)
  window.addEventListener('pointercancel', onWindowProgressPointerUp)
})
onUnmounted(() => {
  clearHideTimer()
  clearInitialTimeListener()
  clearResumeAfterSourceSwapListener()
  releaseMarkerPointerCapture()
  releaseProgressPointerCapture()
  window.removeEventListener('pointermove', onWindowMarkerPointerMove)
  window.removeEventListener('pointerup', onWindowMarkerPointerUp)
  window.removeEventListener('pointercancel', onWindowMarkerPointerUp)
  window.removeEventListener('pointermove', onWindowProgressPointerMove)
  window.removeEventListener('pointerup', onWindowProgressPointerUp)
  window.removeEventListener('pointercancel', onWindowProgressPointerUp)
  window.removeEventListener('keydown', handleKeyDown)
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
  width: 100%;
  height: 100%;
  object-fit: contain;
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
}

.sp-central-hud-content {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(8px);
  padding: 8px 16px;
  border-radius: 20px;
  border: 1px solid var(--sp-border);
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}

.sp-central-hud-icon {
  width: 20px;
  height: 20px;
  color: var(--sp-primary);
}

.sp-central-hud-value {
  color: #fff;
  font-family: var(--sp-font-mono);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.sp-hud-fade-enter-active, .sp-hud-fade-leave-active {
  transition:
    opacity var(--duration-fast) var(--ease-default),
    transform var(--duration-fast) var(--ease-default);
}

.sp-hud-fade-enter-from { opacity: 0; transform: translate(-50%, -30%) scale(0.95); }
.sp-hud-fade-leave-to { opacity: 0; transform: translate(-50%, -70%) scale(1.05); }

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
  text-shadow: 0 0 4px rgba(255, 77, 0, 0.4);
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
  background: var(--sp-primary, #ff4d00);
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
  color: var(--sp-primary, #ff4d00);
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
  color: var(--sp-primary, #ff4d00);
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
  animation: spin var(--duration-slow) linear infinite;
}

@keyframes spin {
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

</style>
