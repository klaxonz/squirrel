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
    <!-- 全屏视觉增强层 -->
    <div class="sp-vignette-overlay"></div>
    <div class="sp-grid-overlay"></div>

    <!-- 战术边角装饰 -->
    <div class="sp-tactical-corners">
      <div class="corner-tl"></div>
      <div class="corner-tr"></div>
      <div class="corner-bl"></div>
      <div class="corner-br"></div>
    </div>

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

    <!-- 中央 HUD 指示器 -->
    <transition name="sp-hud-fade">
      <div v-if="centralHud.visible" class="sp-central-hud">
        <div class="sp-central-hud-content">
          <PlayerIcon :name="centralHud.icon" class="sp-central-hud-icon" />
          <div class="sp-central-hud-value">{{ centralHud.value }}</div>
        </div>
      </div>
    </transition>

    <!-- HUD 系统状态 -->
    <div class="sp-hud-overlay">
      <div class="sp-hud-tag">
        <span class="sp-hud-dot" :class="{ 'is-pulsing': isPlaying }"></span>
        <span class="sp-hud-text">LIVE_DECODE::{{ isPlaying ? 'ACTIVE' : 'STANDBY' }}</span>
        <span class="sp-hud-separator">|</span>
        <span class="sp-hud-code">{{ simulateBitrate }}kbps</span>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="store.loading && !errorState.show" class="sp-loading">
      <div class="sp-loader-ring">
        <div class="sp-loader-segment"></div>
        <div class="sp-loader-segment"></div>
        <div class="sp-loader-segment"></div>
      </div>
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
import type { IconName } from './core/useIcons'
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
const centralHud = ref<{ visible: boolean; type: string; value: string; icon: IconName; percent: number }>({ 
  visible: false, type: '', value: '', icon: 'play', percent: 0 
})
const simulateBitrate = ref(0)

let centralHudTimer: any
const showCentralHud = (type: string, value: string, icon: IconName, percent: number = 0) => {
  clearTimeout(centralHudTimer)
  centralHud.value = { visible: true, type, value, icon, percent }
  centralHudTimer = setTimeout(() => { centralHud.value.visible = false }, 1500)
}

// 模拟码率跳动
let bitrateInterval: any
const updateBitrate = () => {
  if (!isPlaying.value) { simulateBitrate.value = 0; return }
  const base = currentQualityLabel.value?.includes('1080') ? 4500 : 2500
  simulateBitrate.value = base + Math.floor(Math.random() * 800)
}

watch(isPlaying, (val) => {
  if (val) {
    bitrateInterval = setInterval(updateBitrate, 1000)
  } else {
    clearInterval(bitrateInterval)
    simulateBitrate.value = 0
  }
})

watch(volume, (newVol, oldVol) => {
  if (Math.abs(newVol - oldVol) < 0.1) return
  showCentralHud('volume', `${Math.round(newVol)}%`, volumeIconName.value, newVol)
})

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
  if (e.key === 'ArrowLeft') { seek(currentTime.value - 10); showCentralHud('seek', '-10s', 'skipBackward') }
  if (e.key === 'ArrowRight') { seek(currentTime.value + 10); showCentralHud('seek', '+10s', 'skipForward') }
  if (e.key === 'ArrowUp') { setVolume(Math.min(100, volume.value + 5)) }
  if (e.key === 'ArrowDown') { setVolume(Math.max(0, volume.value - 5)) }
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
  transition: transform 0.4s cubic-bezier(0.19, 1, 0.22, 1);
}

/* 全屏视觉增强层 */
.sp-vignette-overlay {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle, transparent 60%, rgba(0,0,0,0.5) 100%);
  pointer-events: none;
  z-index: 5;
}

