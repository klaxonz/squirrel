<template>
  <Transition name="float-bar">
    <div v-if="visible" class="float-bar" :class="{ 'float-bar--dragging': isDragging }">
      <div class="float-bar__inner">
        <div class="float-bar__rec">
          <span class="float-bar__rec-dot"></span>
          <span class="float-bar__rec-label">MARKER</span>
        </div>

        <div class="float-bar__time-display">
          <span class="float-bar__time-label">{{ mode === 'start' ? '开始' : '结束' }}</span>
          <span class="float-bar__time-value">{{ formatTime(safeCurrentTime) }}</span>
        </div>

        <div class="float-bar__duration-hint" v-if="mode === 'start'">
          +{{ formatTime(safeDefaultDuration) }}
        </div>

        <div class="float-bar__actions">
          <button
            v-if="mode === 'start'"
            class="float-bar__btn float-bar__btn--cancel"
            @click="cancelMarking"
            title="取消"
          >
            <AppIcon name="close" class="float-bar__btn-icon" />
          </button>

          <button
            v-if="mode === 'start'"
            class="float-bar__btn float-bar__btn--set-end"
            @click="setEnd"
            title="设置结束时间"
          >
            <AppIcon name="chevronRight" class="float-bar__btn-icon" />
            结束
          </button>

          <button
            v-if="mode === 'end'"
            class="float-bar__btn float-bar__btn--confirm"
            @click="confirmMarking"
            :disabled="isSubmitting"
            title="保存片段"
          >
            <AppIcon name="check" class="float-bar__btn-icon" />
            {{ isSubmitting ? '保存...' : '保存' }}
          </button>

          <button
            v-if="mode === 'end'"
            class="float-bar__btn float-bar__btn--restart"
            @click="restartMarking"
            title="重新标记"
          >
            <AppIcon name="replay" class="float-bar__btn-icon" />
          </button>
        </div>
      </div>

      <button class="float-bar__drag-handle" @mousedown="startDrag" title="拖动调整位置">
        <AppIcon name="gripHorizontal" class="float-bar__drag-icon" />
      </button>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'

const props = defineProps<{
  videoId?: string | number | null
  currentTime?: number
  defaultDuration?: number
}>()

const emit = defineEmits<{
  confirm: [payload: { video_id: string | number; start_time: number; end_time: number }]
}>()

type Mode = 'start' | 'end'

const visible = ref(false)
const mode = ref<Mode>('start')
const isDragging = ref(false)
const isSubmitting = ref(false)
const autoConfirmTimer = ref<ReturnType<typeof setTimeout> | null>(null)

const startTimeRef = ref(0)
const endTimeRef = ref(0)
const barPosition = ref({ top: 'auto', bottom: '80px', left: '50%', right: 'auto' })

const safeCurrentTime = computed(() => Math.max(Number(props.currentTime) || 0, 0))
const safeDefaultDuration = computed(() => Math.max(props.defaultDuration ?? 15, 5))

