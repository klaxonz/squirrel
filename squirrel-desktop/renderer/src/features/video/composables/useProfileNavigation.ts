import type { Router } from 'vue-router'

import { resolveRemoteChannelSite } from '@/shared/lib/remoteChannelSite'
import { Logger } from '@/shared/lib/logger'
import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import { prefetchDesktopPlaybackSource } from '@/features/video/composables/useVideoOperations'
import type { VideoProfile } from '@/features/video/types/video'

export type ProfileNavTarget = {
  id?: number | string | null
  url?: string | null
  name?: string | null
  avatar?: string | null
  is_nsfw?: boolean | null
  profile_source?: VideoProfile['profile_source']
  type?: string | null
  site?: string | null
}

type VideoWithProfiles = {
  subscriptions?: VideoProfile[] | null
  actors?: VideoProfile[] | null
}

const hasId = (id: ProfileNavTarget['id']): id is string | number =>
  id != null && String(id).trim() !== ''

/** Prefer subscriptions when non-empty; empty [] must fall through to actors. */
export function pickPrimaryProfile(video: VideoWithProfiles | null | undefined): VideoProfile | null {
  if (!video) return null
  const subs = video.subscriptions ?? []
  const actors = video.actors ?? []
  if (subs.length > 0) return subs[0]
  if (actors.length > 0) return actors[0]
  return null
}

/** Display names with empty-array-safe fallback (subscriptions=[] is truthy). */
export function profileDisplayNames(video: VideoWithProfiles | null | undefined, fallback = '未知'): string {
  if (!video) return fallback
  const subs = video.subscriptions ?? []
  const actors = video.actors ?? []
  const source = subs.length > 0 ? subs : actors
  const names = source.map((p) => p.name).filter(Boolean)
  return names.length ? names.join(' / ') : fallback
}

export function useProfileNavigation(router: Router) {
  // List cards already carry url/title. Seed the full object so playback can
  // start resolving immediately without waiting on /api/video/detail, and kick
  // off a best-effort desktop resolve so the first paint can hit cache.
  const openVideo = (video: { id: string | number; url?: string | null; title?: string | null }) => {
    rememberVideoPlaybackSeed(video)
    void prefetchDesktopPlaybackSource(video)
    router.push({ name: 'VideoPlay', params: { videoId: String(video.id) } })
  }

  /** Legacy: only when the id is known to be a subscription id. */
  const openSubscription = (id: string | number | null | undefined) => {
    if (id == null || id === '') return
    router.push({ name: 'SubscriptionAllVideos', params: { id: String(id) } })
  }

  const openProfile = async (
    profile: ProfileNavTarget | null | undefined,
    hint?: 'subscription' | 'creator',
  ) => {
    if (!profile) return

    const source = profile.profile_source || hint
    const id = profile.id
    const url = String(profile.url || '').trim()

    if (source === 'subscription' && hasId(id)) {
      await router.push({ name: 'SubscriptionAllVideos', params: { id: String(id) } })
      return
    }

    if (source === 'creator' && hasId(id)) {
      await router.push({ name: 'CreatorAllVideos', params: { id: String(id) } })
      return
    }

    // Source-less: subscriptions[] callers should pass hint, else try remote URL.
    if (!source && hasId(id) && hint === 'subscription') {
      await router.push({ name: 'SubscriptionAllVideos', params: { id: String(id) } })
      return
    }
    if (!source && hasId(id) && hint === 'creator') {
      await router.push({ name: 'CreatorAllVideos', params: { id: String(id) } })
      return
    }

    // Metadata / unknown source with local-looking id: prefer remote if URL maps.
    if (url) {
      const remoteSite = resolveRemoteChannelSite(url)
      if (remoteSite) {
        await router.push({
          name: 'RemoteChannelDetail',
          query: {
            site: remoteSite,
            url,
            id: hasId(id) ? String(id) : undefined,
            name: profile.name || undefined,
            avatar: profile.avatar || undefined,
            is_nsfw: profile.is_nsfw === true ? 'true' : undefined,
          },
        })
        return
      }
    }

    // Last-resort: treat bare id without source as subscription only when hint says so.
    // Never treat creator/metadata bare ids as subscription.
    if (!source && hasId(id) && !url) {
      Logger.debug('[openProfile] Ambiguous profile without source/url; no-op', profile)
      return
    }

    Logger.debug('[openProfile] No navigable target for profile', profile)
  }

  return { openVideo, openSubscription, openProfile }
}
