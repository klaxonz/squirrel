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
          class="relative aspect-video overflow-hidden bg-black shadow-2xl"
          :class="isWidescreen ? 'lg:col-span-2 rounded-xl' : 'rounded-2xl'"
        >
          <div
            ref="videoPlayerHostRef"
            class="absolute inset-0 overflow-hidden"
            :class="isWidescreen ? 'rounded-xl' : 'rounded-2xl'"
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
                <span v-if="(video as any)?.site" class="uppercase tracking-widest text-[10px] bg-accent/50 text-muted-foreground px-1.5 py-0.5 rounded-[4px] font-bold">{{ (video as any).site }}</span>
              </div>
            </div>
            
            <div class="flex flex-wrap items-center justify-between gap-4 py-1">
              <div class="flex items-center gap-6">
                <div v-if="primarySubscription" class="flex items-center gap-3 group cursor-pointer" @click="openChannelDetail(primarySubscription)">
                  <SubscriptionAvatar :src="primarySubscription.avatar" :name="primarySubscription.name" size="xl" />
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
                
                <button class="w-9 h-9 flex items-center justify-center rounded-full bg-accent/40 hover:bg-accent/60 transition-all active:scale-95 ring-1 ring-border/20 text-muted-foreground hover:text-foreground">
                  <AppIcon name="share" class="w-4 h-4" />
                </button>
                <button class="w-9 h-9 flex items-center justify-center rounded-full bg-accent/40 hover:bg-accent/60 transition-all active:scale-95 ring-1 ring-border/20 text-muted-foreground hover:text-foreground">
                  <AppIcon name="more" class="w-4 h-4" />
                </button>
              </div>
            </div>

            <div v-if="displayedVideoActors.length" class="flex flex-wrap items-center gap-2">
              <button
                v-for="actor in displayedVideoActors"
                :key="actor.url || actor.name"
                type="button"
                class="inline-flex h-8 max-w-full items-center gap-2 rounded-full bg-accent/35 px-2.5 text-[12px] font-semibold text-foreground/85 ring-1 ring-border/20 transition-colors hover:bg-accent/55"
                @click="openChannelDetail(actor)"
              >
                <SubscriptionAvatar :src="actor.avatar" :name="actor.name" size="xs" />
                <span class="truncate">{{ actor.name }}</span>
              </button>
            </div>

            <div v-if="videoDescription" class="!mt-0 p-4 bg-accent/20 rounded-xl ring-1 ring-border/10 group">
              <p
                ref="descriptionTextRef"
                class="text-[14px] leading-relaxed text-foreground/80 whitespace-pre-wrap"
                :class="{ 'line-clamp-3': !descriptionExpanded }"
              >
                {{ videoDescription }}
              </p>
              <button
                v-if="hasLongDescription"
                type="button"
                class="mt-3 text-[13px] font-bold text-foreground hover:text-primary transition-colors"
                @click="descriptionExpanded = !descriptionExpanded"
              >
                {{ descriptionExpanded ? '收起' : '展开' }}
              </button>
            </div>
          </div>
          
          <!-- Skeleton -->
          <div v-else class="space-y-4 animate-pulse">
            <div class="h-8 bg-muted rounded-lg w-3/4" />
            <div class="flex items-center gap-4">
              <div class="h-12 w-12 rounded-full bg-muted" />
              <div class="space-y-2">
                <div class="h-4 bg-muted rounded w-32" />
                <div class="h-3 bg-muted rounded w-20" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Sidebar Content (Related/Clips/Playlist) -->
      <div
        class="space-y-6"
        :class="isWidescreen ? 'lg:col-start-2 lg:row-start-2' : 'lg:col-start-2 lg:row-start-1'"
      >
        <div class="flex p-0.5 bg-accent/30 rounded-lg ring-1 ring-border/20">
          <button 
            v-for="tab in asideTabs"
            :key="tab.key"
            @click="asideTab = tab.key"
            class="flex-1 py-1.5 text-[11px] font-bold uppercase tracking-wider rounded-md transition-all"
            :class="asideTab === tab.key ? 'bg-background text-foreground shadow-sm ring-1 ring-border/10' : 'text-muted-foreground hover:text-foreground'"
          >
            {{ tab.label }}
          </button>
        </div>

        <div class="min-h-[400px]">
          <Transition name="fade" mode="out-in">
            <div v-if="asideTab === 'related'" class="space-y-4">
              <article v-for="related in relatedVideos" :key="related.id" class="flex gap-3 group cursor-pointer" @click="goToVideo(related.id, related)">
                <div class="relative w-40 aspect-video shrink-0 overflow-hidden rounded-md bg-muted transition-colors group-hover:bg-muted/80">
                  <VideoThumbnail v-if="related.thumbnail" :src="(related.thumbnail as string)" fit="contain" />
                  <span v-if="related.duration" class="absolute bottom-1 right-1 inline-flex h-5 items-center rounded-md bg-black/65 px-1.5 text-[10px] font-medium text-white tabular-nums backdrop-blur-sm">{{ formatDuration(related.duration as number) }}</span>
                </div>
                <div class="flex-1 min-w-0 flex flex-col gap-0.5">
                  <h4 class="text-[13px] font-semibold line-clamp-2 leading-[1.3] group-hover:text-primary transition-colors tracking-tight text-foreground/90">{{ related.title }}</h4>
                  <p class="text-[11px] text-muted-foreground/60 font-medium truncate">{{ (related as any).subscriptions?.[0]?.name || (related as any).site }}</p>
                  <p class="text-[10px] text-muted-foreground/40 font-medium">{{ formatDate((related as any).uploaded_at) }}</p>
                </div>
              </article>
            </div>
            <div v-else-if="asideTab === 'clips'" class="flex flex-col items-center justify-center py-20 text-muted-foreground">
              <AppIcon name="clip" class="w-10 h-10 mb-4 opacity-20" />
              <p class="text-sm font-medium">Press Shift + M to create a clip</p>
            </div>
          </Transition>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/components/common/AppIcon.vue'
