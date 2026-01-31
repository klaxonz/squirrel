import { post } from '../utils/request'

export default function useVideoInteraction() {
  const INTERACTION_TYPE = {
    LIKE: 1,
    DISLIKE: 2,
    LATER: 3,
  }

  const toggleLike = async (videoId, interactionType) => {
    return post('/api/video-interaction/toggle-like', {
      video_id: videoId,
      interaction_type: interactionType,
    })
  }

  const deleteInteraction = async (videoId) => {
    return post('/api/video-interaction/delete', {
      video_id: videoId,
    })
  }

  return {
    INTERACTION_TYPE,
    toggleLike,
    deleteInteraction,
  }
}
