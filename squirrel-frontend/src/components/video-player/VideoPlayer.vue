<template>
  <div 
    ref="containerRef"
    class="sp-player"
    :class="[`sp-theme-${theme}`]"
    @pointerenter="onPointerEnter"
    @pointerleave="onPointerLeave"
    @pointermove="onPointerMove"
    @keydown="handleKeyDown"
    tabindex="0"
    role="application"
    :aria-label="t('videoPlayer')"
  >
    <!-- 加载状态 -->
    <div v-if="store.loading && store.loadingStage !== 'buffering' && !errorState.show" class="sp-loading sp-loading--stacked" role="status" aria-live="polite">
      <div class="sp-spinner-arc" aria-hidden="true">
        <svg class="sp-spinner-arc-svg" viewBox="0 0 100 100" focusable="false">
          <circle class="sp-spinner-arc-circle" cx="50" cy="50" r="42" />
        </svg>
      </div>
      <div class="sp-loading-text">{{ store.loadingStatusText }}</div>
    </div>

    <!-- 视频元素 -->
    <video
      ref="videoRef"
      class="sp-video"
      :poster="video?.thumbnail"
      :muted="store.muted"
      :autoplay="store.autoplay"
      :loop="store.loop"
      crossorigin="anonymous"
      playsinline
      webkit-playsinline
      @click="handleVideoClick"
      @dblclick="toggleFullscreen"
    />

    <!-- 字幕容器 (由插件管理) -->

    <!-- 缓冲指示器 -->
    <div v-if="isBuffering && !errorState.show" class="sp-buffering sp-loading--stacked sp-loading--buffering" role="status" aria-live="polite">
      <div class="sp-spinner-arc" aria-hidden="true">
        <svg class="sp-spinner-arc-svg" viewBox="0 0 100 100" focusable="false">
          <circle class="sp-spinner-arc-circle" cx="50" cy="50" r="42" />
        </svg>
      </div>
    </div>


    <div v-if="errorState.show" class="sp-error-overlay sp-error-overlay--centered" @click.stop>
      <div class="sp-error-panel" role="alert" aria-live="polite">
        <div class="sp-error-title">{{ errorState.title }}</div>
        <div v-if="errorState.message" class="sp-error-message">{{ errorState.message }}</div>
        <div v-if="errorState.code" class="sp-error-code">{{ errorState.code }}</div>
        <div class="sp-error-actions">
          <button v-if="errorState.canRetry" class="sp-error-btn" @click="handleRetry">{{ t('retry') }}</button>
          <button class="sp-error-btn sp-error-btn--ghost" @click="handleDismissError">{{ t('dismiss') }}</button>
        </div>
      </div>
    </div>

    <!-- 控制栏 -->
    <transition name="sp-fade">
      <div v-show="store.controlsVisible" class="sp-controls" :class="{ 'sp-controls--error': errorState.show }">
        <!-- 进度条 -->
        <div class="sp-progress-container">
          <div
            class="sp-progress"
            :class="{ 'sp-progress--scrubbing': isScrubbing }"
            @pointerdown.prevent="onProgressPointerDown"
            @pointermove="onProgressPointerMove"
            @pointerleave="onProgressPointerLeave"
            @pointerup="onProgressPointerUp"
            @pointercancel="onProgressPointerUp"
          >
            <div class="sp-progress-buffered" :style="{ width: `${store.bufferedProgress}%` }"></div>
            <div class="sp-progress-played" :style="{ width: `${progress}%` }"></div>
            <div class="sp-progress-thumb" :style="{ left: `${progress}%` }"></div>
          </div>
          <!-- 预览时间 -->
          <div v-if="previewTime !== null" class="sp-progress-preview" :style="{ left: `${previewPercent}%` }">
            {{ formatTime(previewTime) }}
          </div>
        </div>

        <!-- 控制按钮行 -->
        <div class="sp-controls-row">
          <!-- 左侧控件 -->
          <div class="sp-controls-left">
            <!-- 播放/暂停 -->
            <button
              class="sp-btn sp-btn--play"
              @click="togglePlay"
              @mouseenter="onControlTooltipEnter($event, isPlaying ? t('pause') : t('play'), 'K')"
              @mouseleave="hideControlTooltip"
              @focus="onControlTooltipEnter($event, isPlaying ? t('pause') : t('play'), 'K')"
              @blur="hideControlTooltip"
              :aria-label="isPlaying ? t('pause') : t('play')"
            >
              <PlayerIcon :name="isPlaying ? 'pause' : 'play'" />
            </button>

            <!-- 上一个/下一个 -->
            <button
              v-if="hasPrev"
              class="sp-btn"
              @click="$emit('prev-video')"
              @mouseenter="onControlTooltipEnter($event, t('previousVideo'))"
              @mouseleave="hideControlTooltip"
              @focus="onControlTooltipEnter($event, t('previousVideo'))"
              @blur="hideControlTooltip"
              :aria-label="t('previousVideo')"
            >
              <PlayerIcon name="previous" />
            </button>
            <button
              v-if="hasNext"
              class="sp-btn"
              @click="$emit('next-video')"
              @mouseenter="onControlTooltipEnter($event, t('nextVideo'))"
              @mouseleave="hideControlTooltip"
              @focus="onControlTooltipEnter($event, t('nextVideo'))"
              @blur="hideControlTooltip"
              :aria-label="t('nextVideo')"
            >
              <PlayerIcon name="next" />
            </button>

            <!-- 音量 -->
            <div class="sp-volume" :class="{ 'is-dragging': isVolumeScrubbing }">
              <button
                class="sp-btn"
                @click="toggleMute"
                @mouseenter="onControlTooltipEnter($event, isMuted ? t('unmute') : t('mute'), 'M')"
                @mouseleave="hideControlTooltip"
                @focus="onControlTooltipEnter($event, isMuted ? t('unmute') : t('mute'), 'M')"
                @blur="hideControlTooltip"
                :aria-label="isMuted ? t('unmute') : t('mute')"
              >
                <PlayerIcon :name="volumeIconName" />
              </button>
              <div
                class="sp-volume-slider"
                @click="onVolumeClick"
                @pointerdown.prevent="onVolumePointerDown"
                @pointermove="onVolumePointerMove"
                @pointerup="onVolumePointerUp"
                @pointercancel="onVolumePointerUp"
              >
                <div class="sp-volume-slider-fill" :style="{ width: `${isMuted ? 0 : volume}%` }"></div>
              </div>
            </div>


            <!-- 时间 -->
            <div class="sp-time">
              <span class="sp-time-current">{{ formatTime(currentTime) }}</span>
              <span class="sp-time-separator">/</span>
              <span class="sp-time-duration">{{ formatTime(duration) }}</span>
            </div>
          </div>

          <!-- 右侧控件 -->
          <div ref="controlsRightRef" class="sp-controls-right">
            <!-- 字幕 -->
            <button
              v-if="subtitleTracks.length > 0"
              class="sp-btn"
              :class="{ 'sp-btn--toggled': store.subtitlesEnabled }"
              @click.stop="toggleSubtitlesQuick"
              @mouseenter="onControlTooltipEnter($event, store.subtitlesEnabled ? t('subtitlesOff') : t('subtitles'), 'C')"  
              @mouseleave="hideControlTooltip"
              @focus="onControlTooltipEnter($event, store.subtitlesEnabled ? t('subtitlesOff') : t('subtitles'), 'C')"       
              @blur="hideControlTooltip"
              :aria-label="t('subtitles')"
            >
              <PlayerIcon :name="store.subtitlesEnabled ? 'subtitles' : 'subtitlesOff'" />
            </button>

            <!-- 设置 -->
            <button
              ref="settingsButtonRef"
              class="sp-btn"
              :class="{ 'sp-btn--toggled': showSettingsMenu }"
              @click.stop="toggleSettingsMenu"
              @mouseenter="onControlTooltipEnter($event, t('settings'))"
              @mouseleave="hideControlTooltip"
              @focus="onControlTooltipEnter($event, t('settings'))"
              @blur="hideControlTooltip"
              :aria-label="t('settings')"
            >
              <PlayerIcon name="settings" />
            </button>

            <!-- 画中画 -->
            <button
              v-if="supportsPiP"
              class="sp-btn"
              @click="togglePictureInPicture"
              @mouseenter="onControlTooltipEnter($event, t('pictureInPicture'))"
              @mouseleave="hideControlTooltip"
              @focus="onControlTooltipEnter($event, t('pictureInPicture'))"
              @blur="hideControlTooltip"
              :aria-label="t('pictureInPicture')"
            >
              <PlayerIcon :name="store.pip ? 'pipExit' : 'pip'" />
            </button>

            <!-- 宽屏 -->
            <button
              class="sp-btn"
              @click="toggleWidescreen"
              @mouseenter="onControlTooltipEnter($event, props.widescreen ? t('exitWidescreen') : t('widescreen'))"
              @mouseleave="hideControlTooltip"
              @focus="onControlTooltipEnter($event, props.widescreen ? t('exitWidescreen') : t('widescreen'))"
              @blur="hideControlTooltip"
              :aria-label="props.widescreen ? t('exitWidescreen') : t('widescreen')"
            >
              <PlayerIcon :name="props.widescreen ? 'widescreenExit' : 'widescreen'" />
            </button>

            <!-- 全屏 -->
            <button
              class="sp-btn"
              @click="toggleFullscreen"
              @mouseenter="onControlTooltipEnter($event, isFullscreen ? t('exitFullscreen') : t('fullscreen'), 'F')"
              @mouseleave="hideControlTooltip"
              @focus="onControlTooltipEnter($event, isFullscreen ? t('exitFullscreen') : t('fullscreen'), 'F')"
              @blur="hideControlTooltip"
              :aria-label="isFullscreen ? t('exitFullscreen') : t('fullscreen')"
            >
              <PlayerIcon :name="isFullscreen ? 'fullscreenExit' : 'fullscreen'" />
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- 设置菜单 -->
    <transition name="sp-overlay">
      <div
        v-if="showSettingsMenu && store.controlsVisible"
        ref="settingsPopupRef"
        class="sp-popup"
        :style="settingsPopupStyle"
        @click.stop
      >
        <div class="sp-popup-surface">
          <!-- 主菜单 -->
        <template v-if="settingsView === 'main'">
          <div class="sp-popup-list sp-popup-list--main">
            <button
              class="sp-popup-item sp-popup-item--toggle"
              type="button"
              role="switch"
              :aria-checked="store.autoplayNext"
              @click="toggleAutoplayNext"
            >
              <span class="sp-popup-item-main">
                <PlayerIcon class="sp-popup-item-icon" name="autoplayNext" />
                <span class="sp-popup-item-label">{{ t('autoplayNext') }}</span>
              </span>
              <span class="sp-switch" :class="{ 'sp-switch--on': store.autoplayNext }" aria-hidden="true"></span>
            </button>

            <button
              class="sp-popup-item sp-popup-item--toggle"
              type="button"
              role="switch"
              :aria-checked="store.loop"
              @click="toggleLoop"
            >
              <span class="sp-popup-item-main">
                <PlayerIcon class="sp-popup-item-icon" name="loop" />
                <span class="sp-popup-item-label">{{ t('loop') }}</span>
              </span>
              <span class="sp-switch" :class="{ 'sp-switch--on': store.loop }" aria-hidden="true"></span>
            </button>

            <button
              v-if="subtitleTracks.length > 0"
              class="sp-popup-item sp-popup-item--submenu"
              type="button"
              @click="settingsView = 'subtitles'"
            >
              <span class="sp-popup-item-main">
                <PlayerIcon class="sp-popup-item-icon" :name="store.subtitlesEnabled ? 'subtitles' : 'subtitlesOff'" />
                <span class="sp-popup-item-label">{{ `${t('subtitles')} (${subtitleTracks.length})` }}</span>
              </span>
              <span class="sp-popup-item-meta">
                <span class="sp-popup-value">{{ subtitlesStatusText }}</span>
                <ChevronRightIcon class="sp-popup-chevron" />
              </span>
            </button>

          <button class="sp-popup-item sp-popup-item--submenu" @click="settingsView = 'speed'">
            <span class="sp-popup-item-main">
              <PlayerIcon class="sp-popup-item-icon" name="speed" />
              <span class="sp-popup-item-label">{{ t('playbackSpeed') }}</span>
            </span>
            <span class="sp-popup-item-meta">
              <span class="sp-popup-value">{{ store.playbackRate === 1 ? t('speedNormal') : `${store.playbackRate}x` }}</span>
              <ChevronRightIcon class="sp-popup-chevron" />
            </span>
          </button>
          <button v-if="qualities.length > 0" class="sp-popup-item sp-popup-item--submenu" @click="settingsView = 'quality'">
            <span class="sp-popup-item-main">
              <PlayerIcon class="sp-popup-item-icon" name="quality" />
              <span class="sp-popup-item-label">{{ t('quality') }}</span>
            </span>
            <span class="sp-popup-item-meta">
              <span class="sp-popup-value">{{ displayedQualityLabel || '' }}</span>
              <ChevronRightIcon class="sp-popup-chevron" />
            </span>
          </button>
          </div>
        </template>

        <!-- 播放速度子菜单 -->
        <template v-else-if="settingsView === 'speed'">
          <button class="sp-popup-back" @click="settingsView = 'main'">
            <ArrowLeftIcon />
            <span>{{ t('playbackSpeed') }}</span>
          </button>
          <div class="sp-popup-list">
            <button
              v-for="rate in playbackRates"
              :key="rate"
              class="sp-popup-option"
              :class="{ active: store.playbackRate === rate }"
              @click="handleSpeedSelect(rate)"
            >
              <CheckIcon v-if="store.playbackRate === rate" class="sp-check" />
              <span>{{ rate === 1 ? t('speedNormal') : `${rate}x` }}</span>
            </button>
          </div>
        </template>

        <!-- 画质子菜单 -->
        <template v-else-if="settingsView === 'quality'">
          <button class="sp-popup-back" @click="settingsView = 'main'">
            <ArrowLeftIcon />
            <span>{{ t('quality') }}</span>
          </button>
          <div class="sp-popup-list">
            <button
              v-for="q in qualities"
              :key="q.id"
              class="sp-popup-option"
              :class="{ active: currentQualityId === q.id }"
              @click="handleQualitySelect(q)"
            >
              <CheckIcon v-if="currentQualityId === q.id" class="sp-check" />
              <span>{{ q.label }}</span>
            </button>
          </div>
        </template>

        <template v-else-if="settingsView === 'subtitles'">
          <button class="sp-popup-back" @click="settingsView = 'main'">
            <ArrowLeftIcon />
            <span>{{ t('subtitles') }}</span>
          </button>
          <div class="sp-popup-list">
            <button
              class="sp-popup-option"
              :class="{ active: !currentSubtitle }"
              @click="handleSubtitleSelect(null)"
            >
              <CheckIcon v-if="!currentSubtitle" class="sp-check" />
              <span>{{ t('subtitlesOff') }}</span>
            </button>
            <button
              v-for="track in subtitleTracks"
              :key="track.id"
              class="sp-popup-option"
              :class="{ active: currentSubtitle?.id === track.id }"
              @click="handleSubtitleSelect(track)"
            >
              <CheckIcon v-if="currentSubtitle?.id === track.id" class="sp-check" />
              <span>{{ track.label }}</span>
            </button>
          </div>
        </template>
        </div>
      </div>
    </transition>

    <!-- 快进/快退指示器 -->
    <transition name="sp-fade">
      <div v-if="seekIndicator.show" class="sp-seek-indicator" :class="seekIndicator.direction">
        <PlayerIcon :name="seekIndicator.direction === 'forward' ? 'skipForward' : 'skipBackward'" />
        <span>{{ seekIndicator.seconds }}{{ t('skipSeconds', { seconds: '' }) }}</span>
      </div>
    </transition>

    <!-- 音量指示器 -->
    <transition name="sp-fade">
      <div v-if="volumeIndicator.show" class="sp-volume-indicator">
        <PlayerIcon :name="volumeIconName" />
        <span>{{ Math.round(volume) }}%</span>
      </div>
    </transition>

    <!-- 控制按钮 Tooltip -->
    <transition name="sp-fade">
      <div
        v-if="controlTooltip.visible && store.controlsVisible"
        class="sp-tooltip sp-tooltip--controls"
        :style="{ left: `${controlTooltip.x}px`, top: `${controlTooltip.y}px` }"
        role="tooltip"
      >
        <span class="sp-tooltip-text">{{ controlTooltip.text }}</span>
        <span v-if="controlTooltip.shortcut" class="sp-tooltip-shortcut">{{ controlTooltip.shortcut }}</span>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { usePlayer } from './core'
