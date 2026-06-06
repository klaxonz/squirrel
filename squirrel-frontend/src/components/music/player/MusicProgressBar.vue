<template>
  <div
    class="music-progress-bar"
    :class="{ 'music-progress-bar--hover': isHovered }"
    @click="handleClick"
    @mousedown="startDrag"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    <div class="music-progress-track">
      <div
        class="music-progress-fill"
        :style="{ width: `${progress * 100}%` }"
      />
    </div>
    <div
      v-if="isHovered || isDragging"
      class="music-progress-thumb"
      :style="{ left: `${progress * 100}%` }"
    />
    <Transition
      enter-active-class="transition-opacity duration-150"
      leave-active-class="transition-opacity duration-100"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <span
        v-if="(isHovered || isDragging) && previewTime"
        class="music-progress-tooltip"
        :style="{ left: `${previewProgress * 100}%` }"
      >
        {{ formatDuration(previewTime) }}
      </span>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onUnmounted } from 'vue'

const props = defineProps<{
  current: number
  total: number
}>()

const emit = defineEmits<{
  seek: [time: number]
}>()

const isHovered = ref(false)
const isDragging = ref(false)
const previewProgress = ref(0)

const progress = computed(() => {
  if (!props.total || props.total <= 0) return 0
  return Math.max(0, Math.min(1, props.current / props.total))
})

const previewTime = computed(() => {
  return previewProgress.value * props.total
})

function formatDuration(seconds: number): string {
  if (!seconds || Number.isNaN(seconds)) return '00:00'
  const rounded = Math.floor(seconds)
  const minutes = Math.floor(rounded / 60)
  const rest = rounded % 60
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}

function handleClick(e: MouseEvent) {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  const percent = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
  emit('seek', percent * props.total)
}

function startDrag(e: MouseEvent) {
  isDragging.value = true
  updatePreview(e)

  const handleMove = (moveEvent: MouseEvent) => {
    updatePreview(moveEvent)
  }

  const handleUp = (upEvent: MouseEvent) => {
    isDragging.value = false
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    const percent = Math.max(0, Math.min(1, (upEvent.clientX - rect.left) / rect.width))
    emit('seek', percent * props.total)
    document.removeEventListener('mousemove', handleMove)
    document.removeEventListener('mouseup', handleUp)
  }

  document.addEventListener('mousemove', handleMove)
  document.addEventListener('mouseup', handleUp)
}

function updatePreview(e: MouseEvent) {
  const rect = (e.currentTarget as HTMLElement)?.getBoundingClientRect?.()
  if (rect) {
    previewProgress.value = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
  }
}

onUnmounted(() => {
  isDragging.value = false
})
</script>

<style scoped>
.music-progress-bar {
  position: relative;
  width: 100%;
  height: 2px;
  cursor: pointer;
  padding: 3px 0;
  margin: 0;
}

.music-progress-track {
  width: 100%;
  height: 2px;
  background: hsl(var(--border) / 0.4);
  border-radius: 9999px;
  overflow: hidden;
  transition: height 0.15s ease;
}

.music-progress-bar--hover .music-progress-track {
  height: 3px;
}

.music-progress-fill {
  height: 100%;
  background: hsl(var(--primary));
  border-radius: 9999px;
  transition: width 0.1s linear;
}

.music-progress-thumb {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 8px;
  height: 8px;
  background: hsl(var(--primary));
  border: 2px solid hsl(var(--background));
  border-radius: 9999px;
  box-shadow: 0 2px 6px hsl(var(--foreground) / 0.2);
  pointer-events: none;
}

.music-progress-tooltip {
  position: absolute;
  bottom: calc(100% + 6px);
  transform: translateX(-50%);
  padding: 0.1875rem 0.4375rem;
  font-size: 0.625rem;
  font-weight: 500;
  background: hsl(var(--foreground));
  color: hsl(var(--background));
  border-radius: 0.25rem;
  white-space: nowrap;
  pointer-events: none;
}

.music-progress-tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 4px solid transparent;
  border-top-color: hsl(var(--foreground));
}
</style>
