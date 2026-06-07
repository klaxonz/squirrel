<template>
  <transition name="sp-ui-fade">
    <div v-if="visible" class="sp-settings-pop" ref="popupRef" data-player-interactive role="menu">
      <template v-if="view === 'main'">
        <div class="sp-menu-list">
          <div class="sp-menu-item" @click="$emit('toggleAutoplayNext')" role="menuitem">
            <span>{{ autoplayNextLabel }}</span>
            <div class="sp-simple-switch" :class="{ 'is-on': autoplayNext }" role="switch" :aria-checked="autoplayNext"></div>
          </div>
          <div class="sp-menu-item" @click="$emit('toggleLoop')" role="menuitem">
            <span>{{ loopLabel }}</span>
            <div class="sp-simple-switch" :class="{ 'is-on': loop }" role="switch" :aria-checked="loop"></div>
          </div>
          <div v-if="showSleepTimer" class="sp-menu-item" @click="$emit('navigate', 'sleepTimer')">
            <span>{{ sleepTimerLabel }}</span>
            <span class="sp-menu-val">{{ sleepTimerValue }}</span>
          </div>
          <div class="sp-menu-item" @click="$emit('screenshot')">
            <span>{{ screenshotLabel }}</span>
          </div>
          <div class="sp-menu-item" @click="$emit('navigate', 'speed')">
            <span>{{ speedLabel }}</span>
            <span class="sp-menu-val">{{ playbackRate }}x</span>
          </div>
          <div class="sp-menu-item" @click="$emit('navigate', 'rotation')">
            <span>{{ rotateLabel }}</span>
            <span class="sp-menu-val">{{ rotation }}°</span>
          </div>
          <div v-if="hasQuality" class="sp-menu-item" @click="$emit('navigate', 'quality')">
            <span>{{ qualityLabel }}</span>
            <span class="sp-menu-val">{{ qualityValue }}</span>
          </div>
          <div v-if="hasSubtitles" class="sp-menu-item" @click="$emit('navigate', 'subtitleStyle')">
            <span>{{ subtitleLabel }}</span>
            <span class="sp-menu-val">{{ subtitleValue }}</span>
          </div>
        </div>
      </template>

      <template v-else-if="view === 'speed'">
        <div class="sp-menu-item" style="opacity: 0.5" @click="$emit('navigate', 'main')">
          <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ speedLabel }}
        </div>
        <div class="sp-menu-list">
          <div v-for="rate in speeds" :key="rate"
               class="sp-menu-item" :class="{ 'is-active': playbackRate === rate }"
               @click="$emit('selectSpeed', rate)">
            {{ rate }}x
          </div>
        </div>
      </template>

      <template v-else-if="view === 'quality'">
        <div class="sp-menu-item" style="opacity: 0.5" @click="$emit('navigate', 'main')">
          <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ qualityLabel }}
        </div>
        <div class="sp-menu-list">
          <div v-for="q in qualities" :key="q.id"
               class="sp-menu-item" :class="{ 'is-active': q.active }"
               @click="$emit('selectQuality', q.id)">
            {{ q.label }}
          </div>
        </div>
      </template>

      <template v-else-if="view === 'rotation'">
        <div class="sp-menu-item" style="opacity: 0.5" @click="$emit('navigate', 'main')">
          <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ rotateLabel }}
        </div>
        <div class="sp-menu-list">
          <div v-for="rot in rotations" :key="rot"
               class="sp-menu-item" :class="{ 'is-active': rotation === rot }"
               @click="$emit('selectRotation', rot)">
            {{ rot }}°
          </div>
        </div>
      </template>

      <template v-else-if="view === 'subtitles'">
        <div class="sp-menu-item" style="opacity: 0.5" @click="$emit('navigate', 'main')">
          <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ subtitleLabel }}
        </div>
        <div class="sp-menu-list">
          <div class="sp-menu-item" :class="{ 'is-active': !subtitlesEnabled }" @click="$emit('disableSubtitles')">
            {{ subtitlesOffLabel }}
          </div>
          <div v-for="track in subtitleTracks" :key="track.id"
               class="sp-menu-item" :class="{ 'is-active': subtitlesEnabled && activeSubtitleId === track.id }"
               @click="$emit('selectSubtitle', track.id)">
            {{ track.label }}
          </div>
        </div>
      </template>

      <template v-else-if="view === 'subtitleStyle'">
        <div class="sp-menu-item" style="opacity: 0.5" @click="$emit('navigate', 'subtitles')">
          <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ subtitleLabel }}
        </div>
        <div class="sp-menu-list">
          <div class="sp-menu-item" @click="$emit('navigate', 'subtitlePreset')">
            <span>{{ presetLabel }}</span>
            <span class="sp-menu-val">{{ currentPresetLabel }}</span>
          </div>
          <div class="sp-menu-item" @click="$emit('navigate', 'subtitleFontSize')">
            <span>{{ fontSizeLabel }}</span>
            <span class="sp-menu-val">{{ fontSizeValue }}</span>
          </div>
          <div class="sp-menu-item" @click="$emit('navigate', 'subtitleColor')">
            <span>{{ fontColorLabel }}</span>
            <span class="sp-subtitle-color-preview" :style="{ background: subtitleColor }"></span>
          </div>
          <div class="sp-menu-item" @click="$emit('navigate', 'subtitleBg')">
            <span>{{ bgColorLabel }}</span>
            <span class="sp-subtitle-color-preview" :style="{ background: subtitleBg }"></span>
          </div>
          <div class="sp-menu-item" @click="$emit('navigate', 'subtitlePosition')">
            <span>{{ positionLabel }}</span>
            <span class="sp-menu-val">{{ positionValue }}</span>
          </div>
          <div class="sp-menu-item sp-menu-item--offset">
            <span>{{ offsetLabel }}</span>
            <div class="sp-offset-controls">
              <button class="sp-offset-btn" @click.stop="$emit('offsetChange', -0.5)">-0.5s</button>
              <span class="sp-offset-value">{{ subtitleOffset > 0 ? '+' : '' }}{{ subtitleOffset.toFixed(1) }}s</span>
              <button class="sp-offset-btn" @click.stop="$emit('offsetChange', 0.5)">+0.5s</button>
            </div>
          </div>
        </div>
      </template>

      <template v-else-if="view === 'subtitleFontSize'">
        <div class="sp-menu-item" style="opacity: 0.5" @click="$emit('navigate', 'subtitleStyle')">
          <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ fontSizeLabel }}
        </div>
        <div class="sp-menu-list">
          <div v-for="opt in fontSizeOptions" :key="opt.value"
               class="sp-menu-item" :class="{ 'is-active': currentFontSize === opt.value }"
               @click="$emit('changeSubtitleStyle', 'fontSize', opt.value)">
            {{ opt.label }}
          </div>
        </div>
      </template>

      <template v-else-if="view === 'subtitleColor'">
        <div class="sp-menu-item" style="opacity: 0.5" @click="$emit('navigate', 'subtitleStyle')">
          <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ fontColorLabel }}
        </div>
        <div class="sp-subtitle-color-grid">
          <div v-for="c in colorOptions" :key="c.value"
               class="sp-subtitle-color-swatch"
               :class="{ 'is-active': subtitleColor === c.value }"
               :style="{ background: c.value }" :title="c.label"
               @click="$emit('changeSubtitleStyle', 'color', c.value)"></div>
        </div>
      </template>

      <template v-else-if="view === 'subtitleBg'">
        <div class="sp-menu-item" style="opacity: 0.5" @click="$emit('navigate', 'subtitleStyle')">
          <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ bgColorLabel }}
        </div>
        <div class="sp-subtitle-color-grid">
          <div v-for="c in bgOptions" :key="c.value"
               class="sp-subtitle-color-swatch"
               :class="{ 'is-active': subtitleBg === c.value }"
               :style="{ background: c.value }" :title="c.label"
               @click="$emit('changeSubtitleStyle', 'backgroundColor', c.value)"></div>
        </div>
        <div class="sp-subtitle-opacity-row">
          <span class="sp-subtitle-opacity-label">{{ opacityLabel }}</span>
          <div class="sp-subtitle-opacity-slider">
            <div class="sp-opacity-rail" ref="opacityRailRef" @pointerdown="onOpacityPointerDown">
              <div class="sp-opacity-fill" :style="{ width: `${bgOpacity * 100}%` }"></div>
              <div class="sp-opacity-thumb" :style="{ left: `${bgOpacity * 100}%` }"></div>
            </div>
          </div>
          <span class="sp-subtitle-opacity-val">{{ Math.round(bgOpacity * 100) }}%</span>
        </div>
      </template>

      <template v-else-if="view === 'subtitlePreset'">
        <div class="sp-menu-item" style="opacity: 0.5" @click="$emit('navigate', 'subtitleStyle')">
          <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ presetLabel }}
        </div>
        <div class="sp-menu-list">
          <div v-for="preset in subtitlePresets" :key="preset.id"
               class="sp-menu-item" :class="{ 'is-active': activePresetId === preset.id }"
               @click="$emit('selectPreset', preset.id)">
            {{ preset.label }}
          </div>
        </div>
      </template>

      <template v-else-if="view === 'subtitlePosition'">
        <div class="sp-menu-item" style="opacity: 0.5" @click="$emit('navigate', 'subtitleStyle')">
          <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ positionLabel }}
        </div>
        <div class="sp-menu-list">
          <div class="sp-menu-item" :class="{ 'is-active': subtitlePosition === 'bottom' }"
               @click="$emit('changeSubtitleStyle', 'position', 'bottom')">
            {{ positionBottomLabel }}
          </div>
          <div class="sp-menu-item" :class="{ 'is-active': subtitlePosition === 'top' }"
               @click="$emit('changeSubtitleStyle', 'position', 'top')">
            {{ positionTopLabel }}
          </div>
        </div>
      </template>

      <template v-else-if="view === 'sleepTimer'">
        <div class="sp-menu-item" style="opacity: 0.5" @click="$emit('navigate', 'main')">
          <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ sleepTimerLabel }}
        </div>
        <div class="sp-menu-list">
          <div class="sp-menu-item" :class="{ 'is-active': activeSleepTimer === null }"
               @click="$emit('selectSleepTimer', null)">
            {{ sleepTimerOffLabel }}
          </div>
          <div v-for="mins in sleepTimerOptions" :key="mins"
               class="sp-menu-item" :class="{ 'is-active': activeSleepTimer === mins }"
               @click="$emit('selectSleepTimer', mins)">
            {{ sleepTimerMinsLabel(mins) }}
          </div>
        </div>
      </template>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import PlayerIcon from './PlayerIcon.vue'

