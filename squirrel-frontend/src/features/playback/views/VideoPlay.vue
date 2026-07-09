<template>
  <div ref="videoPageRef" class="video-play-page" :class="{ 'is-widescreen': isWidescreen }">
    <div
      class="video-play-layout"
      :class="{ 'is-widescreen': isWidescreen }"
    >
      <div
        class="video-play-primary"
        :class="{ 'is-widescreen': isWidescreen }"
      >
        <div
          class="video-player-stage"
          :class="{ 'is-widescreen': isWidescreen }"
        >
          <div
            ref="videoPlayerHostRef"
            class="video-player-host"
          />
        </div>

        <div class="video-play-main" :class="{ 'is-widescreen': isWidescreen }">
          <div v-if="video" class="video-detail">
            <div class="video-detail__title-block">
              <h1 class="app-h2">
                {{ video.title }}
              </h1>
              <div class="video-detail__meta">
                <span>{{ videoPublishedText }}</span>
                <span class="video-detail__dot">·</span>
                <span v-if="video.site" class="video-detail__site">{{ video.site }}</span>
              </div>
            </div>
            
            <div class="video-detail__bar">
              <div class="video-detail__channel-actions">
                <div
                  v-if="primarySubscription"
                  class="video-detail__channel"
                  role="button"
                  tabindex="0"
                  @click="openChannelDetail(primarySubscription)"
                  @keydown.enter.prevent="openChannelDetail(primarySubscription)"
                  @keydown.space.prevent="openChannelDetail(primarySubscription)"
                >
                  <SubscriptionAvatar :src="primarySubscription.avatar" :name="primarySubscription.name || ''" size="xl" />
                  <div class="video-detail__channel-copy">
                    <span>{{ primarySubscription.name }}</span>
                    <small>{{ primarySubscription.total_videos || 0 }} 项视频</small>
                  </div>
                </div>
                <Button
                  v-if="primarySubscriptionUrl"
                  type="button"
                  variant="default"
                  size="sm"
                  class="video-detail__subscribe-button"
                  :class="{ 'is-subscribed': isSubscriptionChecked && isSubscribed }"
                  :disabled="isCheckingSubscription || isSubscribing"
                  @click="handleSubscribe"
                >
                  {{ subscriptionButtonText }}
                </Button>
              </div>

              <div class="video-detail__actions">
                <div class="video-detail__action-group">
                  <Button
                    v-for="action in primaryVisibleActions"
                    :key="action.key"
                    type="button"
                    variant="ghost"
                    size="sm"
                    class="video-detail__action-button"
                    :class="{ 'is-active': action.active }"
                    :aria-pressed="action.active"
                    :aria-label="action.label || action.key"
                    @click="handleVideoAction(action)"
                  >
                    <AppIcon :name="action.icon" class="w-4 h-4" :stroke-width="action.active ? 2.5 : 2" />
                    <span v-if="action.label && action.key === 'like'">{{ action.label }}</span>
                  </Button>
                </div>

                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  class="video-detail__icon-button"
                  title="分享链接"
                  aria-label="分享链接"
                  @click="handleShare"
                >
                  <AppIcon name="share" class="w-4 h-4" />
                </Button>
                <div class="relative" ref="moreMenuRef">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    class="video-detail__icon-button"
                    :aria-expanded="moreMenuOpen"
                    aria-haspopup="menu"
                    aria-label="更多操作"
                    @click.stop="moreMenuOpen = !moreMenuOpen"
                  >
                    <AppIcon name="more" class="w-4 h-4" />
                  </Button>
                  <Transition name="fade">
                    <AppFloatingList
                      v-if="moreMenuOpen"
                      class="video-detail__menu"
                      max-height="16rem"
                    >
                      <AppListOption
                        v-for="action in videoOverflowActions.filter(a => a.key !== 'source')"
                        :key="action.key"
                        role="menuitem"
                        @click.stop="handleVideoAction(action); moreMenuOpen = false"
                      >
                        <AppIcon :name="action.icon" class="w-4 h-4 text-muted-foreground" />
                        {{ action.label }}
                      </AppListOption>
                      <a
                        v-if="video.url"
                        :href="video.url"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="video-detail__menu-link"
                        @click.stop="moreMenuOpen = false"
                      >
                        <AppIcon name="externalLink" class="w-4 h-4 text-muted-foreground" />
                        原视频
                      </a>
                    </AppFloatingList>
                  </Transition>
                </div>
              </div>
            </div>

            <div v-if="displayedVideoActors.length" class="video-detail__actors">
              <div class="video-detail__actor-list no-scrollbar">
                <Button
                  v-for="actor in displayedVideoActors"
                  :key="actor.url || actor.name"
                  type="button"
                  variant="secondary"
                  size="sm"
                  class="video-detail__actor"
                  @click="openChannelDetail(actor)"
                >
                  <SubscriptionAvatar :src="actor.avatar" :name="actor.name || ''" size="xs" />
                  <span class="truncate max-w-[120px]">{{ actor.name }}</span>
                </Button>
              </div>
            </div>

            <div v-if="videoDescription" class="video-detail__description">
              <div
                ref="descriptionTextRef"
                class="relative overflow-hidden"
                :class="{ 'max-h-[4.8em]': !descriptionExpanded }"
              >
                <p class="text-sm leading-relaxed text-foreground/75 whitespace-pre-wrap">
                  {{ videoDescription }}
                </p>
                <div
                  v-if="!descriptionExpanded && hasLongDescription"
                  class="video-detail__description-fade"
                />
              </div>
              <Button
                v-if="hasLongDescription"
                type="button"
                variant="ghost"
                size="xs"
                class="video-detail__description-toggle"
                :aria-expanded="descriptionExpanded"
                @click="descriptionExpanded = !descriptionExpanded"
              >
                {{ descriptionExpanded ? '收起' : '展开' }}
                <AppIcon :name="descriptionExpanded ? 'chevronUp' : 'chevronDown'" class="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
          
          <div v-else class="video-detail__skeleton">
            <div class="space-y-2">
              <AppSkeleton width="75%" height="1.75rem" rounded="var(--radius-lg)" shimmer />
              <AppSkeleton width="9rem" height="1rem" rounded="var(--radius)" shimmer />
            </div>
            <div class="flex items-center gap-4">
              <AppSkeleton width="3rem" height="3rem" rounded="9999px" shimmer />
              <div class="space-y-2 flex-1">
                <AppSkeleton width="7rem" height="1rem" rounded="var(--radius)" shimmer />
                <AppSkeleton width="4rem" height="0.75rem" rounded="var(--radius)" shimmer />
              </div>
              <AppSkeleton width="4rem" height="1.75rem" rounded="9999px" shimmer />
            </div>
            <div class="flex gap-2">
              <AppSkeleton width="4rem" height="2rem" rounded="9999px" shimmer />
              <AppSkeleton width="5rem" height="2rem" rounded="9999px" shimmer />
              <AppSkeleton width="3.5rem" height="2rem" rounded="9999px" shimmer />
            </div>
            <AppSkeleton height="5rem" rounded="var(--radius-xl)" shimmer />
          </div>
        </div>
      </div>

      <div
        class="video-play-aside"
        :class="{ 'is-widescreen': isWidescreen }"
      >
        <AppSegmentedControl
          v-model="asideTab"
          :options="asideTabOptions"
          aria-label="视频侧栏"
          class="w-full"
        />

        <div class="video-play-aside__content">
          <Transition name="fade" mode="out-in">
            <div v-if="asideTab === 'related'" key="related">
              <div v-if="loadingRelated" class="space-y-3">
                <div v-for="n in 4" :key="n" class="flex gap-3">
                  <AppSkeleton width="10rem" height="5.625rem" rounded="var(--radius-md)" class="shrink-0" shimmer />
                  <div class="flex-1 space-y-1.5 py-0.5">
                    <AppSkeleton width="100%" height="0.875rem" rounded="var(--radius)" shimmer />
                    <AppSkeleton width="75%" height="0.875rem" rounded="var(--radius)" shimmer />
                    <AppSkeleton width="4rem" height="0.75rem" rounded="var(--radius)" shimmer />
                  </div>
                </div>
              </div>
              <div v-else-if="relatedVideos.length" class="video-related-list">
                <article
                  v-for="related in relatedVideos"
                  :key="related.id"
                  class="video-related-item"
                  role="button"
                  tabindex="0"
                  @click="related.id != null && goToVideo(related.id, related)"
                  @keydown.enter.prevent="related.id != null && goToVideo(related.id, related)"
                  @keydown.space.prevent="related.id != null && goToVideo(related.id, related)"
                >
                  <div class="video-related-item__thumb">
                    <VideoThumbnail v-if="related.thumbnail" :src="(related.thumbnail as string)" fit="cover" />
                    <span v-if="related.duration" class="video-related-item__duration">{{ formatDuration(related.duration as number) }}</span>
                  </div>
                  <div class="video-related-item__copy">
                    <h4>{{ related.title }}</h4>
                    <p>{{ related.subscriptions?.[0]?.name || related.site || '' }}</p>
                    <small>{{ formatDate(related.uploaded_at) }}</small>
                  </div>
                </article>
              </div>
              <AppEmptyState v-else class="py-16" variant="plain" icon="film" title="暂无相关视频" />
            </div>
            <AppEmptyState v-else-if="asideTab === 'clips'" key="clips" class="py-20" variant="plain" icon="clip" title="按 Shift + M 创建片段" copy="标记精彩时刻" />
            <AppEmptyState v-else-if="asideTab === 'playlist'" key="playlist" class="py-16" variant="plain" icon="playlists" title="播放列表功能开发中" />
          </Transition>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'
