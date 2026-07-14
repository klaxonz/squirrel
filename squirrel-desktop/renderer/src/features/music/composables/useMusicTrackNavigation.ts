import { type ComputedRef, type Ref } from 'vue'
import {
  getMusicAlbumDetail,
  getMusicArtistDetail,
  type MusicAlbum,
  type MusicArtist,
  type MusicTrack,
} from '@/shared/api/music'
import { Logger } from '@/shared/lib/logger'
import { useToast } from '@/shared/components/toast/useToast'

/**
 * Resolve + navigate to artist/album detail from a track or album context.
 *
 * The three flows share one shape: fetch detail by id, then hand the resolved
 * entity to the view's select handler (which navigates). Each surfaces a toast
 * on failure. `handleSelectArtistFromAlbum` synthesises a minimal artist object
 * from the album's `artist_id`/`artist` fields (the album detail payload doesn't
 * include a full artist record).
 *
 * Extracted from Music.vue so the fetch-then-navigate + error-toast pattern
 * isn't triplicated inline.
 */
export interface UseMusicTrackNavigationOptions {
  /** Currently selected album (used to synthesise an artist from album fields). */
  selectedAlbum: ComputedRef<MusicAlbum | null> | Ref<MusicAlbum | null>
  /** View handler that selects + navigates to an artist. */
  onSelectArtist: (artist: MusicArtist) => void | Promise<void>
  /** View handler that selects + navigates to an album. */
  onSelectAlbum: (album: MusicAlbum) => void | Promise<void>
}

export interface UseMusicTrackNavigationReturn {
  handleSelectArtistFromTrack: (track: MusicTrack) => Promise<void>
  handleSelectAlbumFromTrack: (track: MusicTrack) => Promise<void>
  handleSelectArtistFromAlbum: () => void
}

export function useMusicTrackNavigation(
  options: UseMusicTrackNavigationOptions,
): UseMusicTrackNavigationReturn {
  const { selectedAlbum, onSelectArtist, onSelectAlbum } = options
  const toast = useToast()

  const handleSelectArtistFromTrack = async (track: MusicTrack) => {
    if (!track.artist_id) return
    try {
      const data = await getMusicArtistDetail(track.artist_id)
      if (data) await onSelectArtist(data)
    } catch (err) {
      Logger.warn('handleSelectArtistFromTrack failed', err)
      toast.error('歌手信息获取失败')
    }
  }

  const handleSelectAlbumFromTrack = async (track: MusicTrack) => {
    if (!track.album_id) return
    try {
      const data = await getMusicAlbumDetail(track.album_id)
      if (data) await onSelectAlbum(data)
    } catch (err) {
      Logger.warn('handleSelectAlbumFromTrack failed', err)
      toast.error('专辑信息获取失败')
    }
  }

  const handleSelectArtistFromAlbum = () => {
    const album = selectedAlbum.value
    if (!album?.artist_id) return
    const artist: MusicArtist = {
      id: album.artist_id,
      name: album.artist || '',
      avatar: '',
      intro: '',
      song_count: 0,
      album_count: 0,
      fan_count: 0,
    }
    onSelectArtist(artist)
  }

  return {
    handleSelectArtistFromTrack,
    handleSelectAlbumFromTrack,
    handleSelectArtistFromAlbum,
  }
}
