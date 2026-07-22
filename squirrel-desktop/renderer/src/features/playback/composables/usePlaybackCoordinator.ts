import { PlaybackCoordinator } from '@/features/playback/components/video-player/core/PlaybackCoordinator'

let coordinatorInstance: PlaybackCoordinator | null = null

/** App-scoped lifecycle authority shared by resolution, engine and UI. */
export function usePlaybackCoordinator(): PlaybackCoordinator {
  if (!coordinatorInstance) coordinatorInstance = new PlaybackCoordinator()
  return coordinatorInstance
}

export function __resetPlaybackCoordinatorForTests(): void {
  coordinatorInstance?.destroy()
  coordinatorInstance = null
}
