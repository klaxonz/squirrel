<template>
  <div class="video-controls" :class="{ 'controls-visible': playerState.ui.controlsVisible }">
    <!-- 进度条容器 -->
    <ProgressBar
      :progress="progress"
      :buffered-progress="playerState.media.bufferedProgress"
      :duration="playerState.media.duration"
      :current-time="playerState.media.currentTime"
      :chapters="video.chapters"
      @seek-start="$emit('seek-start')"
      @seek="$emit('progress-seek', $event)"
      @seek-end="$emit('seek-end')"
    />

    <!-- 主控制栏 -->
    <div class="controls-main">
      <div class="controls-left">
        <!-- 播放控制 -->
        <PlaybackControls
          :playing="playerState.media.playing"
          @toggle-play="$emit('toggle-play')"
          @skip-forward="$emit('skip-forward')"
          @skip-backward="$emit('skip-backward')"
        />

        <!-- 音量控制 -->
        <VolumeControl
          :volume="playerState.media.volume"
          :muted="playerState.media.muted"
          :volume-icon="volumeIcon"
          @toggle-mute="$emit('toggle-mute')"
          @volume-change="handleVolumeChange"
        />

        <!-- 时间显示 -->
        <TimeDisplay
          :current-time="playerState.media.currentTime"
          :duration="playerState.media.duration"
        />
      </div>

      <div class="controls-right">
        <!-- 播放速度控制 -->
        <PlaybackRateControl
          v-if="!isTouchDevice"
          :current-rate="playerState.media.playbackRate"
          :rates="playbackRates"
          :show-menu="playerState.ui.showPlaybackRateMenu"
          @toggle-menu="togglePlaybackRateMenu"
          @set-rate="$emit('set-playback-rate', $event)"
        />

        <!-- 质量选择器 -->
        <QualitySelector
          v-if="!isTouchDevice && availableQualities.length > 1"
          :current-quality="playerState.media.currentQuality"
          :available-qualities="availableQualities"
          :show-menu="playerState.ui.showQualityMenu"
          @toggle-menu="toggleQualityMenu"
          @set-quality="$emit('set-quality', $event)"
        />

        <!-- 画中画按钮 -->
        <button
          v-if="supportsPip"
          @click="$emit('toggle-pip')"
          class="vp-control-btn"
          :class="{ 'active-control': playerState.media.pictureInPicture }"
          aria-label="画中画"
        >
          <Icon icon="material-symbols:picture-in-picture-alt" class="vp-control-icon" />
        </button>

        <!-- 字幕按钮 -->
        <button
          @click="$emit('toggle-subtitles')"
          class="vp-control-btn"
          :class="{ 'active-control': playerState.media.subtitlesEnabled }"
          :aria-label="playerState.media.subtitlesEnabled ? '关闭字幕' : '开启字幕'"
        >
          <Icon icon="material-symbols:subtitles" class="vp-control-icon" />
        </button>

        <!-- 剧场模式按钮 -->
        <button
          @click="$emit('toggle-theater')"
          class="vp-control-btn"
          :class="{ 'active-control': playerState.ui.theaterMode }"
          aria-label="剧场模式"
        >
          <Icon icon="material-symbols:fit-screen" class="vp-control-icon" />
        </button>

        <!-- 设置菜单 -->
        <SettingsMenu
          :show-menu="playerState.ui.showSettingsMenu"
          :current-quality="playerState.media.currentQuality"
          :available-qualities="availableQualities"
          :current-subtitle="playerState.media.currentSubtitle"
          :subtitles="video.subtitles"
          :autoplay="playerState.media.autoplay"
          :loop="playerState.media.loop"
          @toggle-menu="toggleSettingsMenu"
          @set-quality="$emit('set-quality', $event)"
          @set-subtitle="$emit('set-subtitle', $event)"
          @update-autoplay="updateAutoplay"
          @update-loop="updateLoop"
        />

        <!-- 全屏按钮 -->
        <button
          @click="$emit('toggle-fullscreen')"
          class="vp-control-btn"
          aria-label="全屏"
        >
          <Icon :icon="fullscreenIcon" class="vp-control-icon" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Icon } from '@iconify/vue'
import ProgressBar from './ProgressBar.vue'
import PlaybackControls from './PlaybackControls.vue'
import VolumeControl from './VolumeControl.vue'
import TimeDisplay from './TimeDisplay.vue'
import PlaybackRateControl from './PlaybackRateControl.vue'
import SettingsMenu from './SettingsMenu.vue'
import QualitySelector from './QualitySelector.vue'
import BufferingIndicator from './BufferingIndicator.vue'

