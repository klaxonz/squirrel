<template>
  <Transition
    name="video-controls" 
    appear
  >
    <div 
      v-show="playerState.ui.controlsVisible"
      ref="controlsRoot" 
      class="video-controls"
    >
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
            :has-prev="hasPrev"
            :has-next="hasNext"
            @toggle-play="$emit('toggle-play')"
            @skip-forward="$emit('skip-forward')"
            @skip-backward="$emit('skip-backward')"
            @prev-video="$emit('prev-video')"
            @next-video="$emit('next-video')"
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
          <Icon icon="material-symbols:picture-in-picture-alt" class="vp-control-icon"/>
        </button>

        <!-- CC 字幕按钮：单击切换，长按/右键打开字幕面板 -->
        <button
            @mousedown="onCcDown"
            @mouseup="onCcUp"
            @mouseleave="onCcCancel"
            @click="onCcClick"
            @contextmenu.prevent="openSubtitlesMenu"
            class="vp-control-btn cc-btn"
            :class="{ 'active-control': playerState.media.subtitlesEnabled }"
            aria-label="字幕"
        >
          <span class="cc-icon-wrap">
            <Icon icon="material-symbols:subtitles" class="vp-control-icon"/>
          </span>
        </button>

        <!-- 剧场模式按钮 -->
        <button
            @click="$emit('toggle-theater')"
            class="vp-control-btn"
            :class="{ 'active-control': playerState.ui.theaterMode }"
            aria-label="剧场模式"
        >
          <Icon icon="material-symbols:fit-screen" class="vp-control-icon"/>
        </button>

        <!-- 设置菜单 -->
        <SettingsMenu
            :show-menu="playerState.ui.showSettingsMenu"
            :initial-panel="settingsInitialPanel"
            :current-quality="playerState.media.currentQuality"
            :available-qualities="availableQualities"
            :current-subtitle="playerState.media.currentSubtitle"
            :subtitles="video.subtitles"
            :subtitle-settings="playerState.media.subtitleSettings"
            :autoplay="playerState.media.autoplay"
            :autoplay-next="playerState.media.autoplayNext"
            :loop="playerState.media.loop"
            :current-rate="playerState.media.playbackRate"
            :available-rates="playbackRates"
            @toggle-menu="toggleSettingsMenu"
            @set-quality="$emit('set-quality', $event)"
            @set-subtitle="$emit('set-subtitle', $event)"
            @set-playback-rate="$emit('set-playback-rate', $event)"
            @update-subtitle-font-size="v => props.playerState.media.subtitleSettings.fontSize = v"
            @update-subtitle-color="v => props.playerState.media.subtitleSettings.color = v"
            @update-subtitle-bg-opacity="v => props.playerState.media.subtitleSettings.bgOpacity = v"
            @update-subtitle-position="v => props.playerState.media.subtitleSettings.position = v"
            @update-subtitle-shadow="v => props.playerState.media.subtitleSettings.shadow = v"
            @update-autoplay="updateAutoplay"
            @update-autoplay-next="updateAutoplayNext"
            @update-loop="updateLoop"
        />

        <!-- 全屏按钮 -->
        <button
            @click="$emit('toggle-fullscreen')"
            class="vp-control-btn"
            aria-label="全屏"
        >
          <Icon :icon="fullscreenIcon" class="vp-control-icon"/>
        </button>
      </div>
    </div>
    </div>
  </Transition>
</template>

<script setup>
import {computed, ref, onMounted, onUnmounted} from 'vue'
import {Icon} from '@iconify/vue'
import ProgressBar from './ProgressBar.vue'
import PlaybackControls from './PlaybackControls.vue'
import VolumeControl from './VolumeControl.vue'
import TimeDisplay from './TimeDisplay.vue'
import SettingsMenu from './SettingsMenu.vue'
import QualitySelector from './QualitySelector.vue'

const props = defineProps({
  playerState: Object,
  video: Object,
  progress: Number,
  volumeIcon: String,
  fullscreenIcon: String,
  supportsPip: Boolean,
  availableQualities: Array,
  playbackRates: Array,
  hasPrev: { type: Boolean, default: false },
  hasNext: { type: Boolean, default: false }
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
  'seek-end',
  'prev-video',
  'next-video'
])

const isTouchDevice = computed(() =>
    typeof window !== 'undefined' && ('ontouchstart' in window || navigator.maxTouchPoints > 0)
)

const handleVolumeChange = (volume) => {
  props.playerState.media.volume = volume
}

const settingsInitialPanel = ref('main')
const controlsRoot = ref(null)

const toggleQualityMenu = () => {
  props.playerState.ui.showQualityMenu = !props.playerState.ui.showQualityMenu
  props.playerState.ui.showSettingsMenu = false
  props.playerState.ui.showPlaybackRateMenu = false
}

