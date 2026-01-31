import { post } from '@/utils/request'

export const toggleVideoInteraction = async (videoId, interactionType) => {
  return post('/api/video-interaction/toggle-like', {
    video_id: videoId,
    interaction_type: interactionType,
  })
}

export const deleteVideoInteraction = async (videoId) => {
  return post('/api/video-interaction/delete', { video_id: videoId })
}

