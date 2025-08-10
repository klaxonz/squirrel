<template>
  <div class="video-controls" :class="{ 'controls-visible': playerState.ui.controlsVisible }">
    <!-- 进度条容器 -->
    <ProgressBar
      :progress="progress"
      :buffered-progress="playerState.media.bufferedProgress"
      :duration="playerState.media.duration"
      :current-time="playerState.media.currentTime"
      :chapters="video.chapters"
      :hovering="playerState.ui.hoveringProgress"
      :hover-position="playerState.ui.hoverPosition"
      :preview-time="playerState.ui.previewTime"
      @seek="$emit('progress-seek', $event)"
      @hover-start="handleProgressHoverStart"
      @hover-end="handleProgressHoverEnd"
      @hover-move="handleProgressHoverMove"
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

        <!-- 画中画按钮 -->
        <button
          v-if="supportsPip"
          @click="$emit('toggle-pip')"
          class="control-btn"
          aria-label="画中画"
        >
          <Icon icon="material-symbols:picture-in-picture-alt" class="control-icon" />
        </button>

        <!-- 字幕按钮 -->
        <button
          @click="$emit('toggle-subtitles')"
          class="control-btn"
          :class="{ 'bg-white/20 ring-1 ring-white/30': playerState.media.subtitlesEnabled }"
          :aria-label="playerState.media.subtitlesEnabled ? '关闭字幕' : '开启字幕'"
        >
          <Icon icon="material-symbols:subtitles" class="control-icon" />
        </button>

        <!-- 设置菜单 -->
        <SettingsMenu
          v-if="!isTouchDevice"
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
          class="control-btn"
          aria-label="全屏"
        >
          <Icon :icon="fullscreenIcon" class="control-icon" />
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
  'toggle-pip',
  'set-quality',
  'set-playback-rate',
  'set-subtitle',
  'progress-seek'
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
}

const toggleSettingsMenu = () => {
  props.playerState.ui.showSettingsMenu = !props.playerState.ui.showSettingsMenu
  props.playerState.ui.showPlaybackRateMenu = false
}

const updateAutoplay = (value) => {
  props.playerState.media.autoplay = value
}

const updateLoop = (value) => {
  props.playerState.media.loop = value
}

// 进度条悬停处理
const handleProgressHoverStart = () => {
  props.playerState.ui.hoveringProgress = true
}

const handleProgressHoverEnd = () => {
  props.playerState.ui.hoveringProgress = false
}

const handleProgressHoverMove = ({ previewTime, position, hovering }) => {
  props.playerState.ui.previewTime = previewTime
  props.playerState.ui.hoverPosition = position
  props.playerState.ui.hoveringProgress = hovering
}
</script>

<style scoped>
.video-controls {
  @apply absolute bottom-0 left-0 right-0 px-4
    opacity-0 transition-all duration-200 z-20
    flex flex-col;
}

.controls-main {
  @apply flex items-center justify-between py-2;
}

.controls-left,
.controls-right {
  @apply flex items-center gap-2;
}

.control-btn {
  @apply p-2 rounded-lg bg-black/20 hover:bg-black/40 
    transition-colors duration-200 text-white
    focus:outline-none focus:ring-2 focus:ring-white/50;
}

.control-icon {
  @apply text-lg;
}

/* 控制栏可见状态 */
.video-controls.controls-visible {
  @apply opacity-100;
}
</style>
