<template>
  <section class="clip-markers-panel">
    <div class="clip-markers-panel__header">
      <div>
        <p class="clip-markers-panel__eyebrow">Clip Markers</p>
        <h2 class="clip-markers-panel__title">精彩片段</h2>
        <p class="clip-markers-panel__description">标记精彩时刻，支持回看、编辑和分享带时间戳的链接。</p>
      </div>
      <div class="clip-markers-panel__actions">
        <div class="clip-markers-panel__time-chip">当前 {{ formatTime(safeCurrentTime) }}</div>
        <button class="clip-markers-panel__create-btn" :disabled="!videoId || isSubmitting" @click="openCreateForm">
          标记当前片段
        </button>
      </div>
    </div>

    <div v-if="formVisible" class="clip-markers-form">
      <div class="clip-markers-form__grid">
        <label class="clip-markers-form__field">
          <span>标题</span>
          <input v-model.trim="form.title" type="text" maxlength="255" placeholder="例如：开场高能 / 反转瞬间" />
        </label>
        <label class="clip-markers-form__field">
          <span>备注</span>
          <input v-model.trim="form.note" type="text" maxlength="255" placeholder="可选，用于说明这段为什么值得回看" />
        </label>
        <label class="clip-markers-form__field">
          <span>开始时间</span>
          <div class="clip-markers-form__time-field">
            <input v-model.trim="form.startTimeText" type="text" placeholder="00:01:23" />
            <button type="button" @click="fillStartWithCurrentTime">当前时间</button>
          </div>
        </label>
        <label class="clip-markers-form__field">
          <span>结束时间</span>
          <div class="clip-markers-form__time-field">
            <input v-model.trim="form.endTimeText" type="text" placeholder="00:01:38" />
            <button type="button" @click="fillEndWithCurrentTime">当前时间</button>
          </div>
        </label>
      </div>

      <p v-if="formError" class="clip-markers-form__error">{{ formError }}</p>

      <div class="clip-markers-form__footer">
        <button class="clip-markers-form__ghost-btn" :disabled="isSubmitting" @click="closeForm">
          取消
        </button>
        <button class="clip-markers-form__submit-btn" :disabled="!videoId || isSubmitting" @click="submitForm">
          {{ isSubmitting ? '保存中...' : isEditing ? '更新片段' : '保存片段' }}
        </button>
      </div>
    </div>

    <div v-if="markers.length" class="clip-markers-list">
      <article
        v-for="(marker, index) in markers"
        :key="marker.id"
        class="clip-marker-card"
        :class="{ 'is-active': activeMarkerId === marker.id }"
      >
        <div class="clip-marker-card__meta">
          <div>
            <h3 class="clip-marker-card__title">{{ marker.title || `片段 ${String(index + 1).padStart(2, '0')}` }}</h3>
            <p class="clip-marker-card__time">
              {{ formatTime(marker.start_time) }} - {{ formatTime(marker.end_time) }}
              <span class="clip-marker-card__duration">· {{ formatDuration(marker) }}</span>
            </p>
            <p v-if="marker.note" class="clip-marker-card__note">{{ marker.note }}</p>
          </div>
          <div class="clip-marker-card__badge">{{ activeMarkerId === marker.id ? '播放中' : '已标记' }}</div>
        </div>

        <div class="clip-marker-card__actions">
          <button @click="jumpToMarker(marker)">跳转</button>
          <button @click="copyMarkerLink(marker)">{{ copiedMarkerId === marker.id ? '已复制' : '分享' }}</button>
          <button @click="startEdit(marker)">编辑</button>
          <button class="is-danger" :disabled="deletingMarkerId === marker.id" @click="removeMarker(marker)">
            {{ deletingMarkerId === marker.id ? '删除中...' : '删除' }}
          </button>
        </div>
      </article>
    </div>

    <div v-else class="clip-markers-empty">
      还没有精彩片段标记。播放到关键时刻时点击“标记当前片段”即可保存。
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import {
  createVideoClipMarker,
  deleteVideoClipMarker,
  updateVideoClipMarker,
} from '@/api/videoClipMarkers'
import type { VideoClipMarker } from '@/types/videoClipMarker'
import { formatTime } from '@/utils/dateFormat'

