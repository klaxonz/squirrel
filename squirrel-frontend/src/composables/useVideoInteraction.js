import { deleteVideoInteraction, toggleVideoInteraction } from '@/api'

export default function useVideoInteraction() {
  const INTERACTION_TYPE = {
    LIKE: 1,
    DISLIKE: 2,
    LATER: 3,
  }

  const toggleLike = async (videoId, interactionType) => {
    return toggleVideoInteraction(videoId, interactionType)
  }

  const deleteInteraction = async (videoId) => {
    return deleteVideoInteraction(videoId)
  }

  return {
    INTERACTION_TYPE,
    toggleLike,
    deleteInteraction,
  }
}
