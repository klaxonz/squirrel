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
    <div v-if="store.loading && store.loadingStage !== 'buffering'" class="sp-loading">
      <div class="sp-loading-spinner"></div>
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
    />

    <!-- 字幕容器 (由插件管理) -->

    <!-- 缓冲指示器 -->
    <div v-if="isBuffering" class="sp-buffering">
      <div class="sp-loading-spinner"></div>
    </div>

    <!-- 错误提示 -->
    <div v-if="errorState.show" class="sp-error">
      <div class="sp-error-icon">
        <svg viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
        </svg>
      </div>
      <div class="sp-error-title">{{ errorState.title }}</div>
      <div class="sp-error-message">{{ errorState.message }}</div>
      <button class="sp-btn" @click="handleRetry">{{ t('retry') }}</button>
    </div>

    <!-- 控制栏 -->
    <transition name="sp-fade">
      <div v-show="store.controlsVisible" class="sp-controls">
        <!-- 进度条 -->
        <div class="sp-progress-container">
          <div 
            class="sp-progress"
            @mousedown="onProgressMouseDown"
            @mousemove="onProgressMouseMove"
            @mouseleave="onProgressMouseLeave"
          >
            <div class="sp-progress-buffered" :style="{ width: `${store.bufferedPercent}%` }"></div>
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
            <button class="sp-btn" @click="togglePlay" :aria-label="isPlaying ? t('pause') : t('play')">
              <component :is="icons.renderIcon(isPlaying ? 'pause' : 'play')" />
            </button>

            <!-- 上一个/下一个 -->
            <button v-if="hasPrev" class="sp-btn" @click="$emit('prev-video')" :aria-label="t('previousVideo')">
              <component :is="icons.renderIcon('previous')" />
            </button>
            <button v-if="hasNext" class="sp-btn" @click="$emit('next-video')" :aria-label="t('nextVideo')">
              <component :is="icons.renderIcon('next')" />
            </button>

            <!-- 音量 -->
            <div class="sp-volume">
              <button class="sp-btn" @click="toggleMute" :aria-label="isMuted ? t('unmute') : t('mute')">
                <component :is="icons.renderIcon(volumeIconName)" />
              </button>
              <div class="sp-volume-slider" @click="onVolumeClick">
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
          <div class="sp-controls-right">
            <!-- 字幕 -->
            <button 
              v-if="subtitleTracks.length > 0" 
              class="sp-btn" 
              @click="toggleSubtitlesMenu"
              :aria-label="t('subtitles')"
            >
              <component :is="icons.renderIcon(store.subtitlesEnabled ? 'subtitles' : 'subtitlesOff')" />
            </button>

            <!-- 设置 -->
            <button class="sp-btn" @click="toggleSettingsMenu" :aria-label="t('settings')">
              <component :is="icons.renderIcon('settings')" />
            </button>

            <!-- 画中画 -->
            <button 
              v-if="supportsPiP" 
              class="sp-btn" 
              @click="togglePictureInPicture"
              :aria-label="t('pictureInPicture')"
            >
              <component :is="icons.renderIcon(store.pip ? 'pipExit' : 'pip')" />
            </button>

            <!-- 全屏 -->
            <button class="sp-btn" @click="toggleFullscreen" :aria-label="isFullscreen ? t('exitFullscreen') : t('fullscreen')">
              <component :is="icons.renderIcon(isFullscreen ? 'fullscreenExit' : 'fullscreen')" />
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- 设置菜单 -->
    <transition name="sp-slide">
      <div v-if="showSettingsMenu" class="sp-menu" @click.stop>
        <div class="sp-menu-header">
          <span class="sp-menu-title">{{ t('settings') }}</span>
        </div>
        
        <!-- 质量选择 -->
        <div v-if="qualities.length > 0" class="sp-menu-section">
          <div class="sp-menu-label">{{ t('quality') }}</div>
          <button
            v-for="q in qualities"
            :key="q.id"
            class="sp-menu-item"
            :class="{ 'sp-menu-item--active': currentQuality === q.label || currentQuality === String(q.id) }"
            @click="handleQualitySelect(q)"
          >
            <span>{{ q.label }}</span>
            <component 
              v-if="currentQuality === q.label || currentQuality === String(q.id)" 
              :is="icons.renderIcon('check')" 
              class="sp-menu-item-check"
            />
          </button>
        </div>

        <!-- 播放速度 -->
        <div class="sp-menu-section">
          <div class="sp-menu-label">{{ t('playbackSpeed') }}</div>
          <button
            v-for="rate in playbackRates"
            :key="rate"
            class="sp-menu-item"
            :class="{ 'sp-menu-item--active': store.playbackRate === rate }"
            @click="setPlaybackRate(rate)"
          >
            <span>{{ rate === 1 ? t('speedNormal') : `${rate}x` }}</span>
            <component 
              v-if="store.playbackRate === rate" 
              :is="icons.renderIcon('check')" 
              class="sp-menu-item-check"
            />
          </button>
        </div>
      </div>
    </transition>

    <!-- 字幕菜单 -->
    <transition name="sp-slide">
      <div v-if="showSubtitlesMenu" class="sp-menu" @click.stop>
        <div class="sp-menu-header">
          <span class="sp-menu-title">{{ t('subtitles') }}</span>
        </div>
        <button
          class="sp-menu-item"
          :class="{ 'sp-menu-item--active': !currentSubtitle }"
          @click="setSubtitle(null)"
        >
          <span>{{ t('subtitlesOff') }}</span>
          <component v-if="!currentSubtitle" :is="icons.renderIcon('check')" class="sp-menu-item-check" />
        </button>
        <button
          v-for="track in subtitleTracks"
          :key="track.id"
          class="sp-menu-item"
          :class="{ 'sp-menu-item--active': currentSubtitle?.id === track.id }"
          @click="setSubtitle(track)"
        >
          <span>{{ track.label }}</span>
          <component 
            v-if="currentSubtitle?.id === track.id" 
            :is="icons.renderIcon('check')" 
            class="sp-menu-item-check"
          />
        </button>
      </div>
    </transition>

    <!-- 快进/快退指示器 -->
    <transition name="sp-fade">
      <div v-if="seekIndicator.show" class="sp-seek-indicator" :class="seekIndicator.direction">
        <component :is="icons.renderIcon(seekIndicator.direction === 'forward' ? 'skipForward' : 'skipBackward')" />
        <span>{{ seekIndicator.seconds }}{{ t('skipSeconds', { seconds: '' }) }}</span>
      </div>
    </transition>

    <!-- 音量指示器 -->
    <transition name="sp-fade">
      <div v-if="volumeIndicator.show" class="sp-volume-indicator">
        <component :is="icons.renderIcon(volumeIconName)" />
        <span>{{ Math.round(volume) }}%</span>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { usePlayer } from './core'
