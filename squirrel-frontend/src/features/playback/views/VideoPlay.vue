<template>
  <div ref="videoPageRef" class="min-h-screen bg-background" :class="{ 'px-0': isWidescreen }">
    <div
      class="mx-auto grid grid-cols-1 transition-[max-width,padding] duration-200"
      :class="isWidescreen ? 'max-w-none lg:grid-cols-[1fr,400px] gap-8 p-6 lg:p-8' : 'max-w-[1800px] lg:grid-cols-[1fr,400px] gap-8 p-6 lg:p-10'"
    >
      <div
        class="min-w-0 space-y-6"
        :class="isWidescreen ? 'lg:contents' : 'lg:col-start-1 lg:row-start-1'"
      >
        <!-- Player Section -->
        <div
          class="relative aspect-video overflow-hidden bg-black shadow-lg"
          :class="isWidescreen ? 'lg:col-span-2 rounded-xl' : 'rounded-xl'"
        >
          <div
            ref="videoPlayerHostRef"
            class="absolute inset-0 overflow-hidden rounded-xl"
          />
        </div>

        <!-- Main Content -->
        <div class="min-w-0 space-y-6" :class="{ 'lg:col-start-1 lg:row-start-2': isWidescreen }">
          <!-- Video Header Info -->
          <div v-if="video" class="space-y-6">
            <div class="space-y-2">
              <h1 class="text-lg md:text-xl font-semibold tracking-tight leading-[1.3] text-foreground">
                {{ video.title }}
              </h1>
              <div class="flex items-center gap-2 text-sm text-muted-foreground/60 font-medium">
                <span>{{ videoPublishedText }}</span>
                <span>·</span>
                <span v-if="video.site" class="inline-flex items-center uppercase tracking-wider text-[10px] bg-accent/50 text-muted-foreground px-1.5 py-px rounded font-bold leading-normal">{{ video.site }}</span>
              </div>
            </div>
            
            <div class="flex flex-wrap items-center justify-between gap-4 py-1">
              <div class="flex items-center gap-6">
                <div v-if="primarySubscription" class="flex items-center gap-3 group cursor-pointer" @click="openChannelDetail(primarySubscription)">
                  <SubscriptionAvatar :src="primarySubscription.avatar" :name="primarySubscription.name || ''" size="xl" />
                  <div class="flex flex-col -space-y-0.5">
                    <span class="font-bold text-[15px] group-hover:text-primary transition-colors tracking-tight">{{ primarySubscription.name }}</span>
                    <span class="text-[12px] text-muted-foreground/60 font-medium">{{ primarySubscription.total_videos || 0 }} 项视频</span>
                  </div>
                </div>
                <button
                  v-if="primarySubscriptionUrl"
                  type="button"
                  class="h-7 min-w-16 px-3 text-xs font-semibold rounded-full transition-all shadow-sm disabled:cursor-not-allowed disabled:opacity-60"
                  :class="isSubscriptionChecked && isSubscribed ? 'bg-secondary text-foreground ring-1 ring-border/40' : 'bg-foreground text-background hover:opacity-90 active:scale-95'"
                  :disabled="isCheckingSubscription || isSubscribing"
                  @click="handleSubscribe"
                >
                  {{ subscriptionButtonText }}
                </button>
              </div>

              <div class="flex items-center gap-2">
                <div class="flex bg-accent/40 rounded-full p-0.5 ring-1 ring-border/20">
                  <button
                    v-for="action in primaryVisibleActions"
                    :key="action.key"
                    class="flex items-center gap-2 px-4 py-1.5 rounded-full hover:bg-accent/60 transition-all text-[13px] font-semibold"
                    :class="{ 'text-foreground bg-background shadow-sm ring-1 ring-border/10': action.active, 'text-muted-foreground': !action.active }"
                    @click="handleVideoAction(action)"
                  >
                    <AppIcon :name="action.icon" class="w-4 h-4" :stroke-width="action.active ? 2.5 : 2" />
                    <span v-if="action.label && action.key === 'like'">{{ action.label }}</span>
                  </button>
                </div>

                <button
                  class="w-9 h-9 flex items-center justify-center rounded-full bg-accent/40 hover:bg-accent/60 transition-all active:scale-95 ring-1 ring-border/20 text-muted-foreground hover:text-foreground"
                  title="分享链接"
                  @click="handleShare"
                >
                  <AppIcon name="share" class="w-4 h-4" />
                </button>
                <div class="relative" ref="moreMenuRef">
                  <button
                    class="w-9 h-9 flex items-center justify-center rounded-full bg-accent/40 hover:bg-accent/60 transition-all active:scale-95 ring-1 ring-border/20 text-muted-foreground hover:text-foreground"
                    @click.stop="moreMenuOpen = !moreMenuOpen"
                  >
                    <AppIcon name="more" class="w-4 h-4" />
                  </button>
                  <Transition name="fade">
                    <div v-if="moreMenuOpen" class="absolute right-0 top-full mt-1 w-44 bg-popover border border-border rounded-xl shadow-premium py-1 z-50">
                      <button
                        v-for="action in videoOverflowActions.filter(a => a.key !== 'source')"
                        :key="action.key"
                        class="flex w-full items-center gap-2.5 px-3.5 py-2 text-[13px] font-medium text-foreground/80 hover:bg-accent transition-colors"
                        @click.stop="handleVideoAction(action); moreMenuOpen = false"
                      >
                        <AppIcon :name="action.icon" class="w-4 h-4 text-muted-foreground" />
                        {{ action.label }}
                      </button>
                      <a
                        v-if="video.url"
                        :href="video.url"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="flex w-full items-center gap-2.5 px-3.5 py-2 text-[13px] font-medium text-foreground/80 hover:bg-accent transition-colors"
                        @click.stop="moreMenuOpen = false"
                      >
                        <AppIcon name="externalLink" class="w-4 h-4 text-muted-foreground" />
                        原视频
                      </a>
                    </div>
                  </Transition>
                </div>
              </div>
            </div>

            <div v-if="displayedVideoActors.length" class="-mx-1">
              <div class="flex gap-2 overflow-x-auto px-1 pb-0.5 no-scrollbar">
                <button
                  v-for="actor in displayedVideoActors"
                  :key="actor.url || actor.name"
                  type="button"
                  class="inline-flex h-8 shrink-0 items-center gap-2 rounded-full bg-accent/35 px-2.5 text-[12px] font-semibold text-foreground/85 ring-1 ring-border/20 transition-colors hover:bg-accent/55"
                  @click="openChannelDetail(actor)"
                >
                  <SubscriptionAvatar :src="actor.avatar" :name="actor.name || ''" size="xs" />
                  <span class="truncate max-w-[120px]">{{ actor.name }}</span>
                </button>
              </div>
            </div>

            <div v-if="videoDescription" class="mt-2 p-4 bg-muted/30 rounded-xl ring-1 ring-border/10">
              <div
                ref="descriptionTextRef"
                class="relative overflow-hidden"
                :class="{ 'max-h-[4.8em]': !descriptionExpanded }"
              >
                <p class="text-[14px] leading-relaxed text-foreground/75 whitespace-pre-wrap">
                  {{ videoDescription }}
                </p>
                <div
                  v-if="!descriptionExpanded && hasLongDescription"
                  class="absolute bottom-0 left-0 right-0 h-10 bg-gradient-to-t from-muted/30 to-transparent pointer-events-none"
                />
              </div>
              <button
                v-if="hasLongDescription"
                type="button"
                class="mt-2 text-[13px] font-semibold text-foreground/70 hover:text-foreground transition-colors"
                @click="descriptionExpanded = !descriptionExpanded"
              >
                {{ descriptionExpanded ? '收起' : '展开' }}
              </button>
            </div>
          </div>
          
          <!-- Skeleton -->
          <div v-else class="space-y-6 animate-pulse">
            <div class="space-y-2">
              <div class="h-7 bg-muted rounded-lg w-3/4" />
              <div class="h-4 bg-muted rounded w-36" />
            </div>
            <div class="flex items-center gap-4">
              <div class="h-12 w-12 rounded-full bg-muted shrink-0" />
              <div class="space-y-2 flex-1">
                <div class="h-4 bg-muted rounded w-28" />
                <div class="h-3 bg-muted rounded w-16" />
              </div>
              <div class="h-7 w-16 rounded-full bg-muted" />
            </div>
            <div class="flex gap-2">
              <div class="h-8 w-16 rounded-full bg-muted" />
              <div class="h-8 w-20 rounded-full bg-muted" />
              <div class="h-8 w-14 rounded-full bg-muted" />
            </div>
            <div class="h-20 bg-muted rounded-xl" />
          </div>
        </div>
      </div>

      <!-- Sidebar Content (Related/Clips/Playlist) -->
      <div
        class="space-y-6"
        :class="isWidescreen ? 'lg:col-start-2 lg:row-start-2' : 'lg:col-start-2 lg:row-start-1'"
      >
        <div class="app-tab-list w-full">
          <button
            v-for="tab in asideTabs"
            :key="tab.key"
            @click="asideTab = tab.key"
            class="app-tab-button flex-1 justify-center"
            :class="{ 'is-active': asideTab === tab.key }"
          >
            {{ tab.label }}
          </button>
        </div>

        <div class="min-h-[400px]">
          <Transition name="fade" mode="out-in">
            <div v-if="asideTab === 'related'" key="related">
              <div v-if="loadingRelated" class="space-y-3 animate-pulse">
                <div v-for="n in 4" :key="n" class="flex gap-3">
                  <div class="w-40 aspect-video rounded-md bg-muted shrink-0" />
                  <div class="flex-1 space-y-1.5 py-0.5">
                    <div class="h-3.5 bg-muted rounded w-full" />
                    <div class="h-3.5 bg-muted rounded w-3/4" />
                    <div class="h-3 bg-muted rounded w-16" />
                  </div>
                </div>
              </div>
              <div v-else-if="relatedVideos.length" class="space-y-2">
                <article v-for="related in relatedVideos" :key="related.id" class="flex gap-3 group cursor-pointer rounded-lg p-1.5 -mx-1.5 hover:bg-accent/40 transition-colors" @click="related.id != null && goToVideo(related.id, related)">
                  <div class="relative w-40 aspect-video shrink-0 overflow-hidden rounded-md bg-muted">
                    <VideoThumbnail v-if="related.thumbnail" :src="(related.thumbnail as string)" fit="contain" />
                    <span v-if="related.duration" class="absolute bottom-1 right-1 inline-flex h-[18px] items-center rounded-[4px] bg-black/70 px-1 text-[10px] font-semibold text-white tabular-nums">{{ formatDuration(related.duration as number) }}</span>
                  </div>
                  <div class="flex-1 min-w-0 flex flex-col justify-center gap-0.5">
                    <h4 class="text-[13px] font-semibold line-clamp-2 leading-[1.35] group-hover:text-primary transition-colors text-foreground/85">{{ related.title }}</h4>
                    <p class="text-[11px] text-muted-foreground/55 font-medium truncate">{{ related.subscriptions?.[0]?.name || related.site || '' }}</p>
                    <p class="text-[10px] text-muted-foreground/35 font-medium">{{ formatDate(related.uploaded_at) }}</p>
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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import usePlaybackOrchestrator, { mergeVideoMetadata } from '../composables/usePlaybackOrchestrator'
import usePlaybackReporting from '../composables/usePlaybackReporting'
import useVideoActionBar from '@/features/video/composables/useVideoActionBar'
import useVideoClipMarkers from '@/features/video/composables/useVideoClipMarkers'
import useVideoPlaybackShell from '../composables/useVideoPlaybackShell'
import useVideoPageNavigation from '@/features/video/composables/useVideoPageNavigation'
import { consumeVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import { useGlobalVideoPlayer } from '@/features/playback/composables/useGlobalVideoPlayer'
import { useToast } from '@/shared/components/toast/useToast'
import { storeToRefs } from 'pinia'
import { useThemeStore } from '@/shared/stores/theme'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
import { LocalStorageAdapter } from '@/features/playback/components/video-player/core'
import { useVideoHistory } from '@/features/video/composables/useVideoHistory'
import { formatDate, formatDuration } from '@/shared/lib/dateFormat'
import { Logger } from '@/shared/lib/logger'
import useVideoInteraction from '@/features/video/composables/useVideoInteraction'
import { usePlaylist } from '@/features/video/composables/usePlaylist'
import { getSubscriptionStatus, saveRemoteVideo, subscribe, unsubscribe } from '@/shared/api'
import type { VideoPageVideo, VideoProfile } from '@/features/playback/types/videoPlayback'

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
const asideTabs = [
  { key: 'related', label: '相关' },
  { key: 'clips', label: '片段' },
  { key: 'playlist', label: '列表' },
]
const descriptionExpanded = ref(false)
const descriptionTextRef = ref<HTMLElement | null>(null)
const hasDescriptionOverflow = ref(false)
const isCheckingSubscription = ref(false)
const isSubscriptionChecked = ref(false)
const isSubscribed = ref(false)
const isSubscribing = ref(false)
const subscriptionId = ref<number | null>(null)
let descriptionResizeObserver: ResizeObserver | null = null
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
    }).then(({ data, error }) => {
      if (error || !data?.id) return null
      return data
    })
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