const formatTime = (seconds: number) => {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

const showBar = () => {
  visible.value = true
}

const clearAutoConfirmTimer = () => {
  if (autoConfirmTimer.value) {
    clearTimeout(autoConfirmTimer.value)
  }
  autoConfirmTimer.value = null
}

const hideBar = () => {
  clearAutoConfirmTimer()
  visible.value = false
  mode.value = 'start'
}

const startMarking = () => {
  if (!props.videoId) return
  startTimeRef.value = safeCurrentTime.value
  endTimeRef.value = startTimeRef.value + safeDefaultDuration.value
  mode.value = 'start'
  showBar()
}

const setEnd = () => {
  endTimeRef.value = safeCurrentTime.value
  if (endTimeRef.value <= startTimeRef.value) {
    endTimeRef.value = startTimeRef.value + safeDefaultDuration.value
  }
  mode.value = 'end'
}

const cancelMarking = () => {
  hideBar()
}

const restartMarking = () => {
  startTimeRef.value = safeCurrentTime.value
  endTimeRef.value = startTimeRef.value + safeDefaultDuration.value
  mode.value = 'start'
}

// 外部控制：开始标记
const startMark = () => {
  if (!props.videoId) return
  startTimeRef.value = safeCurrentTime.value
  endTimeRef.value = startTimeRef.value + safeDefaultDuration.value
  mode.value = 'start'
  showBar()
}

// 外部控制：快速确认（自动保存，跳过表单）
const confirmMark = () => {
  if (!props.videoId || isSubmitting.value) return
  isSubmitting.value = true
  emit('confirm', {
    video_id: props.videoId,
    start_time: startTimeRef.value,
    end_time: endTimeRef.value,
  })
  setTimeout(() => {
    isSubmitting.value = false
    hideBar()
  }, 300)
}

// 外部控制：切换到结束模式（播放到该位置后调用）
const setEndMode = () => {
  endTimeRef.value = safeCurrentTime.value
  if (endTimeRef.value <= startTimeRef.value) {
    endTimeRef.value = startTimeRef.value + safeDefaultDuration.value
  }
  mode.value = 'end'
  clearAutoConfirmTimer()
  autoConfirmTimer.value = setTimeout(() => {
    confirmMark()
  }, 2000)
}

const confirmMarking = () => {
  if (!props.videoId || isSubmitting.value) return
  isSubmitting.value = true
  emit('confirm', {
    video_id: props.videoId,
    start_time: startTimeRef.value,
    end_time: endTimeRef.value,
  })
  setTimeout(() => {
    isSubmitting.value = false
    hideBar()
  }, 300)
}

let dragOffsetX = 0
let dragOffsetY = 0

const startDrag = (e: MouseEvent) => {
  isDragging.value = true
  dragOffsetX = e.clientX - (window.innerWidth / 2)
  dragOffsetY = e.clientY - parseInt(String(barPosition.value.bottom || '80').replace('px', ''))

  const onMouseMove = (ev: MouseEvent) => {
    const newLeft = ev.clientX - dragOffsetX
    const newBottom = window.innerHeight - ev.clientY + dragOffsetY
    barPosition.value = {
      top: 'auto',
      bottom: `${Math.max(20, Math.min(window.innerHeight - 80, newBottom))}px`,
      left: 'auto',
      right: `${window.innerWidth - newLeft}px`,
    }
  }

  const onMouseUp = () => {
    isDragging.value = false
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('mouseup', onMouseUp)
  }

  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

defineExpose({ startMark, confirmMark, setEndMode, startMarking, hideBar, mode, visible })
</script>

<style scoped>
.float-bar {
  position: fixed;
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transform: translateX(-50%);
  left: v-bind('barPosition.left');
  right: v-bind('barPosition.right');
  bottom: v-bind('barPosition.bottom');
  top: v-bind('barPosition.top');
}

.float-bar--dragging {
  cursor: grabbing;
  user-select: none;
}

.float-bar__inner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 1rem;
  background: hsl(var(--card) / 0.92);
  backdrop-filter: blur(16px);
  border: 1px solid hsl(var(--primary) / 0.4);
  border-radius: 999px;
  box-shadow:
    0 8px 32px hsl(var(--foreground) / 0.15),
    0 0 0 1px hsl(var(--primary) / 0.1),
    inset 0 1px 0 hsl(var(--foreground) / 0.06);
  white-space: nowrap;
}

.float-bar__rec {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.float-bar__rec-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: hsl(0 84% 60%);
  animation: rec-blink 1.2s ease-in-out infinite;
}

@keyframes rec-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.float-bar__rec-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: hsl(0 84% 60%);
}

.float-bar__time-display {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.float-bar__time-label {
  font-size: 0.6rem;
  color: hsl(var(--muted-foreground));
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.float-bar__time-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.05rem;
  font-weight: 700;
  color: hsl(var(--foreground));
  letter-spacing: 0.04em;
}

.float-bar__duration-hint {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  color: hsl(var(--muted-foreground));
  opacity: 0.7;
}

.float-bar__actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.float-bar__btn {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.4rem 0.75rem;
  border-radius: 999px;
  border: 1px solid;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-default);
}

.float-bar__btn--cancel {
  background: hsl(var(--destructive) / 0.08);
  border-color: hsl(var(--destructive) / 0.3);
  color: hsl(var(--destructive));
}

.float-bar__btn--cancel:hover {
  background: hsl(var(--destructive) / 0.15);
  border-color: hsl(var(--destructive) / 0.5);
}

.float-bar__btn--set-end {
  background: hsl(var(--primary) / 0.1);
  border-color: hsl(var(--primary) / 0.4);
  color: hsl(var(--primary));
}

.float-bar__btn--set-end:hover {
  background: hsl(var(--primary) / 0.18);
  border-color: hsl(var(--primary) / 0.6);
  transform: translateY(-1px);
}

.float-bar__btn--confirm {
  background: hsl(var(--success) / 0.12);
  border-color: hsl(var(--success) / 0.4);
  color: hsl(var(--success));
}

.float-bar__btn--confirm:hover:not(:disabled) {
  background: hsl(var(--success) / 0.2);
  border-color: hsl(var(--success) / 0.6);
  transform: translateY(-1px);
}

.float-bar__btn--confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.float-bar__btn--restart {
  background: hsl(var(--accent) / 0.08);
  border-color: hsl(var(--accent) / 0.3);
  color: hsl(var(--foreground) / 0.6);
  padding: 0.4rem;
}

.float-bar__btn--restart:hover {
  background: hsl(var(--accent) / 0.15);
  border-color: hsl(var(--accent) / 0.5);
  color: hsl(var(--foreground));
}

.float-bar__drag-handle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid hsl(var(--border) / 0.6);
  background: hsl(var(--card) / 0.8);
  backdrop-filter: blur(8px);
  color: hsl(var(--muted-foreground));
  cursor: grab;
  transition: all var(--duration-normal) var(--ease-default);
}

.float-bar__drag-handle:hover {
  background: hsl(var(--background));
  border-color: hsl(var(--border));
  color: hsl(var(--foreground));
}

.float-bar__drag-handle:active {
  cursor: grabbing;
}

/* Transition */
.float-bar-enter-active,
.float-bar-leave-active {
  transition: all var(--duration-slow) var(--ease-out);
}

.float-bar-enter-from,
.float-bar-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(16px) scale(0.9);
}
</style>
