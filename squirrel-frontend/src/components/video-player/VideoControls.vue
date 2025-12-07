<template>
  <Transition name="video-controls" appear>
    <div 
      v-show="store.controlsVisible"
      ref="controlsRoot" 
      class="video-controls"
    >
      <!-- 进度条容器 -->
      <ProgressBar
        :progress="progress"
        :buffered-progress="store.bufferedProgress"
        :duration="store.duration"
        :current-time="store.currentTime"
        :chapters="video.chapters"
        @seek-start="$emit('seek-start')"
        @seek="$emit('progress-seek', $event)"
        @seek-end="$emit('seek-end')"
      />

      <!-- 主控制栏 -->
      <div class="controls-main">
        <div class="controls-left">
          <PlaybackControls
            :playing="store.playing"
            :has-prev="hasPrev"
            :has-next="hasNext"
            @toggle-play="$emit('toggle-play')"
            @skip-forward="$emit('skip-forward')"
            @skip-backward="$emit('skip-backward')"
            @prev-video="$emit('prev-video')"
            @next-video="$emit('next-video')"
          />

          <VolumeControl
            :volume="store.volume"
            :muted="store.muted"
            :volume-icon="volumeIcon"
            @toggle-mute="$emit('toggle-mute')"
            @volume-change="handleVolumeChange"
          />

          <TimeDisplay
            :current-time="store.currentTime"
            :duration="store.duration"
          />
        </div>

        <div class="controls-right">
          <QualitySelector
            v-if="!isTouchDevice && availableQualities.length > 1"
            :current-quality="store.currentQuality"
            :available-qualities="availableQualities"
            :show-menu="store.showQualityMenu"
            @toggle-menu="toggleQualityMenu"
            @set-quality="$emit('set-quality', $event)"
          />

          <button
            v-if="supportsPip"
            @click="$emit('toggle-pip')"
            class="vp-control-btn"
            :class="{ 'active-control': store.pictureInPicture }"
            aria-label="画中画"
          >
            <Icon icon="material-symbols:picture-in-picture-alt" class="vp-control-icon"/>
          </button>

          <button
            @mousedown="onCcDown"
            @mouseup="onCcUp"
            @mouseleave="onCcCancel"
            @click="onCcClick"
            @contextmenu.prevent="openSubtitlesMenu"
            class="vp-control-btn cc-btn"
            :class="{ 'active-control': store.subtitlesEnabled }"
            aria-label="字幕"
          >
            <span class="cc-icon-wrap">
              <Icon icon="material-symbols:subtitles" class="vp-control-icon"/>
            </span>
          </button>

          <button
            @click="$emit('toggle-theater')"
            class="vp-control-btn"
            :class="{ 'active-control': store.theaterMode }"
            aria-label="剧场模式"
          >
            <Icon icon="material-symbols:fit-screen" class="vp-control-icon"/>
          </button>

          <SettingsMenu
            :show-menu="store.showSettingsMenu"
            :initial-panel="settingsInitialPanel"
            :current-quality="store.currentQuality"
            :available-qualities="availableQualities"
            :current-subtitle="store.currentSubtitle"
            :subtitles="video.subtitles"
            :subtitle-settings="store.subtitleSettings"
            :autoplay="store.autoplay"
            :autoplay-next="store.autoplayNext"
            :loop="store.loop"
            :current-rate="store.playbackRate"
            :available-rates="playbackRates"
            @toggle-menu="toggleSettingsMenu"
            @set-quality="$emit('set-quality', $event)"
            @set-subtitle="$emit('set-subtitle', $event)"
            @set-playback-rate="$emit('set-playback-rate', $event)"
            @update-subtitle-font-size="v => store.updateSubtitleSettings({ fontSize: v })"
            @update-subtitle-color="v => store.updateSubtitleSettings({ color: v })"
            @update-subtitle-bg-opacity="v => store.updateSubtitleSettings({ bgOpacity: v })"
            @update-subtitle-position="v => store.updateSubtitleSettings({ position: v })"
            @update-subtitle-shadow="v => store.updateSubtitleSettings({ shadow: v })"
            @update-autoplay="v => store.setAutoplay(v)"
            @update-autoplay-next="v => store.setAutoplayNext(v)"
            @update-loop="v => store.setLoop(v)"
          />

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
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { Icon } from '@iconify/vue'
import { usePlayerStore } from '../../stores/playerStore'
import ProgressBar from './ProgressBar.vue'
import PlaybackControls from './PlaybackControls.vue'
import VolumeControl from './VolumeControl.vue'
import TimeDisplay from './TimeDisplay.vue'
import SettingsMenu from './SettingsMenu.vue'
import QualitySelector from './QualitySelector.vue'

const props = defineProps({
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

const store = usePlayerStore()

const isTouchDevice = computed(() =>
  typeof window !== 'undefined' && ('ontouchstart' in window || navigator.maxTouchPoints > 0)
)

const handleVolumeChange = (volume) => {
  store.setVolume(volume)
}

const settingsInitialPanel = ref('main')
const controlsRoot = ref(null)

const toggleQualityMenu = () => {
  store.showQualityMenu = !store.showQualityMenu
  store.showSettingsMenu = false
  store.showPlaybackRateMenu = false
}

const toggleSettingsMenu = () => {
  settingsInitialPanel.value = 'main'
  store.showSettingsMenu = !store.showSettingsMenu
  store.showPlaybackRateMenu = false
  store.showQualityMenu = false
}

let ccHoldTimer = null
let ccHeld = false

const openSubtitlesMenu = () => {
  settingsInitialPanel.value = 'subtitles'
  store.showSettingsMenu = true
  store.showPlaybackRateMenu = false
  store.showQualityMenu = false
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
  if (ccHoldTimer) { clearTimeout(ccHoldTimer); ccHoldTimer = null }
}

const onCcCancel = () => {
  if (ccHoldTimer) clearTimeout(ccHoldTimer)
  ccHoldTimer = null
}

const onCcClick = () => {
  if (ccHeld) { ccHeld = false; return }
  emit('toggle-subtitles')
}

const onWindowClick = (evt) => {
  const root = controlsRoot.value
  if (!root) return
  const target = evt?.target
  if (target && !root.contains(target)) {
    store.showSettingsMenu = false
    store.showPlaybackRateMenu = false
    store.showQualityMenu = false
  }
}

onMounted(() => {
  try { window.addEventListener('click', onWindowClick, { passive: true }) } catch (_) {}
})

onUnmounted(() => {
  try { window.removeEventListener('click', onWindowClick) } catch (_) {}
})
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

.vp-control-btn:active { transform: scale(0.98); }

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

.video-controls-enter-active { transition: all 450ms cubic-bezier(0.16, 1, 0.3, 1); }
.video-controls-leave-active { transition: all 320ms cubic-bezier(0.7, 0, 0.84, 0); }
.video-controls-enter-from { opacity: 0; transform: translateY(100%); }
.video-controls-leave-to { opacity: 0; transform: translateY(100%); }
.video-controls-enter-to, .video-controls-leave-from { opacity: 1; transform: translateY(0); }

.video-controls::before { display: none; }

.cc-icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
}

.cc-btn::after { left: 50%; transform: translateX(-50%); }
.cc-btn.active-control::after { width: 18px; bottom: 7px; }

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

.cc-btn { position: relative; }

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
