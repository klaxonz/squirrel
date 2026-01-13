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
    <div v-if="store.loading && store.loadingStage !== 'buffering' && !errorState.show" class="sp-loading sp-yt-loading" role="status" aria-live="polite">
      <div class="sp-yt-spinner" aria-hidden="true">
        <span v-for="n in 12" :key="`loading-${n}`" class="sp-yt-spinner-seg"></span>
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
    <div v-if="isBuffering && !errorState.show" class="sp-buffering sp-yt-loading sp-yt-loading--buffering" role="status" aria-live="polite">
      <div class="sp-yt-spinner" aria-hidden="true">
        <span v-for="n in 12" :key="`buffer-${n}`" class="sp-yt-spinner-seg"></span>
      </div>
    </div>


    <div v-if="errorState.show" class="sp-error-overlay sp-yt-error" @click.stop>
      <div class="sp-yt-error-panel" role="alert" aria-live="polite">
        <div class="sp-yt-error-title">{{ errorState.title }}</div>
        <div v-if="errorState.message" class="sp-yt-error-message">{{ errorState.message }}</div>
        <div v-if="errorState.code" class="sp-yt-error-code">{{ errorState.code }}</div>
        <div v-if="errorState.canRetry" class="sp-yt-error-actions">
          <button class="sp-yt-error-btn" @click="handleRetry">{{ t('retry') }}</button>
        </div>
      </div>
    </div>


    <!-- 控制栏 -->
    <transition name="sp-fade">
      <div v-show="store.controlsVisible && !errorState.show" class="sp-controls">
        <!-- 进度条 -->
        <div class="sp-progress-container">
          <div 
            class="sp-progress"
            @mousedown="onProgressMouseDown"
            @mousemove="onProgressMouseMove"
            @mouseleave="onProgressMouseLeave"
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
            <button class="sp-btn sp-btn--play" @click="togglePlay" :aria-label="isPlaying ? t('pause') : t('play')">
              <PlayerIcon :name="isPlaying ? 'pause' : 'play'" />
            </button>

            <!-- 上一个/下一个 -->
            <button v-if="hasPrev" class="sp-btn" @click="$emit('prev-video')" :aria-label="t('previousVideo')">
              <PlayerIcon name="previous" />
            </button>
            <button v-if="hasNext" class="sp-btn" @click="$emit('next-video')" :aria-label="t('nextVideo')">
              <PlayerIcon name="next" />
            </button>

            <!-- 音量 -->
            <div class="sp-volume">
              <button class="sp-btn" @click="toggleMute" :aria-label="isMuted ? t('unmute') : t('mute')">
                <PlayerIcon :name="volumeIconName" />
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
              @click.stop="toggleSubtitlesMenu"
              :aria-label="t('subtitles')"
            >
              <PlayerIcon :name="store.subtitlesEnabled ? 'subtitles' : 'subtitlesOff'" />
            </button>

            <!-- 设置 -->
            <button class="sp-btn" @click.stop="toggleSettingsMenu" :aria-label="t('settings')">
              <PlayerIcon name="settings" />
            </button>

            <!-- 画中画 -->
            <button 
              v-if="supportsPiP" 
              class="sp-btn" 
              @click="togglePictureInPicture"
              :aria-label="t('pictureInPicture')"
            >
              <PlayerIcon :name="store.pip ? 'pipExit' : 'pip'" />
            </button>

            <!-- 宽屏 -->
            <button class="sp-btn" @click="toggleWidescreen" :aria-label="props.widescreen ? t('exitWidescreen') : t('widescreen')">
              <PlayerIcon :name="props.widescreen ? 'widescreenExit' : 'widescreen'" />
            </button>

            <!-- 全屏 -->
            <button class="sp-btn" @click="toggleFullscreen" :aria-label="isFullscreen ? t('exitFullscreen') : t('fullscreen')">
              <PlayerIcon :name="isFullscreen ? 'fullscreenExit' : 'fullscreen'" />
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- 设置菜单 -->
    <transition name="sp-fade">
      <div v-if="showSettingsMenu && store.controlsVisible" class="sp-popup" @click.stop>
        <!-- 主菜单 -->
        <template v-if="settingsView === 'main'">
          <button class="sp-popup-item" @click="settingsView = 'speed'">
            <span>{{ t('playbackSpeed') }}</span>
            <span class="sp-popup-value">{{ store.playbackRate === 1 ? t('speedNormal') : `${store.playbackRate}x` }}</span>
          </button>
          <button v-if="qualities.length > 0" class="sp-popup-item" @click="settingsView = 'quality'">
            <span>{{ t('quality') }}</span>
            <span class="sp-popup-value">{{ currentQuality || 'Auto' }}</span>
          </button>
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
              :class="{ active: currentQuality === q.label || currentQuality === String(q.id) }"
              @click="handleQualitySelect(q)"
            >
              <CheckIcon v-if="currentQuality === q.label || currentQuality === String(q.id)" class="sp-check" />
              <span>{{ q.label }}</span>
            </button>
          </div>
        </template>
      </div>
    </transition>

    <!-- 字幕菜单 -->
    <transition name="sp-slide">
      <div v-if="showSubtitlesMenu && store.controlsVisible" class="sp-menu" @click.stop>
        <div class="sp-menu-section">
          <div class="sp-menu-label">{{ t('subtitles') }}</div>
          <div class="sp-quality-list">
            <button
              class="sp-menu-item"
              :class="{ 'sp-menu-item--active': !currentSubtitle }"
              @click="setSubtitle(null)"
            >
              <span class="sp-menu-item-text">{{ t('subtitlesOff') }}</span>
              <span v-if="!currentSubtitle" class="sp-menu-item-dot"></span>
            </button>
            <button
              v-for="track in subtitleTracks"
              :key="track.id"
              class="sp-menu-item"
              :class="{ 'sp-menu-item--active': currentSubtitle?.id === track.id }"
              @click="setSubtitle(track)"
            >
              <span class="sp-menu-item-text">{{ track.label }}</span>
              <span v-if="currentSubtitle?.id === track.id" class="sp-menu-item-dot"></span>
            </button>
          </div>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { usePlayer } from './core'