type MarkerFormState = {
  title: string
  note: string
  startTimeText: string
  endTimeText: string
}

const props = withDefaults(defineProps<{
  videoId?: string | number | null
  duration?: number
  currentTime?: number
  markers?: VideoClipMarker[]
}>(), {
  videoId: null,
  duration: 0,
  currentTime: 0,
  markers: () => [],
})

const emit = defineEmits<{
  seek: [time: number]
  updated: [markers: VideoClipMarker[]]
}>()

const safeCurrentTime = computed(() => Math.max(Number(props.currentTime) || 0, 0))
const safeDuration = computed(() => Math.max(Number(props.duration) || 0, 0))
const markers = computed(() => Array.isArray(props.markers) ? props.markers : [])
const activeMarkerId = computed(() => {
  const current = safeCurrentTime.value
  const activeMarker = markers.value.find((marker) => current >= marker.start_time && current <= marker.end_time)
  return activeMarker?.id ?? null
})

const form = reactive<MarkerFormState>({
  title: '',
  note: '',
  startTimeText: '',
  endTimeText: '',
})

const formVisible = ref(false)
const formError = ref('')
const editingMarkerId = ref<number | null>(null)
const isSubmitting = ref(false)
const deletingMarkerId = ref<number | null>(null)
const copiedMarkerId = ref<number | null>(null)

const isEditing = computed(() => editingMarkerId.value !== null)

const clampTime = (value: number) => {
  const normalized = Math.max(value, 0)
  if (safeDuration.value <= 0) return normalized
  return Math.min(normalized, safeDuration.value)
}

const createDefaultEndTime = (startTime: number) => {
  const nextEndTime = startTime + 15
  return safeDuration.value > 0 ? Math.min(nextEndTime, safeDuration.value) : nextEndTime
}

const setFormFromTimes = (startTime: number, endTime: number) => {
  form.startTimeText = formatTime(clampTime(startTime))
  form.endTimeText = formatTime(clampTime(endTime))
}

const resetForm = () => {
  form.title = ''
  form.note = ''
  setFormFromTimes(safeCurrentTime.value, createDefaultEndTime(safeCurrentTime.value))
  formError.value = ''
  editingMarkerId.value = null
}

const openCreateForm = () => {
  resetForm()
  formVisible.value = true
}

const closeForm = () => {
  formVisible.value = false
  formError.value = ''
  editingMarkerId.value = null
}

const parseTimeText = (value: string) => {
  const raw = String(value || '').trim()
  if (!raw) return Number.NaN

  if (/^\d+(\.\d+)?$/.test(raw)) {
    return clampTime(Number(raw))
  }

  const segments = raw.split(':').map((item) => item.trim())
  if (!segments.length || segments.some((item) => item === '' || Number.isNaN(Number(item)))) {
    return Number.NaN
  }

  const numbers = segments.map((item) => Number(item))
  const seconds = numbers.reduce((total, current, index) => {
    const power = numbers.length - index - 1
    return total + current * (60 ** power)
  }, 0)

  return clampTime(seconds)
}

const buildMarkerPayload = () => {
  const startTime = parseTimeText(form.startTimeText)
  const endTime = parseTimeText(form.endTimeText)

  if (!Number.isFinite(startTime)) {
    throw new Error('开始时间格式不正确，请使用秒数或 HH:MM:SS')
  }

  if (!Number.isFinite(endTime)) {
    throw new Error('结束时间格式不正确，请使用秒数或 HH:MM:SS')
  }

  if (endTime < startTime) {
    throw new Error('结束时间不能早于开始时间')
  }

  return {
    title: form.title || undefined,
    note: form.note || undefined,
    start_time: startTime,
    end_time: endTime,
  }
}

const emitUpdatedMarkers = (nextMarkers: VideoClipMarker[]) => {
  const orderedMarkers = [...nextMarkers].sort((left, right) => {
    if (left.start_time !== right.start_time) return left.start_time - right.start_time
    return Number(left.id) - Number(right.id)
  })
  emit('updated', orderedMarkers)
}