const moreMenuOpen = ref(false)
const moreMenuRef = ref<HTMLElement | null>(null)
const toast = useToast()

const handleShare = async () => {
  const url = `${window.location.origin}/video/${route.params.videoId}`
  try {
    await navigator.clipboard.writeText(url)
    toast.success('链接已复制到剪贴板')
  } catch (err) {
    Logger.warn('[VideoPlay] Failed to copy share link', err)
    toast.error('复制失败，请手动复制链接')
  }
}

const handleClickOutside = (e: MouseEvent) => {
  if (moreMenuRef.value && !moreMenuRef.value.contains(e.target as Node)) {
    moreMenuOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  void syncDescriptionOverflow()
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
  descriptionResizeObserver?.disconnect()
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
  return !!v && url.includes('javdb.com/') && videoActors.value.length === 0 && window.desktopApp?.isDesktop === true
})
const primaryVisibleActions = computed(() => {
  const keys = isRemoteVideo.value ? ['later', 'like', 'dislike'] : ['like', 'dislike']
  return videoActions.value.filter((action) => keys.includes(action.key))
})

const hasLongDescription = computed(() => hasDescriptionOverflow.value)

const syncDescriptionOverflow = async () => {
  await nextTick()
  const el = descriptionTextRef.value
  hasDescriptionOverflow.value = !!el && el.scrollHeight > el.clientHeight + 1
}