import type { VideoInfo } from '../../types/video-player'

// 导入主题样式
import './themes/variables.css'
import './themes/base.css'
import './themes/dark.css'
import './themes/light.css'

interface Props {
  video?: VideoInfo
  initialTime?: number
  hasPrev?: boolean
  hasNext?: boolean
  externalError?: any
}

const props = withDefaults(defineProps<Props>(), {
  initialTime: 0,
  hasPrev: false,
  hasNext: false,
  externalError: null
})

const emit = defineEmits<{
  play: []
  pause: []
  ended: [data?: { autoplay: boolean; autoplayNext: boolean; loop: boolean }]
  fullscreenChange: [isFullscreen: boolean]
  timeupdate: [currentTime: number]
  error: [error: any]
  'prev-video': []
  'next-video': []
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
  currentQuality,
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
  toggleSubtitles,
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
  onPlay: () => emit('play'),
  onPause: () => emit('pause'),
  onEnded: () => emit('ended', { autoplay: store.autoplay, autoplayNext: store.autoplayNext, loop: store.loop }),
  onError: (e) => emit('error', e),
  onTimeUpdate: (time) => emit('timeupdate', time)
})

// 模板引用
const videoRef = ref<HTMLVideoElement | null>(null)
const containerRef = ref<HTMLElement | null>(null)

// UI 状态
const showSettingsMenu = ref(false)
const showSubtitlesMenu = ref(false)
const previewTime = ref<number | null>(null)
const previewPercent = ref(0)
const seekIndicator = ref({ show: false, direction: 'forward' as 'forward' | 'backward', seconds: 10 })
const volumeIndicator = ref({ show: false })
const errorState = ref({ show: false, title: '', message: '' })

// 播放速度选项
const playbackRates = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2]

// 计算属性
const progress = computed(() => duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0)

const isBuffering = computed(() => {
  return store.loading && store.loadingStage === 'buffering' && store.hasStartedPlayback
})

const supportsPiP = computed(() => {
  return typeof document !== 'undefined' && 'pictureInPictureEnabled' in document
})

const volumeIconName = computed(() => {
  if (isMuted.value || volume.value === 0) return 'volumeOff'
  if (volume.value < 30) return 'volumeLow'
  return 'volumeHigh'
})

// 同步 refs
watch(videoRef, (el) => {
  videoElement.value = el
})

watch(containerRef, (el) => {
  containerElement.value = el
})

// 加载视频
watch(() => props.video, async (video) => {
  if (video) {
    loadSource(video)
    
    // 恢复播放位置
    if (props.initialTime > 0) {
      await nextTick()
      seek(props.initialTime)
    } else if (video.id) {
      const savedTime = await loadProgress(video.id)
      if (savedTime && savedTime > 0) {
        await nextTick()
        seek(savedTime)
      }
    }
  }
}, { immediate: true })

