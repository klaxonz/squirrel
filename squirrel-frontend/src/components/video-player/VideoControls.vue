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

        <!-- 字幕按钮 + 弹出菜单 -->
        <div class="vp-subtitles-control">
          <button
            @click.stop="toggleSubtitlesMenu"
            class="vp-control-btn"
            :class="{ 'active-control': playerState.media.subtitlesEnabled }"
            :aria-label="playerState.media.subtitlesEnabled ? '字幕设置' : '字幕设置'"
          >
            <Icon icon="material-symbols:subtitles" class="vp-control-icon" />
          </button>

          <div v-if="playerState.ui.showSubtitlesMenu" class="subtitle-menu" @click.stop>
            <div class="settings-section">
              <div class="settings-title">字幕</div>
              <div class="subtitle-options">
                <button @click="$emit('set-subtitle', null)" class="subtitle-option" :class="{ active: !playerState.media.currentSubtitle }">关闭</button>
                <button
                  v-for="subtitle in video.subtitles"
                  :key="subtitle.id"
                  @click="$emit('set-subtitle', subtitle)"
                  class="subtitle-option"
                  :class="{ active: playerState.media.currentSubtitle?.id === subtitle.id }"
                >{{ subtitle.language }}</button>
              </div>
            </div>

            <div class="settings-section">
              <div class="settings-title">样式</div>
              <div class="setting-item-row">
                <span class="setting-label">字号</span>
                <div class="btn-group">
                  <button class="btn-chip" :class="{ active: playerState.media.subtitleSettings.fontSize==='small' }" @click="props.playerState.media.subtitleSettings.fontSize='small'">小</button>
                  <button class="btn-chip" :class="{ active: playerState.media.subtitleSettings.fontSize==='medium' }" @click="props.playerState.media.subtitleSettings.fontSize='medium'">中</button>
                  <button class="btn-chip" :class="{ active: playerState.media.subtitleSettings.fontSize==='large' }" @click="props.playerState.media.subtitleSettings.fontSize='large'">大</button>
                  <button class="btn-chip" :class="{ active: playerState.media.subtitleSettings.fontSize==='xlarge' }" @click="props.playerState.media.subtitleSettings.fontSize='xlarge'">特大</button>
                </div>
              </div>
              <div class="setting-item-row">
                <span class="setting-label">颜色</span>
                <div class="btn-group">
                  <button class="btn-chip" :class="{ active: props.playerState.media.subtitleSettings.color==='white' }" @click="props.playerState.media.subtitleSettings.color='white'">白色</button>
                  <button class="btn-chip" :class="{ active: props.playerState.media.subtitleSettings.color==='yellow' }" @click="props.playerState.media.subtitleSettings.color='yellow'">黄色</button>
                </div>
              </div>
              <div class="setting-item-row">
                <span class="setting-label">背景</span>
                <input class="range" type="range" min="0" max="1" step="0.1" :value="props.playerState.media.subtitleSettings.bgOpacity" @input="e => props.playerState.media.subtitleSettings.bgOpacity = Number(e.target.value)" />
              </div>
              <div class="setting-item-row">
                <span class="setting-label">位置</span>
                <div class="btn-group">
                  <button class="btn-chip" :class="{ active: props.playerState.media.subtitleSettings.position==='bottom' }" @click="props.playerState.media.subtitleSettings.position='bottom'">底部</button>
                  <button class="btn-chip" :class="{ active: props.playerState.media.subtitleSettings.position==='top' }" @click="props.playerState.media.subtitleSettings.position='top'">顶部</button>
                </div>
              </div>
              <div class="setting-item-row">
                <label class="setting-label">
                  <input type="checkbox" :checked="props.playerState.media.subtitleSettings.shadow" @change="e => props.playerState.media.subtitleSettings.shadow = e.target.checked" class="setting-checkbox" />
                  阴影
                </label>
              </div>
            </div>
          </div>
        </div>

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
          :subtitle-settings="playerState.media.subtitleSettings"
          :autoplay="playerState.media.autoplay"
          :loop="playerState.media.loop"
          @toggle-menu="toggleSettingsMenu"
          @set-quality="$emit('set-quality', $event)"
          @set-subtitle="$emit('set-subtitle', $event)"
          @update-subtitle-font-size="v => props.playerState.media.subtitleSettings.fontSize = v"
          @update-subtitle-color="v => props.playerState.media.subtitleSettings.color = v"
          @update-subtitle-bg-opacity="v => props.playerState.media.subtitleSettings.bgOpacity = v"
          @update-subtitle-position="v => props.playerState.media.subtitleSettings.position = v"
          @update-subtitle-shadow="v => props.playerState.media.subtitleSettings.shadow = v"
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
  props.playerState.ui.showSubtitlesMenu = false
  props.playerState.ui.showPlaybackRateMenu = false
  props.playerState.ui.showQualityMenu = false
}

