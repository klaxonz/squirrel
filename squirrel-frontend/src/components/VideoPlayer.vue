<template>
  <div class="video-wrapper bg-[#0f0f0f]">
    <div class="video-container"
      :class="{}"
      @pointerenter="onPointerEnter"
      @pointerleave="onPointerLeave"
      @pointermove="onPointerMove"
      @mouseenter="handleMouseEnter"
      @mouseleave="handleMouseLeave"
      @dblclick="!isTouchDevice && togglePlay()"
      @touchstart="handleTouchStart"
      @touchmove="handleTouchMove"
      @touchend="handleTouchEnd"
      @keydown="handleKeyDown"
      tabindex="0"
      role="application"
      aria-label="视频播放器"
    >
      <!-- 优化的加载状态显示 -->
      <div v-if="playerState.media.loading" class="yt-loading-spinner">
        <div class="yt-spinner">
          <svg class="yt-spinner__circle" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="45"/>
          </svg>
        </div>
        <!-- 中央加载速度信息 -->
        <div class="loading-speed-info">
          <div class="loading-speed-text">{{ formatNetworkSpeed(performanceState.bandwidth.current) }}</div>
        </div>
      </div>

      <!-- 左下角加载状态提示 -->
      <div v-if="playerState.media.loading && !playerState.media.playing" class="loading-status-indicator">
        <div class="loading-status-text">{{ loadingStatusText }}</div>
      </div>

      <div class="video-click-layer" @click="handleVideoLayerClick">
        <div class="play-state-indicator" v-if="playerState.ui.showPlayIndicator">
          <Icon :icon="playerState.media.playing ? 'material-symbols:pause' : 'material-symbols:play-arrow'" 
            class="indicator-icon" />
        </div>
      </div>

      <video
        ref="videoPlayer"
        class="video-player"
        :poster="video.thumbnail"
        :src="video.video_stream_url"
        preload="auto"
        crossorigin="anonymous"
        playsinline
        webkit-playsinline
        :muted="playerState.media.muted"
        @play="handleVideoPlay"
        @pause="handleVideoPause"
        @seeking="handleVideoSeeking"
        @seeked="handleVideoSeeked"
        @canplay="handleVideoCanplay"
        @canplaythrough="handleVideoCanplaythrough"
        @waiting="handleVideoWaiting"
        @timeupdate="handleVideoTimeupdate"
        @progress="handleVideoProgress"
        @loadstart="handleVideoLoadstart"
        @loadedmetadata="handleVideoLoadedmetadata"
        @loadeddata="handleVideoLoadeddata"
        @error="handleVideoError"
        @stalled="handleVideoStalled"
        @suspend="handleVideoSuspend"
        @abort="handleVideoAbort"
      ></video>
      <audio
        v-if="!isHlsStream"
        ref="audioPlayer"
        :src="video.audio_stream_url"
        @seeking="handleAudioSeeking"
        @canplay="handleAudioCanplay"
        @error="handleAudioError"
      />
      
      <div class="hover-gradient" v-if="playerState.ui.controlsVisible && !playerState.media.subtitlesEnabled"></div>
      
      <div class="video-controls" :class="{ 'controls-visible': playerState.ui.controlsVisible }">
        <!-- 改进的进度条容器 -->
        <div class="progress-container">
          <!-- 预览时间提示 -->
          <div class="preview-time-tooltip"
            :style="{ left: playerState.ui.hoverPosition + '%' }"
            v-show="playerState.ui.hoveringProgress"
          >
            <div class="tooltip-content">
              {{ formatTime(playerState.ui.previewTime) }}
            </div>
            <div class="tooltip-arrow"></div>
          </div>

          <!-- 章节标记（如果有的话） -->
          <div class="chapter-markers" v-if="video.chapters && video.chapters.length > 0">
            <div
              v-for="chapter in video.chapters"
              :key="chapter.id"
              class="chapter-marker"
              :style="{ left: (chapter.time / playerState.media.duration) * 100 + '%' }"
              :title="chapter.title"
            ></div>
          </div>

          <div class="progress-bar-container"
            @mousemove="debouncedProgressHover"
            @mouseleave="handleProgressLeave"
            @mousedown="handleProgressMouseDown"
            @touchstart="handleProgressTouchStart"
            @touchmove="handleProgressTouchMove"
            @touchend="handleProgressTouchEnd"
          >
            <div class="progress-bar">
              <!-- 缓冲进度 -->
              <div class="progress-bar-loaded" :style="{ width: playerState.media.bufferedProgress + '%' }"></div>
              <!-- 播放进度 -->
              <div class="progress-bar-filled" :style="{ width: progress + '%' }"></div>
              <!-- 悬停预览线 -->
              <div class="progress-bar-hover"
                :style="{ left: playerState.ui.hoverPosition + '%' }"
                v-show="playerState.ui.hoveringProgress"
              ></div>
            </div>
            <!-- 进度点 -->
            <div class="progress-dot"
              :style="{ left: progress + '%' }"
              v-show="playerState.ui.hoveringProgress || playerState.ui.isDragging"
            ></div>
            <!-- 进度手柄 -->
            <div class="progress-handle"
              :style="{ left: progress + '%' }"
              v-show="playerState.ui.hoveringProgress"
            ></div>
          </div>
        </div>
        
        <!-- 改进的控制栏 -->
        <div class="controls-main">
          <div class="controls-left">
            <!-- 播放/暂停按钮 -->
            <button @click="togglePlay" class="control-btn play-btn" :aria-label="playerState.media.playing ? '暂停' : '播放'">
              <Icon v-if="playerState.media.playing" icon="material-symbols:pause" class="control-icon" />
              <Icon v-else icon="material-symbols:play-arrow" class="control-icon" />
            </button>

            <!-- 跳过按钮组 -->
            <div class="skip-controls">
              <button @click="skipBackward" class="control-btn skip-btn" aria-label="后退10秒">
                <Icon icon="material-symbols:replay-10" class="control-icon" />
              </button>
              <button @click="skipForward" class="control-btn skip-btn" aria-label="前进10秒">
                <Icon icon="material-symbols:forward-10" class="control-icon" />
              </button>
            </div>

            <!-- 音量控制 -->
            <div class="volume-control group">
              <button @click="toggleMute" class="control-btn" :aria-label="playerState.media.muted ? '取消静音' : '静音'">
                <Icon :icon="volumeIcon" class="control-icon" />
              </button>

              <div class="volume-slider-container">
                <div class="volume-slider-wrapper">
                  <div class="volume-track-bg"></div>
                  <div
                    class="volume-range-fill"
                    :style="{ width: `${playerState.media.muted ? 0 : Math.min(playerState.media.volume, 100)}%` }"
                  ></div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    v-model="playerState.media.volume"
                    class="volume-range"
                    aria-label="音量"
                  >
                </div>
              </div>
            </div>

            <!-- 时间显示 -->
            <div class="time-display">
              <span class="current-time">{{ formatTime(playerState.media.currentTime) }}</span>
              <span class="time-separator">/</span>
              <span class="total-time">{{ formatTime(playerState.media.duration) }}</span>
            </div>
          </div>

          <div class="controls-right">
            <!-- 播放速度控制 -->
            <div class="playback-rate-control" v-if="!isTouchDevice">
              <button @click="togglePlaybackRateMenu" class="control-btn" aria-label="播放速度">
                <span class="playback-rate-text">{{ playerState.media.playbackRate }}x</span>
              </button>

              <!-- 播放速度菜单 -->
              <div v-if="playerState.ui.showPlaybackRateMenu" class="playback-rate-menu">
                <button
                  v-for="rate in playbackRates"
                  :key="rate"
                  @click="setPlaybackRate(rate)"
                  class="rate-option"
                  :class="{ active: playerState.media.playbackRate === rate }"
                >
                  {{ rate }}x
                </button>
              </div>
            </div>

            <!-- 画中画按钮 -->
            <button
              v-if="supportsPiP"
              @click="togglePictureInPicture"
              class="control-btn"
              aria-label="画中画"
            >
              <Icon icon="material-symbols:picture-in-picture-alt" class="control-icon" />
            </button>

            <!-- 字幕按钮（开启时高亮） -->
            <button 
              @click="toggleSubtitles"
              class="control-btn"
              :class="{ 'bg-white/20 ring-1 ring-white/30': playerState.media.subtitlesEnabled }"
              :aria-label="playerState.media.subtitlesEnabled ? '关闭字幕' : '开启字幕'"
              :aria-pressed="playerState.media.subtitlesEnabled"
              :title="playerState.media.subtitlesEnabled ? '字幕已开启' : '字幕已关闭'"
            >
              <Icon 
                icon="material-symbols:subtitles"
                class="control-icon"
              />
            </button>

            <!-- 设置按钮 -->
            <div class="settings-control" v-if="!isTouchDevice">
              <button @click="toggleSettingsMenu" class="control-btn" aria-label="设置">
                <Icon icon="material-symbols:settings" class="control-icon" />
              </button>

              <!-- 设置菜单 -->
              <div v-if="playerState.ui.showSettingsMenu" class="settings-menu">
                <div class="settings-section">
                  <div class="settings-title">播放质量</div>
                  <div class="quality-options">
                    <button
                      v-for="quality in availableQualities"
                      :key="quality.value"
                      @click="setQuality(quality.value)"
                      class="quality-option"
                      :class="{ active: playerState.media.currentQuality === quality.value }"
                    >
                      {{ quality.label }}
                    </button>
                  </div>
                </div>

                <div class="settings-section" v-if="video.subtitles && video.subtitles.length > 0">
                  <div class="settings-title">字幕</div>
                  <div class="subtitle-options">
                    <button
                      @click="setSubtitle(null)"
                      class="subtitle-option"
                      :class="{ active: !playerState.media.currentSubtitle }"
                    >
                      关闭
                    </button>
                    <button
                      v-for="subtitle in video.subtitles"
                      :key="subtitle.id"
                      @click="setSubtitle(subtitle)"
                      class="subtitle-option"
                      :class="{ active: playerState.media.currentSubtitle?.id === subtitle.id }"
                    >
                      {{ subtitle.language }}
                    </button>
                  </div>
                </div>

                <div class="settings-section">
                  <div class="settings-title">其他设置</div>
                  <div class="setting-item">
                    <label class="setting-label">
                      <input
                        type="checkbox"
                        v-model="playerState.media.autoplay"
                        class="setting-checkbox"
                      >
                      自动播放
                    </label>
                  </div>
                  <div class="setting-item">
                    <label class="setting-label">
                      <input
                        type="checkbox"
                        v-model="playerState.media.loop"
                        class="setting-checkbox"
                      >
                      循环播放
                    </label>
                  </div>
                </div>
              </div>
            </div>

            <!-- 全屏按钮 -->
            <button @click="toggleFullscreen" class="control-btn" aria-label="全屏">
              <Icon :icon="fullscreenIcon" class="control-icon" />
            </button>
          </div>
        </div>
      </div>

      <!-- 改进的错误消息提示 -->
      <div v-if="errorState.hasError" class="error-message">
        <div class="error-content">
          <Icon icon="material-symbols:error" class="error-icon" />
          <div class="error-text">
            <h3 class="error-title">{{ getErrorInfo()?.title }}</h3>
            <p class="error-description">{{ getErrorInfo()?.message }}</p>
            <div v-if="getErrorInfo()?.suggestions" class="error-suggestions">
              <p class="suggestions-title">建议解决方案：</p>
              <ul class="suggestions-list">
                <li v-for="suggestion in getErrorInfo().suggestions" :key="suggestion">
                  {{ suggestion }}
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div class="error-actions">
          <button
            v-if="errorState.canRetry"
            @click="handleRetry"
            class="retry-button"
            :disabled="errorState.retryCount >= errorState.maxRetries"
          >
            <Icon icon="material-symbols:refresh" />
            重试 ({{ errorState.retryCount }}/{{ errorState.maxRetries }})
          </button>

          <button @click="reportErrorToSupport" class="report-button">
            <Icon icon="material-symbols:bug-report" />
            报告问题
          </button>

          <button @click="dismissError" class="dismiss-button">
            <Icon icon="material-symbols:close" />
            关闭
          </button>
        </div>
      </div>

      <!-- 添加快进/快退指示器 -->
      <div class="seeking-indicator" 
        v-if="playerState.ui.seeking.active"
        :data-direction="playerState.ui.seeking.direction"
      >
        <div class="seeking-content">
          <div class="seeking-icon-container">
            <Icon :icon="playerState.ui.seeking.direction === 'forward' ? 'material-symbols:fast-forward-rounded' : 'material-symbols:fast-rewind-rounded'" 
              class="seeking-icon" />
            <div class="seeking-seconds">
              {{ Math.round(Math.abs(playerState.ui.seeking.seekTime - playerState.media.currentTime)) }}秒
            </div>
          </div>
        </div>
      </div>

      <!-- 添加音量调节指示器 -->
      <div v-if="playerState.ui.volume.showIndicator" class="volume-adjust-indicator">
        <div class="volume-control-container">
          <div class="volume-slider">
            <div class="volume-slider-fill" :style="{ height: playerState.media.volume + '%' }"></div>
            <div class="volume-slider-thumb"></div>
          </div>
          <div class="volume-value">{{ Math.round(playerState.media.volume) }}</div>
        </div>
      </div>

      <!-- 键盘操作反馈 -->
      <div v-if="playerState.ui.showKeyboardFeedback" class="keyboard-feedback">
        <Icon icon="material-symbols:keyboard" class="keyboard-icon" />
        <span>{{ playerState.ui.keyboardFeedback }}</span>
      </div>

      <!-- 键盘快捷键帮助 -->
      <div v-if="playerState.ui.showKeyboardHelp" class="keyboard-help-overlay" @click="toggleKeyboardHelp">
        <div class="keyboard-help-modal" @click.stop>
          <div class="keyboard-help-header">
            <h3>键盘快捷键</h3>
            <button @click="toggleKeyboardHelp" class="close-help-btn">
              <Icon icon="material-symbols:close" />
            </button>
          </div>

          <div class="keyboard-help-content">
            <div class="shortcut-section">
              <h4>播放控制</h4>
              <div class="shortcut-list">
                <div class="shortcut-item">
                  <kbd>空格</kbd> 或 <kbd>K</kbd>
                  <span>播放/暂停</span>
                </div>
                <div class="shortcut-item">
                  <kbd>←</kbd> / <kbd>→</kbd>
                  <span>快退/快进 5秒</span>
                </div>
                <div class="shortcut-item">
                  <kbd>J</kbd> / <kbd>L</kbd>
                  <span>快退/快进 10秒</span>
                </div>
              </div>
            </div>

            <div class="shortcut-section">
              <h4>音量控制</h4>
              <div class="shortcut-list">
                <div class="shortcut-item">
                  <kbd>M</kbd>
                  <span>静音/取消静音</span>
                </div>
                <div class="shortcut-item">
                  <kbd>↑</kbd> / <kbd>↓</kbd>
                  <span>音量 +5% / -5%</span>
                </div>
              </div>
            </div>

            <div class="shortcut-section">
              <h4>播放速度</h4>
              <div class="shortcut-list">
                <div class="shortcut-item">
                  <kbd>&lt;</kbd> / <kbd>&gt;</kbd>
                  <span>减慢/加快播放速度</span>
                </div>
              </div>
            </div>

            <div class="shortcut-section">
              <h4>其他功能</h4>
              <div class="shortcut-list">
                <div class="shortcut-item">
                  <kbd>F</kbd>
                  <span>全屏/退出全屏</span>
                </div>
                <div class="shortcut-item">
                  <kbd>I</kbd>
                  <span>画中画</span>
                </div>
                <div class="shortcut-item">
                  <kbd>C</kbd>
                  <span>字幕开/关</span>
                </div>
                <div class="shortcut-item">
                  <kbd>0-9</kbd>
                  <span>跳转到 0%-90%</span>
                </div>
                <div class="shortcut-item">
                  <kbd>?</kbd>
                  <span>显示此帮助</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import {onMounted, watch, ref, computed, onUnmounted, reactive} from 'vue';
