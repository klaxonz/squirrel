import { computed, nextTick, ref } from 'vue'
import type { ComputedRef, Ref } from 'vue'

import { deleteVideoClipMarker, updateVideoClipMarker } from '@/api/videoClipMarkers'

type VideoId = string | number

type ClipMarkerLike = {
  id?: VideoId
  title?: string | null
  start_time: number
  end_time: number
  duration_seconds?: number | null
  preview_image_url?: string | null
}

type VideoLike = {
  clip_markers?: ClipMarkerLike[]
}

const MARKER_COLORS = ['#f87171', '#fb923c', '#facc15', '#4ade80', '#34d399', '#22d3ee', '#60a5fa', '#a78bfa', '#f472b6']

export default function useVideoClipMarkers({
  video,
  seekToTime,
}: {
  video: Ref<VideoLike | null>
  seekToTime: (time: number) => Promise<void>
}) {
  const currentPlaybackTime = ref(0)
  const editingClipMarkerId = ref<VideoId | null>(null)
  const clipMarkerTitleDraft = ref('')
  const isSavingClipMarkerTitle = ref(false)

  const clipMarkers: ComputedRef<ClipMarkerLike[]> = computed(() => (
    Array.isArray(video.value?.clip_markers) ? video.value.clip_markers : []
  ))

  const handlePlaybackTimeUpdate = (currentTime: number) => {
    currentPlaybackTime.value = currentTime
  }

  const handleClipMarkersUpdated = (markers: ClipMarkerLike[]) => {
    if (!video.value) return
    video.value.clip_markers = markers
  }

  const handleClipMarkerSeek = async (time: number) => {
    currentPlaybackTime.value = Number(time) || 0
    await seekToTime(time)
  }

  const cancelClipMarkerTitleEdit = () => {
    editingClipMarkerId.value = null
    clipMarkerTitleDraft.value = ''
    isSavingClipMarkerTitle.value = false
  }

  const handleDeleteMarker = async (markerId: VideoId) => {
    const { error } = await deleteVideoClipMarker(markerId)
    if (error || !video.value) return

    video.value.clip_markers = (video.value.clip_markers || []).filter((marker) => marker.id !== markerId)
    if (String(editingClipMarkerId.value || '') === String(markerId || '')) {
      cancelClipMarkerTitleEdit()
    }
  }

  const getClipMarkerTitle = (marker: ClipMarkerLike) => String(marker.title || '').trim()
  const isEditingClipMarker = (markerId: VideoId) => String(editingClipMarkerId.value || '') === String(markerId || '')

  const focusClipMarkerTitleInput = async (markerId: VideoId) => {
    await nextTick()
    const input = document.querySelector(`[data-clip-title-input="${markerId}"]`)
    if (input instanceof HTMLInputElement) {
      input.focus()
      input.select()
    }
  }

  const startClipMarkerTitleEdit = async (marker: ClipMarkerLike) => {
    editingClipMarkerId.value = marker.id ?? null
    clipMarkerTitleDraft.value = String(marker.title || '')
    if (marker.id != null) {
      await focusClipMarkerTitleInput(marker.id)
    }
  }

  const commitClipMarkerTitle = async (marker: ClipMarkerLike) => {
    if (!video.value || marker.id == null || !isEditingClipMarker(marker.id) || isSavingClipMarkerTitle.value) return

    const nextTitle = String(clipMarkerTitleDraft.value || '').trim() || null
    const currentTitle = String(marker.title || '').trim() || null
    if (currentTitle === nextTitle) {
      cancelClipMarkerTitleEdit()
      return
    }

    isSavingClipMarkerTitle.value = true
    const { data, error } = await updateVideoClipMarker(marker.id, { title: nextTitle })
    isSavingClipMarkerTitle.value = false

    if (error || !data) {
      return
    }

    video.value.clip_markers = (video.value.clip_markers || []).map((item) => (
      String(item.id) === String(marker.id) ? data : item
    ))
    cancelClipMarkerTitleEdit()
  }

  const handleClipRowClick = (marker: ClipMarkerLike) => {
    if (marker.id != null && isEditingClipMarker(marker.id)) return
    void handleClipMarkerSeek(marker.start_time)
  }

  const getMarkerColor = (marker: ClipMarkerLike) => {
    const index = clipMarkers.value.findIndex((item) => item.id === marker.id)
    return MARKER_COLORS[index % MARKER_COLORS.length]
  }

  const isClipActive = (marker: ClipMarkerLike) => {
    const t = currentPlaybackTime.value
    return t >= marker.start_time && t <= marker.end_time
  }

  const getClipProgress = (marker: ClipMarkerLike) => {
    const t = currentPlaybackTime.value
    if (t < marker.start_time) return 0
    if (t > marker.end_time) return 100

    const total = marker.end_time - marker.start_time
    if (!total) return 0
    return Math.round(((t - marker.start_time) / total) * 100)
  }

  const formatClipDuration = (marker: ClipMarkerLike) => {
    const duration = marker.duration_seconds ?? (marker.end_time - marker.start_time)
    if (duration < 60) return `${Math.round(duration)}s`
    const minutes = Math.floor(duration / 60)
    const seconds = Math.round(duration % 60)
    return seconds ? `${minutes}m ${seconds}s` : `${minutes}m`
  }

  return {
    currentPlaybackTime,
    clipMarkers,
    clipMarkerTitleDraft,
    isSavingClipMarkerTitle,
    handlePlaybackTimeUpdate,
    handleClipMarkersUpdated,
    handleClipMarkerSeek,
    handleDeleteMarker,
    getClipMarkerTitle,
    isEditingClipMarker,
    startClipMarkerTitleEdit,
    cancelClipMarkerTitleEdit,
    commitClipMarkerTitle,
    handleClipRowClick,
    getMarkerColor,
    isClipActive,
    getClipProgress,
    formatClipDuration,
  }
}
