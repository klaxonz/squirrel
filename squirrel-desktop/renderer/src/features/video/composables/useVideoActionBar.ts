import { computed, ref } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import type { AppIconName } from '@/shared/icons/app-icons'
import type { VideoId, VideoPageVideo } from '@/features/playback/types/videoPlayback'

type InteractionType = string | number | null | undefined

type VideoAction = {
  key: string
  label: string
  icon: AppIconName
  active: boolean
  tone: string
  variant?: string
  hint?: string
  href?: string
  onClick?: () => Promise<void> | void
}

export default function useVideoActionBar({
  video,
  interactionTypeLike,
  interactionTypeDislike,
  interactionTypeLater,
  toggleLike,
  deleteInteraction,
  ensureLocalVideo,
  commitInteractionType,
  onInteractionError,
  handleAddToPlaylist,
  handlePlayRandom,
}: {
  video: Ref<VideoPageVideo | null>
  interactionTypeLike: string | number
  interactionTypeDislike: string | number
  interactionTypeLater: string | number
  toggleLike: (videoId: VideoId, interactionType: string | number) => Promise<unknown>
  deleteInteraction: (videoId: VideoId) => Promise<unknown>
  ensureLocalVideo?: (video: VideoPageVideo) => Promise<VideoPageVideo | null>
  commitInteractionType: (video: VideoPageVideo, interactionType: InteractionType) => void
  onInteractionError?: (error: unknown) => void
  handleAddToPlaylist: () => Promise<void>
  handlePlayRandom: () => Promise<void>
}) {
  const currentInteractionType = computed(() => video.value?.interaction_type ?? undefined)
  const isLaterActionActive = computed(() => currentInteractionType.value === interactionTypeLater)
  const isInteractionUpdating = ref(false)

  const updateVideoInteraction = async (targetVideo: VideoPageVideo, nextInteractionType: InteractionType) => {
    if (isInteractionUpdating.value) return
    isInteractionUpdating.value = true

    let localVideo: VideoPageVideo | null = null
    let previousInteractionType: InteractionType = currentInteractionType.value
    try {
      localVideo = ensureLocalVideo && targetVideo.source === 'remote'
        ? await ensureLocalVideo(targetVideo)
        : targetVideo
      if (!localVideo?.id) throw new Error('无法保存当前视频')

      previousInteractionType = currentInteractionType.value
      const nextCommittedType = nextInteractionType != null && previousInteractionType !== nextInteractionType
        ? nextInteractionType
        : undefined

      // PlaybackSession exposes a deep readonly projection. Route every
      // optimistic state change through its owner instead of mutating the
      // projected video object (which Vue correctly rejects at runtime).
      commitInteractionType(localVideo, nextCommittedType)

      if (nextCommittedType != null) {
        await toggleLike(localVideo.id, nextCommittedType)
      } else {
        await deleteInteraction(localVideo.id)
      }
    } catch (error) {
      if (localVideo) commitInteractionType(localVideo, previousInteractionType)
      onInteractionError?.(error)
    } finally {
      isInteractionUpdating.value = false
    }
  }

  const videoPrimaryActions: ComputedRef<VideoAction[]> = computed(() => {
    const actions: VideoAction[] = [
      {
        key: 'like',
        label: '喜欢',
        icon: 'like',
        active: currentInteractionType.value === interactionTypeLike,
        tone: 'like',
        variant: 'primary',
        onClick: () => {
          if (!video.value) return
          return updateVideoInteraction(video.value, interactionTypeLike)
        },
      },
      {
        key: 'dislike',
        label: '不喜欢',
        icon: 'dislike',
        active: currentInteractionType.value === interactionTypeDislike,
        tone: 'danger',
        variant: 'secondary',
        onClick: () => {
          if (!video.value) return
          return updateVideoInteraction(video.value, interactionTypeDislike)
        },
      },
      {
        key: 'later',
        label: '稍后看',
        icon: isLaterActionActive.value ? 'watchLaterActive' : 'watchLater',
        active: isLaterActionActive.value,
        tone: 'later',
        variant: 'primary',
        onClick: () => {
          if (!video.value) return
          return updateVideoInteraction(video.value, interactionTypeLater)
        },
      },
      {
        key: 'add-playlist',
        label: '播放列表',
        icon: 'addToPlaylist',
        active: false,
        tone: 'neutral',
        variant: 'secondary',
        onClick: handleAddToPlaylist,
      },
    ]

    if (video.value?.url) {
      actions.push({
        key: 'source',
        label: '原视频',
        icon: 'externalLink',
        active: false,
        tone: 'neutral',
        variant: 'secondary',
        href: video.value.url,
      })
    }

    return actions
  })

  const videoOverflowActions: ComputedRef<VideoAction[]> = computed(() => ([
    {
      key: 'random',
      label: '随机播放',
      icon: 'shuffle',
      active: false,
      tone: 'neutral',
      hint: '',
      onClick: handlePlayRandom,
    },
  ]))

  const videoActions = computed(() => [...videoPrimaryActions.value, ...videoOverflowActions.value])

  const handleVideoAction = async (action: VideoAction) => {
    if (action.href || !action.onClick) return
    await action.onClick()
  }

  return {
    videoActions,
    videoOverflowActions,
    isInteractionUpdating,
    handleVideoAction,
  }
}
