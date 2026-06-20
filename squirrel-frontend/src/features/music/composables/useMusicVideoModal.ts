import { ref, type Ref } from 'vue'
import { getMusicTrackMv, getMusicVideoUrl, type MusicTrack } from '@/shared/api/music'
import { Logger } from '@/shared/lib/logger'
import { useToast } from '@/shared/components/toast/useToast'

/**
 * Music video (MV) modal state + async URL resolution.
 *
 * Owns the modal visibility, title, and resolved video URL for the two entry
 * points that open it: playing a track's MV (resolve MV id → resolve URL) and
 * playing an artist video (resolve URL directly). Both open the modal
 * optimistically, then fill the URL once the backend responds, with a toast on
 * failure. Extracted from Music.vue so the two near-duplicate open-then-fetch
 * flows + their error handling live in one place.
 */
export interface MusicArtistVideo {
  id: string
  name: string
}

export interface UseMusicVideoModalReturn {
  videoModalVisible: Ref<boolean>
  videoTitle: Ref<string>
  videoUrl: Ref<string>
  handlePlayMv: (track: MusicTrack) => Promise<void>
  handlePlayArtistVideo: (video: MusicArtistVideo) => void
  handleCloseVideoModal: () => void
}

export function useMusicVideoModal(): UseMusicVideoModalReturn {
  const toast = useToast()

  const videoModalVisible = ref(false)
  const videoTitle = ref('')
  const videoUrl = ref('')

  const openModal = (title: string) => {
    videoTitle.value = title
    videoModalVisible.value = true
    videoUrl.value = ''
  }

  const resolveUrl = async (videoId: string): Promise<string> => {
    const data = await getMusicVideoUrl(videoId)
    return data?.url || ''
  }

  const handlePlayMv = async (track: MusicTrack) => {
    if (!track.album_audio_id) return
    try {
      const mvData = await getMusicTrackMv(track.album_audio_id)
      const mv = mvData?.items?.[0]
      if (!mv?.id) return

      openModal(`${track.title} - ${track.artist}`)
      videoUrl.value = await resolveUrl(mv.id)
    } catch (err) {
      Logger.warn('handlePlayMv failed', err)
      toast.error('MV 播放失败，请稍后重试')
    }
  }

  const handlePlayArtistVideo = (video: MusicArtistVideo) => {
    openModal(video.name)

    resolveUrl(video.id).catch((err) => {
      Logger.warn('handlePlayArtistVideo failed', err)
      toast.error('MV 播放失败，请稍后重试')
    })
  }

  const handleCloseVideoModal = () => {
    videoModalVisible.value = false
    videoUrl.value = ''
  }

  return {
    videoModalVisible,
    videoTitle,
    videoUrl,
    handlePlayMv,
    handlePlayArtistVideo,
    handleCloseVideoModal,
  }
}
