import { computed, nextTick, ref } from 'vue'
import type { ComputedRef, Ref } from 'vue'

import { deleteVideoClipMarker, updateVideoClipMarker } from '@/shared/api/videoClipMarkers'
import type { ClipMarker, VideoId, VideoPageVideo } from '@/features/playback/types/videoPlayback'
import type { PlaybackSession } from '@/features/playback/composables/usePlaybackSession'

const MARKER_COLORS = ['#f87171', '#fb923c', '#facc15', '#4ade80', '#34d399', '#22d3ee', '#60a5fa', '#a78bfa', '#f472b6']

// ADR-0002 PR2 — clip-marker mutations used to write
// `video.value.clip_markers = ...` in place. Since `video` is now a read-only
// projection of PlaybackSession.facts.video, those writes route through
// session.update({ video: { ...video, clip_markers: [...] } }) instead. The
// session is injected; reads still go through the `video` projection.
export default function useVideoClipMarkers({
  video,
  session,
  seekToTime,
}: {
  video: Ref<VideoPageVideo | null>
  session: PlaybackSession
  seekToTime: (time: number) => Promise<void>
}) {
  const currentPlaybackTime = ref(0)
  const editingClipMarkerId = ref<VideoId | null>(null)
  const clipMarkerTitleDraft = ref('')
  const isSavingClipMarkerTitle = ref(false)

  const clipMarkers: ComputedRef<ClipMarker[]> = computed(() => (
    Array.isArray(video.value?.clip_markers) ? video.value.clip_markers : []
  ))

  const handlePlaybackTimeUpdate = (currentTime: number) => {
    currentPlaybackTime.value = currentTime
  }

  const handleClipMarkersUpdated = (markers: ClipMarker[]) => {
    const current = video.value
    if (!current) return
    session.update({ video: { ...current, clip_markers: markers } })
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
    if (error) return
    const current = video.value
    if (!current) return

    const nextMarkers = (current.clip_markers || []).filter((marker) => marker.id !== markerId)
    session.update({ video: { ...current, clip_markers: nextMarkers } })
    if (String(editingClipMarkerId.value || '') === String(markerId || '')) {
      cancelClipMarkerTitleEdit()
    }
  }

  const getClipMarkerTitle = (marker: ClipMarker) => String(marker.title || '').trim()
  const isEditingClipMarker = (markerId: VideoId) => String(editingClipMarkerId.value || '') === String(markerId || '')

  const focusClipMarkerTitleInput = async (markerId: VideoId) => {
    await nextTick()
    const input = document.querySelector(`[data-clip-title-input="${markerId}"]`)
    if (input instanceof HTMLInputElement) {
      input.focus()
      input.select()
    }
  }

  const startClipMarkerTitleEdit = async (marker: ClipMarker) => {
    editingClipMarkerId.value = marker.id ?? null
    clipMarkerTitleDraft.value = String(marker.title || '')
    if (marker.id != null) {
      await focusClipMarkerTitleInput(marker.id)
    }
  }

  const commitClipMarkerTitle = async (marker: ClipMarker) => {
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

    const current = video.value
    if (!current) return
    const nextMarkers = (current.clip_markers || []).map((item) => (
      String(item.id) === String(marker.id) ? data : item
    ))
    session.update({ video: { ...current, clip_markers: nextMarkers } })
    cancelClipMarkerTitleEdit()
  }

  const handleClipRowClick = (marker: ClipMarker) => {
    if (marker.id != null && isEditingClipMarker(marker.id)) return
    void handleClipMarkerSeek(marker.start_time)
  }

  const getMarkerColor = (marker: ClipMarker) => {
    const index = clipMarkers.value.findIndex((item) => item.id === marker.id)
    return MARKER_COLORS[index % MARKER_COLORS.length]
  }

  const isClipActive = (marker: ClipMarker) => {
    const t = currentPlaybackTime.value
    return t >= marker.start_time && t <= marker.end_time
  }

  const getClipProgress = (marker: ClipMarker) => {
    const t = currentPlaybackTime.value
    if (t < marker.start_time) return 0
    if (t > marker.end_time) return 100

    const total = marker.end_time - marker.start_time
    if (!total) return 0
    return Math.round(((t - marker.start_time) / total) * 100)
  }

  const formatClipDuration = (marker: ClipMarker) => {
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