const props = defineProps({
  playerState: Object,
  video: Object,
  progress: Number,
  volumeIcon: String,
  fullscreenIcon: String,
  supportsPip: Boolean,
  availableQualities: Array,
  playbackRates: Array
})

const emit = defineEmits([
  'toggle-play',
  'skip-forward',
  'skip-backward',
  'toggle-mute',
  'toggle-fullscreen',
  'toggle-subtitles',
  'toggle-theater',
  'toggle-pip',
  'set-quality',
  'set-playback-rate',
  'set-subtitle',
  'seek-start',
  'progress-seek',
  'seek-end'
])

const isTouchDevice = computed(() =>
  typeof window !== 'undefined' && ('ontouchstart' in window || navigator.maxTouchPoints > 0)
)

const handleVolumeChange = (volume) => {
  props.playerState.media.volume = volume
}

const togglePlaybackRateMenu = () => {
  props.playerState.ui.showPlaybackRateMenu = !props.playerState.ui.showPlaybackRateMenu
  props.playerState.ui.showSettingsMenu = false
  props.playerState.ui.showQualityMenu = false
}

const toggleQualityMenu = () => {
  props.playerState.ui.showQualityMenu = !props.playerState.ui.showQualityMenu
  props.playerState.ui.showSettingsMenu = false
  props.playerState.ui.showPlaybackRateMenu = false
}

const toggleSettingsMenu = () => {
  props.playerState.ui.showSettingsMenu = !props.playerState.ui.showSettingsMenu
  props.playerState.ui.showPlaybackRateMenu = false
  props.playerState.ui.showQualityMenu = false
}

const updateAutoplay = (value) => {
  props.playerState.media.autoplay = value
}

const updateLoop = (value) => {
  props.playerState.media.loop = value
}


</script>

<style scoped>
.video-controls {
  @apply absolute bottom-0 left-0 right-0 px-3
    opacity-0 z-20
    flex flex-col;
  background: linear-gradient(to top, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0.4) 50%, transparent 100%);
  padding-bottom: 8px;
  padding-top: 24px;
  transition: all var(--yt-transition-medium) ease;
}

.controls-main {
  @apply flex items-center justify-between py-1;
  height: 40px;
}

.controls-left,
.controls-right {
  @apply flex items-center;
  gap: 8px;
}

.vp-control-btn {
  @apply p-2 rounded-full text-white
    focus:outline-none focus:ring-2 focus:ring-white/30
    flex items-center justify-center;
  background-color: var(--vp-bg-control);
  min-width: 40px;
  min-height: 40px;
  transition: all var(--vp-transition-normal);
}

.vp-control-btn:hover {
  background-color: var(--vp-bg-control-hover);
  transform: scale(1.04);
}

.vp-control-btn:active {
  transform: scale(0.98);
}

/* 激活态：YouTube 风格为中性高亮而非红色 */
.vp-control-btn.active-control {
  background-color: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.18);
}

.vp-control-btn.active-control:hover {
  background-color: rgba(255, 255, 255, 0.18);
}

.vp-control-icon {
  @apply text-xl;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3));
}

/* 控制栏可见状态 */
.video-controls.controls-visible {
  @apply opacity-100;
}

/* YouTube风格的渐变遮罩 */
.video-controls::before {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 120px;
  background: linear-gradient(
    to top,
    rgba(0,0,0,0.8) 0%,
    rgba(0,0,0,0.6) 30%,
    rgba(0,0,0,0.3) 60%,
    transparent 100%
  );
  pointer-events: none;
  z-index: -1;
  transition: opacity var(--yt-transition-medium) ease;
}

.video-controls.controls-visible::before {
  opacity: 1;
}

/* 全屏状态下的样式修复 */
.video-player-container:fullscreen .video-controls,
.video-player-container:-webkit-full-screen .video-controls,
.video-player-container:-moz-full-screen .video-controls {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 2147483647; /* 最高 z-index 值 */
  width: 100%;
}

.video-player-container:fullscreen .video-controls .progress-container,
.video-player-container:-webkit-full-screen .video-controls .progress-container,
.video-player-container:-moz-full-screen .video-controls .progress-container {
  z-index: 2147483647;
}

.video-player-container:fullscreen .video-controls .controls-main,
.video-player-container:-webkit-full-screen .video-controls .controls-main,
.video-player-container:-moz-full-screen .video-controls .controls-main {
  z-index: 2147483647;
}
</style>
