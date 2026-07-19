<template>
  <transition name="sp-ui-fade">
    <div v-if="visible" class="sp-playlist-panel" data-player-interactive @click.stop>
      <div class="sp-playlist-header">
        <span class="sp-playlist-title">{{ title }}</span>
        <span class="sp-playlist-count">{{ entries.length }} 项</span>
        <Button text severity="secondary" size="sm" icon-only class="sp-icon-btn" @click="$emit('close')" title="关闭" aria-label="关闭播放列表">
          <AppIcon name="close" />
        </Button>
      </div>
      <div class="sp-playlist-items">
        <button
          v-for="(entry, index) in entries"
          :key="entry.id"
          type="button"
          class="sp-playlist-item"
          :class="{ 'is-active': index === activeIndex, 'is-playing': index === activeIndex && isPlaying }"
          :aria-current="index === activeIndex ? 'true' : undefined"
          @click.stop="$emit('select', index)"
        >
          <div class="sp-playlist-item-index">{{ index + 1 }}</div>
          <div class="sp-playlist-item-info">
            <div class="sp-playlist-item-title">{{ entry.title }}</div>
            <div v-if="entry.duration" class="sp-playlist-item-duration">{{ formatTime(entry.duration) }}</div>
          </div>
          <div v-if="index === activeIndex" class="sp-playlist-item-status">
            <span class="sp-playlist-playing-indicator" :class="{ 'is-paused': !isPlaying }"></span>
          </div>
        </button>
        <div v-if="entries.length === 0" class="sp-playlist-empty">
          播放列表为空
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { formatTime } from '@/shared/lib/dateFormat'
import type { PlaylistEntry } from '@/features/playback/types/playerSession'
import { Button } from '@/shared/ui/button'
import AppIcon from '@/shared/icons/AppIcon.vue'

withDefaults(defineProps<{
  visible: boolean
  entries: PlaylistEntry[]
  activeIndex: number
  isPlaying: boolean
  title?: string
}>(), {
  title: '播放列表',
})

defineEmits(['close', 'select'])
</script>

<style scoped>
.sp-playlist-panel {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 20rem;
  max-width: 48%;
  background: rgb(14 14 14 / 0.98);
  border-inline-start: 1px solid var(--sp-border, rgba(255, 255, 255, 0.08));
  z-index: 90;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sp-playlist-header {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 3.25rem;
  padding: 8px 10px 8px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.sp-playlist-title {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}

.sp-playlist-count {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  font-family: var(--sp-font-mono);
}

.sp-playlist-items {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.sp-playlist-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 0;
  padding: 10px 14px;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: background var(--duration-fast);
  box-shadow: inset 0 0 0 1px transparent;
}

.sp-playlist-item:hover {
  background: rgba(255, 255, 255, 0.04);
}

.sp-playlist-item:focus-visible {
  background: rgba(255, 255, 255, 0.06);
  outline: 2px solid rgb(255 255 255 / 0.72);
  outline-offset: -2px;
}

.sp-playlist-item.is-active {
  box-shadow: inset 0 0 0 1px rgba(var(--sp-primary-rgb), 0.32);
  background: rgba(var(--sp-primary-rgb), 0.08);
}

.sp-playlist-item-index {
  width: 22px;
  font-size: 11px;
  font-family: var(--sp-font-mono);
  color: rgba(255, 255, 255, 0.3);
  text-align: center;
  flex-shrink: 0;
}

.sp-playlist-item.is-active .sp-playlist-item-index {
  color: var(--sp-primary);
}

.sp-playlist-item-info {
  flex: 1;
  min-width: 0;
}

.sp-playlist-item-title {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sp-playlist-item.is-active .sp-playlist-item-title {
  color: #fff;
}

.sp-playlist-item-duration {
  font-size: var(--app-text-badge-size);
  font-family: var(--sp-font-mono);
  color: rgba(255, 255, 255, 0.35);
  margin-top: 2px;
}

.sp-playlist-item-status {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.sp-playlist-playing-indicator {
  width: 6px;
  height: 6px;
  background: var(--sp-primary);
  border-radius: 50%;
}

.sp-playlist-playing-indicator.is-paused {
  background: rgba(255, 255, 255, 0.3);
}

.sp-playlist-empty {
  padding: 20px 14px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.3);
  text-align: center;
}

@container video-player (max-width: 620px) {
  .sp-playlist-panel {
    width: 100%;
    max-width: none;
  }
}
</style>