const toggleSettingsMenu = () => {
  settingsInitialPanel.value = 'main'
  props.playerState.ui.showSettingsMenu = !props.playerState.ui.showSettingsMenu
  props.playerState.ui.showPlaybackRateMenu = false
  props.playerState.ui.showQualityMenu = false
}

let ccHoldTimer = null
let ccHeld = false
const openSubtitlesMenu = () => {
  settingsInitialPanel.value = 'subtitles'
  props.playerState.ui.showSettingsMenu = true
  props.playerState.ui.showPlaybackRateMenu = false
  props.playerState.ui.showQualityMenu = false
}
const onCcDown = () => {
  ccHeld = false
  if (ccHoldTimer) clearTimeout(ccHoldTimer)
  ccHoldTimer = setTimeout(() => {
    ccHeld = true
    openSubtitlesMenu()
  }, 600)
}
const onCcUp = () => {
  if (ccHoldTimer) {
    clearTimeout(ccHoldTimer)
    ccHoldTimer = null
  }
}
const onCcCancel = () => {
  if (ccHoldTimer) clearTimeout(ccHoldTimer)
  ccHoldTimer = null
}
const onCcClick = () => {
  if (ccHeld) {
    ccHeld = false;
    return
  }
  emit('toggle-subtitles')
}

const onWindowClick = (evt) => {
  const root = controlsRoot.value
  if (!root) return
  const target = evt?.target
  if (target && !root.contains(target)) {
    props.playerState.ui.showSettingsMenu = false
    props.playerState.ui.showPlaybackRateMenu = false
    props.playerState.ui.showQualityMenu = false
  }
}

onMounted(() => {
  try { window.addEventListener('click', onWindowClick, { passive: true }) } catch (_) {}
})

onUnmounted(() => {
  try { window.removeEventListener('click', onWindowClick) } catch (_) {}
})


const updateAutoplay = (value) => {
  props.playerState.media.autoplay = value
}

const updateAutoplayNext = (value) => {
  props.playerState.media.autoplayNext = value
}

const updateLoop = (value) => {
  props.playerState.media.loop = value
}

</script>

<style scoped>
.video-controls {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 20;
  display: flex;
  flex-direction: column;
  background: none;
  padding: 24px 0.75rem 8px;
}

.controls-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 0.25rem;
  padding-bottom: 0.25rem;
  height: 40px;
}

.controls-left, .controls-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.vp-control-btn {
  padding: 0.5rem;
  border-radius: 9999px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  min-height: 40px;
  transition: all 160ms ease;
}

.vp-control-btn:hover {
  background-color: rgba(255, 255, 255, 0.24);
  transform: scale(1.04);
}

.vp-control-btn:active {
  transform: scale(0.98);
}

.vp-control-btn.active-control {
  background-color: transparent;
  border: none;
}

.vp-control-btn:focus { outline: none; box-shadow: none; }

.vp-control-btn.active-control:hover {
  background-color: rgba(255, 255, 255, 0.14);
}

.vp-control-icon {
  font-size: 1.25rem;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
}

/* Vue Transition 动画类 - 阻尼效果 */
.video-controls-enter-active {
  transition: all 450ms cubic-bezier(0.16, 1, 0.3, 1);
}

.video-controls-leave-active {
  transition: all 320ms cubic-bezier(0.7, 0, 0.84, 0);
}

.video-controls-enter-from {
  opacity: 0;
  transform: translateY(100%);
}

.video-controls-leave-to {
  opacity: 0;
  transform: translateY(100%);
}

.video-controls-enter-to,
.video-controls-leave-from {
  opacity: 1;
  transform: translateY(0);
}

.video-controls::before { display: none; }

.cc-icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
}

.cc-btn::after {
  left: 50%;
  transform: translateX(-50%);
}

.cc-btn.active-control::after {
  width: 18px;
  bottom: 7px;
}

.video-player-container:fullscreen .video-controls,
.video-player-container:-webkit-full-screen .video-controls,
.video-player-container:-moz-full-screen .video-controls {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 2147483647;
  width: 100%;
}

.video-player-container:fullscreen .video-controls .controls-main,
.video-player-container:-webkit-full-screen .video-controls .controls-main,
.video-player-container:-moz-full-screen .video-controls .controls-main {
  z-index: 2147483647;
}

.cc-btn {
  position: relative;
}

.cc-btn::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 6px;
  transform: translateX(-50%);
  width: 0;
  height: 3px;
  background: transparent;
  border-radius: 2px;
  transition: width 160ms ease, background-color 160ms ease, opacity 160ms ease;
}

.cc-btn.active-control::after {
  width: 20px;
  background: #cc0000;
}

</style>