import AppFloatingList from '@/shared/components/layout/AppFloatingList.vue'
import AppListOption from '@/shared/components/layout/AppListOption.vue'
import usePlaybackOrchestrator, { mergeVideoMetadata } from '../composables/usePlaybackOrchestrator'
import usePlaybackReporting from '../composables/usePlaybackReporting'
import useVideoActionBar from '@/features/video/composables/useVideoActionBar'
import useVideoClipMarkers from '@/features/video/composables/useVideoClipMarkers'
import useVideoPlaybackShell from '../composables/useVideoPlaybackShell'
import { useVideoDescriptionOverflow } from '../composables/useVideoDescriptionOverflow'
import { useVideoSubscription } from '../composables/useVideoSubscription'
import { useVideoShareMenu } from '../composables/useVideoShareMenu'
import useVideoPageNavigation from '@/features/video/composables/useVideoPageNavigation'
import { consumeVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import { useGlobalVideoPlayer } from '@/features/playback/composables/useGlobalVideoPlayer'
import { storeToRefs } from 'pinia'
import { useThemeStore } from '@/shared/stores/theme'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
import { Button } from '@/shared/ui/button'
import { LocalStorageAdapter } from '@/features/playback/components/video-player/core'
import { useVideoHistory } from '@/features/video/composables/useVideoHistory'
import { formatDate, formatDuration } from '@/shared/lib/dateFormat'
import { Logger } from '@/shared/lib/logger'
import useVideoInteraction from '@/features/video/composables/useVideoInteraction'
import { usePlaylist } from '@/features/video/composables/usePlaylist'
import { saveRemoteVideo } from '@/shared/api'
import { useDesktopBridge } from '@/shared/composables/useDesktopBridge'
import type { VideoPageVideo, VideoProfile } from '@/features/playback/types/videoPlayback'

const { isDesktop: isDesktopEnv } = useDesktopBridge()

const route = useRoute()
const router = useRouter()
// ponytail: useThemeStore replaces the deleted useAppTheme composable (the two
// had diverged — only useAppTheme wired the matchMedia listener). storeToRefs
// keeps the computed ref reactive when passed into useVideoPlaybackShell.
const { effectiveTheme } = storeToRefs(useThemeStore())
const playerAdapter = new LocalStorageAdapter()
const {
  seekGlobalVideoPlayer,
  playGlobalVideoPlayer,
  registerGlobalVideoPlayerTarget,
  unregisterGlobalVideoPlayerTarget,
  focusGlobalVideoPlayer,
  publishGlobalVideoPlayerWiring,
  session,
} = useGlobalVideoPlayer()

// ADR-0002 PR2 — usePlaybackOrchestrator now returns read-only
// projections of PlaybackSession.facts (no local refs, no hydratePlaybackState).
// The initial seed is no longer passed here; the shell hands it to
// session.beginNewVideo(id, seed) at mount. `video` is a computed projection —
// mutations go through session.update({ video }). The other projections
// (playbackSource / subtitleTracks / externalError / isResolvingPlayback /
// startTime) were only ever forwarded into the shell's watcher; with the
// watcher gone, VideoPlay no longer reads them, so they're not destructured.
const {
  video,
  relatedVideos,
  loadingRelated,
  loadAndPlayById,
} = usePlaybackOrchestrator()

const { sendReport } = useVideoHistory()
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction()
const { goToPrev, goToNext } = usePlaylist()

const { onVideoPlay, onVideoPause, onVideoEnded, onVideoTimeUpdate, flushPendingReport } = usePlaybackReporting(video, sendReport)

const { goToVideo, handleAutoplayNext, handlePrevVideoFromPlaylist, handleNextVideoFromPlaylist } = useVideoPageNavigation({
  route, router, video, relatedVideos, 
  goToPrev,
  goToNext,
  onVideoEnded,
})

const asideTab = ref('related')
const asideTabOptions = [
  { value: 'related', label: '相关' },
  { value: 'clips', label: '片段' },
  { value: 'playlist', label: '列表' },
]
const remoteSaveByUrl = new Map<string, Promise<VideoPageVideo | null>>()
let javdbMetadataRequestSeq = 0

const ensureLocalVideo = async (targetVideo: VideoPageVideo | null): Promise<VideoPageVideo | null> => {
  if (!targetVideo || targetVideo.source !== 'remote') return targetVideo

  const url = String(targetVideo.url || '').trim()
  if (!url) return null

  let savePromise = remoteSaveByUrl.get(url)
  if (!savePromise) {
    savePromise = saveRemoteVideo({
      site: targetVideo.site || undefined,
      url,
      title: targetVideo.title || url,
      thumbnail: targetVideo.thumbnail || undefined,
      duration: targetVideo.duration ?? undefined,
      publish_date: targetVideo.publish_date || targetVideo.uploaded_at || undefined,
      uploaded_at: targetVideo.uploaded_at || targetVideo.publish_date || undefined,
      description: targetVideo.description || undefined,
      subscriptions: Array.isArray(targetVideo.subscriptions) ? targetVideo.subscriptions : [],
      actors: Array.isArray(targetVideo.actors) ? targetVideo.actors : [],
    }).then((data) => {
      if (!data?.id) return null
      return data
    }).catch(() => null)
    remoteSaveByUrl.set(url, savePromise)
  }

  const savedVideo = await savePromise
  if (!savedVideo?.id) return null

  const currentVideo = video.value
  if (currentVideo && String(currentVideo.url || '') === url) {
    // ADR-0002 PR2 — `video` is a read-only projection of
    // session.facts.video, so the remote→local id rewrite routes through
    // session.update instead of mutating the ref in place.
    const nextVideo: VideoPageVideo = {
      ...currentVideo,
      id: String(savedVideo.id),
      interaction_type: savedVideo.interaction_type ?? currentVideo.interaction_type ?? undefined,
      last_position: savedVideo.last_position ?? currentVideo.last_position,
      clip_markers: savedVideo.clip_markers ?? currentVideo.clip_markers,
      source: 'local',
      site: currentVideo.site || savedVideo.site,
      url,
    }
    session.update({ video: nextVideo })
    if (String(route.params.videoId || '') !== String(savedVideo.id)) {
      await router.replace({ name: 'VideoPlay', params: { videoId: savedVideo.id } })
    }
  }

  return video.value || savedVideo
}

watch(() => {
  const currentVideo = video.value
  if (currentVideo?.source !== 'remote') return ''
  return String(currentVideo.url || '').trim()
}, async (url) => {
  if (!url) return
  await ensureLocalVideo(video.value)
}, { immediate: true })
// ponytail: "more" dropdown open/close + click-outside lifecycle + share
// action live in useVideoShareMenu. The document click listener + clipboard
// fallback are owned there rather than alongside playback wiring.
const { moreMenuOpen, moreMenuRef, handleShare } = useVideoShareMenu({
  videoId: computed(() => route.params.videoId as string | number | null | undefined),
})


const { videoActions, videoOverflowActions, handleVideoAction } = useVideoActionBar({
  video,
  interactionTypeLike: INTERACTION_TYPE.LIKE,
  interactionTypeDislike: INTERACTION_TYPE.DISLIKE,
  interactionTypeLater: INTERACTION_TYPE.LATER,
  toggleLike: (id, type) => toggleLike(id, Number(type)),
  deleteInteraction,
  ensureLocalVideo,
  handleAddToPlaylist: async () => {},
  handlePlayRandom: async () => {},
})

const { handlePlaybackTimeUpdate, handleClipMarkerSeek, handleClipMarkersUpdated } = useVideoClipMarkers({
  video,
  session,
  seekToTime: async (t: number) => {
    if (await seekGlobalVideoPlayer(t)) await playGlobalVideoPlayer()
    focusGlobalVideoPlayer()
  }
})

const handleVideoTimeUpdate = (currentTime: number) => {
  onVideoTimeUpdate(currentTime)
  handlePlaybackTimeUpdate(currentTime)
}

const videoPublishedText = computed(() => {
  const d = video.value?.publish_date || video.value?.uploaded_at
  return d ? formatDate(d) : ''
})

const videoDescription = computed(() => String(video.value?.description || '').trim())
const isRemoteVideo = computed(() => video.value?.source === 'remote')
const videoActors = computed(() => {
  const actors = video.value?.actors
  if (!Array.isArray(actors)) return []
  return actors
    .filter((actor) => String(actor?.name || '').trim())
    .map((actor) => ({
      ...actor,
      name: String(actor.name || '').trim(),
      url: String(actor.url || '').trim(),
      avatar: String(actor.avatar || '').trim(),
    }))
})
const shouldResolveJavdbMetadata = computed(() => {
  const v = video.value
  const url = String(v?.url || '').trim()
  return !!v && url.includes('javdb.com/') && videoActors.value.length === 0 && isDesktopEnv()
})
const primaryVisibleActions = computed(() => {
  const keys = isRemoteVideo.value ? ['later', 'like', 'dislike'] : ['like', 'dislike']
  return videoActions.value.filter((action) => keys.includes(action.key))
})

// ponytail: description expand/collapse + ResizeObserver overflow detection
// lives in useVideoDescriptionOverflow. The measurement lifecycle + the two
// reset watchers (video id / description text) are owned there.
const {
  descriptionTextRef,
  descriptionExpanded,
  hasLongDescription,
} = useVideoDescriptionOverflow({
  videoId: computed(() => video.value?.id),
  description: videoDescription,
})

watch(shouldResolveJavdbMetadata, async (shouldResolve) => {
  if (!shouldResolve || typeof window.desktopApp?.resolveJavdbMetadata !== 'function') return

  const snapshot = video.value
  const url = String(snapshot?.url || '').trim()
  if (!url) return

  const requestSeq = ++javdbMetadataRequestSeq
  try {
    const metadata = await window.desktopApp.resolveJavdbMetadata(url)
    if (requestSeq !== javdbMetadataRequestSeq) return
    const current = video.value
    if (!current || String(current.url || '') !== url) return
    const mergedVideo = mergeVideoMetadata(current, metadata as Record<string, unknown>, url)
    if (mergedVideo) {
      // ADR-0002 PR2 — `video` is a read-only projection; enrichment
      // routes through session.update.
      session.update({ video: mergedVideo })
    }
  } catch (err) {
    Logger.warn('[VideoPlay] Metadata enrichment failed', err)
  }
}, { immediate: true })

// ponytail: subscription status + toggle live in useVideoSubscription.
// primarySubscription / primarySubscriptionUrl are returned because the view
// also renders the avatar and de-duplicates the actor list against the primary.
const {
  primarySubscription,
  primarySubscriptionUrl,
  isCheckingSubscription,
  isSubscribing,
  isSubscriptionChecked,
  isSubscribed,
  subscriptionButtonText,
  handleSubscribe,
} = useVideoSubscription({ video })

const displayedVideoActors = computed(() => {
  const primary = primarySubscription.value
  const primaryUrl = String(primary?.url || '').trim().toLowerCase()
  const primaryId = primary?.id != null ? String(primary.id).trim() : ''
  const primaryName = String(primary?.name || '').trim().toLowerCase()

  return videoActors.value.filter((actor) => {
    const actorUrl = String(actor?.url || '').trim().toLowerCase()
    if (primaryUrl && actorUrl && actorUrl === primaryUrl) return false

    const actorId = actor?.id != null ? String(actor.id).trim() : ''
    if (primaryId && actorId && actorId === primaryId) return false

    const actorName = String(actor?.name || '').trim().toLowerCase()
    return !(primaryName && actorName && actorName === primaryName)
  })
})

const {
  videoPlayerHostRef,
  isWidescreen,
} = useVideoPlaybackShell({
  route,
  effectiveTheme,
  consumePlaybackSeed: (id: unknown) => consumeVideoPlaybackSeed(String(id || '')),
  loadAndPlayById,
  registerGlobalVideoPlayerTarget,
  unregisterGlobalVideoPlayerTarget,
  focusGlobalVideoPlayer,
  publishWiring: (handlers) => publishGlobalVideoPlayerWiring(handlers, playerAdapter),
  flushPendingReport,
  onVideoPlay,
  onVideoPause,
  handleAutoplayNext,
  handlePlaybackTimeUpdate: handleVideoTimeUpdate,
  handlePrevVideoFromPlaylist,
  handleNextVideoFromPlaylist,
  handlePlayerRetry: () => {
    if (video.value?.id) void loadAndPlayById(video.value.id, video.value, { forceRefresh: true })
  },
  handleClipMarkerSeek,
  handleClipMarkersUpdated,
  hasPrev: ref(false),
  hasNext: ref(false),
})

const resolveRemoteChannelSite = (url: string) => {
  let parsedUrl: URL
  try {
    parsedUrl = new URL(url)
  } catch (err) {
    Logger.debug('[VideoPlay] Failed to parse channel URL', err)
    return ''
  }

  const hostname = parsedUrl.hostname.toLowerCase().replace(/^www\./, '')
  const pathname = parsedUrl.pathname

  if (hostname === 'space.bilibili.com' && /^\/\d+/i.test(pathname)) return 'bilibili'
  if (hostname === 'youtube.com' && /^\/(?:@[^/]+|channel\/[^/]+|c\/[^/]+|user\/[^/]+)/i.test(pathname)) return 'youtube'
  if (hostname === 'javdb.com' && /^\/actors?\//i.test(pathname)) return 'javdb'
  if (hostname === 'pornhub.com' && /^\/(?:users?|channels?|model|pornstar)\//i.test(pathname)) return 'pornhub'
  if (hostname === 'youporn.com' && /^\/(?:channel|amateur|pornstar|model)\//i.test(pathname)) return 'youporn'

  return ''
}

const openChannelDetail = async (profile: VideoProfile) => {
  const url = String(profile?.url || '').trim()
  const remoteSite = resolveRemoteChannelSite(url)

  if (remoteSite) {
    if (url) {
      await router.push({
        name: 'RemoteChannelDetail',
        query: {
          site: remoteSite,
          url,
          id: profile?.id != null ? String(profile.id) : undefined,
          name: profile?.name || undefined,
          avatar: profile?.avatar || undefined,
          is_nsfw: profile?.is_nsfw === true ? 'true' : undefined,
        },
      })
    }
    return
  }

  if (profile?.id) router.push(`/subscription/${profile.id}/all`)
}
</script>

<style scoped>
.video-play-page {
  min-height: 100vh;
  background: hsl(var(--background));
}

.video-play-page.is-widescreen {
  padding-inline: 0;
}

.video-play-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 2rem;
  width: 100%;
  max-width: 1800px;
  margin: 0 auto;
  padding: 1.5rem;
  transition:
    max-width 0.2s ease,
    padding 0.2s ease;
}

.video-play-layout.is-widescreen {
  max-width: none;
}

.video-play-primary {
  min-width: 0;
}

.video-play-primary:not(.is-widescreen) {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.video-play-primary.is-widescreen {
  display: contents;
}

.video-player-stage {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.36);
  border-radius: 0.75rem;
  background: black;
}

.video-player-stage.is-widescreen {
  border-radius: 0.75rem;
}

.video-player-host {
  position: absolute;
  inset: 0;
  overflow: hidden;
  border-radius: inherit;
}

.video-play-main {
  min-width: 0;
}

.video-detail,
.video-detail__skeleton {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.video-detail__title-block {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.video-detail__meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  font-weight: 500;
}

.video-detail__dot {
  color: hsl(var(--muted-foreground) / 0.55);
}

.video-detail__site {
  display: inline-flex;
  align-items: center;
  padding: 0.0625rem 0.375rem;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--radius-sm);
  background: hsl(var(--muted) / 0.4);
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 650;
  line-height: 1.2;
}

.video-detail__bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding-block: 0.25rem;
}

.video-detail__channel-actions,
.video-detail__actions,
.video-detail__action-group {
  display: flex;
  align-items: center;
}

.video-detail__channel-actions {
  gap: 1.25rem;
}

.video-detail__channel {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: -0.25rem;
  padding: 0.25rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  outline: none;
}

.video-detail__channel:focus-visible {
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.45);
}

.video-detail__channel-copy {
  display: flex;
  flex-direction: column;
}

.video-detail__channel-copy span {
  color: hsl(var(--foreground));
  font-size: 0.9375rem;
  font-weight: 650;
  line-height: 1.25;
  letter-spacing: -0.01em;
  transition: color var(--duration-fast) var(--ease-default);
}

.video-detail__channel:hover .video-detail__channel-copy span {
  color: hsl(var(--primary));
}

.video-detail__channel-copy small {
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
}

.video-detail__subscribe-button,
.video-detail__action-button,
.video-detail__icon-button,
.video-detail__actor {
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  outline: none;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default),
    opacity var(--duration-fast) var(--ease-default);
}

