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
    <!-- 全屏视觉增强层 -->
    <div class="sp-vignette-overlay"></div>

    <!-- 视频核心 -->
    <video
      ref="videoRef"
      class="sp-video"
      :poster="effectivePoster"
      :muted="store.muted"
      :autoplay="store.autoplay"
      :loop="store.loop"
      crossorigin="anonymous"
      playsinline
      webkit-playsinline
      @click="handleVideoClick"
      @dblclick="toggleFullscreen"
    />
    <!-- 中央 HUD 指示器 -->
    <transition name="sp-hud-fade">
      <div v-if="centralHud.visible" class="sp-central-hud">
        <div class="sp-central-hud-content">
          <PlayerIcon :name="centralHud.icon" class="sp-central-hud-icon" />
          <div class="sp-central-hud-value">{{ centralHud.value }}</div>
        </div>
      </div>
    </transition>

    <!-- 加载状态 -->
    <Transition name="sp-loading-fade" @after-enter="onLoadingEnter" @after-leave="onLoadingLeave">
      <div v-if="showLoadingOverlay" class="sp-loading">
        <div class="sp-loader">
          <div class="sp-loader-ring"></div>
        </div>
      </div>
    </Transition>

    <!-- 极简控制层 -->
    <transition name="sp-ui-fade">
      <div v-show="store.controlsVisible" class="sp-controls-wrapper" data-player-interactive>
        <!-- 底部渐变遮罩 -->
        <div class="sp-gradient-overlay"></div>

        <div class="sp-controls-content">
          <!-- 极致紧凑进度条 -->
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
                <div class="sp-progress-played" :style="{ width: `${progress}%` }">
                  <div class="sp-progress-dot"></div>
                </div>
              </div>
              <!-- 预览时间浮窗 -->
              <div v-if="previewTime !== null" class="sp-preview-hint" :style="{ left: `${previewPercent}%` }">
                <div class="sp-preview-hint-inner">
                  {{ formatTime(previewTime) }}
                </div>
              </div>
            </div>
          </div>

          <!-- 核心交互区 -->
          <div class="sp-controls-main">
            <div class="sp-controls-left">
              <button class="sp-icon-btn sp-btn--play" @click="togglePlay" :title="isPlaying ? t('pause') : t('play')">
                <PlayerIcon :name="isPlaying ? 'pause' : 'play'" />
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
              <div v-if="displayedQualities.length > 0" class="sp-quality-tag" @click.stop="toggleQualityMenu">
                {{ qualityTagLabel }}
              </div>
              <button v-if="subtitleTracks.length > 0" class="sp-icon-btn" @click.stop="toggleSubtitlesQuick" :title="t('subtitles')">
                <PlayerIcon :name="store.subtitlesEnabled ? 'subtitles' : 'subtitlesOff'" />
              </button>
              <button class="sp-icon-btn" @click.stop="toggleSettingsMenu" :title="t('settings')">
                <PlayerIcon name="settings" />
              </button>
              <button class="sp-icon-btn" @click="toggleWidescreen" :title="props.widescreen ? t('exitWidescreen') : t('widescreen')">
                <PlayerIcon :name="props.widescreen ? 'widescreenExit' : 'widescreen'" />
              </button>
              <button class="sp-icon-btn" @click="toggleFullscreen" :title="isFullscreen ? t('exitFullscreen') : t('fullscreen')">
                <PlayerIcon :name="isFullscreen ? 'fullscreenExit' : 'fullscreen'" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 独立画质菜单 -->
    <transition name="sp-ui-fade">
      <div v-if="showQualityMenu" class="sp-settings-pop sp-quality-pop" data-player-interactive>
        <div class="sp-menu-list">
          <div
            v-for="q in displayedQualities"
            :key="q.id"
            class="sp-menu-item"
            :class="{ 'is-active': currentQualityId === q.id }"
            @click="handleQualitySelect(q)"
          >
            {{ q.label }}
          </div>
        </div>
      </div>
    </transition>

    <!-- 设置菜单 -->
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
            <div v-if="codecFamilies.length > 1" class="sp-menu-item" @click="settingsView = 'codec'">
              <span>{{ t('codec') }}</span>
              <span class="sp-menu-val">{{ codecMenuLabel }}</span>
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
        <template v-else-if="settingsView === 'codec'">
          <div class="sp-menu-item" style="opacity: 0.5" @click="settingsView = 'main'">
            <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ t('codec') }}
          </div>
          <div class="sp-menu-list">
            <div
              v-for="codecFamily in codecFamilies"
              :key="codecFamily"
              class="sp-menu-item"
              :class="{ 'is-active': selectedCodecFamily === codecFamily }"
              @click="handleCodecFamilySelect(codecFamily)"
            >
              {{ formatCodecFamilyLabel(codecFamily) }}
            </div>
          </div>
        </template>
        <template v-else-if="settingsView === 'quality'">
          <div class="sp-menu-item" style="opacity: 0.5" @click="settingsView = 'main'">
            <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ t('quality') }}
          </div>
          <div class="sp-menu-list">
            <div v-for="q in displayedQualities" :key="q.id" 
                 class="sp-menu-item" :class="{ 'is-active': currentQualityId === q.id }"
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
            <!-- 预设 -->
            <div class="sp-menu-item" @click="settingsView = 'subtitlePreset'">
              <span>{{ t('preset') }}</span>
              <span class="sp-menu-val">{{ currentPresetLabel }}</span>
            </div>
            <!-- 字体大小 -->
            <div class="sp-menu-item" @click="settingsView = 'subtitleFontSize'">
              <span>{{ t('fontSize') }}</span>
              <span class="sp-menu-val">{{ subtitleStyleLabel('fontSize', subtitleStyle.fontSize || 'medium', fontSizeOptions) }}</span>
            </div>
            <!-- 字体颜色 -->
            <div class="sp-menu-item" @click="settingsView = 'subtitleColor'">
              <span>{{ t('fontColor') }}</span>
              <span class="sp-subtitle-color-preview" :style="{ background: subtitleStyle.color || '#ffffff' }"></span>
            </div>
            <!-- 背景颜色 -->
            <div class="sp-menu-item" @click="settingsView = 'subtitleBg'">
              <span>{{ t('backgroundColor') }}</span>
              <span class="sp-subtitle-color-preview" :style="{ background: subtitleStyle.backgroundColor || 'rgba(0,0,0,0.8)' }"></span>
            </div>
            <!-- 字幕位置 -->
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
import { usePlayer } from './runtime/usePlayer'
import {
  getNextControlsVisibilityOnTouchTap,
  shouldHandlePointerVisibility,
  shouldAutoHideControls,
  shouldTogglePlayOnVideoClick
} from './runtime/mobileControls'
import type { MediaSource, SubtitleTrack } from './core'
import type { ThemeName } from './themes'
import type { IconName } from './core/useIcons'
import PlayerIcon from './PlayerIcon.vue'