import PlayerIcon from './PlayerIcon.vue'
import {
  ArrowLeftIcon,
  CheckIcon,
  ChevronRightIcon
} from '@heroicons/vue/24/outline'

import type { VideoInfo } from '../../types/video-player'
import type { SubtitleTrack } from './plugins/subtitles'

// 导入 CSS 变量（主题系统基础）
import './themes/variables.css'

interface Props {
  video?: VideoInfo
  initialTime?: number
  hasPrev?: boolean
  hasNext?: boolean
  externalError?: any
  autoplay?: boolean
  widescreen?: boolean
}

type PlayerUiError = {
  title?: string
  message?: string
  code?: string
  canRetry?: boolean
}

const props = withDefaults(defineProps<Props>(), {

  initialTime: 0,
  hasPrev: false,
  hasNext: false,
  externalError: null,
  autoplay: true,
  widescreen: false
})

const emit = defineEmits<{
  play: []
  pause: []
  ended: [data?: { autoplay: boolean; autoplayNext: boolean; loop: boolean }]
  fullscreenChange: [isFullscreen: boolean]
  widescreenChange: [isWidescreen: boolean]
  timeupdate: [currentTime: number]
  error: [error: any]
  'prev-video': []
  'next-video': []
  retry: []
}>()

// 使用集成播放器
const {
  store,
  videoElement,
  containerElement,
  isReady,
  isPlaying,
  currentTime,
  duration,
  volume,
  isMuted,
  isFullscreen,
  qualities,
  currentQualityLabel,
  currentQualityId,
  isHlsStream,
  isDashStream,
  play,
  pause,
  seek,
  setVolume,
  toggleMute,
  setPlaybackRate,
  setQuality,
  toggleFullscreen,
  togglePictureInPicture,
  subtitleTracks,
  currentSubtitle,
  setSubtitle,
  setSubtitleTracks,
  loadSource,
  theme,
  setTheme,
  t,
  locale,
  setLocale,
  saveProgress,
  loadProgress,
  announce,
  on,
  off,
  controlsLayout,
  icons,
  destroy
} = usePlayer({
  autoplay: props.autoplay,
  video: computed(() => props.video),
  onPlay: () => emit('play'),
  onPause: () => emit('pause'),
  onEnded: () => emit('ended', { autoplay: store.autoplay, autoplayNext: store.autoplayNext, loop: store.loop }),
  onError: (e) => {
    internalError.value = e as PlayerUiError
    emit('error', e)
  },

  onTimeUpdate: (time) => emit('timeupdate', time)
})