.video-detail__subscribe-button {
  min-width: 4rem;
  height: 2rem;
  padding: 0 1rem;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  font-size: 0.75rem;
  font-weight: 650;
}

.video-detail__subscribe-button:hover {
  background: hsl(var(--primary) / 0.9);
}

.video-detail__subscribe-button.is-subscribed {
  border-color: hsl(var(--border) / 0.42);
  background: hsl(var(--secondary));
  color: hsl(var(--foreground));
}

.video-detail__subscribe-button.is-subscribed:hover {
  background: hsl(var(--secondary) / 0.82);
}

.video-detail__subscribe-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.video-detail__actions {
  gap: 0.5rem;
}

.video-detail__action-group {
  gap: 0.125rem;
  padding: 0.125rem;
  border: 1px solid hsl(var(--border) / 0.18);
  border-radius: 0.625rem;
  background: hsl(var(--muted) / 0.34);
}

.video-detail__action-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  height: 2rem;
  padding: 0 0.875rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
  font-weight: 650;
}

.video-detail__action-button:hover {
  background: hsl(var(--muted) / 0.62);
  color: hsl(var(--foreground));
}

.video-detail__action-button.is-active {
  border-color: hsl(var(--border) / 0.28);
  background: hsl(var(--background));
  color: hsl(var(--foreground));
}