import { Icon } from '@iconify/vue';
import useVideoOperations from "../composables/useVideoOperations";
import useVideoHistory from "../composables/useVideoHistory";
import useVideoErrorHandler from "../composables/useVideoErrorHandler";
import useVideoPreload from "../composables/useVideoPreload";
import { formatTime } from "../utils/dateFormat";
import Hls from 'hls.js';
import { getCueClass, parseVTT, parseSRT } from "../utils/subtitles";
import { debounce } from "../utils/debounce";
import useKeyboardShortcuts from "../composables/useKeyboardShortcuts";
import useProgressBar from "../composables/useProgressBar";
import useTouchSeek from "../composables/useTouchSeek";

const props = defineProps({
  video: Object
});

const emit = defineEmits(['play', 'pause', 'ended', 'fullscreenChange', 'timeupdate', 'error']);

// DOM 引用
const videoPlayer = ref(null);
const audioPlayer = ref(null);
const {
  playVideo,
} = useVideoOperations();

// 改进的历史管理
const {
  sendReport,
  getLocalHistory,
  updateLocalHistory,
  setupNetworkListeners,
  startPeriodicSync,
} = useVideoHistory();

// 错误处理
const {
  errorState,
  handleError,
  manualRetry,
  clearError,
  getErrorInfo,
  reportError
} = useVideoErrorHandler();

// 预加载优化
const {
  detectNetworkCondition,
  getOptimizedHlsConfig,
  preloadVideo,
  setupNetworkListener
} = useVideoPreload();

// 统一状态对象
const playerState = reactive({
  // 媒体状态
  media: {
    playing: false,
    canPlay: {
      video: false,
      audio: false
    },
    seeking: {
      video: false,
      audio: false
    },
    loading: false,
    loadingStage: 'idle', // 'idle', 'fetching', 'buffering', 'ready'
    volume: 100,
    muted: false,
    currentTime: 0,
    duration: 0,
    bufferedProgress: 0,
    firstInteraction: true,
    playbackRate: 1,
    subtitlesEnabled: false,
    pictureInPicture: false,
    currentQuality: 'auto',
    currentSubtitle: null,
    autoplay: false,
    loop: false
  },
  // UI状态
  ui: {
    controlsVisible: true,
    fullscreen: false,
    hoveringProgress: false,
    hoverPosition: 0,
    previewTime: 0,
    showPlayIndicator: false,
    isDragging: false,
    previewSeekTime: 0,
    errorMessage: null,
    showPlaybackRateMenu: false,
    showSettingsMenu: false,
    showKeyboardHelp: false,
    showKeyboardFeedback: false,
    keyboardFeedback: '',
    seeking: {
      active: false,
      startX: 0,
      currentX: 0,
      distance: 0,
      direction: null,
      seekTime: 0,
      wasPlaying: false
    },
    volume: {
      adjusting: false,
      startY: 0,
      startVolume: 0,
      showIndicator: false
    }
  },
  // 网络状态
  network: {
    reconnectAttempts: 0,
    firstInteraction: true
  }
});

// HLS 实例
const hls = ref(null);

// 计算属性
const isHlsStream = computed(() => 
  props.video?.stream_video_url?.includes('.m3u8')
);

const hasAudioStream = computed(() => {
  return !!props.video?.stream_audio_url;
});

const isCanplay = computed(() => {
  if (!hasAudioStream.value) {
    return playerState.media.canPlay.video;
  }
  return playerState.media.canPlay.video && 
    (isHlsStream.value || playerState.media.canPlay.audio);
});

const isSeeking = computed(() => {
  if (!hasAudioStream.value) {
    return playerState.media.seeking.video;
  }
  return playerState.media.seeking.video || playerState.media.seeking.audio;
});

