import { post } from '@/utils/request'

export const toggleVideoInteraction = async (videoId: string | number, interactionType: number) => {
  return post('/api/video-interaction/toggle-like', {
    video_id: videoId,
    interaction_type: interactionType,
  })
}

export const deleteVideoInteraction = async (videoId: string | number) => {
  return post('/api/video-interaction/delete', { video_id: videoId })
}