.video-detail__icon-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  background: hsl(var(--muted) / 0.38);
  color: hsl(var(--muted-foreground));
}

.video-detail__icon-button:hover {
  background: hsl(var(--muted) / 0.68);
  color: hsl(var(--foreground));
}

.video-detail__menu {
  left: auto;
  width: 11rem;
}

.video-detail__menu-link {
  display: flex;
  min-height: 2.25rem;
  width: 100%;
  align-items: center;
  gap: 0.5rem;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  padding: 0.25rem 0.5rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.video-detail__menu-link:hover,
.video-detail__menu-link:focus-visible {
  background: hsl(var(--accent) / 0.48);
  color: hsl(var(--foreground));
  outline: none;
}

.video-detail__actors {
  margin-inline: -0.25rem;
}

.video-detail__actor-list {
  display: flex;
  gap: 0.5rem;
  overflow-x: auto;
  padding: 0 0.25rem 0.125rem;
}

.video-detail__actor {
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 0.5rem;
  height: 2rem;
  padding: 0 0.625rem;
  background: hsl(var(--muted) / 0.4);
  color: hsl(var(--foreground) / 0.86);
  font-size: 0.75rem;
  font-weight: 650;
}

.video-detail__actor:hover {
  background: hsl(var(--muted) / 0.72);
  color: hsl(var(--foreground));
}

.video-detail__description {
  margin-top: 0.5rem;
  padding: 1rem;
  border: 1px solid hsl(var(--border) / 0.14);
  border-radius: 0.625rem;
  background: hsl(var(--muted) / 0.28);
}

.video-detail__description-fade {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 2.5rem;
  pointer-events: none;
  background: linear-gradient(to top, hsl(var(--muted) / 0.3), transparent);
}

.video-detail__description-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin-top: 0.5rem;
  padding: 0.125rem 0.25rem;
  border-radius: 0.375rem;
  color: hsl(var(--foreground) / 0.72);
  font-size: 0.875rem;
  font-weight: 650;
  outline: none;
  transition: color 0.16s ease;
}

