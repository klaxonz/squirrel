<template>
  <div ref="videoPageRef" class="min-h-screen bg-background" :class="{ 'px-0': isWidescreen }">
    <div class="max-w-[1800px] mx-auto grid grid-cols-1 lg:grid-cols-[1fr,400px] gap-8 p-6 lg:p-10">
      <!-- Main Content -->
      <div class="space-y-6 min-w-0">
        <!-- Player Section -->
        <div class="relative aspect-video rounded-2xl overflow-hidden bg-black shadow-2xl ring-1 ring-white/10">
          <div ref="videoPlayerHostRef" class="absolute inset-0" />
        </div>

        <!-- Video Header Info -->
        <div v-if="video" class="space-y-6">
          <div class="space-y-2">
            <h1 class="text-xl md:text-2xl font-bold tracking-tight leading-[1.2] text-foreground">
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
              <div v-if="primarySubscription" class="flex items-center gap-3 group cursor-pointer" @click="goToChannelDetail(primarySubscription.id)">
                <SubscriptionAvatar :src="primarySubscription.avatar" :name="primarySubscription.name" size="lg" class="w-10 h-10 ring-1 ring-border/20 group-hover:ring-primary/50 transition-all shadow-sm" />
                <div class="flex flex-col -space-y-0.5">
                  <span class="font-bold text-[15px] group-hover:text-primary transition-colors tracking-tight">{{ primarySubscription.name }}</span>
                  <span class="text-[12px] text-muted-foreground/60 font-medium">{{ primarySubscription.total_videos || 0 }} videos</span>
                </div>
              </div>
              <button class="px-4 py-2 bg-foreground text-background text-[13px] font-bold rounded-full hover:opacity-90 active:scale-95 transition-all shadow-sm">Subscribe</button>
            </div>

            <div class="flex items-center gap-2">
              <div class="flex bg-accent/40 rounded-full p-0.5 ring-1 ring-border/20">
                <button 
                  v-for="action in videoActions.filter(a => ['like', 'dislike'].includes(a.key))" 
                  :key="action.key"
                  class="flex items-center gap-2 px-4 py-1.5 rounded-full hover:bg-accent/60 transition-all text-[13px] font-semibold"
                  :class="{ 'text-foreground bg-background shadow-sm ring-1 ring-border/10': action.active, 'text-muted-foreground': !action.active }"
                  @click="handleVideoAction(action)"
                >
                  <component :is="action.icon" class="w-4 h-4" :stroke-width="action.active ? 2.5 : 2" />
                  <span v-if="action.label && action.key === 'like'">{{ action.label }}</span>
                </button>
              </div>
              
              <button class="w-9 h-9 flex items-center justify-center rounded-full bg-accent/40 hover:bg-accent/60 transition-all active:scale-95 ring-1 ring-border/20 text-muted-foreground hover:text-foreground">
                <Share2 class="w-4 h-4" />
              </button>
              <button class="w-9 h-9 flex items-center justify-center rounded-full bg-accent/40 hover:bg-accent/60 transition-all active:scale-95 ring-1 ring-border/20 text-muted-foreground hover:text-foreground">
                <MoreHorizontal class="w-4 h-4" />
              </button>
            </div>
          </div>

          <div class="p-4 bg-accent/20 rounded-xl ring-1 ring-border/10 group">
            <p class="text-[14px] leading-relaxed text-foreground/80 whitespace-pre-wrap">
              {{ (video as any).description || 'No description available.' }}
            </p>
          </div>
        </div>
        
        <!-- Skeleton -->
        <div v-else class="space-y-4 animate-pulse">
          <div class="h-8 bg-muted rounded-lg w-3/4" />
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 bg-muted rounded-full" />
            <div class="space-y-2">
              <div class="h-4 bg-muted rounded w-32" />
              <div class="h-3 bg-muted rounded w-20" />
            </div>
          </div>
        </div>
      </div>

      <!-- Sidebar Content (Related/Clips/Playlist) -->
      <div class="space-y-6">
        <div class="flex p-0.5 bg-accent/30 rounded-lg ring-1 ring-border/20">
          <button 
            v-for="tab in ['related', 'clips', 'playlist']" 
            :key="tab"
            @click="asideTab = tab"
            class="flex-1 py-1.5 text-[11px] font-bold uppercase tracking-wider rounded-md transition-all"
            :class="asideTab === tab ? 'bg-background text-foreground shadow-sm ring-1 ring-border/10' : 'text-muted-foreground hover:text-foreground'"
          >
            {{ tab }}
          </button>
        </div>

        <div class="min-h-[400px]">
          <Transition name="fade" mode="out-in">
            <div v-if="asideTab === 'related'" class="space-y-4">
              <article v-for="related in relatedVideos" :key="related.id" class="flex gap-3 group cursor-pointer" @click="goToVideo(related.id, related)">
                <div class="relative w-40 aspect-video shrink-0 rounded-lg overflow-hidden bg-accent/20 ring-1 ring-border/10 group-hover:ring-border/30 transition-all">
                  <img v-if="related.thumbnail" :src="(related.thumbnail as string)" class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" />
                  <span class="absolute bottom-1 right-1 px-1 py-0.5 bg-black text-[10px] font-bold text-white rounded-[4px] ring-1 ring-white/10 opacity-0 group-hover:opacity-100 transition-opacity">{{ formatDuration(related.duration as number) }}</span>
                </div>
                <div class="flex-1 min-w-0 flex flex-col gap-0.5">
                  <h4 class="text-[13px] font-semibold line-clamp-2 leading-[1.3] group-hover:text-primary transition-colors tracking-tight text-foreground/90">{{ related.title }}</h4>
                  <p class="text-[11px] text-muted-foreground/60 font-medium truncate">{{ (related as any).subscriptions?.[0]?.name || (related as any).site }}</p>
                  <p class="text-[10px] text-muted-foreground/40 font-medium">{{ formatDate((related as any).uploaded_at) }}</p>
                </div>
              </article>
            </div>
            <div v-else-if="asideTab === 'clips'" class="flex flex-col items-center justify-center py-20 text-muted-foreground">
              <Scissors class="w-10 h-10 mb-4 opacity-20" />
              <p class="text-sm font-medium">Press Shift + M to create a clip</p>
            </div>
          </Transition>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Share2, MoreHorizontal, Scissors } from 'lucide-vue-next'
