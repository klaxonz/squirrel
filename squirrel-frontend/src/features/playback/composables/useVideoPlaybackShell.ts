import { onMounted, onUnmounted, ref, watch } from 'vue'
import type { Ref } from 'vue'

import { Logger } from '@/shared/lib/logger'
import type { ClipMarker, VideoId, VideoPageVideo } from '@/features/playback/types/videoPlayback'
import type { PlayerHandlers } from '@/features/playback/types/playerSession'
import { usePlaybackSession } from '@/features/playback/composables/usePlaybackSession'

import { useUIStore } from '@/shared/stores/ui'

type VideoSeedGetter = (videoId: unknown) => VideoPageVideo | null

type RouteLike = {
  params: Record<string, unknown>
}

// ADR-0002 PR2 — the data-flow inversion. The 16-source reconciliation
// `watch([...])` that used to pump orchestrator refs into the session is GONE.
// PlaybackSession.facts is now the single source of truth, written by the
// orchestrator's fetch sites + a few honest 1-source forwards below
// (widescreen / theme / hasPrev / hasNext). Cross-route reuse collapses to
// session.isReusableFor(id), and the no-op-else-beginNewVideo branch below
// replaces the hydrate path.
//
// What this shell still owns:
//   - view-local element refs (host / page / section / meta)
//   - the isWidescreen UI ref + its class/sidebar side effects (fact forwarded)
//   - the global player target lifecycle (register/unregister on the Pinia store)
//   - threading the player event handlers + adapter (ponytail: PR3 relocates
//     these wiring handles into the host)
export default function useVideoPlaybackShell({
  route,
  effectiveTheme,
  consumePlaybackSeed,
  loadAndPlayById,
  registerGlobalVideoPlayerTarget,
  unregisterGlobalVideoPlayerTarget,
  focusGlobalVideoPlayer,
  publishWiring,
  flushPendingReport,
  onVideoPlay,
  onVideoPause,
  handleAutoplayNext,
  handlePlaybackTimeUpdate,
  handlePrevVideoFromPlaylist,
  handleNextVideoFromPlaylist,
  handlePlayerRetry,
  handleClipMarkerSeek,
  handleClipMarkersUpdated,
  hasPrev,
  hasNext,
}: {
  route: RouteLike
  effectiveTheme: Ref<string>
  consumePlaybackSeed: VideoSeedGetter
  loadAndPlayById: (videoId: VideoId, initialVideoData?: VideoPageVideo | null, options?: Record<string, unknown>) => Promise<void>
  registerGlobalVideoPlayerTarget: (target: HTMLElement) => void
  unregisterGlobalVideoPlayerTarget: () => void
  focusGlobalVideoPlayer: () => Promise<void>
  publishWiring: (handlers: PlayerHandlers) => void
  flushPendingReport: () => Promise<void>
  onVideoPlay: () => void
  onVideoPause: () => void
  handleAutoplayNext: (event?: { autoplay?: boolean; autoplayNext?: boolean; loop?: boolean }) => void | Promise<void>
  handlePlaybackTimeUpdate: (currentTime: number) => void
  handlePrevVideoFromPlaylist: () => void | Promise<void>
  handleNextVideoFromPlaylist: () => void | Promise<void>
  handlePlayerRetry: () => void | Promise<void>
  handleClipMarkerSeek: (time: number) => void | Promise<void>
  handleClipMarkersUpdated: (markers: ClipMarker[]) => void
  hasPrev: Ref<boolean>
  hasNext: Ref<boolean>
}) {
  const uiStore = useUIStore()
  const session = usePlaybackSession()
  const videoPlayerHostRef = ref<HTMLElement | null>(null)
  const videoPageRef = ref<HTMLElement | null>(null)
  const videoSectionRef = ref<HTMLElement | null>(null)
  const videoMetaRef = ref<HTMLElement | null>(null)
  const isWidescreen = ref(false)

  const setWidescreenClass = (enabled: boolean) => {
    document.documentElement.classList.toggle('video-widescreen', !!enabled)
  }

  const syncWidescreenSidebarState = (enabled: boolean) => {
    uiStore.setVideoWidescreen(!!enabled)
  }

  const toggleWidescreen = (value: boolean) => {
    isWidescreen.value = value
    setWidescreenClass(isWidescreen.value)
    syncWidescreenSidebarState(isWidescreen.value)
    // Fact forward: the host renders the widescreen flag from facts, so the
    // view-local toggle must reach the owner. (One honest 1-source write — not
    // a reconciliation pump: there is a single writer, toggled on user action.)
    session.update({ widescreen: !!value })
  }

  const focusVideoPlayer = async () => {
    try {
      await focusGlobalVideoPlayer()
    } catch (error) {
      Logger.debug('Failed to focus video player', error)
    }
  }

  // Assembles the player handler bag from the view-supplied callbacks. The host
  // reads it from `playerStore.handlers`; PR2 keeps that Pinia wiring in place.
  // ponytail: PR3 relocates this into the host once the orchestrator becomes
  // the direct emit target (no VideoPlayer emit → host → handlers round-trip).
  const buildPlayerHandlers = (): PlayerHandlers => ({
    onPlay: onVideoPlay,
    onPause: onVideoPause,
    onEnded: handleAutoplayNext,
    onTimeUpdate: handlePlaybackTimeUpdate,
    onPrev: hasPrev.value ? handlePrevVideoFromPlaylist : null,
    onNext: hasNext.value ? handleNextVideoFromPlaylist : null,
    onRetry: handlePlayerRetry,
    onWidescreenChange: toggleWidescreen,
    onClipMarkerSelect: handleClipMarkerSeek,
    onClipMarkersUpdated: handleClipMarkersUpdated,
  })

  const syncWiring = () => {
    publishWiring(buildPlayerHandlers())
  }

  watch(videoPlayerHostRef, (element) => {
    if (element) {
      registerGlobalVideoPlayerTarget(element)
      return
    }

    unregisterGlobalVideoPlayerTarget()
  }, { immediate: true })

  // Honest 1-source forward: theme comes from the theme store (not from a fetch
  // site), so the orchestrator never writes it. The shell — the only consumer
  // that knows about the theme store — forwards store changes into facts.
  watch(effectiveTheme, (theme) => {
    session.update({ theme })
  }, { immediate: true })

  // hasPrev / hasNext feed the host's prev/next buttons via facts. PR1 left
  // them as dead stubs (always false); PR2 still leaves the caller to supply
  // refs, but forwards them so the moment a real caller wires navigation flags
  // in, they reach the host without a pump. The handler bag also depends on
  // these (onPrev/onNext gating), so we republish wiring here too.
  watch([hasPrev, hasNext], ([prev, next]) => {
    session.update({ hasPrev: !!prev, hasNext: !!next })
    syncWiring()
  }, { immediate: true })

  onMounted(async () => {
    const videoId = String(route.params.videoId || '')
    if (session.isReusableFor(videoId)) {
      // No-op: the surviving session already represents this video, and the
      // orchestrator's computed projections reflect it. Nothing to fetch.
    } else {
      // loadAndPlayById owns session.beginNewVideo(videoId, seed) — it clears
      // stale facts, seeds facts.video, and marks externalLoading. Calling
      // beginNewVideo here too would null the seed (begin sets facts.video =
      // seed, and the inner call passes null).
      await loadAndPlayById(videoId, consumePlaybackSeed(videoId))
    }
    await focusVideoPlayer()

    setWidescreenClass(isWidescreen.value)
    syncWidescreenSidebarState(isWidescreen.value)
    syncWiring()
  })

  watch(() => route.params.videoId, async (newId, oldId) => {
    if (!newId || newId === oldId) return
    if (session.facts.videoId === String(newId)) return
    void flushPendingReport()
    const videoId = String(newId || '')
    if (session.isReusableFor(videoId)) {
      // Reuse — see onMounted.
    } else {
      await loadAndPlayById(videoId, consumePlaybackSeed(videoId))
    }
    await focusVideoPlayer()
    syncWiring()
  })

  onUnmounted(() => {
    setWidescreenClass(false)
    syncWidescreenSidebarState(false)
    unregisterGlobalVideoPlayerTarget()
    if (session.facts.pictureInPicture || (typeof document !== 'undefined' && document.pictureInPictureElement)) {
      return
    }
    void flushPendingReport()
    session.release()
  })

  return {
    videoPlayerHostRef,
    videoPageRef,
    videoSectionRef,
    videoMetaRef,
    isWidescreen,
    toggleWidescreen,
    focusVideoPlayer,
  }
}