import usePlaybackOrchestrator, { mergeVideoMetadata } from '../composables/usePlaybackOrchestrator'
import usePlaybackReporting from '../composables/usePlaybackReporting'
import useVideoActionBar from '../composables/useVideoActionBar'
import useVideoClipMarkers from '../composables/useVideoClipMarkers'
import useVideoPlaybackShell from '../composables/useVideoPlaybackShell'
import useVideoPageNavigation from '../composables/useVideoPageNavigation'
import { consumeVideoPlaybackSeed, peekVideoPlaybackSeed } from '@/composables/videoPlaybackSeed'
import { useGlobalVideoPlayer } from '@/composables/useGlobalVideoPlayer'
import { useAppTheme } from '@/composables/useAppTheme'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import VideoThumbnail from '@/components/feed/VideoThumbnail.vue'
import { LocalStorageAdapter } from '@/components/video-player/core'
import useVideoHistory from "../composables/useVideoHistory"
import { formatDate, formatDuration } from '../utils/dateFormat'
import useVideoInteraction from '../composables/useVideoInteraction'
import usePlaylist from '../composables/usePlaylist'
import { getSubscriptionStatus, saveRemoteVideo, subscribe, unsubscribe } from '@/api'

const route = useRoute()
const router = useRouter()
const { effectiveTheme } = useAppTheme()
const playerAdapter = new LocalStorageAdapter()
const {
  seekGlobalVideoPlayer,
  playGlobalVideoPlayer,
  activateGlobalVideoPlayerSession,
  clearGlobalVideoPlayerSession,
  registerGlobalVideoPlayerTarget,
  unregisterGlobalVideoPlayerTarget,
  focusGlobalVideoPlayer,
  globalVideoPlayerSession,
} = useGlobalVideoPlayer()

