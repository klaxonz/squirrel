import type { Router } from 'vue-router'

import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'

type VideoCardSeed = { id: string | number }
type SubscriptionId = string | number | null | undefined

export function useVideoCardNavigation(router: Router) {
  const openVideo = (video: VideoCardSeed) => {
    rememberVideoPlaybackSeed(video)
    router.push({ name: 'VideoPlay', params: { videoId: String(video.id) } })
  }

  const openSubscription = (id: SubscriptionId) => {
    if (id == null || id === '') return
    router.push({ name: 'SubscriptionAllVideos', params: { id: String(id) } })
  }

  return { openVideo, openSubscription }
}