// 模板引用
const videoRef = ref<HTMLVideoElement | null>(null)
const containerRef = ref<HTMLElement | null>(null)

const controlsRightRef = ref<HTMLElement | null>(null)
const settingsButtonRef = ref<HTMLElement | null>(null)
const settingsPopupRef = ref<HTMLElement | null>(null)

const settingsPopupStyle = ref<Record<string, string>>({})

// UI 状态
const showSettingsMenu = ref(false)
const settingsView = ref<'main' | 'speed' | 'quality' | 'subtitles'>('main')
const previewTime = ref<number | null>(null)
const previewPercent = ref(0)
const isScrubbing = ref(false)
const isVolumeScrubbing = ref(false)
const controlTooltip = ref({ visible: false, text: '', shortcut: '', x: 0, y: 0 })
const seekIndicator = ref({ show: false, direction: 'forward' as 'forward' | 'backward', seconds: 10 })
const volumeIndicator = ref({ show: false })
const errorState = ref({ show: false, title: '', message: '', code: '', canRetry: true })
const internalError = ref<PlayerUiError | null>(null)

const CONTROL_TOOLTIP_DELAY = 450
let controlTooltipTimer: ReturnType<typeof setTimeout> | null = null

const clamp = (value: number, min: number, max: number): number => {
  return Math.min(max, Math.max(min, value))
}

