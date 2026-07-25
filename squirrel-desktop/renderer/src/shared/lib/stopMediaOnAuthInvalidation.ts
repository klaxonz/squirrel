import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import { usePlaybackSession } from '@/features/playback/composables/usePlaybackSession'
import { usePlayerStore } from '@/features/playback/stores/player'
import { Logger } from '@/shared/lib/logger'

/**
 * Tear down every live media session when auth ends.
 *
 * Layout unmount alone is not enough: picture-in-picture can keep a video
 * surface alive after `release()`, and the music bar may leave an in-flight
 * resolve that re-arms audio. Call this from the auth-clear path so logout,
 * 401 invalidation, and server switches all stop playback at the source.
 */
export function stopMediaOnAuthInvalidation(): void {
  try {
    if (typeof document !== 'undefined' && document.pictureInPictureElement) {
      void document.exitPictureInPicture().catch(() => {
        // PiP may already be closing with the player; ignore.
      })
    }
  } catch (error) {
    Logger.warn('[auth] Failed to exit picture-in-picture on logout', error)
  }

  try {
    useMusicPlayerStore().clear()
  } catch (error) {
    Logger.warn('[auth] Failed to clear music player on logout', error)
  }

  try {
    usePlaybackSession().end()
  } catch (error) {
    Logger.warn('[auth] Failed to end video session on logout', error)
  }

  try {
    const playerStore = usePlayerStore()
    playerStore.playerRef = null
    playerStore.target = null
    playerStore.adapter = null
    playerStore.handlers = {}
  } catch (error) {
    Logger.warn('[auth] Failed to clear video player wiring on logout', error)
  }
}
