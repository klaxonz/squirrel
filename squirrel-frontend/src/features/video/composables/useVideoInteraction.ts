import { deleteVideoInteraction, toggleVideoInteraction } from '@/shared/api'

type VideoId = string | number
type InteractionType = number

export default function useVideoInteraction() {
  const INTERACTION_TYPE = {
    LIKE: 1,
    DISLIKE: 2,
    LATER: 3,
  }

  const toggleLike = async (videoId: VideoId, interactionType: InteractionType) => {
    return toggleVideoInteraction(videoId, interactionType)
  }

  const deleteInteraction = async (videoId: VideoId) => {
    return deleteVideoInteraction(videoId)
  }

  return {
    INTERACTION_TYPE,
    toggleLike,
    deleteInteraction,
  }
}