const volumeIcon = computed(() => {
  if (playerState.media.muted || playerState.media.volume === 0) 
    return 'material-symbols:volume-off';
  if (playerState.media.volume < 50) 
    return 'material-symbols:volume-down';
  return 'material-symbols:volume-up';
});

const fullscreenIcon = computed(() => 
  playerState.ui.fullscreen ? 'material-symbols:fullscreen-exit' : 'material-symbols:fullscreen'
);

const progress = computed(() => {
  if (playerState.ui.isDragging) {
    return (playerState.ui.previewSeekTime / playerState.media.duration) * 100 || 0;
  }
  return (playerState.media.currentTime / playerState.media.duration) * 100 || 0;
});

// 新增计算属性
const supportsPiP = computed(() =>
  document.pictureInPictureEnabled && videoPlayer.value
);

// 提前声明 setVideoTime，具体实现位于下方唯一实现
let setVideoTime;

// 加载状态文本
const loadingStatusText = computed(() => {
  switch (playerState.media.loadingStage) {
    case 'fetching':
      return '获取视频链接中...';
    case 'buffering':
      return '缓冲中...';
    case 'ready':
      return '准备就绪';
    default:
      return '加载中...';
  }
});

// 格式化网络速度
const formatNetworkSpeed = (bytesPerSecond) => {
  if (!bytesPerSecond || bytesPerSecond === 0) {
    return '--';
  }

  const mbps = (bytesPerSecond / 1024 / 1024).toFixed(1);
  const kbps = (bytesPerSecond / 1024).toFixed(0);

  if (mbps >= 1) {
    return `${mbps} MB/s`;
  } else {
    return `${kbps} KB/s`;
  }
};

// 播放速度选项
const playbackRates = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];

// 质量选项
const availableQualities = ref([
  { value: 'auto', label: '自动' },
  { value: '1080p', label: '1080p' },
  { value: '720p', label: '720p' },
  { value: '480p', label: '480p' },
  { value: '360p', label: '360p' }
]);

// 常量
const MAX_RECONNECT_ATTEMPTS = 3;
const RECONNECT_INTERVAL = 3000;

// 性能优化相关常量
const PRELOAD_BUFFER_SIZE = 10; // 预加载缓冲大小（秒）
const MEMORY_CLEANUP_INTERVAL = 30000; // 内存清理间隔（毫秒）
const BANDWIDTH_SAMPLE_SIZE = 5; // 带宽采样大小

// 性能监控状态
const performanceState = reactive({
  bandwidth: {
    samples: [],
    average: 0,
    current: 0
  },
  memory: {
    used: 0,
    peak: 0,
    lastCleanup: 0
  },
  loading: {
    startTime: 0,
    duration: 0,
    bytesLoaded: 0
  }
});

// 触摸状态已封装至 useTouchSeek

// 计时器
let hideControlsTimer = null;

/**
 * 统一的输入能力检测
 * - isCoarsePointer：使用 CSS 媒体特性检测粗指针（如手指），能区分带触摸的桌面设备，避免误判
 * - isTouchDevice：保留仅触摸优化使用，不再作为禁用鼠标事件的强约束
 * - enablePointerUnified：开关，允许在必要时回退到旧的 mouse 逻辑（默认启用统一 Pointer）
 */
const enablePointerUnified = true;
const isCoarsePointer = computed(() => {
  // SSR/构建时保护
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false;
  try {
    return window.matchMedia('(pointer: coarse)').matches;
  } catch {
    return false;
  }
});
// 添加计算属性（保留）
const isTouchDevice = computed(() =>
  (typeof window !== 'undefined' && ('ontouchstart' in window || navigator.maxTouchPoints > 0))
);


// 使用组合函数封装进度条交互
const {
  debouncedProgressHover,
  handleProgressLeave,
  handleProgressMouseDown,
  handleProgressTouchStart,
  handleProgressTouchMove,
  handleProgressTouchEnd,
  cleanup: cleanupProgressBar
} = useProgressBar(
  playerState,
  { getDuration: () => videoPlayer.value?.duration || playerState.media.duration || 0 },
  { setVideoTime: (t) => setVideoTime?.(t) }
);

// 性能优化函数
const updateBandwidth = (bytesLoaded, duration) => {
  if (duration > 0) {
    const bandwidth = (bytesLoaded * 8) / duration; // bps
    performanceState.bandwidth.current = bandwidth;

    // 保持最近的带宽样本
    performanceState.bandwidth.samples.push(bandwidth);
    if (performanceState.bandwidth.samples.length > BANDWIDTH_SAMPLE_SIZE) {
      performanceState.bandwidth.samples.shift();
    }

    // 计算平均带宽
    performanceState.bandwidth.average =
      performanceState.bandwidth.samples.reduce((a, b) => a + b, 0) /
      performanceState.bandwidth.samples.length;
  }
};

// 监控网络加载速度
const monitorNetworkSpeed = () => {
  if (videoPlayer.value && videoPlayer.value.buffered.length > 0) {
    const buffered = videoPlayer.value.buffered;
    const currentTime = videoPlayer.value.currentTime;

    // 计算当前缓冲区的字节数（估算）
    let totalBufferedBytes = 0;
    for (let i = 0; i < buffered.length; i++) {
      const start = buffered.start(i);
      const end = buffered.end(i);
      const duration = end - start;

      // 估算比特率（假设视频质量为1080p，约5Mbps）
      const estimatedBitrate = 5 * 1024 * 1024; // 5Mbps in bps
      totalBufferedBytes += (duration * estimatedBitrate) / 8; // 转换为字节
    }

    // 更新带宽信息
    const loadingDuration = (Date.now() - performanceState.loading.startTime) / 1000;
    if (loadingDuration > 0) {
      updateBandwidth(totalBufferedBytes, loadingDuration);
    }
  }
};

const optimizeBufferSize = () => {
  if (hls.value && performanceState.bandwidth.average > 0) {
    // 更激进的缓冲策略以减少卡顿
    const bandwidth = performanceState.bandwidth.average;
    const mbps = bandwidth / 1000000;

    // 根据带宽设置更大的缓冲区
    let targetBuffer;
    if (mbps >= 10) {
      targetBuffer = 120; // 高速网络：2分钟缓冲
    } else if (mbps >= 5) {
      targetBuffer = 90;  // 中速网络：1.5分钟缓冲
    } else if (mbps >= 2) {
      targetBuffer = 60;  // 低速网络：1分钟缓冲
    } else {
      targetBuffer = 30;  // 极慢网络：30秒缓冲
    }

    // 动态调整HLS配置
    if (hls.value.config) {
      hls.value.config.maxBufferLength = targetBuffer;
      hls.value.config.maxMaxBufferLength = targetBuffer * 1.5;

      // 根据网络状况调整质量切换策略
      if (mbps < 2) {
        // 慢网络：更保守的质量切换
        hls.value.config.abrBandWidthFactor = 0.6;
        hls.value.config.abrBandWidthUpFactor = 0.4;
      } else {
        // 快网络：正常质量切换
        hls.value.config.abrBandWidthFactor = 0.8;
        hls.value.config.abrBandWidthUpFactor = 0.6;
      }
    }

    console.debug('Buffer size optimized to:', targetBuffer, 'seconds for', mbps.toFixed(1), 'Mbps');
  }
};

const cleanupMemory = () => {
  const now = Date.now();
  if (now - performanceState.memory.lastCleanup > MEMORY_CLEANUP_INTERVAL) {
    // 清理不必要的缓冲区
    if (videoPlayer.value && videoPlayer.value.buffered.length > 0) {
      const currentTime = videoPlayer.value.currentTime;
      const buffered = videoPlayer.value.buffered;

      // 如果缓冲区太大，建议浏览器清理旧数据
      for (let i = 0; i < buffered.length; i++) {
        if (buffered.end(i) < currentTime - 30) {
          // 30秒前的数据可以清理
          console.debug('Suggesting cleanup of old buffer data');
        }
      }
    }

    performanceState.memory.lastCleanup = now;

    // 强制垃圾回收（如果可用）
    if (window.gc) {
      window.gc();
    }
  }
};

const monitorPerformance = () => {
  if (videoPlayer.value) {
    // 监控内存使用
    if (performance.memory) {
      performanceState.memory.used = performance.memory.usedJSHeapSize;
      performanceState.memory.peak = Math.max(
        performanceState.memory.peak,
        performanceState.memory.used
      );
    }

    // 定期优化
    optimizeBufferSize();
    cleanupMemory();
  }
};


// 定义需要清理的变量
let performanceInterval = null;
let cleanupNetworkListeners = null;
let cleanupPeriodicSync = null;
let syncInterval = null;
let showControlsInterval = null;

// 智能预加载函数
const intelligentPreload = async () => {
  if (!props.video?.stream_video_url || !videoPlayer.value) return;

  // 使用新的预加载composable
  const networkCondition = detectNetworkCondition();
  console.debug('Network condition detected:', networkCondition);

  // 根据网络状况设置预加载策略
  if (networkCondition === 'fast') {
    videoPlayer.value.preload = 'auto';
    // 启动智能预加载
    await preloadVideo(videoPlayer.value, props.video.stream_video_url);
  } else if (networkCondition === 'medium') {
    videoPlayer.value.preload = 'metadata';
  } else {
    videoPlayer.value.preload = 'none';
  }
};

// 初始化
onMounted(async () => {
  // 设置网络监听器
  setupNetworkListener();

  // 智能预加载
  await intelligentPreload();

  if (!props.video?.stream_video_url) {
    await playVideo(props.video);
  }

  initializeMediaSources();
  screen.orientation?.addEventListener('change', handleOrientationChange);

  // 启动性能监控 - 减少频率以降低CPU使用
  performanceInterval = setInterval(monitorPerformance, 10000);

  // 设置网络状态监听和定期同步 - 增加同步间隔
  cleanupNetworkListeners = setupNetworkListeners();
  cleanupPeriodicSync = startPeriodicSync(60000); // 60秒同步一次

  // 减少媒体同步频率
  syncInterval = setInterval(syncMedia, 5000);
  showControlsInterval = setInterval(() => {
    if (playerState.media.playing) {
      playerState.ui.controlsVisible = false;
      clearInterval(showControlsInterval);
    }
  }, 3000);
});

