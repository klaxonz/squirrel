import { computed } from 'vue'
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
  handleAddToPlaylist,
  handlePlayRandom,
}: {
  video: Ref<VideoPageVideo | null>
  interactionTypeLike: string | number
  interactionTypeDislike: string | number
  interactionTypeLater: string | number
  toggleLike: (videoId: VideoId, interactionType: string | number) => Promise<{ error?: unknown }>
  deleteInteraction: (videoId: VideoId) => Promise<{ error?: unknown }>
  ensureLocalVideo?: (video: VideoPageVideo) => Promise<VideoPageVideo | null>
  handleAddToPlaylist: () => Promise<void>
  handlePlayRandom: () => Promise<void>
}) {
  const currentInteractionType = computed(() => video.value?.interaction_type ?? undefined)
  const isLaterActionActive = computed(() => currentInteractionType.value === interactionTypeLater)

  const updateVideoInteraction = async (targetVideo: VideoPageVideo, nextInteractionType: InteractionType) => {
    const localVideo = ensureLocalVideo && targetVideo.source === 'remote'
      ? await ensureLocalVideo(targetVideo)
      : targetVideo
    if (!localVideo?.id) return

    if (nextInteractionType != null && localVideo.interaction_type !== nextInteractionType) {
      const { error } = await toggleLike(localVideo.id, nextInteractionType)
      if (!error) {
        localVideo.interaction_type = nextInteractionType
      }
      return
    }

    const { error } = await deleteInteraction(localVideo.id)
    if (!error) {
      localVideo.interaction_type = undefined
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
    handleVideoAction,
  }
}