const submitForm = async () => {
  if (!props.videoId) return

  formError.value = ''
  isSubmitting.value = true

  try {
    const payload = buildMarkerPayload()
    if (isEditing.value && editingMarkerId.value !== null) {
      const { data, error } = await updateVideoClipMarker(editingMarkerId.value, payload)
      if (error || !data) {
        throw new Error(error?.message || '更新片段失败')
      }

      emitUpdatedMarkers(
        markers.value.map((marker) => marker.id === data.id ? data : marker)
      )
    } else {
      const { data, error } = await createVideoClipMarker({
        video_id: props.videoId,
        ...payload,
      })
      if (error || !data) {
        throw new Error(error?.message || '创建片段失败')
      }

      emitUpdatedMarkers([...markers.value, data])
    }

    closeForm()
  } catch (error: any) {
    formError.value = error?.message || '保存片段失败'
  } finally {
    isSubmitting.value = false
  }
}

const jumpToMarker = (marker: VideoClipMarker) => {
  emit('seek', marker.start_time)
}

const copyText = async (value: string) => {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value)
    return
  }

  const textArea = document.createElement('textarea')
  textArea.value = value
  textArea.style.position = 'fixed'
  textArea.style.opacity = '0'
  document.body.appendChild(textArea)
  textArea.focus()
  textArea.select()
  document.execCommand('copy')
  document.body.removeChild(textArea)
}

const buildMarkerLink = (marker: VideoClipMarker) => {
  const url = new URL(window.location.href)
  url.pathname = `/video/${props.videoId}`
  url.searchParams.set('t', String(Math.max(Math.floor(marker.start_time), 0)))
  url.searchParams.set('clip', String(marker.id))
  return url.toString()
}

const copyMarkerLink = async (marker: VideoClipMarker) => {
  try {
    await copyText(buildMarkerLink(marker))
    copiedMarkerId.value = marker.id
    window.setTimeout(() => {
      if (copiedMarkerId.value === marker.id) {
        copiedMarkerId.value = null
      }
    }, 1600)
  } catch (error: any) {
    formError.value = error?.message || '复制分享链接失败'
  }
}

const startEdit = (marker: VideoClipMarker) => {
  editingMarkerId.value = marker.id
  form.title = marker.title || ''
  form.note = marker.note || ''
  setFormFromTimes(marker.start_time, marker.end_time)
  formError.value = ''
  formVisible.value = true
}

const removeMarker = async (marker: VideoClipMarker) => {
  deletingMarkerId.value = marker.id

  try {
    const { error } = await deleteVideoClipMarker(marker.id)
    if (error) {
      throw new Error(error.message || '删除片段失败')
    }

    emitUpdatedMarkers(markers.value.filter((item) => item.id !== marker.id))
    if (editingMarkerId.value === marker.id) {
      closeForm()
    }
  } catch (error: any) {
    formError.value = error?.message || '删除片段失败'
  } finally {
    deletingMarkerId.value = null
  }
}

const fillStartWithCurrentTime = () => {
  form.startTimeText = formatTime(safeCurrentTime.value)
}

const fillEndWithCurrentTime = () => {
  form.endTimeText = formatTime(safeCurrentTime.value)
}

const formatDuration = (marker: VideoClipMarker) => {
  const duration = typeof marker.duration_seconds === 'number'
    ? marker.duration_seconds
    : Math.max(marker.end_time - marker.start_time, 0)
  return `${duration.toFixed(duration >= 10 ? 0 : 1)}s`
}

watch(
  () => props.videoId,
  () => {
    closeForm()
    resetForm()
  },
  { immediate: true }
)

watch(
  () => markers.value.map((marker) => marker.id),
  (markerIds) => {
    if (editingMarkerId.value !== null && !markerIds.includes(editingMarkerId.value)) {
      closeForm()
    }
  }
)
</script>

<style scoped>
.clip-markers-panel {
  margin-top: 1.5rem;
  padding: 1.25rem;
  border: 1px solid hsl(var(--border) / 0.7);
  border-radius: 1rem;
  background:
    linear-gradient(135deg, hsl(var(--card) / 0.96), hsl(var(--card) / 0.84)),
    radial-gradient(circle at top right, hsl(var(--primary) / 0.16), transparent 44%);
  box-shadow: 0 20px 40px hsl(var(--foreground) / 0.08);
}