// 清理定时器和监听器
onUnmounted(() => {
  // 取消进度条 hover 防抖
  if (typeof debouncedProgressHover?.cancel === 'function') {
    debouncedProgressHover.cancel();
  }

  // 清理定时器
  if (syncInterval) clearInterval(syncInterval);
  if (performanceInterval) clearInterval(performanceInterval);
  if (showControlsInterval) clearInterval(showControlsInterval);
  if (hideControlsTimer) {
    clearTimeout(hideControlsTimer);
    hideControlsTimer = null;
  }
  if (saveProgressTimer) clearTimeout(saveProgressTimer);

  // 清理网络监听和定期同步
  if (cleanupNetworkListeners) cleanupNetworkListeners();
  if (cleanupPeriodicSync) cleanupPeriodicSync();

  // 销毁 HLS 实例
  if (hls.value) {
    hls.value.destroy();
    hls.value = null;
  }

  // 组合函数清理
  if (typeof cleanupProgressBar === 'function') cleanupProgressBar();
  if (typeof cleanupKeyboard === 'function') cleanupKeyboard();

  // 移除方向监听
  screen.orientation?.removeEventListener('change', handleOrientationChange);
});

const initializeMediaSources = () => {
  if (props.video?.stream_video_url) {
    if (isHlsStream.value) {
      initializeHlsStream();
    } else {
      videoPlayer.value.src = props.video.stream_video_url;
    }
  }

  if (!isHlsStream.value && props.video.stream_audio_url) {
    audioPlayer.value.src = props.video.stream_audio_url;
  }
};

// 初始化HLS播放
const initializeHlsStream = () => {
  if (Hls.isSupported()) {
    // 使用智能优化的HLS配置
    const hlsConfig = getOptimizedHlsConfig();

    hls.value = new Hls(hlsConfig);
    hls.value.attachMedia(videoPlayer.value);

    // 监听更多事件以优化性能
    hls.value.on(Hls.Events.MEDIA_ATTACHED, () => {
      console.debug('HLS media attached');
      hls.value.loadSource(props.video.stream_video_url);
    });

    hls.value.on(Hls.Events.MANIFEST_PARSED, (event, data) => {
      console.debug('HLS manifest parsed', data);
      // 可以在这里根据网络状况选择初始质量
    });

    hls.value.on(Hls.Events.LEVEL_SWITCHED, (event, data) => {
      console.debug('HLS level switched to', data.level);
    });

    hls.value.on(Hls.Events.FRAG_BUFFERED, () => {
      // 片段缓冲完成，更新缓冲进度
      handleVideoProgress();
    });

    hls.value.on(Hls.Events.ERROR, (event, data) => {
      handleHlsError(data);
    });

    // 监听缓冲事件
    hls.value.on(Hls.Events.BUFFER_APPENDING, () => {
      playerState.media.loading = true;
      playerState.media.loadingStage = 'buffering';
    });

    hls.value.on(Hls.Events.BUFFER_APPENDED, () => {
      playerState.media.loading = false;
      playerState.media.loadingStage = 'ready';
    });

  } else if (videoPlayer.value.canPlayType('application/vnd.apple.mpegurl')) {
    // Safari原生支持
    videoPlayer.value.src = props.video.stream_video_url;
  }
};

// URL变更监听
watch(() => props.video?.stream_video_url, async (newVideoUrl) => {
  if (newVideoUrl && videoPlayer.value) {
    console.debug('video url changed');
    if (isHlsStream.value) {
      initializeHlsStream();
    } else {
      videoPlayer.value.src = newVideoUrl;
    }
  }
});

watch(() => props.video?.stream_audio_url, (newAudioUrl) => {
  if (!isHlsStream.value && audioPlayer.value && newAudioUrl) {
    audioPlayer.value.src = newAudioUrl;
  }
});

// 音量监听
watch(() => playerState.media.volume, (newVolume) => {
  if (videoPlayer.value) {
    videoPlayer.value.volume = newVolume / 100;
    if (audioPlayer.value) {
      audioPlayer.value.volume = newVolume / 100;
    }
  }
});

// 视频事件处理
const handleVideoPlay = () => {
  playerState.network.firstInteraction = false;
  
  if (isCanplay.value) {
    if (!isHlsStream.value && audioPlayer.value) {
      audioPlayer.value.currentTime = videoPlayer.value.currentTime;
      audioPlayer.value.play();
    }
    playerState.media.playing = true;
  } else {
    videoPlayer.value.pause();
    if (!isHlsStream.value && audioPlayer.value) {
      audioPlayer.value.currentTime = videoPlayer.value.currentTime;
    }
  }
};

const handleVideoPause = () => {
  console.debug('video pause');
  if (!isHlsStream.value && audioPlayer.value) {
    audioPlayer.value.pause();
  }
  if (!isSeeking.value) {
    playerState.media.playing = false;
  }
};

const handleVideoSeeking = () => {
  console.debug('video seeking');
  playerState.media.loading = true;
  playerState.media.loadingStage = 'buffering';
  if (!isHlsStream.value && audioPlayer.value) {
    audioPlayer.value.pause();
  }
  videoPlayer.value.pause();
  playerState.media.canPlay.audio = false;
  playerState.media.canPlay.video = false;
  playerState.media.seeking.video = true;
};

const handleVideoCanplay = () => {
  if (videoPlayer.value) {
    playerState.media.duration = videoPlayer.value.duration;

    // 使用改进的进度恢复逻辑
    if (playerState.media.firstInteraction) {
      const restoredPosition = restorePlaybackProgress();
      if (restoredPosition > 0) {
        console.debug('Restoring video position to:', restoredPosition);
        setVideoTime(restoredPosition);
      }
      playerState.media.firstInteraction = false;
    }
  }
  playerState.media.loading = false;
  playerState.media.loadingStage = 'ready';
  playerState.media.canPlay.video = true;
  playerState.media.seeking.video = false;

  if (!isSeeking.value && isCanplay.value) {
    videoPlayer.value.play();
    if (!isHlsStream.value && audioPlayer.value) {
      audioPlayer.value.play();
    }
  }
};

const handleVideoWaiting = () => {
  console.debug('video waiting');
  playerState.media.loading = true;
  playerState.media.loadingStage = 'buffering';
  if (!isHlsStream.value && audioPlayer.value) {
    audioPlayer.value.pause();
  }
};

const handleVideoTimeupdate = () => {
  if (videoPlayer.value) {
    const currentTime = videoPlayer.value.currentTime;
    playerState.media.currentTime = currentTime;

    // 确保duration被正确设置
    if (videoPlayer.value.duration && videoPlayer.value.duration !== Infinity) {
      playerState.media.duration = videoPlayer.value.duration;
    }

    // 改进的进度保存逻辑
    savePlaybackProgress(currentTime);

    emit('timeupdate', currentTime);
  }
};

// 播放进度保存逻辑
let lastSavedTime = 0;
let saveProgressTimer = null;

const savePlaybackProgress = (currentTime) => {
  // 更激进的防抖保存，减少网络请求频率
  if (saveProgressTimer) {
    clearTimeout(saveProgressTimer);
  }

  // 增加时间变化阈值到5秒，减少保存频率
  if (Math.abs(currentTime - lastSavedTime) >= 5) {
    saveProgressTimer = setTimeout(async () => {
      try {
        // 优先更新本地缓存，减少网络依赖
        updateLocalHistory(props.video.id, {
          last_position: currentTime,
          duration: playerState.media.duration,
          progress: (currentTime / playerState.media.duration) * 100,
          lastWatched: Date.now()
        });

        // 减少网络请求频率，只在特定条件下发送
        const shouldSendReport =
          Math.random() < 0.05 || // 5%概率发送
          (currentTime - lastSavedTime) >= 30 || // 或者超过30秒
          isVideoNearEnd(currentTime, playerState.media.duration); // 或者接近结尾

        if (shouldSendReport) {
          await sendReport(props.video.id, currentTime, {
            includeMetadata: false, // 减少数据传输
            retryOnFailure: false   // 不重试，减少网络负担
          });
        }

        lastSavedTime = currentTime;

      } catch (error) {
        console.warn('Failed to save progress:', error);
      }
    }, 2000); // 增加延迟到2秒
  }
};

// 判断视频是否接近结尾（已基本看完）
const isVideoNearEnd = (lastPosition, duration) => {
  if (!duration || duration <= 0 || !lastPosition || lastPosition <= 0) {
    return false;
  }

  const progress = (lastPosition / duration) * 100;
  const remainingTime = duration - lastPosition;

  // 对于短视频（少于5分钟），85%就算看完
  if (duration < 300) {
    return progress >= 85;
  }

  // 对于中等长度视频（5-30分钟），90%或剩余时间少于2分钟就算看完
  if (duration < 1800) {
    return progress >= 90 || remainingTime < 120;
  }

  // 对于长视频（超过30分钟），95%或剩余时间少于3分钟就算看完
  return progress >= 95 || remainingTime < 180;
};

// 恢复播放进度
const restorePlaybackProgress = () => {
  // 首先检查本地缓存
  const localHistory = getLocalHistory(props.video.id);

  if (localHistory && localHistory.last_position > 0) {
    const { last_position, duration } = localHistory;

    if (isVideoNearEnd(last_position, duration)) {
      console.debug('Video near end, starting from beginning');
      return 0;
    }

    console.debug('Restored progress from local cache:', last_position);
    return last_position;
  }

  // 回退到props中的位置
  if (props.video?.last_position > 0) {
    const { last_position, total_duration } = props.video;

    if (isVideoNearEnd(last_position, total_duration)) {
      console.debug('Video near end, starting from beginning');
      return 0;
    }

    console.debug('Restored progress from props:', last_position);
    return last_position;
  }

  return 0;
};