// 处理外部错误
watch(() => props.externalError, (err) => {
  if (err) {
    errorState.value = {
      show: true,
      title: err.title || t('errorTitle'),
      message: err.message || t('errorUnknown')
    }
  } else {
    errorState.value.show = false
  }
})

// 控制栏显示/隐藏
let hideControlsTimer: ReturnType<typeof setTimeout> | null = null

const showControls = () => {
  store.setControlsVisible(true)
  if (hideControlsTimer) clearTimeout(hideControlsTimer)
  hideControlsTimer = setTimeout(() => {
    if (isPlaying.value && !showSettingsMenu.value && !showSubtitlesMenu.value) {
      store.setControlsVisible(false)
    }
  }, 3000)
}

const onPointerEnter = () => showControls()
const onPointerLeave = () => {
  if (isPlaying.value) {
    store.setControlsVisible(false)
  }
}
const onPointerMove = () => showControls()

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
const onProgressMouseDown = (e: MouseEvent) => {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  const percent = (e.clientX - rect.left) / rect.width
  const time = percent * duration.value
  seek(time)
}

const onProgressMouseMove = (e: MouseEvent) => {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  const percent = (e.clientX - rect.left) / rect.width
  previewPercent.value = percent * 100
  previewTime.value = percent * duration.value
}

const onProgressMouseLeave = () => {
  previewTime.value = null
}

// 音量点击
const onVolumeClick = (e: MouseEvent) => {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  const percent = (e.clientX - rect.left) / rect.width
  setVolume(percent * 100)
}

// 菜单切换
const toggleSettingsMenu = () => {
  showSettingsMenu.value = !showSettingsMenu.value
  showSubtitlesMenu.value = false
}

const toggleSubtitlesMenu = () => {
  showSubtitlesMenu.value = !showSubtitlesMenu.value
  showSettingsMenu.value = false
}

// 质量选择
const handleQualitySelect = (q: any) => {
  setQuality(q.label || String(q.id))
  showSettingsMenu.value = false
}

// 重试
const handleRetry = () => {
  errorState.value.show = false
  if (videoRef.value) {
    videoRef.value.load()
    play()
  }
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
      toggleSubtitles()
      break
    case 'Escape':
      if (showSettingsMenu.value || showSubtitlesMenu.value) {
        showSettingsMenu.value = false
        showSubtitlesMenu.value = false
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
  if (showSettingsMenu.value || showSubtitlesMenu.value) {
    const target = e.target as HTMLElement
    if (!target.closest('.sp-menu')) {
      showSettingsMenu.value = false
      showSubtitlesMenu.value = false
    }
  }
}

onMounted(() => {
  document.addEventListener('click', handleOutsideClick)
})

onUnmounted(() => {
  document.removeEventListener('click', handleOutsideClick)
  if (hideControlsTimer) clearTimeout(hideControlsTimer)
})

// 暴露给父组件
defineExpose({
  play,
  pause,
  seek,
  toggleFullscreen,
  videoElement: videoRef
})
</script>

<style scoped>
.sp-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.sp-buffering {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 15;
}

.sp-progress-container {
  position: relative;
  padding: 8px 0;
  margin-bottom: 4px;
}

.sp-progress-preview {
  position: absolute;
  bottom: 100%;
  transform: translateX(-50%);
  padding: 4px 8px;
  background: var(--sp-tooltip-bg);
  border-radius: var(--sp-radius-sm);
  font-size: var(--sp-font-size-sm);
  white-space: nowrap;
  pointer-events: none;
}

.sp-controls-left,
.sp-controls-right {
  display: flex;
  align-items: center;
  gap: var(--sp-spacing-xs);
}

.sp-controls-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sp-menu-section {
  padding: var(--sp-spacing-sm) 0;
  border-top: 1px solid var(--sp-border);
}

.sp-menu-section:first-of-type {
  border-top: none;
}

.sp-menu-label {
  padding: var(--sp-spacing-xs) var(--sp-spacing-md);
  font-size: var(--sp-font-size-xs);
  color: var(--sp-text-tertiary);
  text-transform: uppercase;
}

.sp-seek-indicator,
.sp-volume-indicator {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-spacing-sm);
  padding: var(--sp-spacing-lg);
  background: rgba(0, 0, 0, 0.7);
  border-radius: var(--sp-radius-lg);
  z-index: 25;
}

.sp-seek-indicator svg,
.sp-volume-indicator svg {
  width: 32px;
  height: 32px;
}

/* 过渡动画 */
.sp-fade-enter-active,
.sp-fade-leave-active {
  transition: opacity var(--sp-transition-normal);
}

.sp-fade-enter-from,
.sp-fade-leave-to {
  opacity: 0;
}

.sp-slide-enter-active,
.sp-slide-leave-active {
  transition: transform var(--sp-transition-normal), opacity var(--sp-transition-normal);
}

.sp-slide-enter-from,
.sp-slide-leave-to {
  transform: translateY(10px);
  opacity: 0;
}
</style>