// 基础变量与主题
import './themes/variables.css'
import './themes/dark.css'
import './themes/light.css'
import './themes/cyber.css'
import './themes/scifi.css'

interface Props {
  source?: MediaSource | null
  subtitles?: SubtitleTrack[]
  poster?: string
  title?: string
  autoplay?: boolean
  theme?: ThemeName
  initialTime?: number
  widescreen?: boolean
  externalLoading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  source: null,
  subtitles: () => [],
  poster: '',
  title: '',
  autoplay: true,
  theme: 'dark',
  widescreen: false,
  externalLoading: false,
})

const emit = defineEmits(['play', 'pause', 'ended', 'timeupdate', 'error', 'fullscreenChange', 'retry', 'widescreenChange'])

const {
  store, videoElement, containerElement, isPlaying, currentTime, duration, volume, isMuted, isFullscreen,
  play, pause, seek, setVolume, toggleMute, setPlaybackRate, toggleFullscreen,
  subtitleTracks, currentSubtitle, subtitleStyle, subtitlePresets, setSubtitle, setSubtitleTracks, setSubtitleStyle, applySubtitlePreset, loadSource, theme, t,
  qualities, codecFamilies, selectedCodecFamily, currentCodecFamily,
  currentQualityLabel, currentQualityId, setQuality, setCodecFamily
} = usePlayer({
  autoplay: props.autoplay,
  theme: props.theme,
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

const showSettingsMenu = ref(false)
const showQualityMenu = ref(false)
const settingsView = ref('main')
const previewTime = ref<number | null>(null)
const previewPercent = ref(0)
const isScrubbing = ref(false)
const isVolumeScrubbing = ref(false)
const lastPointerType = ref('mouse')
const shouldResumeAfterSourceSwap = ref(false)
const hidePosterForCurrentSource = ref(false)
const errorState = ref({ show: false, title: '', message: '', code: '', canRetry: true })
const centralHud = ref<{ visible: boolean; type: string; value: string; icon: IconName; percent: number }>({ 
  visible: false, type: '', value: '', icon: 'play', percent: 0 
})
const showLoadingOverlay = computed(() => (store.loading || props.externalLoading) && !errorState.value.show)
const effectivePoster = computed(() => hidePosterForCurrentSource.value ? '' : (props.source?.poster || props.poster || ''))

// 加载状态控制
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
const volumeIconName = computed(() => (isMuted.value || volume.value === 0) ? 'volumeOff' : volume.value < 50 ? 'volumeLow' : 'volumeHigh')
const visibleCodecFamily = computed(() => (
  selectedCodecFamily.value !== 'auto'
    ? selectedCodecFamily.value
    : currentCodecFamily.value || inferCodecFamilyFromLabel(currentQualityLabel.value)
))
const displayedQualities = computed(() => {
  if (!visibleCodecFamily.value) return qualities.value
  const codecMatchedQualities = qualities.value.filter((quality) => getCodecFamily(quality.codec) === visibleCodecFamily.value)
  return codecMatchedQualities.length > 0 ? codecMatchedQualities : qualities.value
})
const isInternalQualityLabel = (label: string | null | undefined) => /^level[_\s-]?\d+$/i.test(String(label || '').trim())
const isAutoQualityLabel = (label: string | null | undefined) => ['auto', '自动', '自動'].includes(String(label || '').trim().toLowerCase())
const isDisplayableQualityLabel = (label: string | null | undefined) => !isInternalQualityLabel(label) && !isAutoQualityLabel(label)
const qualityTagLabel = computed(() => (
  isDisplayableQualityLabel(currentQualityLabel.value)
    ? (currentQualityLabel.value || '')
    : (displayedQualities.value[0]?.label || t('quality'))
))
const qualityMenuLabel = computed(() => isDisplayableQualityLabel(currentQualityLabel.value) ? (currentQualityLabel.value || '') : (displayedQualities.value[0]?.label || t('quality')))
const subtitleMenuLabel = computed(() => {
  if (!store.subtitlesEnabled || !currentSubtitle.value) return t('subtitlesOff')
  return currentSubtitle.value.label
})
const codecMenuLabel = computed(() => (
  selectedCodecFamily.value === 'auto'
    ? formatCodecFamilyLabel(currentCodecFamily.value || visibleCodecFamily.value || codecFamilies.value[0] || null)
    : formatCodecFamilyLabel(selectedCodecFamily.value)
))

let removeInitialTimeListener: (() => void) | null = null
let initialTimeAppliedSourceKey: string | null = null

const clearInitialTimeListener = (): void => {
  if (!removeInitialTimeListener) return
  removeInitialTimeListener()
  removeInitialTimeListener = null
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

watch(videoRef, (el) => { videoElement.value = el }, { immediate: true })
watch(containerRef, (el) => { containerElement.value = el }, { immediate: true })
watch(() => props.source, (s, previousSource) => {
  const sourceChanged = getSourceIdentity(s) !== getSourceIdentity(previousSource)
  if (sourceChanged) {
    clearInitialTimeListener()
    initialTimeAppliedSourceKey = null
    hidePosterForCurrentSource.value = false
  }
  if (!s) {
    shouldResumeAfterSourceSwap.value = isPlaying.value
    pause()
    return
  }
  loadSource(s)
  if (shouldResumeAfterSourceSwap.value) {
    shouldResumeAfterSourceSwap.value = false
    void play()
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
const handleCodecFamilySelect = (codecFamily: string) => { setCodecFamily(codecFamily); closeMenus() }
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
const toggleWidescreen = () => emit('widescreenChange', !props.widescreen)
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

const onPointerEnter = (event: PointerEvent) => {
  if (!shouldHandlePointerVisibility(event.pointerType)) return
  showControls()
}
const onPointerLeave = (event: PointerEvent) => {
  if (!shouldHandlePointerVisibility(event.pointerType)) return
  if (!isScrubbing.value) hideControls()
}
const onPointerMove = (event: PointerEvent) => {
  if (!shouldHandlePointerVisibility(event.pointerType)) return
  showControls()
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

  if (isScrubbing.value) {
    seek(previewTime.value)
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
}

const getCodecFamily = (codec: string | null | undefined) => {
  if (!codec) return null
  const normalized = String(codec).toLowerCase()
  if (normalized.includes('av01') || normalized.includes('av1')) return 'av1'
  if (normalized.includes('vp09') || normalized.includes('vp9')) return 'vp9'
  if (normalized.includes('avc1') || normalized.includes('avc') || normalized.includes('h264')) return 'avc'
  return normalized
}

const inferCodecFamilyFromLabel = (label: string | null | undefined) => {
  if (!label) return null
  return getCodecFamily(label)
}

const formatCodecFamilyLabel = (codecFamily: string | null | undefined) => {
  if (!codecFamily) return t('codec')
  const normalized = String(codecFamily).toLowerCase()
  if (normalized === 'av1') return 'AV1'
  if (normalized === 'vp9') return 'VP9'
  if (normalized === 'avc') return 'AVC'
  return normalized.toUpperCase()
}

const markPlayerActive = () => {}
const handlePointerDown = (event: PointerEvent) => {
  lastPointerType.value = event.pointerType || 'mouse'
}

watch(isPlaying, (playing) => {
  if (playing) {
    hidePosterForCurrentSource.value = true
  }

  if (!playing) {
    showControls()
    return
  }

  syncHideTimer()
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
  window.addEventListener('pointermove', onWindowProgressPointerMove)
  window.addEventListener('pointerup', onWindowProgressPointerUp)
  window.addEventListener('pointercancel', onWindowProgressPointerUp)
})
onUnmounted(() => {
  clearHideTimer()
  clearInitialTimeListener()
  releaseProgressPointerCapture()
  window.removeEventListener('pointermove', onWindowProgressPointerMove)
  window.removeEventListener('pointerup', onWindowProgressPointerUp)
  window.removeEventListener('pointercancel', onWindowProgressPointerUp)
  window.removeEventListener('keydown', handleKeyDown)
})

defineExpose({ play, pause, seek, toggleFullscreen })
</script>

<style scoped>
.sp-player {
  position: absolute;
  inset: 0;
  background: #000;
  overflow: hidden;
  cursor: none;
  font-family: var(--sp-font-family);
  user-select: none;
  letter-spacing: 0.015em;
}

.sp-player.is-active {
  cursor: pointer;
}

.sp-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

/* 全屏视觉增强层 */
.sp-vignette-overlay {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle, transparent 50%, rgba(0,0,0,0.4) 100%);
  pointer-events: none;
  z-index: 5;
}

/* 中央 HUD 指示器 */
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
  transition: opacity 0.15s, transform 0.15s cubic-bezier(0.19, 1, 0.22, 1);
}

.sp-hud-fade-enter-from { opacity: 0; transform: translate(-50%, -30%) scale(0.95); }
.sp-hud-fade-leave-to { opacity: 0; transform: translate(-50%, -70%) scale(1.05); }

/* HUD 系统状态 */
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

/* 底部渐变遮罩 */
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

/* 进度条容器 */
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
  transition: height 0.2s cubic-bezier(0.19, 1, 0.22, 1);
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

.sp-progress-dot {
  width: 10px;
  height: 100%;
  background: #fff;
  position: absolute;
  right: 0;
  transform: scaleX(0);
  transform-origin: right;
  transition: transform 0.2s ease;
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.8);
}

.sp-progress-container:hover .sp-progress-dot {
  transform: scaleX(1);
  width: 2px;
}

/* 预览时间提示 */
.sp-preview-hint {
  position: absolute;
  bottom: 20px;
  transform: translateX(-50%);
  pointer-events: none;
  animation: hint-fade 0.2s ease-out;
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

/* 控制按钮主区域 */
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

/* 画质标签 */
.sp-quality-tag {
  font-family: var(--sp-font-mono);
  font-size: 10px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.6);
  padding: 2px 6px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.2s;
  background: rgba(255, 255, 255, 0.05);
  letter-spacing: 0.05em;
  margin-right: 4px;
}

.sp-quality-tag:hover {
  color: var(--sp-primary);
  border-color: var(--sp-primary);
  background: rgba(var(--sp-primary-rgb), 0.1);
  box-shadow: 0 0 8px rgba(var(--sp-primary-rgb), 0.3);
}

/* 按钮样式优化 */
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
  transition: all 0.25s cubic-bezier(0.19, 1, 0.22, 1);
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
  transition: all 0.2s cubic-bezier(0.19, 1, 0.22, 1);
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

/* 时间显示 */
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

/* 音量控制 */
.sp-volume-group {
  display: flex;
  align-items: center;
  gap: 2px;
}

.sp-volume-slider-wrap {
  width: 0;
  overflow: hidden;
  opacity: 0;
  transition: all 0.3s cubic-bezier(0.19, 1, 0.22, 1);
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

/* 设置菜单提示框 */
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
  transition: all 0.2s;
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
  transition: background 0.3s;
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
  transition: transform 0.25s cubic-bezier(0.19, 1, 0.22, 1);
}

.sp-simple-switch.is-on::after { transform: translateX(14px); }

/* 字幕颜色预览 */
.sp-subtitle-color-preview {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  border: 1px solid rgba(255,255,255,0.2);
  flex-shrink: 0;
}

/* 字幕颜色网格 */
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
  transition: all 0.2s;
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

/* 字幕透明度滑块 */
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

/* 加载动画 */
.sp-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
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
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 加载状态过渡动画 */
.sp-loading-fade-enter-active,
.sp-loading-fade-leave-active {
  transition: opacity 0.3s ease;
}

.sp-loading-fade-enter-from,
.sp-loading-fade-leave-to {
  opacity: 0;
}

.sp-ui-fade-enter-active, .sp-ui-fade-leave-active {
  transition: opacity 0.3s cubic-bezier(0.19, 1, 0.22, 1), transform 0.3s cubic-bezier(0.19, 1, 0.22, 1);
}

.sp-ui-fade-enter-from, .sp-ui-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