.sp-grid-overlay {
  position: absolute;
  inset: 0;
  background-image: 
    linear-gradient(rgba(255, 77, 0, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 77, 0, 0.02) 1px, transparent 1px);
  background-size: 30px 30px;
  pointer-events: none;
  z-index: 6;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.is-active .sp-grid-overlay {
  opacity: 1;
}

/* 战术边角 */
.sp-tactical-corners div {
  position: absolute;
  width: 12px;
  height: 12px;
  border: 1px solid rgba(255, 77, 0, 0.3);
  z-index: 10;
  pointer-events: none;
  transition: all 0.4s cubic-bezier(0.19, 1, 0.22, 1);
}

.corner-tl { top: 20px; left: 20px; border-right: none; border-bottom: none; }
.corner-tr { top: 20px; right: 20px; border-left: none; border-bottom: none; }
.corner-bl { bottom: 20px; left: 20px; border-right: none; border-top: none; }
.corner-br { bottom: 20px; right: 20px; border-left: none; border-top: none; }

.is-active .sp-tactical-corners div {
  width: 24px;
  height: 24px;
  border-color: rgba(255, 77, 0, 0.6);
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
  background: rgba(10, 10, 10, 0.6);
  backdrop-filter: blur(12px);
  padding: 8px 18px;
  border-radius: 20px;
  border: 1px solid rgba(255, 77, 0, 0.3);
  box-shadow: 0 0 30px rgba(255, 77, 0, 0.15);
}

.sp-central-hud-icon {
  width: 18px;
  height: 18px;
  color: var(--sp-primary);
  filter: drop-shadow(0 0 5px var(--sp-primary));
}

.sp-central-hud-value {
  color: #fff;
  font-family: var(--sp-font-mono);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.sp-hud-fade-enter-active, .sp-hud-fade-leave-active {
  transition: opacity 0.1s, transform 0.1s cubic-bezier(0.19, 1, 0.22, 1);
}

.sp-hud-fade-enter-from { opacity: 0; transform: translate(-50%, -45%) scale(0.98); }
.sp-hud-fade-leave-to { opacity: 0; transform: translate(-50%, -55%) scale(1.02); }

/* HUD 系统状态 */
.sp-hud-overlay {
  position: absolute;
  top: 24px;
  left: 24px;
  z-index: 10;
  pointer-events: none;
  transition: transform 0.3s ease;
}

.is-active .sp-hud-overlay {
  transform: translateX(10px);
}

.sp-hud-tag {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 77, 0, 0.2);
  border-radius: 4px;
  position: relative;
}

.sp-hud-tag::after {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: 4px;
  background: linear-gradient(45deg, var(--sp-primary), transparent, var(--sp-primary));
  opacity: 0.1;
  pointer-events: none;
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
  color: rgba(255, 255, 255, 0.5);
  font-family: var(--sp-font-mono);
  font-size: 9px;
  width: 55px;
}

/* 底部渐变遮罩 */
.sp-gradient-overlay {
  position: absolute;
  inset: auto 0 0 0;
  height: 140px;
  background: linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.4) 50%, transparent 100%);
  pointer-events: none;
  z-index: 15;
  transition: opacity 0.3s ease;
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
  padding: 0 16px 12px;
  margin: 0;
  position: relative;
  z-index: 25;
  pointer-events: auto;
  transition: transform 0.3s cubic-bezier(0.19, 1, 0.22, 1);
}

.sp-controls-wrapper:not(.is-active) .sp-controls-content {
  transform: translateY(10px);
}

/* 模块化控制栏设计 */
.sp-controls-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 40px;
  margin-top: 4px;
  background: rgba(10, 10, 10, 0.7);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 0 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
}

.sp-controls-left, .sp-controls-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 进度条容器 */
.sp-progress-container {
  padding: 8px 0;
  margin: 0 4px;
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
  background: rgba(255, 255, 255, 0.1);
  transition: all 0.25s cubic-bezier(0.19, 1, 0.22, 1);
  border-radius: 2px;
  overflow: hidden;
  position: relative;
}

.sp-progress-container:hover .sp-progress-rail {
  height: 6px;
  background: rgba(255, 255, 255, 0.15);
}

.sp-progress-buffered {
  position: absolute;
  height: 100%;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
  border-right: 1px solid rgba(255, 255, 255, 0.3);
}

