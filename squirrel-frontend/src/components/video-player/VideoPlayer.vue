<template>
  <div 
    ref="containerRef"
    class="sp-player"
    :class="[`sp-theme-${theme}`, { 'is-active': store.controlsVisible }]"
    @pointerenter="onPointerEnter"
    @pointerleave="onPointerLeave"
    @pointermove="onPointerMove"
    @pointerdown="handlePointerDown"
    @click="handleVideoClick"
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
      @dblclick="toggleFullscreen"
    />

    <!-- HUD 系统状态 -->
    <div class="sp-hud-overlay">
      <div class="sp-hud-tag">
        <span class="sp-hud-dot" :class="{ 'is-pulsing': isPlaying }"></span>
        <span class="sp-hud-text">LIVE_DECODE::{{ isPlaying ? 'ACTIVE' : 'STANDBY' }}</span>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="store.loading && store.loadingStage !== 'buffering' && !errorState.show" class="sp-loading">
      <div class="sp-loader-ring">
        <div class="sp-loader-segment"></div>
        <div class="sp-loader-segment"></div>
        <div class="sp-loader-segment"></div>
        <div class="sp-loader-segment"></div>
      </div>
      <div class="sp-loading-text">SYNCING_DATA...</div>
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
              <div v-if="qualities.length > 0" class="sp-quality-tag" @click.stop="toggleQualityMenu">
                {{ currentQualityLabel || 'AUTO' }}
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
            <div v-if="qualities.length > 0" class="sp-menu-item" @click="settingsView = 'quality'">
              <span>{{ t('quality') }}</span>
              <span class="sp-menu-val">{{ currentQualityLabel || 'AUTO' }}</span>
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
            <div v-for="q in qualities" :key="q.id" 
                 class="sp-menu-item" :class="{ 'is-active': currentQualityId === q.id }"
                 @click="handleQualitySelect(q)">
              {{ q.label }}
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
  title?: string
  autoplay?: boolean
  theme?: ThemeName
  initialTime?: number
  widescreen?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  source: null,
  subtitles: () => [],
  poster: '',
  title: '',
  autoplay: true,
  theme: 'dark',
  widescreen: false
})

const emit = defineEmits(['play', 'pause', 'timeupdate', 'error', 'fullscreenChange', 'retry', 'widescreenChange'])

const {
  store, videoElement, containerElement, isPlaying, currentTime, duration, volume, isMuted, isFullscreen,
  play, pause, seek, setVolume, toggleMute, setPlaybackRate, toggleFullscreen,
  subtitleTracks, currentSubtitle, setSubtitle, setSubtitleTracks, loadSource, theme, t,
  qualities, currentQualityLabel, currentQualityId, setQuality
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
const toggleQualityMenu = () => { showSettingsMenu.value = true; settingsView.value = 'quality' }
const handleSpeedSelect = (rate: number) => { setPlaybackRate(rate); showSettingsMenu.value = false }
const handleQualitySelect = (q: any) => { setQuality(q.id); showSettingsMenu.value = false }
const toggleWidescreen = () => emit('widescreenChange', !props.widescreen)
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
  padding: 4px 10px;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 77, 0, 0.2);
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
  border: 1px solid rgba(255, 77, 0, 0.25);
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
  background: rgba(255, 77, 0, 0.1);
  border: 1px solid rgba(255, 77, 0, 0.15);
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
  background: rgba(10, 10, 10, 0.95);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 77, 0, 0.2);
  border-radius: 8px;
  padding: 6px;
  z-index: 100;
  box-shadow: 0 16px 48px rgba(0,0,0,0.85);
  overflow: hidden;
}

.sp-settings-pop::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(255, 77, 0, 0.05) 50%);
  background-size: 100% 4px;
  pointer-events: none;
  opacity: 0.2;
}

.sp-menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  color: rgba(255, 255, 255, 0.85);
  font-size: 13px;
  font-family: var(--sp-font-family);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  z-index: 1;
  letter-spacing: 0.03em;
}

.sp-menu-item:hover {
  background: rgba(255, 77, 0, 0.15);
  color: #fff;
}

.sp-menu-item.is-active {
  color: var(--sp-primary);
  background: rgba(var(--sp-primary-rgb), 0.1);
}

.sp-simple-switch {
  width: 30px;
  height: 16px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  position: relative;
  transition: background 0.3s;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.sp-simple-switch.is-on { 
  background: var(--sp-primary);
  border-color: rgba(255, 77, 0, 0.5);
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

/* 加载动画 - 终端旋转环 */
.sp-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 5;
  gap: 16px;
  background: rgba(0,0,0,0.2);
}

.sp-loader-ring {
  width: 54px;
  height: 54px;
  position: relative;
  animation: loader-rotate 2s linear infinite;
}

.sp-loader-segment {
  position: absolute;
  inset: 0;
  border: 3px solid transparent;
  border-top-color: var(--sp-primary);
  border-radius: 50%;
  opacity: 0.3;
}

.sp-loader-segment:nth-child(1) { transform: rotate(0deg); opacity: 1; }
.sp-loader-segment:nth-child(2) { transform: rotate(120deg); }
.sp-loader-segment:nth-child(3) { transform: rotate(240deg); }

.sp-loading-text {
  color: var(--sp-primary);
  font-family: var(--sp-font-mono);
  font-size: 11px;
  letter-spacing: 0.2em;
  font-weight: 700;
  text-shadow: 0 0 10px rgba(255, 77, 0, 0.4);
  animation: text-pulse 1.5s infinite;
}

@keyframes loader-rotate {
  to { transform: rotate(360deg); }
}

@keyframes text-pulse {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}

.sp-ui-fade-enter-active, .sp-ui-fade-leave-active {
  transition: opacity 0.3s cubic-bezier(0.19, 1, 0.22, 1), transform 0.3s cubic-bezier(0.19, 1, 0.22, 1);
}

.sp-ui-fade-enter-from, .sp-ui-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
