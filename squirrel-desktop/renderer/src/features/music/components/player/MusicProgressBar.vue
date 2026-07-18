<template>
  <div
    ref="barRef"
    class="music-progress-bar"
    :class="{ 'music-progress-bar--hover': isHovered || isDragging }"
    role="slider"
    :aria-valuemin="0"
    :aria-valuemax="Math.max(0, Math.round(total || 0))"
    :aria-valuenow="Math.max(0, Math.round(current || 0))"
    :aria-label="ariaLabel"
    tabindex="0"
    @pointerdown.prevent="onPointerDown"
    @pointerenter="isHovered = true"
    @pointerleave="onPointerLeave"
    @keydown="onKeydown"
  >
    <div class="music-progress-track">
      <div
        class="music-progress-fill"
        :style="{ width: `${displayProgress * 100}%` }"
      />
    </div>
    <div
      v-if="isHovered || isDragging"
      class="music-progress-thumb"
      :style="{ left: `${(isDragging ? previewProgress : progress) * 100}%` }"
    />
    <Transition
      enter-active-class="transition-opacity duration-150"
      leave-active-class="transition-opacity duration-100"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <span
        v-if="(isHovered || isDragging) && previewLabel"
        class="music-progress-tooltip"
        :style="{ left: `${previewProgress * 100}%` }"
      >
        {{ previewLabel }}
      </span>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import { formatPlaybackTime as formatDuration } from '@/features/music/lib/musicFormatters'
import { pointerProgress } from './musicProgressPointer'

const props = defineProps<{
  current: number
  total: number
}>()

const emit = defineEmits<{
  seek: [time: number]
}>()

const barRef = ref<HTMLElement | null>(null)
const isHovered = ref(false)
const isDragging = ref(false)
const previewProgress = ref(0)
let activePointerId: number | null = null
let pendingSeek: number | null = null
let rafId = 0

const progress = computed(() => {
  if (!props.total || props.total <= 0) return 0
  return Math.max(0, Math.min(1, props.current / props.total))
})

const displayProgress = computed(() => (
  isDragging.value ? previewProgress.value : progress.value
))

const previewLabel = computed(() => {
  if (!props.total || props.total <= 0) return ''
  return formatDuration(previewProgress.value * props.total)
})

const ariaLabel = computed(() => {
  if (!props.total || props.total <= 0) return '播放进度'
  return `播放进度 ${formatDuration(props.current)} / ${formatDuration(props.total)}`
})

function setPreviewFromEvent(e: PointerEvent) {
  const bar = barRef.value
  if (!bar) return 0
  const next = pointerProgress(e.clientX, bar.getBoundingClientRect())
  previewProgress.value = next
  return next
}

function releasePointerCapture() {
  const bar = barRef.value
  if (!bar || activePointerId === null || typeof bar.hasPointerCapture !== 'function') return
  if (!bar.hasPointerCapture(activePointerId)) return
  try {
    bar.releasePointerCapture(activePointerId)
  } catch {
    // Capture may already be gone.
  }
}

function addWindowListeners() {
  window.addEventListener('pointermove', onWindowPointerMove)
  window.addEventListener('pointerup', onWindowPointerUp)
  window.addEventListener('pointercancel', onWindowPointerUp)
}

function removeWindowListeners() {
  window.removeEventListener('pointermove', onWindowPointerMove)
  window.removeEventListener('pointerup', onWindowPointerUp)
  window.removeEventListener('pointercancel', onWindowPointerUp)
}

function stopDrag(pointerId?: number) {
  if (activePointerId !== null && typeof pointerId === 'number' && pointerId !== activePointerId) return

  if (rafId) {
    window.cancelAnimationFrame(rafId)
    rafId = 0
  }
  pendingSeek = null
  releasePointerCapture()
  removeWindowListeners()
  activePointerId = null
  isDragging.value = false
}

function flushPendingSeek() {
  rafId = 0
  if (pendingSeek === null || props.total <= 0) return
  emit('seek', pendingSeek * props.total)
  pendingSeek = null
}

function onWindowPointerMove(e: PointerEvent) {
  if (!isDragging.value) return
  if (activePointerId !== null && e.pointerId !== activePointerId) return
  pendingSeek = setPreviewFromEvent(e)
  if (!rafId) {
    rafId = window.requestAnimationFrame(flushPendingSeek)
  }
}

function onWindowPointerUp(e: PointerEvent) {
  if (!isDragging.value) return
  if (activePointerId !== null && e.pointerId !== activePointerId) return

  const next = setPreviewFromEvent(e)
  if (props.total > 0) emit('seek', next * props.total)
  stopDrag(e.pointerId)
}

function onPointerDown(e: PointerEvent) {
  if (e.button !== 0 && e.pointerType === 'mouse') return

  activePointerId = e.pointerId
  isDragging.value = true
  isHovered.value = true
  addWindowListeners()

  const bar = barRef.value
  if (bar && typeof bar.setPointerCapture === 'function') {
    try {
      bar.setPointerCapture(e.pointerId)
    } catch {
      // Some environments reject capture for this pointer.
    }
  }

  const next = setPreviewFromEvent(e)
  if (props.total > 0) emit('seek', next * props.total)
}

function onPointerLeave() {
  if (!isDragging.value) isHovered.value = false
}

function onKeydown(e: KeyboardEvent) {
  if (!props.total || props.total <= 0) return

  const step = e.shiftKey ? 10 : 5
  let next = props.current

  if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
    e.preventDefault()
    next = Math.min(props.total, props.current + step)
  } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
    e.preventDefault()
    next = Math.max(0, props.current - step)
  } else if (e.key === 'Home') {
    e.preventDefault()
    next = 0
  } else if (e.key === 'End') {
    e.preventDefault()
    next = props.total
  } else {
    return
  }

  emit('seek', next)
}

onUnmounted(() => {
  stopDrag()
})
</script>

<style scoped>
.music-progress-bar {
  position: relative;
  width: 100%;
  /* Visual track is hairline; expand the hit target so YesPlayMusic-style
     seeking stays reliable without thickening the chrome. */
  height: 12px;
  cursor: pointer;
  touch-action: none;
  outline: none;
}

.music-progress-bar:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: 2px;
}

.music-progress-track {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: hsl(var(--border) / 0.55);
  border-radius: 9999px;
  overflow: hidden;
  transition: height 0.15s ease;
}

.music-progress-bar--hover .music-progress-track {
  height: 3px;
}

.music-progress-fill {
  height: 100%;
  background: hsl(var(--foreground) / 0.62);
  border-radius: 9999px;
  transition: width 0.1s linear;
}

.music-progress-bar--hover .music-progress-fill,
.music-progress-bar:active .music-progress-fill {
  transition: none;
}

.music-progress-thumb {
  position: absolute;
  top: 1px;
  transform: translate(-50%, -50%);
  width: 8px;
  height: 8px;
  background: hsl(var(--foreground));
  border: 2px solid hsl(var(--background));
  border-radius: 9999px;
  box-shadow: 0 1px 4px hsl(var(--foreground) / 0.18);
  pointer-events: none;
}

.music-progress-tooltip {
  position: absolute;
  bottom: calc(100% + 4px);
  transform: translateX(-50%);
  padding: 0.1875rem 0.4375rem;
  font-size: var(--app-text-badge-size);
  font-weight: 500;
  background: hsl(var(--foreground));
  color: hsl(var(--background));
  border-radius: 0.25rem;
  white-space: nowrap;
  pointer-events: none;
  z-index: 1;
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
