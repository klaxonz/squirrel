<template>
  <transition name="sp-ui-fade">
    <div v-if="visible || qualityMenuVisible" class="sp-settings-pop" ref="popupRef" data-player-interactive role="menu">
      <template v-if="qualityMenuVisible">
        <div class="sp-menu-item" style="opacity: 0.5" @click="$emit('navigate', 'main')">
          <PlayerIcon name="chevronLeft" style="width: 14px" /> {{ qualityMenuLabel }}
        </div>
        <div class="sp-menu-list">
          <div
            v-for="q in qualities"
            :key="q.id"
            class="sp-menu-item"
            :class="{ 'is-active': q.active }"
            @click="$emit('selectQuality', q)"
            role="menuitemradio"
            :aria-checked="q.active"
          >
            {{ q.label }}
          </div>
        </div>
      </template>

      <template v-else-if="view === 'main'">
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
               @click="$emit('selectSubtitle', track)">
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
              <Button text severity="secondary" size="sm" class="sp-offset-btn" @click.stop="$emit('offsetChange', -0.5)">-0.5s</Button>
              <span class="sp-offset-value">{{ subtitleOffset > 0 ? '+' : '' }}{{ subtitleOffset.toFixed(1) }}s</span>
              <Button text severity="secondary" size="sm" class="sp-offset-btn" @click.stop="$emit('offsetChange', 0.5)">+0.5s</Button>
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
import type { SubtitleTrack } from './core'
import { Button } from '@/shared/ui/button'

interface QualityOption {
  id: string | number
  label: string
  active: boolean
}

// ponytail: alias so the prop list reads as a plain option shape; the runtime
// value is a full SubtitleTrack, which the parent needs back on select.
type SubtitleTrackOption = SubtitleTrack

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
  qualityMenuVisible: boolean
  view: string
  autoplayNext: boolean
  loop: boolean
  playbackRate: number
  rotation: number
  qualities: QualityOption[]
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
  subtitleValue: string
  qualityMenuLabel: string
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
  selectQuality: [option: QualityOption]
  disableSubtitles: []
  selectSubtitle: [track: SubtitleTrackOption]
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

// ponytail: drag the opacity thumb by listening on window while the pointer is
// held. Matches the inline VideoPlayer behaviour (press + drag updates the
// value); a press-only emit would lose the drag. Listeners are added on
// pointerdown and removed on pointerup.
function computeOpacityFromEvent(rail: HTMLElement, clientX: number): number {
  const rect = rail.getBoundingClientRect()
  return Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
}

const popupRef = ref<HTMLElement | null>(null)

function onOpacityPointerDown(e: PointerEvent) {
  const rail = opacityRailRef.value
  if (!rail) return
  emit('updateOpacity', computeOpacityFromEvent(rail, e.clientX))

  if (typeof rail.setPointerCapture === 'function') {
    try {
      rail.setPointerCapture(e.pointerId)
    } catch {
      // Capture may be unsupported for this pointer.
    }
  }

  const onMove = (ev: PointerEvent) => {
    if (opacityRailRef.value) {
      emit('updateOpacity', computeOpacityFromEvent(opacityRailRef.value, ev.clientX))
    }
  }
  const onUp = () => {
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
    window.removeEventListener('pointercancel', onUp)
  }
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
  window.addEventListener('pointercancel', onUp)
}
</script>

<style scoped>
.sp-settings-pop {
  position: absolute;
  right: 12px;
  bottom: 56px;
  width: min(236px, calc(100% - 24px));
  max-height: calc(100% - 72px);
  background: var(--sp-menu-bg);
  border: 1px solid var(--sp-menu-border);
  border-radius: 10px;
  padding: 6px;
  z-index: 100;
  box-shadow: var(--sp-menu-shadow);
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-color: rgb(255 255 255 / 0.18) transparent;
  scrollbar-width: thin;
}

.sp-settings-pop::-webkit-scrollbar {
  width: 5px;
}

.sp-settings-pop::-webkit-scrollbar-track {
  background: transparent;
}

.sp-settings-pop::-webkit-scrollbar-thumb {
  border-radius: var(--sp-radius-full);
  background: rgb(255 255 255 / 0.18);
}

.sp-menu-list {
  display: block;
}

.sp-menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 2.5rem;
  padding: 8px 12px;
  color: var(--sp-text-secondary);
  font-size: 12px;
  font-family: var(--sp-font-family);
  border-radius: 6px;
  cursor: pointer;
  transition:
    color var(--duration-normal) var(--ease-default),
    background-color var(--duration-normal) var(--ease-default),
    transform var(--duration-normal) var(--ease-default);
  position: relative;
  z-index: 1;
  letter-spacing: 0;
}