watch(() => video.value?.id, () => {
  descriptionExpanded.value = false
  void syncDescriptionOverflow()
})

watch(videoDescription, () => {
  descriptionExpanded.value = false
  void syncDescriptionOverflow()
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

watch(descriptionTextRef, (el) => {
  descriptionResizeObserver?.disconnect()
  descriptionResizeObserver = null

  if (el) {
    descriptionResizeObserver = new ResizeObserver(() => {
      if (!descriptionExpanded.value) void syncDescriptionOverflow()
    })
    descriptionResizeObserver.observe(el)
  }

  void syncDescriptionOverflow()
})

const primarySubscription = computed(() => {
  const v = video.value
  if (!v) return null
  return v.subscriptions?.[0] || v.actors?.[0] || null
})

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

const primarySubscriptionUrl = computed(() => String(primarySubscription.value?.url || '').trim())

const subscriptionButtonText = computed(() => {
  if (isCheckingSubscription.value) return '检查中'
  if (isSubscribing.value) return '订阅中'
  return isSubscriptionChecked.value && isSubscribed.value ? '取消订阅' : '订阅'
})

const refreshSubscriptionStatus = async (url: string) => {
  isSubscribed.value = false
  isSubscriptionChecked.value = false
  subscriptionId.value = null
  if (!url) return

  isCheckingSubscription.value = true
  const { data, error } = await getSubscriptionStatus(url)
  isCheckingSubscription.value = false

  if (url !== primarySubscriptionUrl.value) return
  if (error) return

  isSubscribed.value = data?.is_subscribed === true
  subscriptionId.value = data?.subscription_id ?? null
  isSubscriptionChecked.value = true
}

watch(primarySubscriptionUrl, async (url) => {
  await refreshSubscriptionStatus(url)
}, { immediate: true })

const handleSubscribe = async () => {
  const url = primarySubscriptionUrl.value
  if (!url || isSubscribing.value) return

  isSubscribing.value = true
  const result = isSubscribed.value && subscriptionId.value
    ? await unsubscribe(subscriptionId.value)
    : await subscribe(url)
  isSubscribing.value = false

  if (result.error) return

  if (!isSubscribed.value) {
    isSubscribed.value = result.data?.is_subscribed === true
    subscriptionId.value = result.data?.subscription_id ?? null
    isSubscriptionChecked.value = true
  }

  await refreshSubscriptionStatus(url)
}

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
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.toast-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.toast-leave-active {
  transition: all 0.2s ease-in;
}
.toast-enter-from {
  opacity: 0;
  transform: translate(-50%, 0.5rem);
}
.toast-leave-to {
  opacity: 0;
  transform: translate(-50%, 0.25rem);
}
</style>