import usePlaybackOrchestrator from '../composables/usePlaybackOrchestrator'
import usePlaybackReporting from '../composables/usePlaybackReporting'
import useVideoActionBar from '../composables/useVideoActionBar'
import useVideoClipMarkers from '../composables/useVideoClipMarkers'
import useVideoPlaybackShell from '../composables/useVideoPlaybackShell'
import useVideoPageNavigation from '../composables/useVideoPageNavigation'
import { consumeVideoPlaybackSeed, peekVideoPlaybackSeed } from '@/composables/videoPlaybackSeed'
import { useGlobalVideoPlayer } from '@/composables/useGlobalVideoPlayer'
import { useAppTheme } from '@/composables/useAppTheme'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import { LocalStorageAdapter } from '@/components/video-player/core'
import useVideoHistory from "../composables/useVideoHistory"
import { formatDate, formatDuration } from '../utils/dateFormat'
import useVideoInteraction from '../composables/useVideoInteraction'
import usePlaylist from '../composables/usePlaylist'

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
const { videoActions, handleVideoAction } = useVideoActionBar({
  video,
  interactionTypeLike: INTERACTION_TYPE.LIKE,
  interactionTypeDislike: INTERACTION_TYPE.DISLIKE,
  interactionTypeLater: INTERACTION_TYPE.LATER,
  toggleLike: (id: any, type: any) => toggleLike(id, type as any) as any, 
  deleteInteraction: deleteInteraction as any, 
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

const videoPublishedText = computed(() => {
  const d = video.value?.publish_date || video.value?.uploaded_at
  return d ? formatDate(d as any) : ''
})

const primarySubscription = computed(() => {
  const v = video.value as any
  if (!v) return null
  return v.subscriptions?.[0] || v.actors?.[0] || null
})

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
  handlePlaybackTimeUpdate,
  handlePrevVideoFromPlaylist: handlePrevVideoFromPlaylist as any, 
  handleNextVideoFromPlaylist: handleNextVideoFromPlaylist as any,
  handlePlayerRetry: () => {
    if (video.value?.id) (loadAndPlayById as any)(video.value.id, video.value, { forceRefresh: true })
  },
  handleClipMarkerSeek: handleClipMarkerSeek as any, 
  handleClipMarkersUpdated: handleClipMarkersUpdated as any, 
  flushPendingReport
} as any)

const goToChannelDetail = (id: any) => router.push(`/subscription/${id}/all`)
</script>

<style scoped>
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