.sp-menu-item:hover {
  background: var(--sp-menu-item-hover-bg);
  color: var(--sp-text-strong);
}

.sp-settings-pop > .sp-menu-item:first-child {
  justify-content: flex-start;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
  border-bottom: 1px solid var(--sp-menu-border);
  border-radius: 6px 6px 2px 2px;
  color: var(--sp-text-strong);
  font-weight: 650;
  opacity: 1 !important;
}

.sp-menu-item.is-active {
  color: var(--sp-primary);
  background: var(--sp-menu-item-active-bg);
}

.sp-menu-val {
  font-size: 11px;
  opacity: 0.6;
  font-family: var(--sp-font-mono);
}

.sp-simple-switch {
  width: 32px;
  height: 18px;
  background: var(--sp-switch-bg);
  border: 1px solid var(--sp-border);
  border-radius: 999px;
  position: relative;
  transition: background var(--duration-normal) var(--ease-default);
}

.sp-simple-switch.is-on {
  background: var(--sp-primary);
  border-color: rgba(var(--sp-primary-rgb), 0.5);
}

.sp-simple-switch::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 12px;
  height: 12px;
  background: #fff;
  border-radius: 50%;
  transition: transform var(--duration-normal) var(--ease-default);
}

.sp-simple-switch.is-on::after {
  transform: translateX(14px);
}

.sp-subtitle-color-preview {
  width: 14px;
  height: 14px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 3px;
  flex-shrink: 0;
}

.sp-subtitle-color-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 6px;
  padding: 8px 14px;
}

.sp-subtitle-color-swatch {
  width: 24px;
  height: 24px;
  margin: 0 auto;
  border: 2px solid transparent;
  border-radius: 4px;
  cursor: pointer;
  transition:
    transform var(--duration-normal) var(--ease-default),
    border-color var(--duration-normal) var(--ease-default),
    box-shadow var(--duration-normal) var(--ease-default);
}

.sp-subtitle-color-swatch:hover {
  transform: scale(1.15);
  border-color: rgba(255, 255, 255, 0.5);
}

.sp-subtitle-color-swatch.is-active {
  border-color: var(--sp-primary);
}

.sp-subtitle-opacity-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
}

.sp-subtitle-opacity-label {
  width: 52px;
  color: var(--sp-text-secondary);
  font-size: 12px;
  flex-shrink: 0;
}

.sp-subtitle-opacity-slider {
  flex: 1;
}

.sp-opacity-rail {
  position: relative;
  height: 3px;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 1.5px;
  cursor: pointer;
}

.sp-opacity-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: var(--sp-primary);
  border-radius: 1.5px;
}

.sp-opacity-thumb {
  position: absolute;
  top: 50%;
  width: 12px;
  height: 12px;
  background: #fff;
  border-radius: 50%;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
  cursor: grab;
  transform: translate(-50%, -50%);
}

.sp-opacity-thumb:active {
  cursor: grabbing;
  transform: translate(-50%, -50%) scale(1.2);
}

.sp-subtitle-opacity-val {
  width: 32px;
  color: var(--sp-text-secondary);
  font-size: 11px;
  font-family: var(--sp-font-mono);
  text-align: right;
  flex-shrink: 0;
}

.sp-offset-controls {
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: var(--sp-font-mono);
}

.sp-offset-btn {
  padding: 2px 6px;
  background: var(--sp-bg-hover);
  border: 1px solid var(--sp-border);
  border-radius: 3px;
  color: var(--sp-text-secondary);
  font-size: 11px;
  font-family: var(--sp-font-mono);
  cursor: pointer;
  transition:
    color var(--duration-normal) var(--ease-default),
    border-color var(--duration-normal) var(--ease-default),
    background-color var(--duration-normal) var(--ease-default);
}

.sp-offset-btn:hover {
  color: var(--sp-primary);
  border-color: var(--sp-primary);
}

.sp-offset-value {
  min-width: 36px;
  color: var(--sp-text-strong);
  font-size: 11px;
  text-align: center;
}

.sp-ui-fade-enter-active,
.sp-ui-fade-leave-active {
  transition:
    opacity var(--duration-slow) var(--ease-out),
    transform var(--duration-slow) var(--ease-out);
}

.sp-ui-fade-enter-from,
.sp-ui-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
