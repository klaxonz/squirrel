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
    <!-- 视频核心 -->
    <video
      ref="videoRef"
      class="sp-video"
      :poster="source?.poster || poster"
      :muted="store.muted"
      :autoplay="store.autoplay"
      :loop="store.loop"
      crossorigin="anonymous"
      playsinline
      webkit-playsinline
      @click="handleVideoClick"
      @dblclick="toggleFullscreen"
    />

    <!-- 加载状态 -->
    <div v-if="store.loading && store.loadingStage !== 'buffering' && !errorState.show" class="sp-loading">
      <div class="sp-spinner-pulse"></div>
    </div>

    <!-- 极简控制层 -->
    <transition name="sp-ui-fade">
      <div v-show="store.controlsVisible" class="sp-controls-wrapper">
        <!-- 底部渐变遮罩 -->
        <div class="sp-gradient-overlay"></div>

        <div class="sp-controls-content">
          <!-- 极致紧凑进度条 -->
          <div class="sp-progress-container">
            <div class="sp-progress-area" 
                 @pointerdown.prevent="onProgressPointerDown"
                 @pointermove="onProgressPointerMove"
                 @pointerleave="onProgressPointerLeave"
                 @pointerup="onProgressPointerUp">
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
                    <div class="sp-volume-fill" :style="{ width: `${isMuted ? 0 : volume}%` }"></div>
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
              <button v-if="subtitleTracks.length > 0" class="sp-icon-btn" @click.stop="toggleSubtitlesQuick" :title="t('subtitles')">
                <PlayerIcon :name="store.subtitlesEnabled ? 'subtitles' : 'subtitlesOff'" />
              </button>
              <button class="sp-icon-btn" @click.stop="toggleSettingsMenu" :title="t('settings')">
                <PlayerIcon name="settings" />
              </button>
              <button class="sp-icon-btn" @click="toggleFullscreen" :title="isFullscreen ? t('exitFullscreen') : t('fullscreen')">
                <PlayerIcon :name="isFullscreen ? 'fullscreenExit' : 'fullscreen'" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 设置菜单 -->
    <transition name="sp-ui-fade">
      <div v-if="showSettingsMenu" class="sp-settings-pop" ref="settingsPopupRef">
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
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { usePlayer } from './runtime/usePlayer'
import type { MediaSource, SubtitleTrack } from './core'
import type { ThemeName } from './themes'
import PlayerIcon from './PlayerIcon.vue'

// 基础变量
import './themes/variables.css'

interface Props {
  source?: MediaSource | null
  subtitles?: SubtitleTrack[]
  poster?: string
  autoplay?: boolean
  theme?: ThemeName
  initialTime?: number
}

const props = withDefaults(defineProps<Props>(), {
  source: null,
  subtitles: () => [],
  poster: '',
  autoplay: true,
  theme: 'dark'
})

const emit = defineEmits(['play', 'pause', 'timeupdate', 'error', 'fullscreenChange', 'retry'])

const {
  store, videoElement, containerElement, isPlaying, currentTime, duration, volume, isMuted, isFullscreen,
  play, pause, seek, setVolume, toggleMute, setPlaybackRate, toggleFullscreen,
  subtitleTracks, currentSubtitle, setSubtitle, setSubtitleTracks, loadSource, theme, t
} = usePlayer({
  autoplay: props.autoplay,
  theme: props.theme,
  onPlay: () => emit('play'),
  onPause: () => emit('pause'),
  onError: (e) => emit('error', e),
  onTimeUpdate: (time) => emit('timeupdate', time)
})

const videoRef = ref<HTMLVideoElement | null>(null)
const containerRef = ref<HTMLElement | null>(null)
const settingsPopupRef = ref<HTMLElement | null>(null)

const showSettingsMenu = ref(false)
const settingsView = ref('main')
const previewTime = ref<number | null>(null)
const previewPercent = ref(0)
const isScrubbing = ref(false)
const isVolumeScrubbing = ref(false)
const errorState = ref({ show: false, title: '', message: '', code: '', canRetry: true })

const playbackRates = [0.5, 0.75, 1, 1.25, 1.5, 2]
const progress = computed(() => duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0)
const volumeIconName = computed(() => (isMuted.value || volume.value === 0) ? 'volumeOff' : volume.value < 50 ? 'volumeLow' : 'volumeHigh')

watch(videoRef, (el) => { videoElement.value = el }, { immediate: true })
watch(containerRef, (el) => { containerElement.value = el }, { immediate: true })
watch(() => props.source, (s) => { if (s) loadSource(s) }, { immediate: true })
watch(() => props.subtitles, (ts) => { setSubtitleTracks(ts || []) }, { immediate: true, deep: true })

const togglePlay = () => isPlaying.value ? pause() : play()
const toggleSettingsMenu = () => { showSettingsMenu.value = !showSettingsMenu.value; settingsView.value = 'main' }
const handleSpeedSelect = (rate: number) => { setPlaybackRate(rate); showSettingsMenu.value = false }
const toggleAutoplayNext = () => store.setAutoplayNext(!store.autoplayNext)
const toggleLoop = () => store.setLoop(!store.loop)
const toggleSubtitlesQuick = () => setSubtitle(store.subtitlesEnabled ? null : (subtitleTracks.value[0] || null))
const handleVideoClick = () => togglePlay()

