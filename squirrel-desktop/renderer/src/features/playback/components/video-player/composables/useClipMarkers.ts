import { ref, computed, watch, type ComputedRef, type Ref } from 'vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import { formatTime } from '@/shared/lib/dateFormat'
import type { IconName } from '../core/useIcons'
import {
  createPointMarkerDraft,
  createSegmentMarkerDraft,
  isClipMarkerActive,
  isPointMarker,
  resolveClipMarkerVideoId,
} from '../runtime/clipMarkers'
import { createVideoClipMarker, deleteVideoClipMarker, updateVideoClipMarker, uploadVideoClipMarkerPreview } from '@/shared/api/videoClipMarkers'
import type { MediaSource } from '../core'
import type { VideoClipMarker } from '@/features/video/types/videoClipMarker'

// UI-facing marker shape after normalization (percent-based positioning for the
// progress rail). Distinct from the persisted VideoClipMarker (time-based).
interface NormalizedClipMarker {
  id: number
  title: string | null | undefined
  startTime: number
  endTime: number
  isPoint: boolean
  startPercent: number
  widthPercent: number
  color: string
}

export interface UseClipMarkersOptions {
  clipMarkers: Ref<VideoClipMarker[]>
  videoId: Ref<string | number | null>
  source: Ref<MediaSource | null>
  currentTime: Ref<number>
  duration: Ref<number>
  seek: (time: number) => void
  showCentralHud: (type: string, value: string, icon: IconName, percent?: number) => void
  onClipMarkerSelect?: (time: number) => void
  onClipMarkersUpdated?: (markers: VideoClipMarker[]) => void
}

export interface UseClipMarkersReturn {
  localClipMarkers: Ref<VideoClipMarker[]>
  clipMarkerVideoId: Ref<string | number | null>
  hoveredMarkerId: Ref<number | null>
  hasPendingSegment: ComputedRef<boolean>
  pendingSegmentStartTime: Ref<number | null>
  pendingSegmentEndTime: Ref<number | null>
  pendingSegmentPreviewEnd: ComputedRef<number>
  isSavingMarker: Ref<boolean>
  draggingMarker: Ref<{
    markerId: number
    pointerId: number
    dragType: 'start' | 'end' | 'move'
    startX: number
    originalStart: number
    originalEnd: number
    previewStart: number
    previewEnd: number
    moved: boolean
  } | null>
  normalizedClipMarkers: ComputedRef<NormalizedClipMarker[]>
  markerColorById: ComputedRef<Record<number, string>>
  activeClipMarkerId: ComputedRef<number | null>
  getMarkerTitle: (marker: VideoClipMarker | NormalizedClipMarker) => string
  getMarkerTimeText: (marker: VideoClipMarker | NormalizedClipMarker) => string
  markCurrentPoint: () => Promise<void>
  startSegmentCapture: () => void
  finishSegmentCapture: () => Promise<void>
  cancelSegmentCapture: () => void
  deleteMarkerFromPanel: (marker: { id: number }) => Promise<void>
  onMarkerPointerDown: (e: PointerEvent, marker: NormalizedClipMarker) => void
  onWindowMarkerPointerMove: (event: PointerEvent) => void
  onWindowMarkerPointerUp: (event: PointerEvent) => void
  commitDrag: () => void
  handleClipMarkerSelect: (marker: { id: number; startTime: number }) => void
  handleOverlaySeek: (time: number) => void
  captureCurrentFrameDataUrl: (videoRef: Ref<HTMLVideoElement | null>) => string | null
  releaseMarkerPointerCapture: () => void
  removeMarkerDragListeners: () => void
}

const COLORS = [
  'hsl(24 100% 50%)',
  'hsl(186 100% 50%)',
  'hsl(145 70% 50%)',
  'hsl(280 80% 60%)',
  'hsl(38 92% 55%)',
]

