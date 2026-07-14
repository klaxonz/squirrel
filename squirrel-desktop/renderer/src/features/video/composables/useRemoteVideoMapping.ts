import { type ComputedRef, type Ref } from 'vue'
import { useRouter } from 'vue-router'
import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import type { RemoteVideoItem, RemoteChannelProfile } from '@/features/video/composables/useRemoteChannel'
import type { SubscriptionListItem } from '@/features/video/types/subscription'

/**
 * Remote-video → playback-seed mapping + playability gating.
 *
 * Three concerns that all key off a remote video item and the active channel:
 *   1. `canPlayRemoteResult` — is this site/url one of the remotely-playable
 *      patterns (bilibili / pornhub / youtube / youporn)?
 *   2. `buildRemoteVideoSeed` — synthesise a stable playback seed (id hashed
 *      from the url so re-opening the same remote video resumes) carrying the
 *      channel as its subscription.
 *   3. `openRemoteResult` — remember the seed + navigate to the player route.
 *
 * Extracted from Subscribed.vue so the url-hash id scheme + the playability
 * pattern table live in one reusable place — any surface that renders remote
 * videos (search, channel detail, feed) wants the same mapping.
 */
const REMOTE_PLAYABLE_SITE_PATTERNS: Record<string, RegExp> = {
  bilibili: /(?:bilibili\.com\/video\/|b23\.tv\/)/i,
  pornhub: /pornhub\.com\/(?:view_video\.php|video\/|embed\/)/i,
  youtube: /(?:youtube\.com\/|youtu\.be\/)/i,
  youporn: /youporn\.com\/watch\//i,
}

/** Deterministic short id for a remote url so re-opening it resumes playback. */
const hashRemoteUrl = (url: string): string => {
  let hash = 0
  for (let index = 0; index < url.length; index += 1) {
    hash = Math.imul(31, hash) + url.charCodeAt(index)
    hash |= 0
  }
  return Math.abs(hash).toString(36)
}

export interface RemoteVideoSeed {
  id: string
  source: string
  site: string
  title: string
  url: string
  thumbnail: string
  duration: number | null
  publish_date: string | null
  uploaded_at: string | null
  description: string
  subscriptions: RemoteChannelProfile[]
  actors: RemoteChannelProfile[]
}

export interface UseRemoteVideoMappingOptions {
  activeChannel: ComputedRef<SubscriptionListItem | null> | Ref<SubscriptionListItem | null>
}

export interface UseRemoteVideoMappingReturn {
  canPlayRemoteResult: (item: RemoteVideoItem) => boolean
  buildRemoteVideoSeed: (item: RemoteVideoItem) => RemoteVideoSeed
  openRemoteResult: (item: RemoteVideoItem) => Promise<void>
}

export function useRemoteVideoMapping(
  options: UseRemoteVideoMappingOptions,
): UseRemoteVideoMappingReturn {
  const { activeChannel } = options
  const router = useRouter()

  const canPlayRemoteResult = (item: RemoteVideoItem): boolean => {
    const pattern = REMOTE_PLAYABLE_SITE_PATTERNS[item.site]
    return !!pattern && pattern.test(String(item.url || ''))
  }

  const buildRemoteVideoSeed = (item: RemoteVideoItem): RemoteVideoSeed => {
    const channel = activeChannel.value
    const url = String(item.url || '').trim()
    // Fallback subscription synthesised from the active channel so a remote
    // video whose source didn't list subscriptions still carries its channel.
    const channelSubscription: RemoteChannelProfile = {
      id: channel?.id ?? null,
      type: 'CHANNEL',
      name: channel?.name || '',
      url: channel?.url || '',
      avatar: channel?.avatar || '',
      is_nsfw: channel?.is_nsfw === true,
    }
    return {
      id: `remote-${item.site}-${hashRemoteUrl(url)}`,
      source: 'remote',
      site: item.site,
      title: item.title,
      url,
      thumbnail: item.thumbnail || '',
      duration: item.duration || null,
      publish_date: item.publish_date || null,
      uploaded_at: item.publish_date || null,
      description: item.description || '',
      subscriptions: item.subscriptions?.length ? item.subscriptions : [channelSubscription],
      actors: item.actors || [],
    }
  }

  const openRemoteResult = async (item: RemoteVideoItem) => {
    if (!item.url || !canPlayRemoteResult(item)) return
    const videoSeed = buildRemoteVideoSeed(item)
    rememberVideoPlaybackSeed(videoSeed)
    await router.push({ name: 'VideoPlay', params: { videoId: videoSeed.id } })
  }

  return {
    canPlayRemoteResult,
    buildRemoteVideoSeed,
    openRemoteResult,
  }
}

/** Exposed for tests / other surfaces that need the playability table directly. */
export { REMOTE_PLAYABLE_SITE_PATTERNS }