const handleVideoProgress = () => {
  if (videoPlayer.value && videoPlayer.value.buffered.length > 0) {
    const buffered = videoPlayer.value.buffered;
    let bufferedEnd = 0;

    // 找到包含当前播放时间的缓冲区间
    for (let i = 0; i < buffered.length; i++) {
      if (buffered.start(i) <= playerState.media.currentTime &&
          buffered.end(i) >= playerState.media.currentTime) {
        bufferedEnd = buffered.end(i);
        break;
      }
      // 如果没有找到包含当前时间的区间，使用最大的缓冲区间
      if (buffered.end(i) > bufferedEnd) {
        bufferedEnd = buffered.end(i);
      }
    }

    playerState.media.bufferedProgress =
      (bufferedEnd / playerState.media.duration) * 100;

    // 监控网络加载速度
    monitorNetworkSpeed();
  }
};

// 新增的性能优化事件处理函数
const handleVideoLoadstart = () => {
  console.debug('Video load started');
  playerState.media.loading = true;
  playerState.media.loadingStage = 'fetching';
  performanceState.loading.startTime = Date.now();
  performanceState.loading.bytesLoaded = 0;
};

const handleVideoLoadedmetadata = () => {
  console.debug('Video metadata loaded');
  playerState.media.loadingStage = 'buffering';
  if (videoPlayer.value) {
    playerState.media.duration = videoPlayer.value.duration;
  }
  // 确保字幕在元数据就绪后被加载展示
  if (playerState.media.subtitlesEnabled && playerState.media.currentSubtitle) {
    // 若 track 无 cues，重新加载字幕
    const track = videoPlayer.value?.textTracks?.[0];
    if (!track || !track.cues || track.cues.length === 0) {
      loadSubtitle(playerState.media.currentSubtitle);
    } else {
      track.mode = 'showing';
    }
  }
};

const handleVideoLoadeddata = () => {
  console.debug('Video data loaded');
  playerState.media.loadingStage = 'ready';
  playerState.media.loading = false;
};

const handleVideoSeeked = () => {
  console.debug('Video seeked');
  playerState.media.loading = false;
  playerState.media.loadingStage = 'ready';
  playerState.media.seeking.video = false;
};

const handleVideoCanplaythrough = () => {
  console.debug('Video can play through');
  playerState.media.loading = false;
  playerState.media.loadingStage = 'ready';
};

const handleVideoStalled = () => {
  console.debug('Video stalled');
  playerState.media.loading = true;
  playerState.media.loadingStage = 'buffering';
};

const handleVideoSuspend = () => {
  console.debug('Video suspended');
  // 网络空闲时暂停下载
};

const handleVideoAbort = () => {
  console.debug('Video aborted');
  playerState.media.loading = false;
};

// 音频事件处理
const handleAudioSeeking = () => {
  console.debug('audio seeking');
  playerState.media.seeking.audio = true;
};

const handleAudioCanplay = () => {
  playerState.media.canPlay.audio = true;
  playerState.media.seeking.audio = false;
  
  if (!isSeeking.value && isCanplay.value) {
    videoPlayer.value.play().then(() => {
      if (!isHlsStream.value && audioPlayer.value) {
        audioPlayer.value.play();
      }
    });
  }
};

// 用户交互
const togglePlay = () => {
  if (!videoPlayer.value) return;

  if (playerState.media.playing) {
    // 暂停播放
    videoPlayer.value.pause();
    if (hasAudioStream.value && audioPlayer.value) {
      audioPlayer.value.pause();
    }
    playerState.media.playing = false;
    emit('pause');
  } else {
    // 开始播放
    if (playerState.network.firstInteraction) {
      playerState.network.firstInteraction = false;
    }
    
    videoPlayer.value.play().then(() => {
      playerState.media.playing = true;
      if (hasAudioStream.value && audioPlayer.value) {
        audioPlayer.value.play().catch(err => {
          console.error('Failed to play audio:', err);
        });
      }
      emit('play');
    }).catch(err => {

    });
  }
  
  // 显示播放状态指示器已在 togglePlay 函数中处理
};

const toggleMute = () => {
  videoPlayer.value.muted = !videoPlayer.value.muted;
  if (!isHlsStream.value && audioPlayer.value) {
    audioPlayer.value.muted = videoPlayer.value.muted;
  }
  playerState.media.muted = videoPlayer.value.muted;
};

const toggleFullscreen = async () => {
  const elem = videoPlayer.value.parentElement;
  if (document.fullscreenElement) {
    await document.exitFullscreen();
  } else {
    if (elem.requestFullscreen) {
      await elem.requestFullscreen();
    } else if (elem.webkitRequestFullscreen) { /* Safari */
      await elem.webkitRequestFullscreen();
    } else if (elem.mozRequestFullScreen) { /* Firefox */
      await elem.mozRequestFullScreen();
    }
  }
  playerState.ui.fullscreen = !!document.fullscreenElement;
};

// 设置视频时间（唯一实现）
setVideoTime = (time) => {
  if (!videoPlayer.value) return;
  videoPlayer.value.currentTime = time;
  if (!isHlsStream.value && audioPlayer.value) {
    audioPlayer.value.currentTime = time;
  }
  playerState.media.currentTime = time;
};

// UI交互
/**
 * 兼容旧逻辑的鼠标进入处理
 * - 当启用统一 Pointer 时，不再依赖 isTouchDevice 来整体禁用 hover
 * - 继续复用核心显隐与定时器清理逻辑
 */
const handleMouseEnter = () => {
  playerState.ui.controlsVisible = true;
  if (hideControlsTimer) {
    clearTimeout(hideControlsTimer);
    hideControlsTimer = null;
  }
};

/**
 * 兼容旧逻辑的鼠标离开处理
 * - 当启用统一 Pointer 时，仍按定时器隐藏控制栏，且保持进度条悬停不隐藏的规则
 */
const handleMouseLeave = () => {
  hideControlsTimer = setTimeout(() => {
    if (!playerState.ui.hoveringProgress) {
      playerState.ui.controlsVisible = false;
    }
  }, 2000);
};

// 改进HLS错误处理
const handleHlsError = (data) => {
  if (data.fatal) {
    switch (data.type) {
      case Hls.ErrorTypes.NETWORK_ERROR:
        console.warn('HLS network error, trying to recover');
        if (playerState.network.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          playerState.network.reconnectAttempts++;
          hls.value.startLoad();
        } else {
          playerState.ui.errorMessage = '网络连接失败，请检查您的网络后重试';
          emit('error', {type: 'network', message: 'Network connection failed'});
        }
        break;
      case Hls.ErrorTypes.MEDIA_ERROR:
        console.warn('HLS media error, recovering');
        hls.value.recoverMediaError();
        break;
      default:
        if (playerState.network.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          playerState.network.reconnectAttempts++;
          initHls();
        } else {
          emit('error', {type: 'fatal', message: 'Cannot play video'});
        }
        break;
    }
  }
};

const initHls = () => {
  if (hls.value) {
    hls.value.destroy();
  }
  initializeHlsStream();
};

const handleVideoError = (error) => {
  console.error('Video error:', error);

  // 使用新的错误处理系统
  const errorInfo = handleError(error || videoPlayer.value?.error, {
    videoId: props.video?.id,
    isHlsStream: isHlsStream.value,
    reconnectAttempts: playerState.network.reconnectAttempts,
    retryCallback: () => {
      if (isHlsStream.value && hls.value) {
        playerState.media.loading = true;
        setTimeout(initHls, RECONNECT_INTERVAL);
      } else {
        playerState.media.loading = true;
        setTimeout(() => {
          videoPlayer.value.src = props.video.stream_video_url;
          videoPlayer.value.load();
          videoPlayer.value.play().catch(handleVideoError);
        }, RECONNECT_INTERVAL);
      }
    }
  });

  playerState.media.loading = false;
  emit('error', { type: 'video', error, errorInfo });
};

const handleAudioError = () => {
  if (!isHlsStream.value && 
      playerState.network.reconnectAttempts < MAX_RECONNECT_ATTEMPTS && 
      audioPlayer.value && 
      !audioPlayer.value.paused) {
    setTimeout(() => {
      audioPlayer.value.src = props.video.stream_audio_url;
      audioPlayer.value.load();
      audioPlayer.value.play().catch(() => {
        handleAudioError();
      });
    }, RECONNECT_INTERVAL);
  } else {
    console.error('Audio playback failed after maximum retries');
  }
};


// 使用组合函数封装触摸手势
const showControls = () => {
  playerState.ui.controlsVisible = true;
  if (hideControlsTimer) {
    clearTimeout(hideControlsTimer);
  }
};
const scheduleHideControls = (delay = 3000) => {
  if (hideControlsTimer) clearTimeout(hideControlsTimer);
  hideControlsTimer = setTimeout(() => {
    playerState.ui.controlsVisible = false;
  }, delay);
};
const { handleTouchStart, handleTouchMove, handleTouchEnd } = useTouchSeek(
  playerState,
  { videoRef: videoPlayer },
  { setVideoTime },
  { showControls, scheduleHideControls }
);

// 屏幕方向
const handleOrientationChange = () => {
  if (screen.orientation.type.includes('landscape')) {
    videoPlayer.value.classList.add('landscape-mode');
  } else {
    videoPlayer.value.classList.remove('landscape-mode');
  }
};


defineExpose({
  videoPlayer
});

// 键盘快捷键封装
const adjustVolume = (delta) => {
  const newVolume = Math.min(Math.max(playerState.media.volume + delta, 0), 100);
  playerState.media.volume = newVolume;
  playerState.ui.volume.showIndicator = true;
  setTimeout(() => { playerState.ui.volume.showIndicator = false; }, 1000);
};
const adjustPlaybackRate = (delta) => {
  const currentRate = playerState.media.playbackRate;
  const newRate = Math.min(Math.max(currentRate + delta, 0.25), 2);
  setPlaybackRate(newRate);
};
const toggleKeyboardHelp = () => { playerState.ui.showKeyboardHelp = !playerState.ui.showKeyboardHelp; };
const handleEscapeKey = () => {
  if (playerState.ui.showKeyboardHelp) playerState.ui.showKeyboardHelp = false;
  else if (playerState.ui.showSettingsMenu) playerState.ui.showSettingsMenu = false;
  else if (playerState.ui.showPlaybackRateMenu) playerState.ui.showPlaybackRateMenu = false;
  else if (playerState.ui.fullscreen) toggleFullscreen();
};