const initialPlaybackSeed = peekVideoPlaybackSeed(route.params.videoId as string)
const {
  video,
  startTime,
  relatedVideos,
  loadingRelated,
  playbackSource,
  subtitleTracks,
  loadAndPlayById,
  externalError,
  isResolvingPlayback,
  hydratePlaybackState,
} = usePlaybackOrchestrator(initialPlaybackSeed as any)

const { sendReport } = useVideoHistory()
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction()
const { goToPrev, goToNext } = usePlaylist()

const { onVideoPlay, onVideoPause, onVideoEnded, onVideoTimeUpdate, flushPendingReport } = usePlaybackReporting(video, sendReport)

const { goToVideo, handleAutoplayNext, handlePrevVideoFromPlaylist, handleNextVideoFromPlaylist } = useVideoPageNavigation({
  route, router, video, relatedVideos, 
  goToPrev: goToPrev as any, 
  goToNext: goToNext as any, 
  onVideoEnded: onVideoEnded as any
} as any)

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
const remoteSaveByUrl = new Map<string, Promise<any>>()
let javdbMetadataRequestSeq = 0

const ensureLocalVideo = async (targetVideo: any) => {
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
    }).then(({ data, error }: any) => {
      if (error || !data?.id) return null
      return data
    })
    remoteSaveByUrl.set(url, savePromise)
  }

  const savedVideo = await savePromise
  if (!savedVideo?.id) return null

  if (video.value && String((video.value as any).url || '') === url) {
    video.value = {
      ...(video.value as any),
      id: String(savedVideo.id),
      interaction_type: savedVideo.interaction_type ?? (video.value as any).interaction_type ?? null,
      last_position: savedVideo.last_position ?? (video.value as any).last_position,
      clip_markers: savedVideo.clip_markers ?? (video.value as any).clip_markers,
      source: 'local',
      site: (video.value as any).site || savedVideo.site,
      url,
    } as any
    if (String(route.params.videoId || '') !== String(savedVideo.id)) {
      await router.replace({ name: 'VideoPlay', params: { videoId: savedVideo.id } })
    }
  }

  return video.value || savedVideo
}

watch(() => {
  const currentVideo = video.value as any
  if (currentVideo?.source !== 'remote') return ''
  return String(currentVideo.url || '').trim()
}, async (url) => {
  if (!url) return
  await ensureLocalVideo(video.value as any)
}, { immediate: true })

const { videoActions, handleVideoAction } = useVideoActionBar({
  video,
  interactionTypeLike: INTERACTION_TYPE.LIKE,
  interactionTypeDislike: INTERACTION_TYPE.DISLIKE,
  interactionTypeLater: INTERACTION_TYPE.LATER,
  toggleLike: (id: any, type: any) => toggleLike(id, type as any) as any, 
  deleteInteraction: deleteInteraction as any, 
  ensureLocalVideo: ensureLocalVideo as any,
  handleAddToPlaylist: () => Promise.resolve() as any,
  handlePlayRandom: () => Promise.resolve() as any
} as any)

const { handlePlaybackTimeUpdate, handleClipMarkerSeek, handleClipMarkersUpdated } = useVideoClipMarkers({
  video,
  seekToTime: async (t: number) => {
    if (await seekGlobalVideoPlayer(t)) await playGlobalVideoPlayer()
    focusGlobalVideoPlayer()
  }
} as any)

const handleVideoTimeUpdate = (currentTime: number) => {
  onVideoTimeUpdate(currentTime)
  handlePlaybackTimeUpdate(currentTime)
}

const videoPublishedText = computed(() => {
  const d = video.value?.publish_date || video.value?.uploaded_at
  return d ? formatDate(d as any) : ''
})

