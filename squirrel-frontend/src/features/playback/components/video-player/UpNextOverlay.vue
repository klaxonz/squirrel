<template>
  <transition name="sp-info-fade">
    <div v-if="visible" class="sp-upnext-overlay" @click.stop="$emit('startNow')">
      <div class="sp-upnext-label">{{ label }}</div>
      <div class="sp-upnext-title">{{ nextTitle }}</div>
      <div class="sp-upnext-countdown">{{ countdown }}s</div>
      <Button variant="player" size="sm" class="sp-upnext-btn" @click.stop="$emit('startNow')">{{ startNowLabel }}</Button>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { Button } from '@/shared/ui/button'

defineProps<{
  visible: boolean
  label: string
  nextTitle: string
  countdown: number
  startNowLabel: string
}>()

defineEmits<{
  startNow: []
}>()
</script>