const hideControlTooltip = (): void => {
  if (controlTooltipTimer) {
    clearTimeout(controlTooltipTimer)
    controlTooltipTimer = null
  }
  controlTooltip.value.visible = false
}

const onControlTooltipEnter = (e: Event, text: string, shortcut?: string): void => {
  if (!containerRef.value) return

  const target = e.currentTarget as HTMLElement | null
  if (!target) return

  hideControlTooltip()

  const containerRect = containerRef.value.getBoundingClientRect()
  const targetRect = target.getBoundingClientRect()
  const x = clamp(targetRect.left - containerRect.left + targetRect.width / 2, 16, containerRect.width - 16)
  const y = clamp(targetRect.top - containerRect.top - 10, 16, containerRect.height - 16)

  controlTooltip.value = { visible: false, text, shortcut: shortcut ?? '', x, y }
  controlTooltipTimer = setTimeout(() => {
    controlTooltip.value.visible = true
  }, CONTROL_TOOLTIP_DELAY)
}

const updateOverlayPosition = (
  anchorEl: HTMLElement | null,
  overlayEl: HTMLElement | null,
  styleRef: { value: Record<string, string> }
): void => {
  if (!containerRef.value || !anchorEl || !overlayEl) return

  const containerRect = containerRef.value.getBoundingClientRect()
  const anchorRect = anchorEl.getBoundingClientRect()
  const overlayWidth = overlayEl.offsetWidth
  const overlayHeight = overlayEl.offsetHeight
  if (!overlayWidth || !overlayHeight) return

  const padding = 8
  const gap = 16
 

  const left = clamp(
    anchorRect.right - containerRect.left - overlayWidth,
    padding,
    containerRect.width - overlayWidth - padding
  )

  const top = clamp(
    anchorRect.top - containerRect.top - overlayHeight - gap,
    padding,
    containerRect.height - overlayHeight - padding
  )

  styleRef.value = {
    left: `${left}px`,
    top: `${top}px`,
    right: 'auto',
    bottom: 'auto'
  }
}

const getSettingsAnchor = (): HTMLElement | null => {
  return controlsRightRef.value || settingsButtonRef.value
}

const updateSettingsPopupPosition = async (): Promise<void> => {
  await nextTick()
  const update = () => {
    updateOverlayPosition(getSettingsAnchor(), settingsPopupRef.value, settingsPopupStyle)
  }

  if (typeof requestAnimationFrame === 'function') {
    requestAnimationFrame(update)
  } else {
    update()
  }
}

watch(showSettingsMenu, async (open) => {
  if (!open) {
    settingsPopupStyle.value = {}
    return
  }
  hideControlTooltip()
  await updateSettingsPopupPosition()
})

watch(settingsView, async () => {
  if (!showSettingsMenu.value) return
  await updateSettingsPopupPosition()
})

const handleResize = (): void => {
  hideControlTooltip()
  if (showSettingsMenu.value) {
    updateOverlayPosition(getSettingsAnchor(), settingsPopupRef.value, settingsPopupStyle)
  }
}


const resolveErrorMessage = (err: PlayerUiError | null): string => {
  if (err?.message) return err.message

  const code = String(err?.code || '').toUpperCase()
  if (code.includes('NETWORK') || code.includes('TIMEOUT')) return t('errorNetwork')
  if (code.includes('DECODE')) return t('errorDecode')
  if (code.includes('MEDIA')) return t('errorMedia')
  if (code.includes('NOT_SUPPORTED') || code.includes('UNSUPPORTED')) return t('errorNotSupported')
  return t('errorUnknown')
}

const clearErrorState = (): void => {
  errorState.value = {
    show: false,
    title: '',
    message: '',
    code: '',
    canRetry: true
  }
}

const applyErrorState = (err: PlayerUiError | null): void => {
  if (!err) {
    clearErrorState()
    return
  }

  errorState.value = {
    show: true,
    title: err.title || t('errorTitle'),
    message: resolveErrorMessage(err),
    code: err.code || '',
    canRetry: err.canRetry !== false
  }

  store.setLoading(false, 'idle')
  store.setPlaying(false)
}

const activeError = computed<PlayerUiError | null>(() => props.externalError || internalError.value)

watch(activeError, (err) => {
  applyErrorState(err)
}, { immediate: true })

// 播放速度选项

const playbackRates = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2]

// 计算属性
const progress = computed(() => duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0)

const pendingResume = ref<{ videoId: string; time: number } | null>(null)

const queueResume = (videoId: string | number | undefined, time: number): void => {
  if (!videoId || !time || time <= 0) return
  pendingResume.value = { videoId: String(videoId), time }
  attemptResume()
}

const attemptResume = (): void => {
  const pending = pendingResume.value
  const media = videoRef.value
  if (!pending || !media) return
  const currentId = String((props.video as any)?.id ?? '')
  if (pending.videoId && currentId && pending.videoId !== currentId) return
  if (!duration.value || !isFinite(duration.value) || media.readyState < 1) return
  const maxTime = Math.max(0, duration.value - 0.5)
  const safeTime = clamp(pending.time, 0, maxTime)
  if (safeTime <= 0) {
    pendingResume.value = null
    return
  }
  seek(safeTime)
  pendingResume.value = null
}

watch(duration, () => {
  attemptResume()
})

const isBuffering = computed(() => {
  return store.loading && store.loadingStage === 'buffering' && store.hasStartedPlayback
})


const displayedQualityLabel = computed(() => {
  const byId = currentQualityId.value !== null
    ? qualities.value.find((item) => item.id === currentQualityId.value)
    : undefined
  if (byId?.label) return byId.label
  return currentQualityLabel.value || ''
})


const supportsPiP = computed(() => {
  return typeof document !== 'undefined' && 'pictureInPictureEnabled' in document
})

const lastSubtitleTrack = ref<SubtitleTrack | null>(null)

watch(currentSubtitle, (track) => {
  if (track) lastSubtitleTrack.value = track
}, { immediate: true })

const subtitlesStatusText = computed(() => {
  if (!store.subtitlesEnabled || !currentSubtitle.value) return '关闭'
  return currentSubtitle.value.label
})

const volumeIconName = computed(() => {
  if (isMuted.value || volume.value === 0) return 'volumeOff'
  if (volume.value < 30) return 'volumeLow'
  return 'volumeHigh'
})

