<template>
  <transition name="sp-hud-fade">
    <div
      v-if="hud.visible"
      class="sp-central-hud"
      :class="{ 'sp-central-hud--shifted': shifted }"
    >
      <!-- Volume: horizontal capsule bar (icon -> track+thumb -> percent) -->
      <template v-if="hud.type === 'volume'">
        <div class="sp-vol-capsule">
          <div class="sp-vol-icon-wrap">
            <PlayerIcon :name="hud.icon" class="sp-vol-icon" />
          </div>
          <div class="sp-vol-track">
            <div class="sp-vol-fill" :style="{ width: `${volumeRatio * 100}%` }"></div>
            <div class="sp-vol-thumb" :style="{ left: `${volumeRatio * 100}%` }"></div>
          </div>
          <div class="sp-vol-percent">{{ hud.value }}</div>
        </div>
      </template>

      <!-- Generic notice: badge + text -->
      <template v-else>
        <div class="sp-notice-badge">
          <PlayerIcon :name="hud.icon" class="sp-notice-icon" />
        </div>
        <div class="sp-notice-text">{{ hud.value }}</div>
      </template>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PlayerIcon from './PlayerIcon.vue'
import type { CentralHudState } from './composables/useCentralHud'

const props = defineProps<{
  hud: CentralHudState
  /** When the loading/buffering overlay is up, nudge the HUD upward so they don't stack. */
  shifted?: boolean
}>()

const volumeRatio = computed(() => Math.min(1, Math.max(0, (props.hud.percent ?? 0) / 100)))
</script>

<style scoped>
.sp-central-hud {
  position: absolute;
  top: 50%;
  left: 50%;
  z-index: 100;
  display: flex;
  pointer-events: none;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  transform: translate(-50%, -50%);
  transition: transform var(--duration-slow) var(--ease-default);
}

.sp-central-hud--shifted {
  transform: translate(-50%, -240%);
}

.sp-vol-capsule {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 16px;
  border: 1px solid var(--sp-menu-border);
  border-radius: var(--sp-radius-lg);
  background: var(--sp-menu-bg);
  box-shadow: var(--sp-menu-shadow);
}

.sp-vol-icon-wrap {
  display: flex;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
}

.sp-vol-icon {
  width: 22px;
  height: 22px;
  color: #fff;
  filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.5));
}

.sp-vol-track {
  position: relative;
  width: 160px;
  height: 6px;
  flex-shrink: 0;
  overflow: visible;
  border-radius: var(--sp-radius-full);
  background: rgba(255, 255, 255, 0.15);
}

.sp-vol-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  border-radius: var(--sp-radius-full);
  background: var(--sp-primary);
  transition: width var(--duration-normal) var(--ease-default);
}

.sp-vol-thumb {
  position: absolute;
  top: 50%;
  width: 14px;
  height: 14px;
  border-radius: var(--sp-radius-full);
  background: #fff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
  transform: translate(-50%, -50%);
  transition: left var(--duration-normal) var(--ease-default);
}

.sp-vol-percent {
  min-width: 40px;
  flex-shrink: 0;
  color: #fff;
  font-family: var(--sp-font-mono);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0;
  text-align: right;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.6);
}

.sp-notice-badge {
  display: flex;
  width: 56px;
  height: 56px;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--sp-menu-border);
  border-radius: var(--sp-radius-full);
  background: var(--sp-menu-bg);
  box-shadow: var(--sp-menu-shadow);
}

.sp-notice-icon {
  width: 24px;
  height: 24px;
  color: #fff;
}

.sp-notice-text {
  padding: 3px 14px;
  border: 1px solid var(--sp-menu-border);
  border-radius: var(--sp-radius-full);
  background: var(--sp-menu-bg);
  box-shadow: var(--sp-menu-shadow);
  color: #fff;
  font-family: var(--sp-font-mono);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.6);
}

.sp-hud-fade-enter-active,
.sp-hud-fade-leave-active {
  transition: opacity var(--duration-normal) var(--ease-default);
}

.sp-hud-fade-enter-from,
.sp-hud-fade-leave-to {
  opacity: 0;
}

@container video-player (max-width: 560px) {
  .sp-vol-capsule {
    gap: 10px;
    padding: 8px 12px;
  }

  .sp-vol-track {
    width: 112px;
  }
}
</style>