export function useClipMarkers(options: UseClipMarkersOptions): UseClipMarkersReturn {
  const {
    clipMarkers,
    videoId,
    source,
    currentTime,
    duration,
    seek,
    showCentralHud,
    onClipMarkerSelect,
    onClipMarkersUpdated,
  } = options

  const localClipMarkers = ref<VideoClipMarker[]>([])
  const clipMarkerVideoId = ref<string | number | null>(null)
  const hoveredMarkerId = ref<number | null>(null)
  const pendingSegmentStartTime = ref<number | null>(null)
  const pendingSegmentEndTime = ref<number | null>(null)
  const pendingSegmentPreviewImageDataUrl = ref<string | null>(null)
  const isSavingMarker = ref(false)

  const hasPendingSegment = computed(() => pendingSegmentStartTime.value !== null)

  const pendingSegmentPreviewEnd = computed(() => {
    const end = pendingSegmentEndTime.value
    if (end === null) return currentTime.value
    if (pendingSegmentStartTime.value !== null && end < pendingSegmentStartTime.value) {
      return pendingSegmentStartTime.value
    }
    return end
  })

  const draggingMarker = ref<{
    markerId: number
    pointerId: number
    dragType: 'start' | 'end' | 'move'
    startX: number
    originalStart: number
    originalEnd: number
    previewStart: number
    previewEnd: number
    moved: boolean
  } | null>(null)

  let activeMarkerPointerTarget: HTMLElement | null = null
  let suppressMarkerClickUntil = 0

  const handleOverlaySeek = (time: number) => {
    seek(time)
    onClipMarkerSelect?.(time)
  }

  const syncLocalClipMarkers = (markers: VideoClipMarker[]) => {
    localClipMarkers.value = [...markers].sort((a, b) => a.start_time - b.start_time)
    onClipMarkersUpdated?.(localClipMarkers.value)
  }

  const captureCurrentFrameDataUrl = (videoRef: Ref<HTMLVideoElement | null>): string | null => {
    const video = videoRef.value
    if (
      !video
      || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA
      || video.videoWidth <= 0
      || video.videoHeight <= 0
    ) {
      return null
    }

    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const context = canvas.getContext('2d')
    if (!context) return null

    try {
      context.drawImage(video, 0, 0, canvas.width, canvas.height)
      return canvas.toDataURL('image/jpeg', 0.82)
    } catch {
      return null
    }
  }

  const uploadMarkerPreviewIfAvailable = async (
    marker: VideoClipMarker,
    imageDataUrl: string | null
  ): Promise<VideoClipMarker> => {
    if (!imageDataUrl) return marker
    try {
      const data = await uploadVideoClipMarkerPreview(marker.id, {
        image_data_url: imageDataUrl,
      })
      return data || marker
    } catch {
      // preview upload is best-effort — fall back to the marker without preview
      return marker
    }
  }

  const markCurrentPoint = async () => {
    if (!clipMarkerVideoId.value || isSavingMarker.value) return
    isSavingMarker.value = true
    try {
      const data = await createVideoClipMarker({
        video_id: clipMarkerVideoId.value,
        start_time: currentTime.value,
        end_time: currentTime.value,
      })
      if (!data) {
        showCentralHud('error', '标记失败', 'play')
        return
      }
      syncLocalClipMarkers([...localClipMarkers.value, data])
      showCentralHud('marker', `标记 ${formatTime(currentTime.value)}`, 'play')
    } catch (err) {
      showCentralHud('error', errorMessage(err, '标记失败'), 'play')
    } finally {
      isSavingMarker.value = false
    }
  }

  const startSegmentCapture = () => {
    if (isSavingMarker.value) return
    const t = currentTime.value
    if (!isFinite(t) || t < 0 || !duration.value) return
    const draft = createPointMarkerDraft({ currentTime: t, duration: duration.value })
    pendingSegmentStartTime.value = draft.startTime
    showCentralHud('marker', `起点 ${formatTime(draft.startTime)}`, 'skipBackward')
  }

  const finishSegmentCapture = async () => {
    if (!clipMarkerVideoId.value || pendingSegmentStartTime.value === null || isSavingMarker.value) return
    const startTime = pendingSegmentStartTime.value
    const endTime = pendingSegmentEndTime.value ?? currentTime.value
    const draft = createSegmentMarkerDraft({
      startTime,
      currentTime: endTime,
      duration: duration.value,
    })
    pendingSegmentStartTime.value = null
    pendingSegmentEndTime.value = null
    const previewImageDataUrl = pendingSegmentPreviewImageDataUrl.value
    pendingSegmentPreviewImageDataUrl.value = null
    isSavingMarker.value = true

    try {
      const data = await createVideoClipMarker({
        video_id: clipMarkerVideoId.value,
        start_time: draft.startTime,
        end_time: draft.endTime,
      })
      if (!data) {
        showCentralHud('error', '保存失败', 'play')
        return
      }
      const markerWithPreview = await uploadMarkerPreviewIfAvailable(data, previewImageDataUrl)
      syncLocalClipMarkers([...localClipMarkers.value, markerWithPreview])
      showCentralHud('segment', `片段 ${formatTime(draft.startTime)}`, 'skipForward')
    } catch (err) {
      showCentralHud('error', errorMessage(err, '保存失败'), 'play')
    } finally {
      isSavingMarker.value = false
    }
  }

  const cancelSegmentCapture = () => {
    pendingSegmentStartTime.value = null
    pendingSegmentEndTime.value = null
    pendingSegmentPreviewImageDataUrl.value = null
    showCentralHud('seek', '已取消', 'play')
  }

  const deleteMarkerFromPanel = async (marker: { id: number }) => {
    try {
      await deleteVideoClipMarker(marker.id)
      syncLocalClipMarkers(localClipMarkers.value.filter((item) => item.id !== marker.id))
      hoveredMarkerId.value = null
    } catch (err) {
      showCentralHud('error', errorMessage(err, '删除失败'), 'play')
    }
  }

  const getProgressRect = () => {
    const el = document.querySelector<HTMLElement>('[data-progress-area]')
    return el?.getBoundingClientRect()
  }

  const addMarkerDragListeners = () => {
    window.addEventListener('pointermove', onWindowMarkerPointerMove)
    window.addEventListener('pointerup', onWindowMarkerPointerUp)
    window.addEventListener('pointercancel', onWindowMarkerPointerUp)
  }

  const removeMarkerDragListeners = () => {
    window.removeEventListener('pointermove', onWindowMarkerPointerMove)
    window.removeEventListener('pointerup', onWindowMarkerPointerUp)
    window.removeEventListener('pointercancel', onWindowMarkerPointerUp)
  }

  const onMarkerPointerDown = (e: PointerEvent, marker: NormalizedClipMarker) => {
    if (isSavingMarker.value || !marker) return
    const rect = getProgressRect()
    if (!rect) return
    const ratio = (e.clientX - rect.left) / rect.width
    const markerStartRatio = marker.startPercent / 100
    const markerEndRatio = (marker.startPercent + marker.widthPercent) / 100

    let dragType: 'start' | 'end' | 'move' = 'move'
    if (!marker.isPoint && marker.widthPercent > 0.5) {
      const startDist = Math.abs(ratio - markerStartRatio)
      const endDist = Math.abs(ratio - markerEndRatio)
      if (startDist < endDist) dragType = 'start'
      else if (endDist < startDist) dragType = 'end'
    }

    draggingMarker.value = {
      markerId: marker.id,
      pointerId: e.pointerId,
      dragType,
      startX: e.clientX,
      originalStart: marker.startTime,
      originalEnd: marker.endTime,
      previewStart: marker.startTime,
      previewEnd: marker.endTime,
      moved: false,
    }
    addMarkerDragListeners()

    if (e.currentTarget instanceof HTMLElement && typeof e.currentTarget.setPointerCapture === 'function') {
      try {
        e.currentTarget.setPointerCapture(e.pointerId)
        activeMarkerPointerTarget = e.currentTarget
      } catch {
        activeMarkerPointerTarget = null
      }
    }
  }

  const releaseMarkerPointerCapture = () => {
    const markerPointerId = draggingMarker.value?.pointerId
    if (activeMarkerPointerTarget === null || markerPointerId === undefined || markerPointerId === null) return
    if (typeof activeMarkerPointerTarget.hasPointerCapture !== 'function') {
      activeMarkerPointerTarget = null
      return
    }
    if (!activeMarkerPointerTarget.hasPointerCapture(markerPointerId)) {
      activeMarkerPointerTarget = null
      return
    }
    try {
      activeMarkerPointerTarget.releasePointerCapture(markerPointerId)
    } catch {
      // Ignore browsers that reject release when capture is already gone.
    }
    activeMarkerPointerTarget = null
  }

  const updateDragPreview = (deltaTime: number) => {
    const d = draggingMarker.value
    if (!d) return
    const rect = getProgressRect()
    if (!rect || !duration.value) return

    const rawStart = d.originalStart + deltaTime
    const rawEnd = d.originalEnd + deltaTime

    let newStart: number, newEnd: number
    if (d.dragType === 'move') {
      const span = d.originalEnd - d.originalStart
      newStart = Math.max(0, Math.min(duration.value - span, rawStart))
      newEnd = newStart + span
    } else if (d.dragType === 'start') {
      newStart = Math.max(0, Math.min(d.originalEnd - 0.1, rawStart))
      newEnd = d.originalEnd
    } else {
      newStart = d.originalStart
      newEnd = Math.min(duration.value, Math.max(d.originalStart + 0.1, rawEnd))
    }

    d.previewStart = newStart
    d.previewEnd = newEnd
    d.moved = d.moved
      || Math.abs(newStart - d.originalStart) > 0.01
      || Math.abs(newEnd - d.originalEnd) > 0.01

    showCentralHud('seek', `${formatTime(newStart)} → ${formatTime(newEnd)}`, 'skipForward')
  }

  const commitDrag = () => {
    const d = draggingMarker.value
    if (!d) return
    const normMarker = normalizedClipMarkers.value.find((m) => m.id === d.markerId)
    if (!normMarker || !duration.value) {
      releaseMarkerPointerCapture()
      removeMarkerDragListeners()
      draggingMarker.value = null
      return
    }

    const newStart = Math.max(0, Math.min(duration.value, d.previewStart))
    const newEnd = Math.max(newStart, Math.min(duration.value, d.previewEnd))

    releaseMarkerPointerCapture()
    removeMarkerDragListeners()
    draggingMarker.value = null
    if (d.moved) {
      suppressMarkerClickUntil = Date.now() + 250
    }

    if (normMarker.isPoint || Math.abs(newStart - newEnd) < 0.1) {
      updateVideoClipMarker(d.markerId, { start_time: newStart, end_time: newStart }).then((data) => {
        if (!data) return
        syncLocalClipMarkers(localClipMarkers.value.map((m) => m.id === d.markerId ? data : m))
        showCentralHud('marker', `标记 ${formatTime(newStart)}`, 'skipForward')
      }).catch((err: unknown) => {
        showCentralHud('error', errorMessage(err, '更新失败'), 'play')
      })
      return
    }

    updateVideoClipMarker(d.markerId, { start_time: newStart, end_time: newEnd }).then((data) => {
      if (!data) return
      syncLocalClipMarkers(localClipMarkers.value.map((m) => m.id === d.markerId ? data : m))
      showCentralHud('segment', `${formatTime(newStart)} → ${formatTime(newEnd)}`, 'skipForward')
    }).catch((err: unknown) => {
      showCentralHud('error', errorMessage(err, '更新失败'), 'play')
    })
  }

  const onWindowMarkerPointerMove = (event: PointerEvent) => {
    if (!draggingMarker.value) return
    if (event.pointerId !== draggingMarker.value.pointerId) return
    const rect = getProgressRect()
    if (!rect || !duration.value) return
    const deltaX = event.clientX - draggingMarker.value.startX
    const deltaTime = (deltaX / rect.width) * duration.value
    updateDragPreview(deltaTime)
  }

  const onWindowMarkerPointerUp = (event: PointerEvent) => {
    if (!draggingMarker.value) return
    if (event.pointerId !== draggingMarker.value.pointerId) return
    commitDrag()
  }

  watch(() => clipMarkers.value, (markers) => {
    localClipMarkers.value = Array.isArray(markers) ? [...markers] : []
  }, { immediate: true, deep: true })

  watch(() => [videoId.value, source.value] as const, ([vid, src]) => {
    clipMarkerVideoId.value = resolveClipMarkerVideoId(vid, src)
  }, { immediate: true })

  const normalizedClipMarkers = computed(() => {
    if (!duration.value || duration.value <= 0) return []

    return localClipMarkers.value.map((marker, index) => {
      const dragPreview = draggingMarker.value?.markerId === marker.id
        ? {
            startTime: draggingMarker.value.previewStart,
            endTime: draggingMarker.value.previewEnd,
          }
        : null
      const startTime = Math.max(
        Number(dragPreview?.startTime ?? marker.start_time) || 0,
        0,
      )
      const rawEndTime = Number(dragPreview?.endTime ?? marker.end_time)
      const endTime = Number.isFinite(rawEndTime) ? Math.max(rawEndTime, startTime) : startTime
      const isPoint = isPointMarker({ startTime, endTime })
      const startPercent = Math.min((startTime / duration.value) * 100, 100)
      const widthPercent = isPoint ? 0.001 : Math.max(((endTime - startTime) / duration.value) * 100, 0.35)

      return {
        id: marker.id,
        title: marker.title,
        startTime,
        endTime,
        isPoint,
        startPercent,
        widthPercent,
        color: COLORS[index % COLORS.length],
      }
    })
  })

  const markerColorById = computed(() => Object.fromEntries(
    normalizedClipMarkers.value.map((marker) => [marker.id, marker.color]),
  ))

  const activeClipMarkerId = computed(() => {
    const activeMarker = normalizedClipMarkers.value.find((marker) => isClipMarkerActive(marker, currentTime.value))
    return activeMarker?.id ?? null
  })

  const getMarkerTitle = (marker: VideoClipMarker | NormalizedClipMarker): string => {
    if (marker.title) return marker.title
    const startTime = Number('start_time' in marker ? marker.start_time : marker.startTime ?? 0)
    return isPointMarker(marker) ? `📍 ${formatTime(startTime)}` : `📌 ${formatTime(startTime)}`
  }

  const getMarkerTimeText = (marker: VideoClipMarker | NormalizedClipMarker): string => {
    const startTime = Number('start_time' in marker ? marker.start_time : marker.startTime ?? 0)
    const rawEnd = 'end_time' in marker ? marker.end_time : marker.endTime
    const endTime = Number(rawEnd ?? startTime)
    return isPointMarker(marker)
      ? `时间点 ${formatTime(startTime)}`
      : `${formatTime(startTime)} → ${formatTime(endTime)}`
  }

  const handleClipMarkerSelect = (marker: { id: number; startTime: number }) => {
    if (Date.now() < suppressMarkerClickUntil) return
    seek(marker.startTime)
    onClipMarkerSelect?.(marker.startTime)
  }

  return {
    localClipMarkers,
    clipMarkerVideoId,
    hoveredMarkerId,
    hasPendingSegment,
    pendingSegmentStartTime,
    pendingSegmentEndTime,
    pendingSegmentPreviewEnd,
    isSavingMarker,
    draggingMarker,
    normalizedClipMarkers,
    markerColorById,
    activeClipMarkerId,
    getMarkerTitle,
    getMarkerTimeText,
    markCurrentPoint,
    startSegmentCapture,
    finishSegmentCapture,
    cancelSegmentCapture,
    deleteMarkerFromPanel,
    onMarkerPointerDown,
    onWindowMarkerPointerMove,
    onWindowMarkerPointerUp,
    commitDrag,
    handleClipMarkerSelect,
    handleOverlaySeek,
    captureCurrentFrameDataUrl,
    releaseMarkerPointerCapture,
    removeMarkerDragListeners,
  }
}