// 同步 refs - 使用 immediate 确保初始值同步
watch(videoRef, (el, oldEl) => {
  if (oldEl) {
    oldEl.removeEventListener('loadedmetadata', attemptResume)
  }
  videoElement.value = el
  if (el) {
    el.addEventListener('loadedmetadata', attemptResume)
    attemptResume()
  }
}, { immediate: true })


watch(containerRef, (el) => {
  containerElement.value = el
}, { immediate: true })

// 业务数据适配：将 VideoInfo 转换为通用 MediaSource
const adaptVideoToSource = (video: VideoInfo) => {
  const videoAny = video as any
  
  // 优先使用 mpd_url（DASH，支持音视频合流）
  // 其次使用 stream_video_url（HLS 或原生视频）
  const src = videoAny.mpd_url || videoAny.stream_video_url || ''
  
  if (!src) return null
  
  return {
    src,
    type: 'auto' as const,
    poster: video.thumbnail,
    title: video.title
  }
}

// 记录当前加载的源，避免重复加载
let currentLoadedSrc = ''

// 业务数据适配：将字幕数据转换为 SubtitleTrack
const adaptSubtitles = (video: VideoInfo) => {
  const videoAny = video as any
  if (!videoAny.subtitles?.length) return []
  
  return videoAny.subtitles.map((s: any, i: number) => ({
    id: s.id || `sub-${i}`,
    label: s.label || s.language || `Subtitle ${i + 1}`,
    language: s.language || 'unknown',
    url: s.url,
    default: i === 0
  }))
}

// 加载视频
watch(
  () => props.video,
  async (video, oldVideo) => {
    if (!video) return
    
    // 如果是新视频（id 变化），重置已加载的源记录
    const newVideoId = (video as any).id
    const oldVideoId = (oldVideo as any)?.id
    if (newVideoId !== oldVideoId) {
      currentLoadedSrc = ''
      internalError.value = null
      // 立即重置播放器状态
      store.setCurrentTime(0)

      store.setDuration(0)
      store.setBufferedProgress(0)
      store.setPlaying(false)
      store.setLoading(true, 'fetching')
    }
    
    // 适配视频源
    const source = adaptVideoToSource(video)
    if (!source) return
    
    // 避免重复加载相同的源
    if (source.src === currentLoadedSrc) return
    currentLoadedSrc = source.src
    
    // 加载视频源
    loadSource(source)
    
    // 适配并设置字幕
    const subtitles = adaptSubtitles(video)
    if (subtitles.length > 0) {
      setSubtitleTracks(subtitles)
    }
    
  // 恢复播放位置
    const videoId = (video as any).id
    if (props.initialTime > 0) {
      await nextTick()
      queueResume(videoId, props.initialTime)
    } else if (videoId) {
      const savedTime = await loadProgress(videoId)
      if (savedTime && savedTime > 0) {
        await nextTick()
        queueResume(videoId, savedTime)
      }
    }
  },
  { immediate: true, deep: true }
)



// 控制栏显示/隐藏
let hideControlsTimer: ReturnType<typeof setTimeout> | null = null
const isPointerInside = ref(false)

const closeMenus = (): void => {
  showSettingsMenu.value = false
  hideControlTooltip()
}


const scheduleHideControls = (delay = 3000): void => {
  if (hideControlsTimer) clearTimeout(hideControlsTimer)
  hideControlsTimer = setTimeout(() => {
    if (!isPointerInside.value) return
    if (!isPlaying.value) return
    if (isScrubbing.value) return
    store.setControlsVisible(false)
    closeMenus()
  }, delay)
}

const showControls = (): void => {
  store.setControlsVisible(true)
  if (isPlaying.value) {
    scheduleHideControls(3000)
  } else if (hideControlsTimer) {
    clearTimeout(hideControlsTimer)
  }
}

const onPointerEnter = (): void => {
  isPointerInside.value = true
  showControls()
}

const onPointerLeave = (): void => {
  if (isScrubbing.value) return
  isPointerInside.value = false
  if (hideControlsTimer) clearTimeout(hideControlsTimer)
  if (!errorState.value.show) {
    store.setControlsVisible(false)
  }
  closeMenus()
}



const onPointerMove = (): void => {
  isPointerInside.value = true
  showControls()
}

// 视频点击
const handleVideoClick = () => {
  if (isPlaying.value) {
    pause()
  } else {
    play()
  }
}

// 切换播放
const togglePlay = () => {
  if (isPlaying.value) {
    pause()
  } else {
    play()
  }
}

// 进度条交互
const updateProgressPreview = (e: PointerEvent): { percent: number; time: number } => {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  const percent = clamp((e.clientX - rect.left) / rect.width, 0, 1)
  const time = percent * duration.value

  // 预览时间位置做边界限制，避免贴边溢出
  previewPercent.value = clamp(percent * 100, 2, 98)
  previewTime.value = time

  return { percent, time }
}

const onProgressPointerDown = (e: PointerEvent) => {
  hideControlTooltip()
  isScrubbing.value = true
  showControls()

  const el = e.currentTarget as HTMLElement
  if (typeof el.setPointerCapture === 'function') {
    el.setPointerCapture(e.pointerId)
  }

  const { time } = updateProgressPreview(e)
  seek(time)
}

const onProgressPointerMove = (e: PointerEvent) => {
  const { time } = updateProgressPreview(e)
  if (!duration.value) return

  if (isScrubbing.value) {
    showControls()
    seek(time)
  }
}

const onProgressPointerLeave = () => {
  if (isScrubbing.value) return
  previewTime.value = null
}

const onProgressPointerUp = (e?: PointerEvent) => {
  if (!isScrubbing.value) return

  if (e) {
    const { time } = updateProgressPreview(e)
    seek(time)
  }

  isScrubbing.value = false
  setTimeout(() => {
    if (!isScrubbing.value) previewTime.value = null
  }, 250)
}


// 音量点击
const updateVolumeFromPointer = (e: PointerEvent | MouseEvent) => {
  const target = e.currentTarget as HTMLElement | null
  if (!target) return
  const rect = target.getBoundingClientRect()
  const percent = clamp((e.clientX - rect.left) / rect.width, 0, 1)
  setVolume(percent * 100)
  showVolumeIndicator()
}

const onVolumeClick = (e: MouseEvent) => {
  updateVolumeFromPointer(e)
}

const onVolumePointerDown = (e: PointerEvent) => {
  hideControlTooltip()
  isVolumeScrubbing.value = true
  showControls()

  const target = e.currentTarget as HTMLElement | null
  if (target && typeof target.setPointerCapture === 'function') {
    target.setPointerCapture(e.pointerId)
  }

  updateVolumeFromPointer(e)
}

