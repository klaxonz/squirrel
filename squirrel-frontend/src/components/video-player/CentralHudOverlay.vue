<template>
  <transition name="sp-hud-fade">
    <div v-if="hud.visible" class="sp-central-hud">
      <div class="sp-central-hud-content">
        <PlayerIcon :name="hud.icon as any" class="sp-central-hud-icon" />
        <div class="sp-central-hud-value">{{ hud.value }}</div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import PlayerIcon from './PlayerIcon.vue'
import type { CentralHudState } from './composables/useCentralHud'
defineProps<{
  hud: CentralHudState
}>()
</script>
