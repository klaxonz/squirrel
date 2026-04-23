import { computed } from 'vue'
import type { ComputedRef, Ref } from 'vue'

type VideoId = string | number

type InteractionType = string | number | null

type VideoLike = {
  id?: VideoId
  url?: string | null
  interaction_type?: InteractionType
  [key: string]: unknown
}

type VideoAction = {
  key: string
  label: string
  icon: string
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
  handleAddToPlaylist,
  handlePlayRandom,
}: {
  video: Ref<VideoLike | null>
  interactionTypeLike: string | number
  interactionTypeDislike: string | number
  interactionTypeLater: string | number
  toggleLike: (videoId: VideoId, interactionType: string | number) => Promise<{ error?: unknown }>
  deleteInteraction: (videoId: VideoId) => Promise<{ error?: unknown }>
  handleAddToPlaylist: () => Promise<void>
  handlePlayRandom: () => Promise<void>
}) {
  const currentInteractionType = computed(() => video.value?.interaction_type ?? null)
  const isLaterActionActive = computed(() => currentInteractionType.value === interactionTypeLater)

  const updateVideoInteraction = async (targetVideo: VideoLike, nextInteractionType: string | number | null) => {
    if (targetVideo.id == null) return

    if (nextInteractionType !== null && targetVideo.interaction_type !== nextInteractionType) {
      const { error } = await toggleLike(targetVideo.id, nextInteractionType)
      if (!error) {
        targetVideo.interaction_type = nextInteractionType
      }
      return
    }

    const { error } = await deleteInteraction(targetVideo.id)
    if (!error) {
      targetVideo.interaction_type = null
    }
  }

  const videoPrimaryActions: ComputedRef<VideoAction[]> = computed(() => {
    const actions: VideoAction[] = [
      {
        key: 'like',
        label: '喜欢',
        icon: 'lucide:thumbs-up',
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
        icon: 'lucide:thumbs-down',
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
        icon: isLaterActionActive.value ? 'lucide:bookmark-check' : 'lucide:bookmark-plus',
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
        icon: 'lucide:list-plus',
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
        icon: 'lucide:external-link',
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
      icon: 'lucide:shuffle',
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
    handleVideoAction,
  }
}