interface QualityOption {
  id: string
  label: string
  active: boolean
}

interface SubtitleTrackOption {
  id: string
  label: string
}

interface PresetOption {
  id: string
  label: string
}

interface ColorOption {
  value: string
  label: string
}

interface FontSizeOption {
  value: string
  label: string
}

const props = defineProps<{
  visible: boolean
  view: string
  autoplayNext: boolean
  loop: boolean
  playbackRate: number
  rotation: number
  qualities: QualityOption[]
  hasQuality: boolean
  hasSubtitles: boolean
  subtitleTracks: SubtitleTrackOption[]
  subtitlesEnabled: boolean
  activeSubtitleId: string | null
  subtitleColor: string
  subtitleBg: string
  subtitlePosition: string
  subtitleOffset: number
  bgOpacity: number
  currentFontSize: string
  currentPresetLabel: string
  activePresetId: string | null
  subtitlePresets: PresetOption[]
  colorOptions: ColorOption[]
  bgOptions: ColorOption[]
  fontSizeOptions: FontSizeOption[]
  fontSizeValue: string
  qualityValue: string
  subtitleValue: string
  speeds: number[]
  rotations: number[]
  showSleepTimer: boolean
  activeSleepTimer: number | null
  sleepTimerOptions: number[]
  sleepTimerValue: string
  // i18n labels
  autoplayNextLabel: string
  loopLabel: string
  speedLabel: string
  rotateLabel: string
  qualityLabel: string
  subtitleLabel: string
  subtitlesOffLabel: string
  presetLabel: string
  fontSizeLabel: string
  fontColorLabel: string
  bgColorLabel: string
  positionLabel: string
  positionBottomLabel: string
  positionTopLabel: string
  opacityLabel: string
  offsetLabel: string
  sleepTimerLabel: string
  sleepTimerOffLabel: string
  screenshotLabel: string
  sleepTimerMinsLabel: (mins: number) => string
}>()

const emit = defineEmits<{
  navigate: [view: string]
  toggleAutoplayNext: []
  toggleLoop: []
  screenshot: []
  selectSpeed: [rate: number]
  selectRotation: [rot: number]
  selectQuality: [id: string]
  disableSubtitles: []
  selectSubtitle: [id: string]
  changeSubtitleStyle: [key: string, value: string]
  selectPreset: [id: string]
  offsetChange: [delta: number]
  selectSleepTimer: [mins: number | null]
  updateOpacity: [value: number]
}>()

const positionValue = computed(() => {
  return props.subtitlePosition === 'top' ? props.positionTopLabel : props.positionBottomLabel
})

const opacityRailRef = ref<HTMLElement | null>(null)

function onOpacityPointerDown(e: PointerEvent) {
  const rail = opacityRailRef.value
  if (!rail) return
  const rect = rail.getBoundingClientRect()
  const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
  emit('updateOpacity', pct)
}
</script>