const onVolumePointerMove = (e: PointerEvent) => {
  if (!isVolumeScrubbing.value) return
  updateVolumeFromPointer(e)
}

const onVolumePointerUp = (e?: PointerEvent) => {
  if (!isVolumeScrubbing.value) return
  if (e) updateVolumeFromPointer(e)
  isVolumeScrubbing.value = false
}


// 菜单切换
const toggleSettingsMenu = () => {
  hideControlTooltip()
  showControls()
  showSettingsMenu.value = !showSettingsMenu.value
  settingsView.value = 'main'
}

const toggleAutoplayNext = () => {
  store.setAutoplayNext(!store.autoplayNext)
}

const toggleLoop = () => {
  store.setLoop(!store.loop)
}

const toggleSubtitlesQuick = () => {
  hideControlTooltip()
  showControls()

  if (subtitleTracks.value.length === 0) return

  if (store.subtitlesEnabled) {
    setSubtitle(null)
    return
  }

  const track = lastSubtitleTrack.value || subtitleTracks.value[0] || null
  if (track) setSubtitle(track)
}

const handleSubtitleSelect = (track: SubtitleTrack | null) => {
  setSubtitle(track)
  settingsView.value = 'main'
}


// 宽屏模式切换
const toggleWidescreen = async () => {
  if (isFullscreen.value) {
    await toggleFullscreen()
  }
  emit('widescreenChange', !props.widescreen)
}

// 循环播放速度
const cyclePlaybackRate = () => {
  const currentIndex = playbackRates.indexOf(store.playbackRate)
  const nextIndex = (currentIndex + 1) % playbackRates.length
  setPlaybackRate(playbackRates[nextIndex])
}

// 循环质量
const cycleQuality = () => {
  if (qualities.value.length === 0) return
  const ids = qualities.value.map((q: any) => q.id)
  const currentIndex = currentQualityId.value !== null
    ? ids.indexOf(currentQualityId.value)
    : -1
  const fallbackIndex = currentIndex >= 0
    ? currentIndex
    : qualities.value.findIndex((q: any) => q.label === currentQualityLabel.value)
  const nextIndex = ((fallbackIndex >= 0 ? fallbackIndex : -1) + 1) % ids.length
  const nextQuality = qualities.value[nextIndex]
  if (nextQuality) setQuality(nextQuality.id ?? nextQuality.label)
}


// 播放速度选择
const handleSpeedSelect = (rate: number) => {
  setPlaybackRate(rate)
  showSettingsMenu.value = false
}

// 质量选择
const handleQualitySelect = (q: any) => {
  const nextQuality = q?.id !== undefined ? q.id : (q.label || String(q.id))
  setQuality(nextQuality)
  showSettingsMenu.value = false
}

// 重试
const handleRetry = () => {
  internalError.value = null
  clearErrorState()
  store.setLoading(true, 'fetching')
  emit('retry')
  if (videoRef.value) {
    videoRef.value.load()
    play()
  }
}

const handleDismissError = () => {
  internalError.value = null
  clearErrorState()
}



// 键盘快捷键
const handleKeyDown = (e: KeyboardEvent) => {
  if (e.target !== containerRef.value) return

  switch (e.key) {
    case ' ':
    case 'k':
      e.preventDefault()
      togglePlay()
      break
    case 'ArrowLeft':
      e.preventDefault()
      seek(Math.max(0, currentTime.value - 10))
      showSeekIndicator('backward', 10)
      break
    case 'ArrowRight':
      e.preventDefault()
      seek(Math.min(duration.value, currentTime.value + 10))
      showSeekIndicator('forward', 10)
      break
    case 'ArrowUp':
      e.preventDefault()
      setVolume(Math.min(100, volume.value + 5))
      showVolumeIndicator()
      break
    case 'ArrowDown':
      e.preventDefault()
      setVolume(Math.max(0, volume.value - 5))
      showVolumeIndicator()
      break
    case 'm':
      toggleMute()
      break
    case 'f':
      toggleFullscreen()
      break
    case 'c':
      toggleSubtitlesQuick()
      break
    case 'Escape':
      if (showSettingsMenu.value) {
        showSettingsMenu.value = false
      } else if (isFullscreen.value) {
        toggleFullscreen()
      }
      break
  }
}

// 指示器
const showSeekIndicator = (direction: 'forward' | 'backward', seconds: number) => {
  seekIndicator.value = { show: true, direction, seconds }
  setTimeout(() => {
    seekIndicator.value.show = false
  }, 500)
}

const showVolumeIndicator = () => {
  volumeIndicator.value.show = true
  setTimeout(() => {
    volumeIndicator.value.show = false
  }, 500)
}

// 格式化时间
const formatTime = (seconds: number): string => {
  if (!isFinite(seconds) || isNaN(seconds)) return '0:00'
  
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }
  return `${m}:${s.toString().padStart(2, '0')}`
}

// 点击外部关闭菜单
const handleOutsideClick = (e: MouseEvent) => {
  if (errorState.value.show) return
  if (showSettingsMenu.value) {
    const target = e.target as HTMLElement
    if (!target.closest('.sp-popup')) {
      showSettingsMenu.value = false
    }
  }
}

onMounted(() => {
  document.addEventListener('click', handleOutsideClick)
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', handleResize)
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleOutsideClick)
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', handleResize)
  }
  if (videoRef.value) {
    videoRef.value.removeEventListener('loadedmetadata', attemptResume)
  }
  if (hideControlsTimer) clearTimeout(hideControlsTimer)
  hideControlTooltip()
})


// 停止播放并重置状态
const stop = () => {
  pause()
  if (videoRef.value) {
    videoRef.value.currentTime = 0
  }
  store.resetForNewVideo()
}

// 暴露给父组件
defineExpose({
  play,
  pause,
  stop,
  seek,
  toggleFullscreen,
  videoElement: videoRef
})
</script>

<style scoped>
/* 播放器容器 */
.sp-player {
  position: absolute;
  inset: 0;
  background: var(--sp-bg);
  font-family: var(--sp-font-family);
  color: var(--sp-text);
  overflow: hidden;
  user-select: none;
  --sp-primary: #ff0000;
  --sp-primary-hover: #ff3333;
  --sp-primary-active: #cc0000;
  --sp-primary-rgb: 255, 0, 0;
  --sp-glow-primary: none;
  --sp-menu-bg: rgba(28, 28, 28, 0.88);

  /* YouTube-like bottom overlay behind controls */
  --sp-controls-bg: linear-gradient(
    to top,
    rgba(0, 0, 0, 0.78) 0%,
    rgba(0, 0, 0, 0.36) 45%,
    rgba(0, 0, 0, 0) 100%
  );

  --sp-controls-row-padding: 0 12px;
  --sp-controls-group-bg: transparent;
  --sp-controls-group-padding: 0;
  --sp-controls-group-radius: 0;
  --sp-progress-radius: 0px;
}

