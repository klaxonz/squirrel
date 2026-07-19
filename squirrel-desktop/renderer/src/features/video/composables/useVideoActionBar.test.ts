import { ref } from 'vue'
import { describe, expect, it, vi } from 'vitest'

import type { VideoPageVideo } from '@/features/playback/types/videoPlayback'
import useVideoActionBar from './useVideoActionBar'

const createVideo = (interactionType?: number) => ref<VideoPageVideo | null>({
  id: 42,
  title: 'Test video',
  source: 'local',
  interaction_type: interactionType,
})

const setupActionBar = ({
  interactionType,
  toggleLike = vi.fn().mockResolvedValue(undefined),
  deleteInteraction = vi.fn().mockResolvedValue(undefined),
  onInteractionError = vi.fn(),
}: {
  interactionType?: number
  toggleLike?: ReturnType<typeof vi.fn>
  deleteInteraction?: ReturnType<typeof vi.fn>
  onInteractionError?: ReturnType<typeof vi.fn>
} = {}) => {
  const video = createVideo(interactionType)
  const commitInteractionType = vi.fn((target: VideoPageVideo, nextType: string | number | null | undefined) => {
    video.value = { ...target, interaction_type: nextType ?? undefined }
  })
  const actionBar = useVideoActionBar({
    video,
    interactionTypeLike: 1,
    interactionTypeDislike: 2,
    interactionTypeLater: 3,
    toggleLike,
    deleteInteraction,
    commitInteractionType,
    onInteractionError,
    handlePlayRandom: vi.fn().mockResolvedValue(undefined),
  })

  return { video, commitInteractionType, onInteractionError, ...actionBar }
}

describe('useVideoActionBar', () => {
  it('updates the visible like state optimistically through the state owner', async () => {
    let resolveRequest = () => {}
    const toggleLike = vi.fn(() => new Promise<void>((resolve) => { resolveRequest = resolve }))
    const actionBar = setupActionBar({ toggleLike })
    const likeAction = actionBar.videoActions.value.find((action) => action.key === 'like')

    const request = actionBar.handleVideoAction(likeAction!)

    expect(actionBar.video.value?.interaction_type).toBe(1)
    expect(actionBar.videoActions.value.find((action) => action.key === 'like')?.active).toBe(true)
    expect(actionBar.isInteractionUpdating.value).toBe(true)

    resolveRequest()
    await request
    expect(actionBar.isInteractionUpdating.value).toBe(false)
  })

  it('removes the interaction when the active like action is clicked again', async () => {
    const deleteInteraction = vi.fn().mockResolvedValue(undefined)
    const actionBar = setupActionBar({ interactionType: 1, deleteInteraction })
    const likeAction = actionBar.videoActions.value.find((action) => action.key === 'like')

    await actionBar.handleVideoAction(likeAction!)

    expect(deleteInteraction).toHaveBeenCalledWith(42)
    expect(actionBar.video.value?.interaction_type).toBeUndefined()
    expect(actionBar.videoActions.value.find((action) => action.key === 'like')?.active).toBe(false)
  })

  it('rolls back the optimistic state and reports API failures', async () => {
    const error = new Error('network unavailable')
    const toggleLike = vi.fn().mockRejectedValue(error)
    const actionBar = setupActionBar({ toggleLike })
    const likeAction = actionBar.videoActions.value.find((action) => action.key === 'like')

    await actionBar.handleVideoAction(likeAction!)

    expect(actionBar.video.value?.interaction_type).toBeUndefined()
    expect(actionBar.onInteractionError).toHaveBeenCalledWith(error)
  })
})