import PlayerIcon from './PlayerIcon.vue'
import {
  ArrowLeftIcon,
  CheckIcon
} from '@heroicons/vue/24/outline'

import type { VideoInfo } from '../../types/video-player'

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
  setSubtitleTracks,
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
  autoplay: props.autoplay,
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

// UI 状态
const showSettingsMenu = ref(false)
const showSubtitlesMenu = ref(false)
const settingsView = ref<'main' | 'speed' | 'quality'>('main')
const previewTime = ref<number | null>(null)
const previewPercent = ref(0)
const seekIndicator = ref({ show: false, direction: 'forward' as 'forward' | 'backward', seconds: 10 })
const volumeIndicator = ref({ show: false })
const errorState = ref({ show: false, title: '', message: '', code: '', canRetry: true })
const internalError = ref<PlayerUiError | null>(null)

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

// 同步 refs - 使用 immediate 确保初始值同步
watch(videoRef, (el) => {
  videoElement.value = el
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
      seek(props.initialTime)
    } else if (videoId) {
      const savedTime = await loadProgress(videoId)
      if (savedTime && savedTime > 0) {
        await nextTick()
        seek(savedTime)
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
  showSubtitlesMenu.value = false
}

const scheduleHideControls = (delay = 3000): void => {
  if (hideControlsTimer) clearTimeout(hideControlsTimer)
  hideControlsTimer = setTimeout(() => {
    if (!isPointerInside.value) return
    if (!isPlaying.value) return
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
  isPointerInside.value = false
  if (hideControlsTimer) clearTimeout(hideControlsTimer)
  store.setControlsVisible(false)
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
  settingsView.value = 'main'
}

const toggleSubtitlesMenu = () => {
  showSubtitlesMenu.value = !showSubtitlesMenu.value
  showSettingsMenu.value = false
}

// 宽屏模式切换
const toggleWidescreen = () => {
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
  const labels = qualities.value.map((q: any) => q.label || String(q.id))
  const currentIndex = labels.indexOf(currentQuality.value)
  const nextIndex = (currentIndex + 1) % labels.length
  setQuality(labels[nextIndex])
}

// 播放速度选择
const handleSpeedSelect = (rate: number) => {
  setPlaybackRate(rate)
  showSettingsMenu.value = false
}

// 质量选择
const handleQualitySelect = (q: any) => {
  setQuality(q.label || String(q.id))
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
  padding: 0 14px 10px;
  background: var(--sp-controls-bg);
  padding-top: 40px;
}

/* 进度条 */
.sp-progress-container {
  position: relative;
  padding: 10px 0 8px;
  margin-bottom: 2px;
}

.sp-progress {
  position: relative;
  height: var(--sp-progress-height);
  background: var(--sp-progress-bg);
  border-radius: 1.5px;
  cursor: pointer;
  transition: height 0.1s ease, transform 0.1s ease;
}

.sp-progress:hover {
  height: var(--sp-progress-height-hover);
  transform: translateY(-1px);
}

.sp-progress-buffered {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: var(--sp-progress-buffered);
  border-radius: inherit;
  transition: width 0.1s ease;
}

.sp-progress-played {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: var(--sp-progress-played);
  border-radius: inherit;
  box-shadow: var(--sp-glow-primary);
}

.sp-progress-thumb {
  position: absolute;
  top: 50%;
  width: 13px;
  height: 13px;
  background: var(--sp-progress-thumb-color);
  border-radius: 50%;
  transform: translate(-50%, -50%) scale(0);
  transition: transform 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: var(--sp-shadow-sm);
}

.sp-progress:hover .sp-progress-thumb {
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

/* 控制按钮行 */
.sp-controls-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 40px;
}

.sp-controls-left,
.sp-controls-right {
  display: flex;
  align-items: center;
  gap: 2px;
}

/* 按钮 */
.sp-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: none;
  border-radius: 6px;
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
  transform: scale(0.92);
}

.sp-btn:focus-visible {
  outline: 2px solid var(--sp-primary);
  outline-offset: 2px;
}

.sp-btn--play {
  width: 40px;
  height: 40px;
}

.sp-btn svg,
.sp-btn .sp-icon {
  width: 22px;
  height: 22px;
}

.sp-btn--play svg,
.sp-btn--play .sp-icon {
  width: 26px;
  height: 26px;
}

/* 音量 */
.sp-volume {
  display: flex;
  align-items: center;
  gap: 2px;
}

.sp-volume-slider {
  position: relative;
  width: 70px;
  height: 3px;
  background: var(--sp-progress-bg);
  border-radius: 1.5px;
  cursor: pointer;
  transition: height 0.1s ease;
}

.sp-volume:hover .sp-volume-slider {
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

.sp-volume:hover .sp-volume-slider-fill::after {
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
  margin-left: 8px;
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
  bottom: 56px;
  min-width: 200px;
  background: var(--sp-menu-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 10px;
  box-shadow: var(--sp-shadow-lg);
  overflow: hidden;
  z-index: var(--sp-z-menu, 30);
}

.sp-popup-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 11px 14px;
  border: none;
  background: transparent;
  color: var(--sp-text-strong);
  font-size: var(--font-size-xs);
  text-align: left;
  cursor: pointer;
  transition: background 0.12s ease;
}

.sp-popup-item:hover {
  background: var(--sp-bg-hover);
}

.sp-popup-value {
  color: var(--sp-text-tertiary);
  font-size: var(--font-size-xs);
}

.sp-popup-back {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 11px 14px;
  border: none;
  border-bottom: 1px solid var(--sp-border);
  background: transparent;
  color: var(--sp-text);
  font-size: var(--font-size-xs);
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: background 0.12s ease;
}

.sp-popup-back:hover {
  background: var(--sp-bg-hover);
}

.sp-popup-back svg {
  width: 16px;
  height: 16px;
  opacity: 0.7;
}

.sp-popup-list {
  max-height: 220px;
  overflow-y: auto;
  padding: 6px 0;
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
  padding: 9px 14px;
  border: none;
  background: transparent;
  color: var(--sp-text-secondary);
  font-size: var(--font-size-xs);
  text-align: left;
  cursor: pointer;
  transition: background 0.12s ease, color 0.12s ease;
}

.sp-popup-option:hover {
  background: var(--sp-bg-hover);
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
  padding-left: 38px;
}

/* 字幕菜单 */
.sp-menu {
  position: absolute;
  right: 12px;
  bottom: 56px;
  min-width: 180px;
  max-height: 260px;
  overflow-y: auto;
  padding: 6px 0;
  background: var(--sp-menu-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 10px;
  box-shadow: var(--sp-shadow-lg);
  z-index: var(--sp-z-menu, 30);
}

.sp-menu::-webkit-scrollbar {
  width: 4px;
}

.sp-menu::-webkit-scrollbar-track {
  background: transparent;
}

.sp-menu::-webkit-scrollbar-thumb {
  background: var(--sp-border);
  border-radius: 2px;
}

.sp-menu-section {
  padding: 0;
}

.sp-menu-label {
  padding: 8px 14px 6px;
  font-size: var(--font-size-3xs);
  font-weight: 600;
  color: var(--sp-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sp-quality-list {
  display: flex;
  flex-direction: column;
}

.sp-menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  padding: 10px 14px;
  border: none;
  background: transparent;
  color: var(--sp-text-secondary);
  font-size: var(--font-size-xs);
  text-align: left;
  cursor: pointer;
  transition: background 0.12s ease, color 0.12s ease;
}

.sp-menu-item:hover {
  background: var(--sp-bg-hover);
  color: var(--sp-text);
}

.sp-menu-item--active {
  color: var(--sp-text);
}

.sp-menu-item-text {
  flex: 1;
}

.sp-menu-item-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--sp-primary);
  flex-shrink: 0;
  box-shadow: var(--sp-glow-primary);
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

.sp-yt-loading {
  flex-direction: column;
  gap: 12px;
  text-align: center;
}

.sp-yt-loading--buffering {
  gap: 0;
}

.sp-yt-spinner {
  --sp-yt-spinner-radius: 18px;
  --sp-yt-spinner-radius-neg: -18px;
  position: relative;
  width: 46px;
  height: 46px;
}

.sp-yt-loading--buffering .sp-yt-spinner {
  --sp-yt-spinner-radius: 14px;
  --sp-yt-spinner-radius-neg: -14px;
  width: 36px;
  height: 36px;
}

.sp-yt-spinner-seg {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 4px;
  height: 12px;
  background: var(--sp-text);
  border-radius: 999px;
  opacity: 0.9;
  animation: sp-yt-spinner-fade 1.2s linear infinite;
}

.sp-yt-loading--buffering .sp-yt-spinner-seg {
  height: 10px;
}

.sp-yt-spinner-seg:nth-child(1) { transform: translate(-50%, -50%) rotate(0deg) translateY(var(--sp-yt-spinner-radius-neg)); animation-delay: -1.1s; }
.sp-yt-spinner-seg:nth-child(2) { transform: translate(-50%, -50%) rotate(30deg) translateY(var(--sp-yt-spinner-radius-neg)); animation-delay: -1s; }
.sp-yt-spinner-seg:nth-child(3) { transform: translate(-50%, -50%) rotate(60deg) translateY(var(--sp-yt-spinner-radius-neg)); animation-delay: -0.9s; }
.sp-yt-spinner-seg:nth-child(4) { transform: translate(-50%, -50%) rotate(90deg) translateY(var(--sp-yt-spinner-radius-neg)); animation-delay: -0.8s; }
.sp-yt-spinner-seg:nth-child(5) { transform: translate(-50%, -50%) rotate(120deg) translateY(var(--sp-yt-spinner-radius-neg)); animation-delay: -0.7s; }
.sp-yt-spinner-seg:nth-child(6) { transform: translate(-50%, -50%) rotate(150deg) translateY(var(--sp-yt-spinner-radius-neg)); animation-delay: -0.6s; }
.sp-yt-spinner-seg:nth-child(7) { transform: translate(-50%, -50%) rotate(180deg) translateY(var(--sp-yt-spinner-radius-neg)); animation-delay: -0.5s; }
.sp-yt-spinner-seg:nth-child(8) { transform: translate(-50%, -50%) rotate(210deg) translateY(var(--sp-yt-spinner-radius-neg)); animation-delay: -0.4s; }
.sp-yt-spinner-seg:nth-child(9) { transform: translate(-50%, -50%) rotate(240deg) translateY(var(--sp-yt-spinner-radius-neg)); animation-delay: -0.3s; }
.sp-yt-spinner-seg:nth-child(10) { transform: translate(-50%, -50%) rotate(270deg) translateY(var(--sp-yt-spinner-radius-neg)); animation-delay: -0.2s; }
.sp-yt-spinner-seg:nth-child(11) { transform: translate(-50%, -50%) rotate(300deg) translateY(var(--sp-yt-spinner-radius-neg)); animation-delay: -0.1s; }
.sp-yt-spinner-seg:nth-child(12) { transform: translate(-50%, -50%) rotate(330deg) translateY(var(--sp-yt-spinner-radius-neg)); animation-delay: 0s; }

.sp-loading-text {
  font-size: var(--font-size-xs);
  color: var(--sp-text-secondary);
  font-weight: 500;
  text-shadow: var(--sp-text-shadow);
}

@keyframes sp-yt-spinner-fade {
  0% { opacity: 1; }
  100% { opacity: 0.2; }
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
}

.sp-yt-error {
  text-align: center;
}

.sp-yt-error-panel {
  max-width: 520px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: var(--sp-text);
}

.sp-yt-error-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  letter-spacing: 0.2px;
}

.sp-yt-error-message {
  font-size: var(--font-size-xs);
  color: var(--sp-text-secondary);
  line-height: 1.5;
  max-width: 420px;
}

.sp-yt-error-code {
  font-size: var(--font-size-2xs);
  color: var(--sp-text-tertiary);
  letter-spacing: 0.3px;
}

.sp-yt-error-actions {
  margin-top: 8px;
  display: flex;
  justify-content: center;
}

.sp-yt-error-btn {
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

.sp-yt-error-btn:hover {
  background: rgba(255, 255, 255, 0.18);
  border-color: rgba(255, 255, 255, 0.35);
}

.sp-yt-error-btn:active {
  background: rgba(255, 255, 255, 0.28);
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
</style>
