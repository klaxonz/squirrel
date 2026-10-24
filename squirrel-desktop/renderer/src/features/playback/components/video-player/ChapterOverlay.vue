<template>
  <transition name="sp-info-fade">
    <div
      v-if="visible"
      class="sp-chapter-overlay"
      role="dialog"
      :aria-label="chaptersLabel"
      @mouseleave="$emit('close')"
    >
      <div class="sp-chapter-overlay-title">{{ chaptersLabel }}</div>
      <button
        v-for="chapter in chapters"
        :key="chapter.id"
        type="button"
        class="sp-chapter-overlay-item"
        :class="{ 'is-active': chapter.startTime <= currentTime && (chapter.endTime || duration) > currentTime }"
        :aria-current="chapter.startTime <= currentTime && (chapter.endTime || duration) > currentTime ? 'true' : undefined"
        @click="$emit('select', chapter.startTime)"
      >
        <span class="sp-chapter-overlay-time">{{ formatTime(chapter.startTime) }}</span>
        <span class="sp-chapter-overlay-name">{{ chapter.title }}</span>
      </button>
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

<style scoped>
.sp-chapter-overlay {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 35;
  width: min(252px, calc(100% - 24px));
  max-height: calc(100% - 84px);
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 8px;
  border: 1px solid var(--sp-menu-border);
  border-radius: var(--sp-radius-lg);
  background: var(--sp-menu-bg);
  box-shadow: var(--sp-menu-shadow);
  scrollbar-color: rgb(255 255 255 / 0.18) transparent;
  scrollbar-width: thin;
}

.sp-chapter-overlay::-webkit-scrollbar {
  width: 5px;
}

.sp-chapter-overlay::-webkit-scrollbar-track {
  background: transparent;
}

.sp-chapter-overlay::-webkit-scrollbar-thumb {
  border-radius: var(--sp-radius-full);
  background: rgb(255 255 255 / 0.18);
}

.sp-chapter-overlay-title {
  margin-bottom: 6px;
  padding: 6px 8px 10px;
  border-bottom: 1px solid var(--sp-menu-border);
  color: var(--sp-text-strong);
  font-family: var(--sp-font-family);
  font-size: 12px;
  font-weight: 600;
}

.sp-chapter-overlay-item {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border: 0;
  border-radius: var(--sp-radius-md);
  background: transparent;
  cursor: pointer;
  font: inherit;
  text-align: left;
  transition: background var(--duration-fast);
}

.sp-chapter-overlay-item:hover {
  background: var(--sp-menu-item-hover-bg);
}

.sp-chapter-overlay-item.is-active {
  background: rgba(var(--sp-primary-rgb), 0.12);
}

.sp-chapter-overlay-item:focus-visible {
  outline: 2px solid var(--sp-primary);
  outline-offset: -2px;
}

.sp-chapter-overlay-time {
  min-width: 50px;
  flex-shrink: 0;
  color: var(--sp-primary);
  font-family: var(--sp-font-mono);
  font-size: 11px;
}

.sp-chapter-overlay-name {
  overflow: hidden;
  color: var(--sp-text-secondary);
  font-size: 12px;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sp-info-fade-enter-active,
.sp-info-fade-leave-active {
  transition: opacity 0.4s ease;
}

.sp-info-fade-enter-from,
.sp-info-fade-leave-to {
  opacity: 0;
}
</style>