const toggleSubtitlesMenu = () => {
  props.playerState.ui.showSubtitlesMenu = !props.playerState.ui.showSubtitlesMenu
  props.playerState.ui.showSettingsMenu = false
  props.playerState.ui.showPlaybackRateMenu = false
  props.playerState.ui.showQualityMenu = false
}

// 点击空白处关闭字幕菜单
if (typeof window !== 'undefined') {
  window.addEventListener('click', () => {
    props.playerState.ui.showSubtitlesMenu = false
  })
}

const updateAutoplay = (value) => {
  props.playerState.media.autoplay = value
}

const updateLoop = (value) => {
  props.playerState.media.loop = value
}


</script>

<style scoped>
.video-controls { position: absolute; left: 0; right: 0; bottom: 0; padding-left: 0.75rem; padding-right: 0.75rem; opacity: 0; z-index: 20; display: flex; flex-direction: column; background: linear-gradient(to top, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0.4) 50%, transparent 100%); padding-bottom: 8px; padding-top: 24px; transition: all var(--yt-transition-medium) ease; }
.controls-main { display: flex; align-items: center; justify-content: space-between; padding-top: 0.25rem; padding-bottom: 0.25rem; height: 40px; }
.controls-left, .controls-right { display: flex; align-items: center; gap: 8px; }
.vp-control-btn { padding: 0.5rem; border-radius: 9999px; color: #fff; display: flex; align-items: center; justify-content: center; background-color: var(--vp-bg-control); min-width: 40px; min-height: 40px; transition: all var(--vp-transition-normal); }
.vp-control-btn:hover { background-color: var(--vp-bg-control-hover); transform: scale(1.04); }
.vp-control-btn:active { transform: scale(0.98); }
.vp-control-btn.active-control { background-color: transparent; border: none; }
.vp-control-btn.active-control:hover { background-color: var(--vp-bg-control-hover); }
.vp-control-icon { font-size: 1.25rem; filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3)); }
.video-controls.controls-visible { opacity: 1; }
.video-controls::before { content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 120px; background: linear-gradient(to top, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0.6) 30%, rgba(0,0,0,0.3) 60%, transparent 100%); pointer-events: none; z-index: -1; transition: opacity var(--yt-transition-medium) ease; }
.video-controls.controls-visible::before { opacity: 1; }
.video-player-container:fullscreen .video-controls,
.video-player-container:-webkit-full-screen .video-controls,
.video-player-container:-moz-full-screen .video-controls { position: fixed; bottom: 0; left: 0; right: 0; z-index: 2147483647; width: 100%; }
.video-player-container:fullscreen .video-controls .progress-container,
.video-player-container:-webkit-full-screen .video-controls .progress-container,
.video-player-container:-moz-full-screen .video-controls .progress-container { z-index: 2147483647; }
.video-player-container:fullscreen .video-controls .controls-main,
.video-player-container:-webkit-full-screen .video-controls .controls-main,
.video-player-container:-moz-full-screen .video-controls .controls-main { z-index: 2147483647; }

/* 字幕弹出菜单样式 */
.vp-subtitles-control { position: relative; }
.subtitle-menu { position: absolute; bottom: 100%; right: 0; margin-bottom: 0.5rem; width: 16rem; border-radius: 0.75rem; padding: 0.5rem; border: 1px solid rgba(255,255,255,.1); background: rgba(40,40,40,.95); backdrop-filter: blur(12px); box-shadow: 0 8px 32px rgba(0,0,0,.6); z-index: 60; }
.settings-section { padding: 0.25rem 0; border-bottom: 1px solid rgba(255,255,255,.08); }
.settings-section:last-child { border-bottom: none; }
.settings-title { color: #fff; font-weight: 500; font-size: 12px; margin-bottom: 0.5rem; }
.subtitle-options { display: grid; gap: 6px; }
.subtitle-option { width: 100%; text-align: left; padding: 6px 8px; border-radius: 8px; color: #eaeaea; background: transparent; border: none; cursor: pointer; }
.subtitle-option.active, .subtitle-option:hover { background: rgba(255,255,255,.08); }
.setting-item-row { margin: 6px 0; display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.setting-label { color: #eaeaea; font-size: 12px; display: flex; align-items: center; gap: 8px; }
.btn-group { display: flex; gap: 6px; }
.btn-chip { padding: 4px 8px; border-radius: 9999px; border: 1px solid rgba(255,255,255,.14); background: transparent; color: #eaeaea; font-size: 12px; cursor: pointer; }
.btn-chip.active, .btn-chip:hover { background: rgba(255,255,255,.08); }
.range { width: 100%; }
</style>
