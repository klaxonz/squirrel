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
            <PlayerIcon :name="hud.icon as any" class="sp-vol-icon" />
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
          <PlayerIcon :name="hud.icon as any" class="sp-notice-icon" />
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