// 改进的错误处理函数
const handleRetry = () => {
  const success = manualRetry(() => {
    playerState.network.reconnectAttempts = 0;
    if (isHlsStream.value) {
      initHls();
    } else {
      videoPlayer.value.load();
      videoPlayer.value.play().catch((error) => {
        handleVideoError(error);
      });
    }
  });

  if (!success) {
    console.warn('Retry failed or not allowed');
  }
};

const reportErrorToSupport = async () => {
  try {
    await reportError({
      videoId: props.video?.id,
      videoUrl: props.video?.stream_video_url,
      userAction: 'manual_report',
      additionalContext: {
        playerState: {
          currentTime: playerState.media.currentTime,
          duration: playerState.media.duration,
          volume: playerState.media.volume,
          playbackRate: playerState.media.playbackRate
        }
      }
    });

    // 显示成功消息
    console.log('错误报告已发送');
  } catch (error) {
    console.error('Failed to report error:', error);
  }
};

const dismissError = () => {
  clearError();
};

// 更新同步函数
const syncMedia = () => {
  if (!videoPlayer.value || !hasAudioStream.value || !audioPlayer.value) return;
  
  // 只有在有音频流的情况下才进行同步
  const videoCurrent = videoPlayer.value.currentTime;
  const audioCurrent = audioPlayer.value.currentTime;

  // 只在差异较大时同步
  if (Math.abs(videoCurrent - audioCurrent) > 0.3) {
    audioPlayer.value.currentTime = videoCurrent;
  }
};

// 新增的UI功能函数
const skipForward = () => {
  const newTime = Math.min(playerState.media.currentTime + 10, playerState.media.duration);
  setVideoTime(newTime);
};

const skipBackward = () => {
  const newTime = Math.max(playerState.media.currentTime - 10, 0);
  setVideoTime(newTime);
};


const togglePlaybackRateMenu = () => {
  playerState.ui.showPlaybackRateMenu = !playerState.ui.showPlaybackRateMenu;
  playerState.ui.showSettingsMenu = false;
};

const setPlaybackRate = (rate) => {
  playerState.media.playbackRate = rate;
  if (videoPlayer.value) {
    videoPlayer.value.playbackRate = rate;
  }
  if (audioPlayer.value) {
    audioPlayer.value.playbackRate = rate;
  }
  playerState.ui.showPlaybackRateMenu = false;
};

const toggleSubtitles = () => {
  const willEnable = !playerState.media.subtitlesEnabled;
  playerState.media.subtitlesEnabled = willEnable;

  if (willEnable) {
    // 优先当前所选字幕，否则自动选择第一个
    const current = playerState.media.currentSubtitle || (props.video?.subtitles?.[0] || null);
    if (current) {
      playerState.media.currentSubtitle = current;
      loadSubtitle(current);
    }
  } else {
    hideSubtitles();
  }
};

const toggleSettingsMenu = () => {
  playerState.ui.showSettingsMenu = !playerState.ui.showSettingsMenu;
  playerState.ui.showPlaybackRateMenu = false;
};

const togglePictureInPicture = async () => {
  if (!supportsPiP.value) return;

  try {
    if (document.pictureInPictureElement) {
      await document.exitPictureInPicture();
      playerState.media.pictureInPicture = false;
    } else {
      await videoPlayer.value.requestPictureInPicture();
      playerState.media.pictureInPicture = true;
    }
  } catch (error) {
    console.error('Picture-in-Picture error:', error);
  }
};

// 现在初始化键盘快捷键（确保所需依赖均已声明）
const { handleKeyDown, cleanup: cleanupKeyboard } = useKeyboardShortcuts(playerState, {
  togglePlay,
  skipForward,
  skipBackward,
  setVideoTime,
  toggleMute,
  adjustVolume,
  adjustPlaybackRate,
  toggleFullscreen,
  togglePictureInPicture,
  toggleSubtitles,
  toggleKeyboardHelp,
  handleEscapeKey,
  getDuration: () => playerState.media.duration,
  getCurrentTime: () => playerState.media.currentTime,
});

// 高级功能函数
const setQuality = (quality) => {
  playerState.media.currentQuality = quality;

  if (hls.value) {
    if (quality === 'auto') {
      hls.value.currentLevel = -1; // 自动选择
    } else {
      // 根据质量标签找到对应的level
      const levels = hls.value.levels;
      const targetLevel = levels.findIndex(level =>
        level.height === parseInt(quality) ||
        level.name === quality
      );
      if (targetLevel !== -1) {
        hls.value.currentLevel = targetLevel;
      }
    }
  }

  playerState.ui.showSettingsMenu = false;
  console.debug('Quality changed to:', quality);
};

const setSubtitle = (subtitle) => {
  playerState.media.currentSubtitle = subtitle;
  playerState.media.subtitlesEnabled = !!subtitle;

  // 这里可以添加字幕显示逻辑
  if (subtitle) {
    console.debug('Subtitle enabled:', subtitle.language);
    // 加载字幕文件
    loadSubtitle(subtitle);
  } else {
    console.debug('Subtitles disabled');
    // 隐藏字幕
    hideSubtitles();
  }

  playerState.ui.showSettingsMenu = false;
};

const loadSubtitle = async (subtitle) => {
  try {
    // 这里可以实现字幕加载逻辑
    // 例如加载 WebVTT 文件
    if (subtitle.url) {
      const response = await fetch(subtitle.url);
      const text = await response.text();

      // 创建或更新字幕轨道
      let track = videoPlayer.value.textTracks[0];
      if (!track) {
        const label = subtitle.label || subtitle.language || 'Subtitles';
        const langCode = subtitle.srclang || 'zh';
        track = videoPlayer.value.addTextTrack('subtitles', label, langCode);
      }

      // 清空旧的 cues
      for (let i = track.cues?.length - 1; i >= 0; i--) {
        track.removeCue(track.cues[i]);
      }

      // 自动识别 SRT/VTT
      const isVtt = text.trimStart().startsWith('WEBVTT');
      if (isVtt) {
        parseVTT(text, track);
      } else {
        parseSRT(text, track);
      }
      track.mode = 'showing';
    }
  } catch (error) {
    console.error('Failed to load subtitle:', error);
  }
};

const hideSubtitles = () => {
  // 隐藏所有字幕轨道
  for (let i = 0; i < videoPlayer.value.textTracks.length; i++) {
    videoPlayer.value.textTracks[i].mode = 'hidden';
  }
};


// 当视频的字幕列表变为可用时，自动选择并加载第一条（仅在未手动选择时）
watch(() => props.video?.subtitles, (newSubs) => {
  if (Array.isArray(newSubs) && newSubs.length > 0 && !playerState.media.currentSubtitle) {
    const first = newSubs[0];
    playerState.media.currentSubtitle = first;
    playerState.media.subtitlesEnabled = true;
    loadSubtitle(first);
  }
});

/**
 * 点击透明层的处理：
 * - 统一处理所有设备的单击播放切换
 * - 触摸设备也支持单击切换播放状态
 */
const handleVideoLayerClick = () => {
  // 检查是否正在进行触摸手势操作（快进快退或音量调节）
  if (playerState.ui.seeking.active || playerState.ui.volume.adjusting) {
    return;
  }

  // 统一处理播放切换
  togglePlay();

  // 显示播放状态指示器
  playerState.ui.showPlayIndicator = true;
  setTimeout(() => {
    playerState.ui.showPlayIndicator = false;
  }, 500);
};

/**
 * Pointer 事件统一入口：
 * - onPointerEnter/onPointerLeave 基于 handleMouseEnter/handleMouseLeave 复用逻辑
 * - onPointerMove 作为“保底显隐”，移动时显示控制栏并重置隐藏定时器（与进度条悬停逻辑一致）
 * - 对 coarse 指针（触摸）不强制禁用，仅在需要时微调阈值
 */
const onPointerEnter = (e) => {
  if (!enablePointerUnified) return; // 可选回退
  // 对所有指针类型统一处理
  handleMouseEnter();
};

const onPointerLeave = (e) => {
  if (!enablePointerUnified) return; // 可选回退
  handleMouseLeave();
};

const onPointerMove = (e) => {
  if (!enablePointerUnified) return; // 可选回退

  // 保底显隐：移动时显示控制栏，并重置隐藏计时器
  playerState.ui.controlsVisible = true;

  if (hideControlsTimer) {
    clearTimeout(hideControlsTimer);
    hideControlsTimer = null;
  }

  // 进度条悬停时不隐藏，保持与现有规则一致
  hideControlsTimer = setTimeout(() => {
    if (!playerState.ui.hoveringProgress) {
      playerState.ui.controlsVisible = false;
    }
  }, 2000);
};
</script>

<style scoped>
/* 提取公共变量 */
:root {
  --primary-red: #FF0000;
  --control-icon-size: 1.2rem;
  --progress-bar-height: 0.1875rem;
  --hover-transition: opacity 0.2s ease-in-out;
}

/* 合并重复的定位样式 */
.video-container,
.yt-loading-spinner,
.play-state-indicator,
.error-message,
.seeking-indicator {
  @apply absolute;
}

/* 简化transform写法 */
.transform-center {
  @apply top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2;
}

.play-state-indicator,
.error-message,
.seeking-indicator {
  @apply transform-center;
}

/* 合并颜色相关样式 */
.bg-semi-dark {
  background-color: rgba(0, 0, 0, 0.7);
}

/* 优化媒体查询 */
@media (hover: none), (pointer: coarse) {
  .volume-slider-container {
    width: 1.25rem !important;
  }
  .progress-bar {
    height: 0.3125rem;
  }
  .progress-bar-container {
    height: 1.25rem;
  }
}