const videoDescription = computed(() => String((video.value as any)?.description || '').trim())
const isRemoteVideo = computed(() => (video.value as any)?.source === 'remote')
const videoActors = computed(() => {
  const actors = (video.value as any)?.actors
  if (!Array.isArray(actors)) return []
  return actors
    .filter((actor: any) => String(actor?.name || '').trim())
    .map((actor: any) => ({
      ...actor,
      name: String(actor.name || '').trim(),
      url: String(actor.url || '').trim(),
      avatar: String(actor.avatar || '').trim(),
    }))
})
const shouldResolveJavdbMetadata = computed(() => {
  const v = video.value as any
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

  const snapshot = video.value as any
  const url = String(snapshot?.url || '').trim()
  if (!url) return

  const requestSeq = ++javdbMetadataRequestSeq
  try {
    const metadata = await window.desktopApp.resolveJavdbMetadata(url)
    if (requestSeq !== javdbMetadataRequestSeq) return
    const current = video.value as any
    if (!current || String(current.url || '') !== url) return
    const mergedVideo = mergeVideoMetadata(current, metadata as any, url)
    if (mergedVideo) {
      video.value = mergedVideo as any
    }
  } catch {
    // Metadata enrichment must not block playback.
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

onMounted(() => {
  void syncDescriptionOverflow()
})

onBeforeUnmount(() => {
  descriptionResizeObserver?.disconnect()
})

const primarySubscription = computed(() => {
  const v = video.value as any
  if (!v) return null
  return v.subscriptions?.[0] || v.actors?.[0] || null
})

const displayedVideoActors = computed(() => {
  const primary = primarySubscription.value as any
  const primaryUrl = String(primary?.url || '').trim().toLowerCase()
  const primaryId = primary?.id != null ? String(primary.id).trim() : ''
  const primaryName = String(primary?.name || '').trim().toLowerCase()

  return videoActors.value.filter((actor: any) => {
    const actorUrl = String(actor?.url || '').trim().toLowerCase()
    if (primaryUrl && actorUrl && actorUrl === primaryUrl) return false

    const actorId = actor?.id != null ? String(actor.id).trim() : ''
    if (primaryId && actorId && actorId === primaryId) return false

    const actorName = String(actor?.name || '').trim().toLowerCase()
    return !(primaryName && actorName && actorName === primaryName)
  })
})

const primarySubscriptionUrl = computed(() => String((primarySubscription.value as any)?.url || '').trim())

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
  route, playerAdapter, video, playbackSource, subtitleTracks,
  resolvedInitialTime: computed(() => startTime.value),
  clipMarkers: ref([]),
  hasPrevVideo: ref(false), hasNextVideo: ref(false),
  externalError, isResolvingPlayback, effectiveTheme, relatedVideos, loadingRelated,
  hasPrev: ref(false), hasNext: ref(false),
  globalVideoPlayerSession: globalVideoPlayerSession as any, 
  activateGlobalVideoPlayerSession: activateGlobalVideoPlayerSession as any, 
  clearGlobalVideoPlayerSession: clearGlobalVideoPlayerSession as any,
  registerGlobalVideoPlayerTarget: registerGlobalVideoPlayerTarget as any, 
  unregisterGlobalVideoPlayerTarget: unregisterGlobalVideoPlayerTarget as any,
  focusGlobalVideoPlayer, hydratePlaybackState: hydratePlaybackState as any, 
  loadAndPlayById: loadAndPlayById as any,
  consumePlaybackSeed: (id: any) => consumeVideoPlaybackSeed(id as string),
  onVideoPlay, onVideoPause, handleAutoplayNext: handleAutoplayNext as any, 
  handlePlaybackTimeUpdate: handleVideoTimeUpdate,
  handlePrevVideoFromPlaylist: handlePrevVideoFromPlaylist as any, 
  handleNextVideoFromPlaylist: handleNextVideoFromPlaylist as any,
  handlePlayerRetry: () => {
    if (video.value?.id) (loadAndPlayById as any)(video.value.id, video.value, { forceRefresh: true })
  },
  handleClipMarkerSeek: handleClipMarkerSeek as any, 
  handleClipMarkersUpdated: handleClipMarkersUpdated as any, 
  flushPendingReport
} as any)

const resolveRemoteChannelSite = (url: string) => {
  let parsedUrl: URL
  try {
    parsedUrl = new URL(url)
  } catch {
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

const openChannelDetail = async (profile: any) => {
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
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
