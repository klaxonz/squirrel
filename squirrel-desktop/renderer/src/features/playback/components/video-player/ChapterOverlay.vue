<template>
  <transition name="sp-info-fade">
    <div v-if="visible" class="sp-chapter-overlay" @mouseleave="$emit('close')">
      <div class="sp-chapter-overlay-title">{{ chaptersLabel }}</div>
      <div
        v-for="chapter in chapters"
        :key="chapter.id"
        class="sp-chapter-overlay-item"
        :class="{ 'is-active': chapter.startTime <= currentTime && (chapter.endTime || duration) > currentTime }"
        @click="$emit('select', chapter.startTime)"
      >
        <span class="sp-chapter-overlay-time">{{ formatTime(chapter.startTime) }}</span>
        <span class="sp-chapter-overlay-name">{{ chapter.title }}</span>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { formatTime } from '@/shared/lib/dateFormat'
import type { Chapter } from './core/types'

defineProps<{
  visible: boolean
  chapters: Chapter[]
  chaptersLabel: string
  currentTime: number
  duration: number
}>()

defineEmits<{
  close: []
  select: [time: number]
}>()
</script>