/* 使用CSS变量优化重复值 */
.progress-bar-filled,
.progress-handle,
.progress-dot {
  background-color: var(--primary-red);
}

.control-icon {
  font-size: var(--control-icon-size);
}

/* 合并动画相关样式 */
@keyframes media-spinner {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

/* 合并到下方统一定义 */

/* 优化伪类选择器 */
.volume-range {
  &::-webkit-slider-thumb,
  &::-moz-range-thumb {
    width: 0.75rem;
    height: 0.75rem;
    border-radius: 50%;
    background: white;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  }
}

/* 合并过渡效果 */
.video-controls,
.hover-gradient,
.progress-handle {
  transition: var(--hover-transition);
}

/* 使用:where()简化选择器 */
:where(.progress-container:hover, .video-controls:hover) .preview-time-tooltip {
  @apply opacity-100;
}

/* 优化flex布局声明 */
.controls-main,
.controls-left,
.controls-right,
.volume-slider-wrapper {
  @apply flex items-center;
}

/* 简化z-index管理 */
:root {
  --z-video-layer: 10;
  --z-controls: 20;
  --z-spinner: 30;
  --z-error: 40;
}

.video-click-layer { z-index: var(--z-video-layer); }
.video-controls { z-index: var(--z-controls); }
.yt-loading-spinner { z-index: var(--z-spinner); }
.error-message { z-index: var(--z-error); }

.video-wrapper {
  @apply absolute top-0 left-0 w-full h-full flex items-center justify-center;
}

.video-container {
  /* 保持容器可命中 pointerenter/leave，禁止在此处使用 pointer-events: none
     如需拦截点击，请在 .video-click-layer 层面控制 pointer-events */
  @apply relative w-full h-full cursor-pointer;
}

.video-player {
  @apply w-full h-full object-contain;
}

.hover-gradient {
  @apply absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent 
    opacity-100 transition-opacity duration-300;
}

.video-controls {
  @apply absolute bottom-0 left-0 right-0 px-4
    opacity-0 transition-all duration-200 z-20
    flex flex-col;
}

.controls-visible {
  @apply opacity-100;
  transition-delay: 0s;
}

.progress-container {
  @apply relative mb-0;
  height: 0.3125rem;
}

.preview-time-tooltip {
  @apply absolute bottom-8 bg-black/90 text-white rounded text-sm
    transform -translate-x-1/2 opacity-0 transition-opacity duration-200;
  padding: 0.25rem 0.5rem;
}

.progress-container:hover .preview-time-tooltip {
  @apply opacity-100;
}

.progress-bar-container {
  @apply absolute bottom-0 left-0 right-0 cursor-pointer z-30;
  height: 1rem;
  margin-bottom: -0.375rem;
}

.progress-bar {
  @apply relative w-full bg-[#FFFFFF33] overflow-hidden;
  height: 0.1875rem;
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
}

.progress-bar-loaded {
  @apply absolute top-0 left-0 h-full;
  background-color: rgba(255, 255, 255, 0.15);
}

.progress-bar-filled {
  @apply absolute top-0 left-0 h-full;
  background-color: #FF0000; /* 恢复为YouTube红色 */
}

.progress-handle {
  @apply absolute bottom-1/2 rounded-full bg-[#FF0000]
    transform translate-y-1/2 -translate-x-1/2
    transition-opacity duration-200 opacity-0;
  width: 0.75rem;
  height: 0.75rem;
}

.progress-container:hover .progress-handle {
  @apply opacity-100;
}

.controls-main {
  @apply flex justify-between items-center;
}

.controls-left, .controls-right {
  @apply flex items-center gap-1;
}

.control-btn {
  @apply p-2 rounded-full hover:bg-white/20 transition-colors;
}

.control-icon {
  @apply text-white text-[1.2rem];
}

.volume-control {
  position: relative;
  display: flex;
  align-items: center;
  height: 2.5rem;
}

.volume-slider-container {
  overflow: hidden;
  transition: width 0.2s;
  width: 0;
  height: 2.5rem;
  display: flex;
  align-items: center;
}

.volume-control:hover .volume-slider-container {
  width: 5rem;
}

.volume-slider-wrapper {
  position: relative;
  width: 100%;
  height: 2.5rem;
  display: flex;
  align-items: center;
  padding: 0 0.375rem;
}

.volume-track-bg {
  position: absolute;
  top: 50%;
  left: 0.375rem;
  right: 0.375rem;
  height: 0.1875rem;
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-50%);
  pointer-events: none;
  z-index: 1;
}

.volume-range-fill {
  position: absolute;
  height: 0.1875rem;
  background-color: white;
  left: 0.375rem;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  z-index: 2;
}

.time-display {
  @apply text-white text-sm ml-3 select-none;
}

.video-controls {
  font-family: "YouTube Noto", Roboto, Arial, sans-serif;
}

.progress-container:hover ~ .video-controls,
.video-controls:hover {
  @apply opacity-100;
  transition-delay: 0s;
}

.progress-dot {
  position: absolute;
  width: 0.375rem;
  height: 0.375rem;
  background-color: #FF0000;
  border-radius: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
  transition: width 0.2s, height 0.2s;
}

.progress-bar-container:hover .progress-dot {
  width: 0.5rem;
  height: 0.5rem;
}

.play-state-indicator {
  @apply absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2
    bg-black/50 rounded-full p-4 z-20
    animate-fade-out;
}

.indicator-icon {
  @apply text-white text-6xl;
}

@keyframes fade-out {
  from {
    opacity: 1;
  }
  to {
    opacity: 0;
  }
}

.animate-fade-out {
  animation: fade-out 0.5s ease-out forwards;
}

.video-click-layer {
  /* 点击层仅负责点击，不要影响父容器的 pointerenter/leave 命中 */
  @apply absolute inset-0 z-10;
  bottom: 5.25rem;
  pointer-events: auto;
}

.yt-loading-spinner {
  @apply absolute inset-0 flex flex-col items-center justify-center z-20;
}

.yt-spinner {
  @apply w-12 h-12 mb-4;
}

.yt-spinner__circle {
  @apply w-full h-full;
  fill: none;
  stroke: currentColor;
  stroke-width: 0.375rem;
  stroke-linecap: round;
  color: white;
  animation: media-spinner 1.4s linear infinite;
}

.yt-spinner__circle circle {
  stroke-dasharray: 12.5rem;
  stroke-dashoffset: 50rem;
}

/* 上方已设置 animation: media-spinner */

/* 中央加载速度信息 */
.loading-speed-info {
  @apply text-center;
}

.loading-speed-text {
  @apply text-white text-sm font-medium;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
}

/* 左下角加载状态指示器 */
.loading-status-indicator {
  position: absolute;
  bottom: 4rem;
  left: 1rem;
  z-index: 30;
}

.loading-status-text {
  color: white;
  font-size: 0.8125rem;
  font-weight: 400;
  font-family: -apple-system, BlinkMacSystemFont, "YouTube Noto", Roboto, sans-serif;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
  white-space: nowrap;
}

@media (orientation: portrait) {
  .video-player {
    object-fit: contain;
  }
}

/* 改进的错误消息样式 */
.error-message {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(28, 28, 28, 0.95);
  backdrop-filter: blur(10px);
  color: white;
  border-radius: 1rem;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  z-index: 50;
  max-width: 90%;
  min-width: 320px;
  max-height: 80vh;
  overflow-y: auto;
}

.error-content {
  padding: 1.5rem;
  display: flex;
  align-items: flex-start;
  gap: 1rem;
}

.error-icon {
  color: #ef4444;
  font-size: 2rem;
  flex-shrink: 0;
  margin-top: 0.25rem;
}

.error-text {
  flex: 1;
}

.error-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: white;
}

.error-description {
  font-size: 0.875rem;
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 1rem;
  line-height: 1.5;
}

.error-suggestions {
  margin-top: 1rem;
}

.suggestions-title {
  font-size: 0.875rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 0.5rem;
}

.suggestions-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.suggestions-list li {
  font-size: 0.8125rem;
  color: rgba(255, 255, 255, 0.7);
  padding: 0.25rem 0;
  position: relative;
  padding-left: 1rem;
}

.suggestions-list li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: #3ea6ff;
}