const onPointerEnter = () => store.setControlsVisible(true)
const onPointerLeave = () => { if (!isScrubbing.value) store.setControlsVisible(false); showSettingsMenu.value = false }
const onPointerMove = () => { store.setControlsVisible(true); resetHideTimer() }

let hideTimer: any
const resetHideTimer = () => {
  clearTimeout(hideTimer)
  if (isPlaying.value && !isScrubbing.value) hideTimer = setTimeout(() => store.setControlsVisible(false), 3000)
}

const onProgressPointerDown = (e: PointerEvent) => {
  isScrubbing.value = true
  handleProgressMove(e)
}
const onProgressPointerMove = (e: PointerEvent) => {
  handleProgressMove(e)
}
const handleProgressMove = (e: PointerEvent) => {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  const p = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
  previewPercent.value = p * 100
  previewTime.value = p * duration.value
  if (isScrubbing.value) seek(previewTime.value)
}
const onProgressPointerUp = () => { isScrubbing.value = false }
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
}

const formatTime = (s: number) => {
  if (!isFinite(s)) return '0:00'
  const m = Math.floor(s / 60), sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

const markPlayerActive = () => {}
const handlePointerDown = () => {}

onMounted(() => { window.addEventListener('keydown', handleKeyDown) })
onUnmounted(() => { window.removeEventListener('keydown', handleKeyDown) })

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
}

.sp-player.is-active {
  cursor: default;
}

.sp-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
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
}

.sp-controls-content {
  padding: 0 10px 4px;
  margin: 0;
  position: relative;
  z-index: 25;
}

/* 进度条容器 - 增加点击感知范围 */
.sp-progress-container {
  padding: 4px 0;
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
  background: rgba(15, 15, 15, 0.9);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #fff;
  font-size: 10px;
  font-family: var(--sp-font-mono);
  border-radius: 4px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.5);
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
  gap: 8px;
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
  transition: all 0.2s cubic-bezier(0.19, 1, 0.22, 1);
  position: relative;
}

.sp-icon-btn::after {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  transform: scale(0.8);
  opacity: 0;
  transition: all 0.2s cubic-bezier(0.19, 1, 0.22, 1);
}

.sp-icon-btn:hover {
  color: var(--sp-primary, #ff4d00);
}

.sp-icon-btn:hover::after {
  transform: scale(1);
  opacity: 1;
}

.sp-icon-btn :deep(svg) {
  width: 18px;
  height: 18px;
  filter: drop-shadow(0 0 4px rgba(0,0,0,0.2));
}

.sp-btn--play :deep(svg) {
  width: 20px;
  height: 20px;
}

/* 时间显示 */
.sp-time-display {
  font-family: var(--sp-font-mono);
  font-size: 12px;
  color: #fff;
  display: flex;
  align-items: center;
  padding-left: 4px;
  letter-spacing: 0.01em;
}

.sp-time-separator {
  margin: 0 4px;
  opacity: 0.25;
}

.sp-time-total {
  opacity: 0.45;
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
  width: 70px;
  opacity: 1;
  padding: 0 6px;
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
  background: #fff;
  border-radius: 1.5px;
}

/* 设置菜单提示框 */
.sp-settings-pop {
  position: absolute;
  bottom: 56px;
  right: 10px;
  width: 200px;
  background: rgba(10, 10, 10, 0.94);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 5px;
  z-index: 100;
  box-shadow: 0 12px 40px rgba(0,0,0,0.7);
}

.sp-menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  color: rgba(255, 255, 255, 0.85);
  font-size: 13px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.sp-menu-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.sp-menu-item.is-active {
  color: var(--sp-primary);
  background: rgba(var(--sp-primary-rgb), 0.1);
}

.sp-simple-switch {
  width: 32px;
  height: 18px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 9px;
  position: relative;
  transition: background 0.3s;
}

.sp-simple-switch.is-on { background: var(--sp-primary); }

.sp-simple-switch::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 12px;
  height: 12px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.25s cubic-bezier(0.19, 1, 0.22, 1);
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

.sp-simple-switch.is-on::after { transform: translateX(14px); }

/* 加载动画 */
.sp-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 5;
}

.sp-spinner-pulse {
  width: 48px;
  height: 48px;
  border: 3px solid var(--sp-primary);
  border-radius: 50%;
  animation: sp-pulse 1.2s ease-out infinite;
}

@keyframes sp-pulse {
  0% { transform: scale(0.6); opacity: 1; }
  100% { transform: scale(1.6); opacity: 0; }
}

.sp-ui-fade-enter-active, .sp-ui-fade-leave-active {
  transition: opacity 0.3s cubic-bezier(0.19, 1, 0.22, 1), transform 0.3s cubic-bezier(0.19, 1, 0.22, 1);
}

.sp-ui-fade-enter-from, .sp-ui-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