.clip-markers-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.clip-markers-panel__eyebrow {
  margin: 0 0 0.35rem;
  font-size: 0.75rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: hsl(var(--muted-foreground));
}

.clip-markers-panel__title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: hsl(var(--foreground));
}

.clip-markers-panel__description {
  margin: 0.35rem 0 0;
  font-size: 0.92rem;
  color: hsl(var(--muted-foreground));
}

.clip-markers-panel__actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.clip-markers-panel__time-chip,
.clip-markers-panel__create-btn,
.clip-marker-card__actions button,
.clip-markers-form__ghost-btn,
.clip-markers-form__submit-btn,
.clip-markers-form__time-field button {
  border: 1px solid hsl(var(--border));
  border-radius: 999px;
  background: hsl(var(--background) / 0.7);
  color: hsl(var(--foreground));
  padding: 0.5rem 0.85rem;
  font-size: 0.86rem;
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;
}

.clip-markers-panel__create-btn:hover,
.clip-marker-card__actions button:hover,
.clip-markers-form__ghost-btn:hover,
.clip-markers-form__submit-btn:hover,
.clip-markers-form__time-field button:hover {
  border-color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.1);
  transform: translateY(-1px);
}

.clip-markers-panel__create-btn,
.clip-markers-form__submit-btn {
  background: linear-gradient(135deg, hsl(var(--primary) / 0.22), hsl(var(--primary) / 0.08));
}

.clip-markers-form {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid hsl(var(--border) / 0.7);
}

.clip-markers-form__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem;
}

.clip-markers-form__field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  font-size: 0.88rem;
  color: hsl(var(--muted-foreground));
}

.clip-markers-form__field input {
  width: 100%;
  padding: 0.7rem 0.85rem;
  border-radius: 0.85rem;
  border: 1px solid hsl(var(--border));
  background: hsl(var(--background) / 0.7);
  color: hsl(var(--foreground));
}

.clip-markers-form__time-field {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.5rem;
}

.clip-markers-form__time-field button {
  white-space: nowrap;
}

.clip-markers-form__error {
  margin: 0.85rem 0 0;
  color: hsl(var(--destructive));
  font-size: 0.88rem;
}

.clip-markers-form__footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1rem;
}

.clip-markers-list {
  display: grid;
  gap: 0.85rem;
  margin-top: 1rem;
}

.clip-marker-card {
  padding: 1rem;
  border-radius: 0.95rem;
  border: 1px solid hsl(var(--border) / 0.7);
  background: linear-gradient(180deg, hsl(var(--background) / 0.8), hsl(var(--background) / 0.55));
}

.clip-marker-card.is-active {
  border-color: hsl(var(--primary));
  box-shadow: 0 0 0 1px hsl(var(--primary) / 0.2), 0 14px 30px hsl(var(--primary) / 0.12);
}

.clip-marker-card__meta {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.clip-marker-card__title {
  margin: 0;
  font-size: 1rem;
  color: hsl(var(--foreground));
}

.clip-marker-card__time {
  margin: 0.3rem 0 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.88rem;
}

.clip-marker-card__duration {
  color: hsl(var(--foreground));
}

.clip-marker-card__note {
  margin: 0.45rem 0 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.88rem;
}

.clip-marker-card__badge {
  align-self: flex-start;
  padding: 0.35rem 0.65rem;
  border-radius: 999px;
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--foreground));
  font-size: 0.78rem;
}

.clip-marker-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 0.9rem;
}

.clip-marker-card__actions .is-danger {
  color: hsl(var(--destructive));
}

.clip-markers-empty {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 0.9rem;
  border: 1px dashed hsl(var(--border));
  color: hsl(var(--muted-foreground));
  text-align: center;
}

@media (max-width: 768px) {
  .clip-markers-panel__header {
    flex-direction: column;
  }

  .clip-markers-panel__actions {
    justify-content: flex-start;
  }

  .clip-markers-form__grid {
    grid-template-columns: 1fr;
  }

  .clip-marker-card__meta {
    flex-direction: column;
  }
}
</style>