/* 视频元素 */
.sp-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  z-index: var(--sp-z-video, 1);
}

/* 控制栏 */
.sp-controls {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: var(--sp-z-controls, 20);
  padding: 28px 0 8px;
  background: var(--sp-controls-bg);
  text-shadow: var(--sp-text-shadow);
}

.sp-controls.sp-controls--error {
  z-index: calc(var(--sp-z-overlay, 15) + 1);
}

/* 进度条 */
.sp-progress-container {
  position: relative;
  padding: 0 0 6px;
  margin-bottom: 0;
}

.sp-progress {
  position: relative;
  height: var(--sp-progress-height);
  background: var(--sp-progress-bg);
  border-radius: var(--sp-progress-radius);
  cursor: pointer;
  touch-action: none;
  transition: height 0.1s ease;
}

.sp-progress:hover,
.sp-progress--scrubbing {
  height: var(--sp-progress-height-hover);
}



.sp-progress-buffered {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: var(--sp-progress-buffered);
  border-radius: var(--sp-progress-radius);
  transition: width 0.1s ease;
}

.sp-progress-played {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: var(--sp-progress-played);
  border-radius: var(--sp-progress-radius);
  box-shadow: var(--sp-glow-primary);
}

.sp-progress-thumb {
  position: absolute;
  top: 50%;
  width: var(--sp-progress-thumb-size);
  height: var(--sp-progress-thumb-size);
  background: var(--sp-progress-thumb-color);
  border-radius: 50%;
  transform: translate(-50%, -50%) scale(0);
  transition: transform 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: var(--sp-shadow-sm);
  pointer-events: none;
}

.sp-progress:hover .sp-progress-thumb,
.sp-progress--scrubbing .sp-progress-thumb {
  transform: translate(-50%, -50%) scale(1);
}


.sp-progress-preview {
  position: absolute;
  bottom: calc(100% + 8px);
  transform: translateX(-50%);
  padding: 5px 10px;
  background: var(--sp-tooltip-bg);
  border-radius: 4px;
  font-size: var(--font-size-xs);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  pointer-events: none;
  box-shadow: var(--sp-shadow-md);
}

.sp-progress-preview::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-top-color: var(--sp-tooltip-bg);
}

/* 控制按钮 Tooltip */
.sp-tooltip--controls {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transform: translate(-50%, -100%);
}

.sp-tooltip--controls::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: var(--sp-tooltip-bg);
}

.sp-tooltip-shortcut {
  color: var(--sp-text-secondary);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.4px;
}

/* 控制按钮行 */
.sp-controls-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 40px;
  padding: var(--sp-controls-row-padding);
}

.sp-controls-left,
.sp-controls-right {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: var(--sp-controls-group-padding);
  background: var(--sp-controls-group-bg);
  border-radius: var(--sp-controls-group-radius);
  border: none;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

/* 按钮 */
.sp-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--sp-btn-size);
  height: var(--sp-btn-size);
  padding: 0;
  border: none;
  border-radius: var(--sp-radius-full);
  background: transparent;
  color: var(--sp-text-strong);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, transform 0.1s ease;
}

.sp-btn:hover {
  background: var(--sp-btn-hover-bg);
  color: var(--sp-text);
}

.sp-btn:active {
  background: var(--sp-btn-active-bg);
  transform: scale(0.94);
}

.sp-btn--toggled {
  background: rgba(255, 255, 255, 0.14);
  color: var(--sp-text);
}

.sp-btn:focus-visible {
  outline: 2px solid var(--sp-primary);
  outline-offset: 2px;
}

.sp-btn--play {
  width: var(--sp-btn-size);
  height: var(--sp-btn-size);
}

.sp-btn svg,
.sp-btn .sp-icon {
  width: var(--sp-btn-icon-size);
  height: var(--sp-btn-icon-size);
  filter: drop-shadow(var(--sp-drop-shadow-sm));
}

.sp-btn--play svg,
.sp-btn--play .sp-icon {
  width: var(--sp-btn-icon-size-lg);
  height: var(--sp-btn-icon-size-lg);
}


/* 音量 */
.sp-volume {
  display: flex;
  align-items: center;
  gap: 2px;
}

.sp-volume-slider {
  position: relative;
  width: 0;
  height: 3px;
  margin-left: 0;
  background: var(--sp-progress-bg);
  border-radius: 1.5px;
  cursor: pointer;
  overflow: hidden;
  opacity: 0;
  pointer-events: none;
  touch-action: none;
  transition: width 0.18s ease, opacity 0.18s ease, height 0.1s ease, margin-left 0.18s ease;
}

.sp-volume:hover .sp-volume-slider,
.sp-volume:focus-within .sp-volume-slider,
.sp-volume.is-dragging .sp-volume-slider {
  width: 70px;
  margin-left: 6px;
  opacity: 1;
  pointer-events: auto;
  height: 4px;
}


.sp-volume-slider-fill {
  position: relative;
  height: 100%;
  background: var(--sp-text);
  border-radius: inherit;
  transition: width 0.05s ease;
}

.sp-volume-slider-fill::after {
  content: '';
  position: absolute;
  right: 0;
  top: 50%;
  width: 10px;
  height: 10px;
  background: var(--sp-text);
  border-radius: 50%;
  transform: translate(50%, -50%) scale(0);
  transition: transform 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: var(--sp-shadow-sm);
}

.sp-volume:hover .sp-volume-slider-fill::after,
.sp-volume:focus-within .sp-volume-slider-fill::after {
  transform: translate(50%, -50%) scale(1);
}


/* 时间 */
.sp-time {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: var(--font-size-xs);
  font-variant-numeric: tabular-nums;
  color: var(--sp-text-strong);
  margin-left: 4px;
}

.sp-time-current {
  color: var(--sp-text);
}

.sp-time-separator {
  color: var(--sp-text-disabled);
  margin: 0 1px;
}

.sp-time-duration {
  color: var(--sp-text-muted);
}

/* 设置弹出菜单 */
.sp-popup {
  position: absolute;
  right: 12px;
  bottom: 64px;
  min-width: 300px;
  z-index: var(--sp-z-menu, 30);
  transform-origin: bottom right;
}

.sp-popup-surface {
  padding: 6px;
  background: var(--sp-menu-bg);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.6);
  overflow: hidden;
}


.sp-popup-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  min-height: 40px;
  padding: 10px 12px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--sp-text-strong);
  font-size: var(--font-size-xs);
  text-align: left;
  cursor: pointer;
  transition: background 0.12s ease;
}

.sp-popup-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.sp-popup-item-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.sp-popup-item-icon {
  width: 20px;
  height: 20px;
  color: var(--sp-text-secondary);
  flex-shrink: 0;
}