.sp-progress-played {
  position: absolute;
  height: 100%;
  background: var(--sp-primary, #ff4d00);
  box-shadow: 0 0 15px rgba(var(--sp-primary-rgb), 0.6);
  border-radius: 2px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.sp-progress-dot {
  width: 2px;
  height: 100%;
  background: #fff;
  position: absolute;
  right: 0;
  transform: scaleY(0);
  transition: transform 0.2s ease;
  box-shadow: 0 0 10px #fff;
}

.sp-progress-container:hover .sp-progress-dot {
  transform: scaleY(1.5);
}

/* 预览时间提示 */
.sp-preview-hint {
  position: absolute;
  bottom: 24px;
  transform: translateX(-50%);
  pointer-events: none;
}

.sp-preview-hint-inner {
  padding: 4px 10px;
  background: rgba(10, 10, 10, 0.9);
  backdrop-filter: blur(12px);
  border: 1px solid var(--sp-primary);
  color: #fff;
  font-size: 11px;
  font-family: var(--sp-font-mono);
  border-radius: 4px;
  box-shadow: 0 0 15px rgba(255, 77, 0, 0.3);
}

/* 画质标签 */
.sp-quality-tag {
  font-family: var(--sp-font-mono);
  font-size: 9px;
  font-weight: 800;
  color: var(--sp-primary);
  padding: 1px 5px;
  border: 1px solid rgba(255, 77, 0, 0.4);
  border-radius: 2px;
  cursor: pointer;
  transition: all 0.2s;
  background: rgba(255, 77, 0, 0.05);
  letter-spacing: 0.05em;
}

.sp-quality-tag:hover {
  background: var(--sp-primary);
  color: #000;
  box-shadow: 0 0 12px var(--sp-primary);
}

/* 按钮样式优化 */
.sp-icon-btn {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s cubic-bezier(0.19, 1, 0.22, 1);
  position: relative;
}

.sp-icon-btn:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
  transform: scale(1.1);
}

.sp-icon-btn :deep(svg) {
  width: 18px;
  height: 18px;
}

/* 时间显示 */
.sp-time-display {
  font-family: var(--sp-font-mono);
  font-size: 11px;
  color: #fff;
  display: flex;
  align-items: center;
  padding-left: 4px;
  letter-spacing: 0.02em;
}

.sp-time-separator {
  margin: 0 4px;
  opacity: 0.2;
}

.sp-time-total {
  opacity: 0.4;
}

/* 音量控制 */
.sp-volume-group {
  display: flex;
  align-items: center;
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
  padding: 0 8px;
}

.sp-volume-bar {
  width: 100%;
  height: 2px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 1px;
  position: relative;
  cursor: pointer;
}

.sp-volume-fill {
  height: 100%;
  background: var(--sp-primary);
  border-radius: 1px;
  box-shadow: 0 0 8px var(--sp-primary);
}

/* 设置菜单 */
.sp-settings-pop {
  position: absolute;
  bottom: 64px;
  right: 16px;
  width: 200px;
  background: rgba(10, 10, 10, 0.85);
  backdrop-filter: blur(25px);
  border: 1px solid rgba(255, 77, 0, 0.3);
  border-radius: 12px;
  padding: 6px;
  z-index: 100;
  box-shadow: 0 20px 50px rgba(0,0,0,0.8);
}

.sp-settings-pop::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(rgba(255, 77, 0, 0.03) 50%, transparent 50%);
  background-size: 100% 2px;
  pointer-events: none;
}

.sp-menu-item {
  padding: 10px 14px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
  font-family: var(--sp-font-family);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sp-menu-item:hover {
  background: rgba(255, 77, 0, 0.15);
  color: #fff;
  transform: translateX(4px);
}

/* 加载动画 */
.sp-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 5;
}

.sp-loader-ring {
  width: 36px;
  height: 36px;
  position: relative;
  animation: loader-rotate 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
}

.sp-loader-segment {
  position: absolute;
  inset: 0;
  border: 2px solid transparent;
  border-top-color: var(--sp-primary);
  border-radius: 50%;
  filter: drop-shadow(0 0 5px var(--sp-primary));
}

.sp-loader-segment:nth-child(2) { transform: rotate(120deg); opacity: 0.5; }
.sp-loader-segment:nth-child(3) { transform: rotate(240deg); opacity: 0.2; }

@keyframes loader-rotate {
  to { transform: rotate(360deg); }
}

.sp-ui-fade-enter-active, .sp-ui-fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.19, 1, 0.22, 1);
}

.sp-ui-fade-enter-from, .sp-ui-fade-leave-to {
  opacity: 0;
  transform: translateY(15px);
}
</style>