.error-actions {
  padding: 1rem 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.retry-button,
.report-button,
.dismiss-button {
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  border: none;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.retry-button {
  background: #3ea6ff;
  color: white;
}

.retry-button:hover:not(:disabled) {
  background: #2563eb;
}

.retry-button:disabled {
  background: rgba(62, 166, 255, 0.5);
  cursor: not-allowed;
}

.report-button {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.report-button:hover {
  background: rgba(255, 255, 255, 0.2);
}

.dismiss-button {
  background: transparent;
  color: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.dismiss-button:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

/* 键盘操作反馈样式 */
.keyboard-feedback {
  position: absolute;
  top: 20%;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(28, 28, 28, 0.9);
  color: white;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  z-index: 40;
  animation: fadeInOut 1.5s ease-in-out;
}

.keyboard-icon {
  font-size: 1rem;
  color: #3ea6ff;
}

@keyframes fadeInOut {
  0% {
    opacity: 0;
    transform: translateX(-50%) translateY(-10px);
  }
  20%, 80% {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
  100% {
    opacity: 0;
    transform: translateX(-50%) translateY(-10px);
  }
}

/* 键盘帮助覆盖层样式 */
.keyboard-help-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(4px);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.keyboard-help-modal {
  background: rgba(28, 28, 28, 0.95);
  border-radius: 1rem;
  max-width: 600px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.keyboard-help-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.keyboard-help-header h3 {
  color: white;
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.close-help-btn {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 0.25rem;
  transition: all 0.2s;
}

.close-help-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.keyboard-help-content {
  padding: 1.5rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.shortcut-section h4 {
  color: white;
  font-size: 1rem;
  font-weight: 600;
  margin: 0 0 1rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.shortcut-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.shortcut-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.shortcut-item kbd {
  background: rgba(255, 255, 255, 0.1);
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-family: 'Roboto Mono', monospace;
  font-size: 0.75rem;
  font-weight: 500;
  border: 1px solid rgba(255, 255, 255, 0.2);
  min-width: fit-content;
}

.shortcut-item span {
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.875rem;
  text-align: right;
}

/* 响应式调整 */
@media (max-width: 640px) {
  .keyboard-help-overlay {
    padding: 1rem;
  }

  .keyboard-help-content {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .shortcut-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }

  .shortcut-item span {
    text-align: left;
  }
}

/* 新增UI元素样式 */
.skip-controls {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  margin-left: 0.5rem;
}

.skip-btn {
  padding: 0.375rem;
}

.play-btn {
  padding: 0.5rem;
  margin-right: 0.5rem;
}

.time-display {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  margin-left: 1rem;
  font-family: 'Roboto Mono', monospace;
}

.time-separator {
  color: rgba(255, 255, 255, 0.7);
}

.current-time, .total-time {
  color: white;
  font-size: 0.875rem;
  font-weight: 500;
}

.playback-rate-control {
  position: relative;
}

.playback-rate-text {
  font-size: 0.875rem;
  font-weight: 500;
  color: white;
  min-width: 2rem;
  text-align: center;
}

.playback-rate-menu {
  position: absolute;
  bottom: 100%;
  right: 0;
  background: rgba(28, 28, 28, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 0.5rem;
  padding: 0.5rem;
  margin-bottom: 0.5rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  z-index: 50;
}

.rate-option {
  display: block;
  width: 100%;
  padding: 0.5rem 1rem;
  text-align: center;
  color: white;
  background: transparent;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  transition: background-color 0.2s;
  font-size: 0.875rem;
}

.rate-option:hover {
  background: rgba(255, 255, 255, 0.1);
}

.rate-option.active {
  background: rgba(255, 255, 255, 0.2);
  color: #3ea6ff;
}

/* 设置菜单样式 */
.settings-control {
  position: relative;
}

.settings-menu {
  position: absolute;
  bottom: 100%;
  right: 0;
  background: rgba(28, 28, 28, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 0.5rem;
  padding: 1rem;
  margin-bottom: 0.5rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  z-index: 50;
  min-width: 200px;
  max-width: 300px;
}

.settings-section {
  margin-bottom: 1rem;
}

.settings-section:last-child {
  margin-bottom: 0;
}

.settings-title {
  color: white;
  font-size: 0.875rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.quality-options,
.subtitle-options {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.quality-option,
.subtitle-option {
  display: block;
  width: 100%;
  padding: 0.5rem 0.75rem;
  text-align: left;
  color: white;
  background: transparent;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  transition: background-color 0.2s;
  font-size: 0.875rem;
}

.quality-option:hover,
.subtitle-option:hover {
  background: rgba(255, 255, 255, 0.1);
}

.quality-option.active,
.subtitle-option.active {
  background: rgba(255, 255, 255, 0.2);
  color: #3ea6ff;
}

.setting-item {
  margin-bottom: 0.5rem;
}

.setting-item:last-child {
  margin-bottom: 0;
}

.setting-label {
  display: flex;
  align-items: center;
  color: white;
  font-size: 0.875rem;
  cursor: pointer;
  padding: 0.25rem 0;
}

.setting-checkbox {
  margin-right: 0.5rem;
  accent-color: #3ea6ff;
}

/* 章节标记样式 */
.chapter-markers {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.chapter-marker {
  position: absolute;
  top: 0;
  width: 2px;
  height: 100%;
  background: rgba(255, 255, 255, 0.6);
  transform: translateX(-50%);
}

/* 预览悬停线 */
.progress-bar-hover {
  position: absolute;
  top: 0;
  width: 1px;
  height: 100%;
  background: rgba(255, 255, 255, 0.8);
  transform: translateX(-50%);
  z-index: 3;
}

/* 改进的提示框样式 */
.preview-time-tooltip {
  position: absolute;
  bottom: 100%;
  transform: translateX(-50%);
  margin-bottom: 0.5rem;
  z-index: 10;
}

.tooltip-content {
  background: rgba(28, 28, 28, 0.9);
  color: white;
  padding: 0.375rem 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  white-space: nowrap;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.tooltip-arrow {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 4px solid rgba(28, 28, 28, 0.9);
}

/* 响应式调整 */
@media (max-width: 640px) {
  .controls-main {
    flex-wrap: nowrap;
    justify-content: space-between;
    width: 100%;
  }

  .controls-right {
    margin-top: 0;
    display: flex;
    justify-content: flex-end;
  }

  .controls-left {
    display: flex;
    justify-content: flex-start;
  }

  /* 隐藏部分控件，简化移动端界面 */
  .controls-left .volume-control,
  .skip-controls,
  .playback-rate-control {
    display: none;
  }

  /* 调整时间显示 */
  .time-display {
    font-size: 0.75rem;
    white-space: nowrap;
    margin-left: 0.5rem;
  }

  /* 调整按钮大小 */
  .control-btn {
    margin: 0 0.125rem;
    padding: 0.25rem;
  }

  .control-icon {
    font-size: 1.1rem;
  }

  .play-btn {
    margin-right: 0.25rem;
  }

  /* 移动端加载状态指示器调整 */
  .loading-status-indicator {
    bottom: 3.5rem;
    left: 0.75rem;
  }

  .loading-status-text {
    font-size: 0.75rem;
  }

  /* 移动端中央加载速度信息调整 */
  .loading-speed-text {
    font-size: 0.8125rem;
  }
}

/* 无障碍焦点样式 */
.video-container:focus-visible {
  outline: 2px solid white;
  outline-offset: 2px;
}

/* 将音量控制样式与YouTube保持一致 */
.volume-range {
  -webkit-appearance: none;
  appearance: none;
  background: transparent;
  width: 100%;
  height: 2.5rem;
  margin: 0;
  cursor: pointer;
  position: relative;
  z-index: 10;
}

/* 修复小圆点位置并与YouTube保持一致 */
.volume-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 50%;
  background: white;
  cursor: pointer;
  border: none;
  margin-top: -0.28125rem;
  z-index: 11;
  box-shadow: 0 0.0625rem 0.1875rem rgba(0, 0, 0, 0.2);
}

.volume-range::-moz-range-thumb {
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 50%;
  background: white;
  cursor: pointer;
  border: none;
  box-shadow: 0 0.0625rem 0.1875rem rgba(0, 0, 0, 0.2);
}

/* 设置轨道样式 */
.volume-range::-webkit-slider-runnable-track {
  width: 100%;
  height: 0.1875rem;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 0.09375rem;
}

/* 调整填充颜色 */
.volume-range-fill {
  background-color: white; /* 保持音量填充为白色 */
}

/* 确保其他样式保持不变 */
.volume-track-bg {
  background: rgba(255, 255, 255, 0.2); /* 保持浅灰色背景 */
}

/* 添加快进/快退指示器样式 */
.seeking-indicator {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
  background: rgba(28, 28, 28, 0.85);
  backdrop-filter: blur(0.75rem);
  -webkit-backdrop-filter: blur(0.75rem);
  border: 0.0625rem solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 0.5rem 2rem rgba(0, 0, 0, 0.2);
  width: 5rem;
  height: 5rem;
  border-radius: 1rem;
}

.seeking-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
}

.seeking-content::after {
  content: '';
  position: absolute;
  inset: -2.5rem;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 70%);
  opacity: 0.5;
  z-index: -1;
}

.seeking-icon-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.seeking-icon {
  color: white;
  transition: transform 0.3s;
  font-size: 1.75rem;
  filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.2));
}

.seeking-seconds {
  color: rgba(255, 255, 255, 0.9);
  font-weight: 500;
  letter-spacing: 0.025em;
  font-size: 0.875rem;
  font-family: -apple-system, BlinkMacSystemFont, "YouTube Noto", Roboto, sans-serif;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

@keyframes seeking-pulse {
  0% {
    transform: translate(-50%, -50%) scale(0.98);
    opacity: 0.95;
  }
  50% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 1;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
  }
  100% {
    transform: translate(-50%, -50%) scale(0.98);
    opacity: 0.95;
  }
}

.seeking-indicator {
  animation: seeking-pulse 2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  
  &[data-direction="forward"] {
    .seeking-content::before {
      content: '';
      position: absolute;
      right: -1.25rem;
      width: 2.5rem;
      height: 100%;
      background: linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.1) 100%);
      transform: skewX(-15deg);
      opacity: 0;
      animation: slide-light 1.5s ease-in-out infinite;
    }
  }
  
  &[data-direction="backward"] {
    .seeking-content::before {
      content: '';
      position: absolute;
      left: -1.25rem;
      width: 2.5rem;
      height: 100%;
      background: linear-gradient(-90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.1) 100%);
      transform: skewX(15deg);
      opacity: 0;
      animation: slide-light 1.5s ease-in-out infinite;
    }
  }
}

@keyframes slide-light {
  0% {
    opacity: 0;
    transform: translateX(0) skewX(-15deg);
  }
  20% {
    opacity: 0.4;
  }
  80% {
    opacity: 0;
  }
  100% {
    opacity: 0;
    transform: translateX(100%) skewX(-15deg);
  }
}

.volume-adjust-indicator {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  top: 15%;
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 30;
  width: 8rem;
}

.volume-control-container {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  width: 100%;
  padding: 0.5rem 0.75rem;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 0.5rem;
}

.volume-slider {
  height: 0.125rem;
  width: 100%;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 9999px;
  position: relative;
  overflow: hidden;
}

.volume-slider-fill {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  background: rgba(255, 255, 255, 0.9);
  transition: all 0.1s;
}

.volume-slider-thumb {
  position: absolute;
  width: 0.625rem;
  height: 0.625rem;
  background: white;
  border-radius: 50%;
  top: 50%;
  transform: translateY(-50%);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  transition: left 0.1s ease-out;
}

.volume-value {
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.75rem;
  font-weight: 500;
  margin-top: 0.25rem;
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