.sp-popup-item-label {
  flex: 1;
  min-width: 0;
}

.sp-popup-item-meta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.sp-popup-value {
  color: var(--sp-text-secondary);
  font-size: var(--font-size-xs);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sp-popup-chevron {
  width: 16px;
  height: 16px;
  opacity: 0.7;
}

.sp-switch {
  position: relative;
  width: 36px;
  height: 20px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.2);
  flex-shrink: 0;
  transition: background 0.15s ease;
}

.sp-switch::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.95);
  transition: transform 0.15s ease;
}

.sp-switch--on {
  /* Follow the player's accent color (which is mapped to project tokens via --sp-primary-*) */
  background: rgba(var(--sp-primary-rgb, 255, 0, 0), 0.85);
}

.sp-switch--on::after {
  transform: translateX(16px);
}


.sp-popup-back {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 40px;
  padding: 10px 12px;
  border: none;
  border-radius: 10px;
  margin-bottom: 6px;
  background: transparent;
  color: var(--sp-text);
  font-size: var(--font-size-xs);
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: background 0.12s ease;
}

.sp-popup-back:hover {
  background: rgba(255, 255, 255, 0.08);
}

.sp-popup-back svg {
  width: 18px;
  height: 18px;
  opacity: 0.85;
}

.sp-popup-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 360px;
  overflow-y: auto;
  padding: 0;
}

.sp-popup-list--main {
  max-height: 360px;
}

.sp-popup-list::-webkit-scrollbar {
  width: 4px;
}

.sp-popup-list::-webkit-scrollbar-thumb {
  background: var(--sp-border-hover);
  border-radius: 2px;
}

.sp-popup-option {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 40px;
  padding: 10px 12px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--sp-text-secondary);
  font-size: var(--font-size-xs);
  text-align: left;
  cursor: pointer;
  transition: background 0.12s ease, color 0.12s ease;
}

.sp-popup-option:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--sp-text);
}

.sp-popup-option.active {
  color: var(--sp-text);
}

.sp-check {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  color: var(--sp-primary);
}

.sp-popup-option:not(.active) .sp-check {
  visibility: hidden;
}

.sp-popup-option:not(.active) {
  padding-left: 36px;
}

/* 加载/缓冲 */
.sp-loading,
.sp-buffering {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  transform: none;
  z-index: var(--sp-z-overlay, 15);
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.sp-loading--stacked {
  flex-direction: column;
  gap: 12px;
  text-align: center;
}

.sp-loading--buffering {
  gap: 0;
}

/* YouTube-like buffering spinner (single arc, no base ring) */
.sp-spinner-arc {
  --sp-spinner-size: 44px;
  --sp-spinner-stroke: 7px;
  width: var(--sp-spinner-size);
  height: var(--sp-spinner-size);
  filter: drop-shadow(var(--sp-drop-shadow-sm));
}

.sp-loading--buffering .sp-spinner-arc {
  --sp-spinner-size: 34px;
  --sp-spinner-stroke: 6px;
}

.sp-spinner-arc-svg {
  width: 100%;
  height: 100%;
  display: block;
  animation: sp-spinner-arc-spin 0.9s linear infinite;
}

.sp-spinner-arc-circle {
  fill: none;
  stroke: rgba(255, 255, 255, 0.9);
  stroke-width: var(--sp-spinner-stroke);
  stroke-linecap: round;
  /* arc length + gap to match YouTube look */
  stroke-dasharray: 168 96;
  stroke-dashoffset: 0;
  transform-origin: 50px 50px;
}

@media (prefers-reduced-motion: reduce) {
  .sp-spinner-arc-svg {
    animation-duration: 2.7s;
  }
}

.sp-loading-text {
  font-size: var(--font-size-xs);
  color: var(--sp-text-secondary);
  font-weight: 500;
  text-shadow: var(--sp-text-shadow);
}

@keyframes sp-spinner-arc-spin {
  to { transform: rotate(360deg); }
}


/* 错误 */
.sp-error-overlay {
  position: absolute;
  inset: 0;
  z-index: var(--sp-z-overlay, 15);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 22px;
  background: rgba(0, 0, 0, 0.82);
  pointer-events: none;
}


.sp-error-overlay--centered {
  text-align: center;
}

.sp-error-panel {
  max-width: 520px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: var(--sp-text);
  pointer-events: auto;
}


.sp-error-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  letter-spacing: 0.2px;
}

.sp-error-message {
  font-size: var(--font-size-xs);
  color: var(--sp-text-secondary);
  line-height: 1.5;
  max-width: 420px;
}

.sp-error-code {
  font-size: var(--font-size-2xs);
  color: var(--sp-text-tertiary);
  letter-spacing: 0.3px;
}

.sp-error-actions {
  margin-top: 8px;
  display: flex;
  justify-content: center;
  gap: 10px;
}

.sp-error-btn {
  height: 32px;
  padding: 0 14px;
  border-radius: 2px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  background: rgba(255, 255, 255, 0.12);
  color: var(--sp-text);
  font-size: var(--font-size-2xs);
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.sp-error-btn:hover {
  background: rgba(255, 255, 255, 0.18);
  border-color: rgba(255, 255, 255, 0.35);
}

.sp-error-btn:active {
  background: rgba(255, 255, 255, 0.28);
}

.sp-error-btn--ghost {
  background: transparent;
}

.sp-error-btn--ghost:hover {
  background: rgba(255, 255, 255, 0.12);
}

.sp-error-btn--ghost:active {
  background: rgba(255, 255, 255, 0.2);
}



/* 指示器 */
.sp-seek-indicator,
.sp-volume-indicator {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 18px;
  background: var(--sp-overlay);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-radius: 10px;
  z-index: var(--sp-z-indicator);
}

.sp-seek-indicator svg,
.sp-seek-indicator .sp-icon,
.sp-volume-indicator svg,
.sp-volume-indicator .sp-icon {
  width: 28px;
  height: 28px;
  opacity: 0.9;
}

.sp-seek-indicator span,
.sp-volume-indicator span {
  font-size: var(--font-size-xs);
  font-weight: 500;
  color: var(--sp-text-strong);
}

/* 过渡动画 */
.sp-fade-enter-active,
.sp-fade-leave-active {
  transition: opacity 0.2s ease;
}

.sp-fade-enter-from,
.sp-fade-leave-to {
  opacity: 0;
}

.sp-slide-enter-active,
.sp-slide-leave-active {
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease;
}

.sp-slide-enter-from,
.sp-slide-leave-to {
  transform: translateY(8px);
  opacity: 0;
}

.sp-overlay-enter-active,
.sp-overlay-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.sp-overlay-enter-from,
.sp-overlay-leave-to {
  opacity: 0;
  transform: translateY(6px) scale(0.98);
}
</style>