.video-detail__description-toggle:hover,
.video-detail__description-toggle:focus-visible {
  color: hsl(var(--foreground));
}

.video-play-aside {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.video-play-aside__content {
  min-height: 25rem;
}

.video-related-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.video-related-item {
  display: flex;
  gap: 0.75rem;
  margin-inline: -0.375rem;
  padding: 0.375rem;
  border-radius: 0.625rem;
  cursor: pointer;
  outline: none;
  transition:
    color 0.16s ease,
    background-color 0.16s ease;
}

.video-related-item:hover,
.video-related-item:focus-visible {
  background: hsl(var(--accent) / 0.4);
}

.video-related-item__thumb {
  position: relative;
  width: 10rem;
  aspect-ratio: 16 / 9;
  flex: 0 0 auto;
  overflow: hidden;
  border: 0;
  border-radius: var(--app-card-radius);
  background: hsl(0 0% 0% / 0.55);
  isolation: isolate;
}

.video-related-item__duration {
  position: absolute;
  right: 0.25rem;
  bottom: 0.25rem;
  display: inline-flex;
  align-items: center;
  height: 1.25rem;
  padding: 0 0.375rem;
  border-radius: 0.375rem;
  background: hsl(0 0% 0% / 0.72);
  color: white;
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
  font-weight: 650;
}

.video-related-item__copy {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  flex-direction: column;
  justify-content: center;
  gap: 0.125rem;
}

.video-related-item__copy h4 {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: hsl(var(--foreground) / 0.86);
  font-size: 0.875rem;
  font-weight: 650;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  transition: color 0.16s ease;
}

.video-related-item:hover .video-related-item__copy h4 {
  color: hsl(var(--primary));
}

.video-related-item__copy p,
.video-related-item__copy small {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.video-related-item__copy p {
  color: hsl(var(--muted-foreground) / 0.62);
  font-size: 0.75rem;
  font-weight: 500;
}

.video-related-item__copy small {
  color: hsl(var(--muted-foreground) / 0.46);
  font-size: 0.6875rem;
  font-weight: 500;
}

@media (min-width: 1024px) {
  .video-play-layout {
    grid-template-columns: minmax(0, 1fr) 400px;
    padding: 2.5rem;
  }

  .video-play-layout.is-widescreen {
    padding: 2rem;
  }

  .video-player-stage.is-widescreen {
    grid-column: span 2;
  }

  .video-play-main.is-widescreen {
    grid-column: 1;
    grid-row: 2;
  }

  .video-play-aside:not(.is-widescreen) {
    grid-column: 2;
    grid-row: 1;
  }

  .video-play-aside.is-widescreen {
    grid-column: 2;
    grid-row: 2;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .video-play-layout,
  .video-detail__channel-copy span,
  .video-detail__subscribe-button,
  .video-detail__action-button,
  .video-detail__icon-button,
  .video-detail__actor,
  .video-detail__menu-link,
  .video-detail__description-toggle,
  .video-related-item,
  .video-related-item__copy h4,
  .fade-enter-active,
  .fade-leave-active {
    transition: none;
  }
}
</style>
