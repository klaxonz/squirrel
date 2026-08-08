/**
 * DASH stream adapter — based on shaka-player.
 *
 * Stream-adapter form of the former ShakaDashPlugin. See docs/adr/0001-stream-adapter-and-sink.md.
 * The internal loading / quality / codec-family / recovery logic is byte-identical
 * to the pre-refactor plugin; only the shell changed (constructor injection of
 * StreamContext, no PlayerPlugin lifecycle hooks, videoElement via lazy getter).
 */

import shaka from 'shaka-player'
import { SabrStreamingAdapter } from 'googlevideo/sabr-streaming-adapter'
import { errorMessage } from '@/shared/lib/errorMessage'
import { chooseOriginalAudioTrack } from './originalAudioTrack'
import { SabrShakaPlayerAdapter } from './SabrShakaPlayerAdapter'

// ponytail: shaka-player's TypedEvent<->detail surface and track.allowedByApplication
// field are runtime-only or loosely declared. The few `as any` reads below are
// deliberate interop casts at the shaka boundary, not loose internal typing.

import { getCodecFamily, compareCodecFamilies } from '../core/codec'
import {
  hasPresentedVideoFrameAfterSeek,
  shouldRecoverVideoAfterSeek,
} from '../core/post-seek-video-health'
import type { StreamAdapter, StreamContext, StreamSeekResult } from '../core/StreamAdapter'
import type { StreamSink } from '../core/StreamSink'
import type {
  MediaSource,
  PlaybackRecoveryAction,
  PlaybackRecoveryContext,
  PlayerError,
  QualityLevel,
  QualitySelectionRequest,
  SabrPlaybackConfig,
  SabrPlaybackSession,
} from '../core/types'

export interface ShakaDashAdapterOptions {
  enableAutoQuality?: boolean
}

type ShakaVariantTrack = shaka.extern.Track

/** FreeTube: body of a googlevideo alr=yes redirect starts with ASCII "http". */
const HTTP_IN_HEX = 0x68747470
const RequestType = shaka.net.NetworkingEngine.RequestType
const POST_SEEK_FRAME_CHECK_DELAY_MS = 3000
// Segment requests for a seek target typically fire within seconds of the
// scrub. A 4xx arriving later is treated as a mid-play failure (generic chain).
const SEEK_4XX_WINDOW_MS = 15_000
// FreeTube remaps settings "auto" → 720 until auto is fixed. The official
// YouTube player opens at the selected/top quality; pinning 720p read as the
// app being unable to hold quality. Open on the 1080p rung (highest class the
// vast majority of streams offer without VP9/AV1 4K penalties); ABR may climb
// or step down afterward.
const STARTUP_QUALITY_HEIGHT = 1080

const trackPrimaryDimension = (track: ShakaVariantTrack): number => {
  const width = Number(track.width || 0)
  const height = Number(track.height || 0)
  if (height <= 0 && width <= 0) return 0
  // FreeTube setDashQuality: portrait uses width as the "resolution" axis.
  return height > width && width > 0 ? width : height
}

/** Runtime Shaka flag; published d.ts omits allowedByApplication. */
const isApplicationAllowedTrack = (track: ShakaVariantTrack): boolean => {
  // Read via `in` + unknown so we never fall back to `any`.
  if (!('allowedByApplication' in track)) return true
  const flag: unknown = Reflect.get(track, 'allowedByApplication')
  return flag !== false
}

/**
 * Pick the best opening variant for auto quality.
 * Prefer an exact target-height match; otherwise the highest rung at or below
 * target; finally the lowest available (never jump straight to 4K on open).
 */
const pickStartupVariantTrack = (
  tracks: ShakaVariantTrack[],
  targetHeight = STARTUP_QUALITY_HEIGHT,
): ShakaVariantTrack | null => {
  if (tracks.length === 0) return null

  const scored = tracks
    .map((track) => ({ track, dimension: trackPrimaryDimension(track) }))
    .filter((entry) => entry.dimension > 0)

  if (scored.length === 0) {
    return [...tracks].sort((left, right) => (right.bandwidth || 0) - (left.bandwidth || 0))[0] || null
  }

  const exact = scored
    .filter((entry) => entry.dimension === targetHeight)
    .sort((left, right) => (right.track.bandwidth || 0) - (left.track.bandwidth || 0))
  if (exact[0]) return exact[0].track

  const atOrBelow = scored
    .filter((entry) => entry.dimension <= targetHeight)
    .sort((left, right) => {
      const dimensionDelta = right.dimension - left.dimension
      if (dimensionDelta !== 0) return dimensionDelta
      return (right.track.bandwidth || 0) - (left.track.bandwidth || 0)
    })
  if (atOrBelow[0]) return atOrBelow[0].track

  // Everything is above target (rare short ladder) — take the lowest height.
  const ascending = [...scored].sort((left, right) => {
    const dimensionDelta = left.dimension - right.dimension
    if (dimensionDelta !== 0) return dimensionDelta
    return (left.track.bandwidth || 0) - (right.track.bandwidth || 0)
  })
  return ascending[0]?.track ?? null
}

type VideoWithDecodedFrameCount = HTMLVideoElement & {
  webkitDecodedFrameCount?: number
}

export class ShakaDashAdapter implements StreamAdapter {
  private context: StreamContext
  private options: ShakaDashAdapterOptions
  // The sink handed to onSourceChange; the only channel back to the engine.
  private sink: StreamSink | null = null
  private player: shaka.Player | null = null
  private sabrAdapter: SabrStreamingAdapter | null = null
  private currentSource: string | null = null
  private sourceQualityHints: QualityLevel[] = []
  private selectedCodecFamily = 'auto'
  private activeCodecFamily: string | null = null
  private hasInstalledPolyfills = false
  private loadRequestSeq = 0
  private isSelectingQuality = false
  /** Whether ABR should come back on after the FreeTube-style startup pin. */
  private wantAutoQualityAfterStartupPin = true
  private postSeekWatchdogSeq = 0
  private postSeekWatchdogTimer: number | null = null
  private postSeekFrameCallbackId: number | null = null
  private postSeekFrameCallbackVideo: HTMLVideoElement | null = null
  private postSeekCompletion: ((visuallyReady: boolean) => void) | null = null
  /** Latest SABR session (poToken/serverAbrUrl/formats); shared by poToken minting, server-driven reloads and seek-4xx refresh. */
  private sabrSession: SabrPlaybackSession | null = null
  /** Wall-clock of the most recent seek(); used to scope seek-triggered HTTP 4xx recovery. */
  private lastSeekAt = 0
  /** One SABR-session refresh is attempted per seek before degrading to DASH. */
  private sabrRefreshAttemptedSinceSeek = false
  /** True once this source degraded SABR → bundled DASH; prevents repeated degrade loops. */
  private degradedToDashFallback = false

  constructor(context: StreamContext, options?: ShakaDashAdapterOptions) {
    this.context = context
    this.options = {
      // Match FreeTube / official players: ABR on, climb after start.
      enableAutoQuality: true,
      ...options,
    }
  }

  onSourceChange(source: MediaSource, sink: StreamSink): void {
    this.cancelPostSeekVideoWatchdog()
    this.sink = sink
    this.sourceQualityHints = Array.isArray(source.qualities) ? source.qualities : []
    this.lastSeekAt = 0
    this.sabrRefreshAttemptedSinceSeek = false
    this.degradedToDashFallback = false

    const isDash = source.type === 'dash' || (source.type === 'auto' && /\.mpd($|\?)/i.test(source.src))
    const wantsShaka = source.playbackEngine === 'shaka'

    if (!isDash || !wantsShaka) {
      this.loadRequestSeq += 1
      void this.destroyPlayer()
      this.currentSource = null
      return
    }

    // Publish official youtubei.js ladder immediately (itag heights/labels).
    // player.load() is async; without this the 画质 menu stays empty until
    // variants are parsed — and stays empty forever if load fails.
    this.updateQualities()

    const requestSeq = ++this.loadRequestSeq
    void this.loadSource(source, requestSeq)
  }

  private async loadSource(source: MediaSource, requestSeq: number): Promise<void> {
    if (!this.context.videoElement()) return
    const src = source.src

    if (!this.hasInstalledPolyfills) {
      shaka.polyfill.installAll()
      this.hasInstalledPolyfills = true
    }

    await this.destroyPlayer()
    const video = this.context.videoElement()
    if (requestSeq !== this.loadRequestSeq || !video) return
    this.currentSource = src

    const player = new shaka.Player()
    this.player = player

    await player.attach(video)
    if (requestSeq !== this.loadRequestSeq || this.player !== player) {
      await player.destroy().catch((e) => {
        this.context.logger.warn('[ShakaDashAdapter] Failed to destroy player on attach race', e)
      })
      return
    }

    // FreeTube getPlayerConfig('dash'): YouTube-tuned buffer goals + ABR that
    // respects the video element size. Our previous 10s/2s goals forced long
    // spinner waits on SegmentBase index seeks; rebufferingGoal 0.02 matches
    // official FreeTube and resumes as soon as a few frames are buffered.
    //
    // ABR stays off during load (FreeTube pattern) so a warm bandwidth
    // for the opening selection (pure ABR often opens on a tiny rung, or on a
    // prior-session high estimate that jumps straight to 1080p/4K and stalls
    // estimate cannot fetch 4K init+media first; pin after load, then
    // still climb — see applyStartupQuality.
    const wantAutoQuality = this.options.enableAutoQuality !== false
    player.configure({
      abr: {
        // Disabled until applyStartupQuality pins the opening rung. Leaving ABR
        // on during player.load lets a warm bandwidth estimate fetch 1080p/4K
        // init+media before we can pin, which is the dominant "slow start" after
        // resolve is already warm.
        enabled: false,
        // Quality must NOT depend on the video element's rendered size —
        // a small window/player then caps ABR at 480p/240p/144p. The official
        // players select by bandwidth only; element size never touches the
        // ladder (verified: 640x360 element pinned active track to 480p with
        // this on, 1080p with it off on the same manifest).
        restrictToElementSize: false,
        // Seed ~1080p-class so the first AbrManager sample after re-enable is
        // not Shaka's 500 kbps default.
        defaultBandwidthEstimate: 6_000_000,
      },
      streaming: {
        // SABR already has server-side buffer control. Asking Shaka for three
        // minutes causes an unnecessary UMP request storm; a shorter forward
        // window is enough for smooth playback and keeps startup responsive.
        // 12s ≈ a couple of media segments — far less than FreeTube's 180s DASH
        // goal, and tighter than our previous 30s SABR window.
        bufferingGoal: source.sabr ? 12 : 60,
        rebufferingGoal: 0.02,
        bufferBehind: source.sabr ? 30 : 120,
        retryParameters: {
          maxAttempts: 4,
          baseDelay: 1000,
          backoffFactor: 2,
          fuzzFactor: 0.5,
          timeout: 30000,
        },
      },
      manifest: {
        // Live + VOD captions; FreeTube keeps this on for all DASH.
        segmentRelativeVttTiming: true,
        retryParameters: {
          maxAttempts: 3,
          baseDelay: 1000,
          backoffFactor: 2,
          fuzzFactor: 0.5,
          timeout: 30000,
        },
      },
      // youtubei.js marks creator-original audio as role=main and localized
      // dubbing as alternate+dub. Make the correct language the initial Shaka
      // adaptation set; a post-load refinement below removes DRC/Stable Volume.
      preferredAudio: [{
        language: '',
        role: 'main',
        label: '',
        channelCount: 0,
        codec: '',
      }],
      // Prefer variants that decode smoothly / with hardware when available.
      preferredDecodingAttributes: ['smooth', 'powerEfficient'],
    })
    // Stash so applyStartupQuality knows whether to re-enable ABR.
    this.wantAutoQualityAfterStartupPin = wantAutoQuality

    if (source.sabr) {
      this.installSabrPlayback(player, source.sabr)
    } else {
      // Legacy official DASH: googlevideo videoplayback uses POST + range=
      // query + alr=yes, and follows textual http redirect bodies.
      this.installYouTubeNetworkingFilters(player)
    }
    this.setupEventListeners(player)

    try {
      // FreeTube: player.load(manifestSrc, startTime, manifestMimeType).
      // Pass DASH mime so data: / remote MPD never mis-detect as other types.
      try {
        await player.load(src, /* startTime */ null, 'application/dash+xml')
      } catch (sabrError) {
        if (!source.sabr?.fallbackSrc) throw sabrError
        if (requestSeq !== this.loadRequestSeq || this.player !== player) return

        // SABR is preferred but not required. The provider includes a regular
        // DASH manifest from the same player response so this retry adds no
        // resolver round trip and preserves a reliable playback path.
        this.context.logger.warn('[ShakaDashAdapter] SABR load failed; falling back to DASH', sabrError)
        await this.loadBundledDashFallback(player, source.sabr.fallbackSrc, null)
      }
      if (requestSeq !== this.loadRequestSeq || this.player !== player) {
        await player.destroy().catch((e) => {
          this.context.logger.warn('[ShakaDashAdapter] Failed to destroy player on load race', e)
        })
        return
      }
      this.selectOriginalAudioTrack()
      // Pin a concrete mid-high ladder before the first segment so AbrManager
      // cannot open on 144p/240p; ABR stays enabled and may still climb afterward.
      // on 144p/240p; ABR stays enabled and may still climb afterward.
      this.applyStartupQuality()
      this.updateActiveCodecFamily()
      this.updateQualities()
    } catch (error) {
      // Keep provider quality hints visible even when shaka fails to attach —
      // empty ladder + "画质" chrome is worse than a menu that still lists rungs.
      this.updateQualities()
      this.sink?.error({
        code: 'SHAKA_LOAD_FAILED',
        message: errorMessage(error, 'Shaka failed to load DASH source'),
        fatal: false,
        details: error,
      })
    }
  }

  private installSabrPlayback(player: shaka.Player, config: SabrPlaybackConfig): void {
    this.sabrSession = config
    const adapter = new SabrStreamingAdapter({
      playerAdapter: new SabrShakaPlayerAdapter(),
      clientInfo: config.clientInfo,
      enableCaching: true,
      maxCacheSizeMB: 8,
      maxCacheAgeSeconds: 300,
    })

    adapter.onMintPoToken(async () => this.sabrSession?.poToken ?? '')
    adapter.onReloadPlayerResponse(async () => {
      const refreshed = await config.refresh?.()
      if (!refreshed) {
        throw new Error('YouTube SABR session refresh returned no playable payload')
      }
      this.applySabrSession(refreshed)
    })
    adapter.onSnackbarMessage((message) => {
      this.context.logger.debug('[ShakaDashAdapter] YouTube SABR message', message)
    })

    adapter.attach(player)
    adapter.setStreamingURL(config.serverAbrUrl)
    adapter.setUstreamerConfig(config.ustreamerConfig)
    adapter.setServerAbrFormats(config.formats)
    this.sabrAdapter = adapter
  }

  /** Push a fresh SABR session (serverAbrUrl / ustreamer / formats) onto the adapter. */
  private applySabrSession(session: SabrPlaybackSession): void {
    this.sabrSession = session
    this.sabrAdapter?.setStreamingURL(session.serverAbrUrl)
    this.sabrAdapter?.setUstreamerConfig(session.ustreamerConfig)
    this.sabrAdapter?.setServerAbrFormats(session.formats)
  }

  private disposeSabrAdapter(): void {
    if (!this.sabrAdapter) return
    this.sabrAdapter.dispose()
    this.sabrAdapter = null
    this.sabrSession = null
  }

  /**
   * Switch a live Shaka player from SABR to the bundled regular DASH manifest
   * from the same player response. Shared by the SABR start-failure path
   * (loadSource) and seek-4xx degradation: dispose the SABR adapter, install
   * the YouTube networking filters (POST + range= + alr=yes) once, then load
   * the fallback MPD — optionally at a resume time so a mid-play degrade does
   * not rewind the playhead to 0.
   */
  private async loadBundledDashFallback(
    player: shaka.Player,
    fallbackSrc: string,
    startTime: number | null,
  ): Promise<void> {
    this.disposeSabrAdapter()
    this.installYouTubeNetworkingFilters(player)
    this.currentSource = fallbackSrc
    await player.load(fallbackSrc, startTime, 'application/dash+xml')
  }

  // --- YouTube SABR seek-triggered HTTP 4xx recovery ---
  //
  // googlevideo byte-range segment fetches can 400/403 in the wake of a large
  // seek (the session/poToken binding is not valid for the requested range).
  // The generic retry chain would re-request the SAME range forever, so this
  // early hook (consulted by error-recovery BEFORE retry/quality-fallback):
  //   1. refreshes the SABR session (new poToken / serverAbrUrl) and nudges
  //      the segment pipeline — once per seek;
  //   2. if refresh is unavailable or the 4xx recurs, degrades to the bundled
  //      regular DASH manifest and seeks straight to the target time.
  // Transient single-segment aborts (no HTTP status) and mid-play 4xx outside
  // the seek window keep the exact pre-existing generic chain.

  /** HTTP status captured from a Shaka error detail (BAD_HTTP_STATUS data[1]). */
  private extractHttpStatus(error: PlayerError): number | null {
    const detail = error?.details as { data?: unknown[] } | undefined
    const data = Array.isArray(detail?.data) ? detail.data : []
    const status = Number(data[1])
    if (Number.isInteger(status) && status >= 400 && status < 600) return status

    const message = String(error?.message || '')
    const match = message.match(/(?:^|[\s,])(4\d{2})(?:[\s,]|$)/)
    return match ? Number(match[1]) : null
  }

  private isSeekContextHttp4xx(error: PlayerError): boolean {
    if (Date.now() - this.lastSeekAt > SEEK_4XX_WINDOW_MS) return false
    const status = this.extractHttpStatus(error)
    return status === 400 || status === 403
  }

  /**
   * SABR session invalidated mid-play: the UMP response came back empty
   * ("Empty SABR response without redirect information", Shaka 1002) — the
   * signed serverAbrUrl/poToken binding is dead, not the network or the
   * bandwidth. Unlike a plain network error this is NOT a quality problem:
   * the generic chain steps 1080p→720p→480p on it and the session stays
   * broken. Refresh the session instead (or degrade to the bundled DASH,
   * which keeps the full ladder at the current playhead).
   */
  private isSabrSessionInvalidated(error: PlayerError): boolean {
    const code = String(error?.code || '')
    if (code !== 'SHAKA_1002') return false
    return /empty sabr response/i.test(String(error?.message || ''))
  }

  /**
   * Early recovery hook (StreamAdapter.handleProviderRecovery). Returns
   * 'handled' only when this adapter took over a seek-triggered HTTP 4xx or a
   * mid-play SABR session invalidation on a SABR session; anything else
   * returns null so the generic chain is untouched (zero impact on normal
   * SABR playback and legacy DASH).
   */
  async handleProviderRecovery(error: PlayerError, context: PlaybackRecoveryContext): Promise<PlaybackRecoveryAction | null> {
    const isSeek4xx = this.isSeekContextHttp4xx(error)
    const isSessionInvalidated = this.isSabrSessionInvalidated(error)
    if (!isSeek4xx && !isSessionInvalidated) return null
    const sabrConfig = context.source?.sabr
    if (!sabrConfig || this.degradedToDashFallback) return null

    if (!this.sabrRefreshAttemptedSinceSeek) {
      this.sabrRefreshAttemptedSinceSeek = true
      if (await this.tryRefreshSabrSession(sabrConfig)) {
        this.context.logger.warn('[ShakaDashAdapter] SABR session invalidated: refreshed session, retrying segment pipeline')
        try {
          this.player?.retryStreaming?.(0.1)
        } catch (e) {
          this.context.logger.warn('[ShakaDashAdapter] retryStreaming after SABR refresh failed', e)
        }
        return 'handled'
      }
    }

    if (!sabrConfig.fallbackSrc || !this.player) return null

    const player = this.player
    const target = Number.isFinite(context.currentTime)
      ? context.currentTime
      : (this.context.videoElement()?.currentTime ?? 0)
    this.degradedToDashFallback = true
    this.context.logger.warn('[ShakaDashAdapter] SABR recovery exhausted: degrading to bundled DASH at', target)
    try {
      await this.loadBundledDashFallback(player, sabrConfig.fallbackSrc, target > 0 ? target : null)
      this.updateActiveCodecFamily()
      this.updateQualities()
      this.syncBufferingToSink()
      const video = this.context.videoElement()
      if (video && !video.paused && !video.ended) {
        void video.play().catch((e) => {
          this.context.logger.warn('[ShakaDashAdapter] Play after DASH degrade failed', e)
        })
      }
    } catch (e) {
      this.context.logger.warn('[ShakaDashAdapter] DASH degrade failed', e)
      return null
    }
    return 'handled'
  }

  private async tryRefreshSabrSession(config: SabrPlaybackConfig): Promise<boolean> {
    if (typeof config.refresh !== 'function' || !this.sabrAdapter) return false
    try {
      const refreshed = await config.refresh()
      if (!refreshed) return false
      this.applySabrSession(refreshed)
      return true
    } catch (e) {
      this.context.logger.warn('[ShakaDashAdapter] SABR session refresh failed', e)
      return false
    }
  }

  /**
   * FreeTube request/response filters for official youtubei.js DASH BaseURLs.
   * Without POST+alr, long googlevideo SegmentBase sessions often 403 mid-play.
   *
   * CRITICAL: append range=/alr= as literal strings. Never rebuild the URI via
   * URL / URLSearchParams — that re-encodes googlevideo `sig` / `lsig`
   * (e.g. A/B+C → A%2FB+C) and YouTube rejects the segment (403 / empty).
   * FreeTube: `request.uris[0] += \`&range=${...}\`` then `+= '&alr=yes'`.
   */
  private installYouTubeNetworkingFilters(player: shaka.Player): void {
    const networkingEngine = player.getNetworkingEngine()
    if (!networkingEngine) return

    networkingEngine.registerRequestFilter((type, request) => {
      if (type !== RequestType.SEGMENT || !request.uris?.[0]) return
      let url: URL
      try {
        url = new URL(request.uris[0])
      } catch {
        return
      }
      // FreeTube: skip sabr: and only rewrite googlevideo videoplayback.
      if (
        url.protocol === 'sabr:'
        || !url.hostname.endsWith('.googlevideo.com')
        || url.pathname !== '/videoplayback'
      ) {
        return
      }

      // Official player: POST with tiny protobuf body, Range → query range=, alr=yes.
      request.method = 'POST'
      request.body = new Uint8Array([0x78, 0]) // protobuf: { 15: 0 }

      // FreeTube always appends via string concat (BaseURLs already have a query).
      // Never rebuild with URLSearchParams — re-encodes sig/lsig → 403.
      //
      // Idempotent on Shaka retries: if the URI was already rewritten, do not
      // stack a second &range= / &alr=yes (double params → googlevideo 403).
      const rangeHeader = request.headers.Range || request.headers.range
      if (rangeHeader) {
        if (!/[?&]range=/.test(request.uris[0])) {
          const rangeValue = String(rangeHeader).includes('=')
            ? String(rangeHeader).split('=').slice(1).join('=')
            : String(rangeHeader)
          request.uris[0] += `&range=${rangeValue}`
        }
        delete request.headers.Range
        delete request.headers.range
      }
      // Strip Content-Type here too — main-process webRequest can miss casing races.
      delete request.headers['Content-Type']
      delete request.headers['content-type']
      if (!/[?&]alr=/.test(request.uris[0])) {
        request.uris[0] += '&alr=yes'
      }
    })

    networkingEngine.registerResponseFilter(async (type, response, context) => {
      if (type !== RequestType.SEGMENT || !response.data) return
      try {
        if (response.uri && new URL(response.uri).protocol === 'sabr:') return
      } catch {
        // continue — still try redirect body decode
      }

      // FreeTube: DataView(response.data) assumes ArrayBuffer. Shaka may hand
      // an ArrayBufferView; normalize so getUint32 / fromUTF8 see the same bytes.
      const rawData = response.data
      const bytes = ArrayBuffer.isView(rawData)
        ? new Uint8Array(rawData.buffer, rawData.byteOffset, rawData.byteLength)
        : new Uint8Array(rawData as ArrayBuffer)
      if (bytes.byteLength <= 4) return
      const dataView = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
      if (dataView.getUint32(0) !== HTTP_IN_HEX) return

      // googlevideo alr redirect: body is a plain URL string to the real media.
      // Strip whitespace/NUL — a dirty URL on makeRequest follow → 403 / empty.
      const responseAsString = shaka.util.StringUtils.fromUTF8(bytes)
        .replace(/\0+$/g, '')
        .trim()
      if (!/^https?:\/\//i.test(responseAsString)) return

      const retryParameters = player.getConfiguration().streaming.retryParameters
      // FreeTube: makeRequest → SEGMENT request → same requestFilter rewrites
      // to POST + alr. Session UA must be Chrome (no Electron) or follow 403s.
      const redirectRequest = shaka.net.NetworkingEngine.makeRequest(
        [responseAsString],
        retryParameters,
      )
      const requestOperation = player.getNetworkingEngine()?.request(
        type,
        redirectRequest,
        context,
      )
      if (!requestOperation) return
      const redirectResponse = await requestOperation.promise
      response.data = redirectResponse.data
      response.headers = redirectResponse.headers
      response.uri = redirectResponse.uri
    })
  }

  private setupEventListeners(player: shaka.Player): void {
    player.addEventListener('error', (event: Event) => {
      if (this.player !== player) return
      const detail = (event as CustomEvent).detail
      this.sink?.error({
        code: `SHAKA_${detail?.code || 'UNKNOWN'}`,
        message: detail?.message || 'Shaka playback error',
        fatal: false,
        details: detail,
      })
    })

    player.addEventListener('buffering', (event: Event) => {
      // destroyPlayer() nulls this.player before awaiting Shaka teardown; ignore
      // late events from that old instance so they cannot mutate a new source.
      if (this.player !== player) return
      // Shaka FakeEvent copies Map('buffering', isBuffering) onto the event
      // itself (see makeEvent_ + FakeEvent). FreeTube reads event.buffering;
      // CustomEvent.detail is not used for this event and is usually undefined.
      const e = event as Event & { buffering?: boolean; detail?: { buffering?: boolean } }
      let buffering: boolean
      if (typeof e.buffering === 'boolean') {
        buffering = e.buffering
      } else if (typeof e.detail?.buffering === 'boolean') {
        buffering = e.detail.buffering
      } else {
        buffering = this.player?.isBuffering() ?? false
      }
      this.sink?.loadingStateChanged(buffering)

      // Shaka PlayRateController forces playbackRate=0 while STARVING. On the
      // SATISFIED edge it normally restores the rate; repair only a stale zero.
      // Playback intent remains engine-owned so a user pause is never undone.
      if (!buffering) {
        this.restorePlaybackRateAfterRebuffer()
      }
    })

    const refresh = () => {
      if (this.player !== player) return
      this.updateActiveCodecFamily()
      this.updateQualities()
    }

    player.addEventListener('loading', refresh)
    player.addEventListener('adaptation', refresh)
    player.addEventListener('variantchanged', refresh)
    player.addEventListener('trackschanged', refresh)
  }

  private getVariantTracks(): ShakaVariantTrack[] {
    if (!this.player) return []
    return this.player.getVariantTracks().filter((track) => track.type === 'variant')
  }

  private selectOriginalAudioTrack(): void {
    if (!this.player) return
    const tracks = this.player.getAudioTracks()
    const originalTrack = chooseOriginalAudioTrack(tracks)
    if (!originalTrack || originalTrack.active) return

    this.player.selectAudioTrack(originalTrack, 0)
    this.context.logger.info('[ShakaDashAdapter] Selected creator-original audio track', {
      language: originalTrack.language,
      label: originalTrack.label,
      roles: originalTrack.roles,
    })
  }

  /**
   * Pin the startup rung (1080p-class) after the manifest loads
   * first load, with abr disabled for that selection. Without an explicit pin:
   *   - cold AbrManager opens on 144p/240p (undersized layout / 500kbps default)
   *   - warm AbrManager opens on 1080p/4K from the previous video's throughput
   * Both feel like "slow start": either mushy first frame or a multi-MB first
   * segment. ABR stays off during load, then re-enables so quality climbs.
   */
  private applyStartupQuality(): void {
    if (!this.player) return

    const tracks = this.getVariantTracks().filter(isApplicationAllowedTrack)
    if (tracks.length === 0) {
      this.restoreAbrAfterStartupPin()
      return
    }

    const selected = pickStartupVariantTrack(tracks, STARTUP_QUALITY_HEIGHT)
    if (!selected) {
      this.restoreAbrAfterStartupPin()
      return
    }

    try {
      this.isSelectingQuality = true
      // ABR stays off (configured at load). Always pin the startup rung even when
      // track is already higher — that warm AbrManager path is the slow start.
      const active = tracks.find((track) => track.active) || null
      const activeDimension = active ? trackPrimaryDimension(active) : 0
      const selectedDimension = trackPrimaryDimension(selected)
      const needsDownshift = activeDimension > selectedDimension && selectedDimension > 0
      if (!selected.active || needsDownshift) {
        // clearBuffer only when abandoning a higher rung so its init/media cannot
        // monopolize the first network slots; otherwise keep whatever is buffered.
        this.player.selectVariantTrack(
          selected,
          /* clearBuffer */ needsDownshift,
          /* safeMargin */ 0,
        )
      }
      this.context.logger.debug('[ShakaDashAdapter] Pinned FreeTube-style startup quality', {
        height: selected.height,
        bandwidth: selected.bandwidth,
        id: selected.id,
        wasActive: selected.active,
        needsDownshift,
      })
    } catch (error) {
      this.context.logger.warn('[ShakaDashAdapter] Failed to pin startup quality', error)
    } finally {
      this.isSelectingQuality = false
      this.restoreAbrAfterStartupPin()
    }
  }

  private restoreAbrAfterStartupPin(): void {
    if (!this.player) return
    if (this.wantAutoQualityAfterStartupPin === false) return
    if (this.options.enableAutoQuality === false) return
    try {
      this.player.configure({ abr: { enabled: true } })
    } catch (error) {
      this.context.logger.warn('[ShakaDashAdapter] Failed to re-enable ABR after startup pin', error)
    }
  }



  private updateActiveCodecFamily(): void {
    const activeTrack = this.getVariantTracks().find((track) => track.active)
    this.activeCodecFamily = getCodecFamily(activeTrack?.videoCodec) || null
  }

  private buildQualitiesFromVariants(): QualityLevel[] {
    const tracks = this.getVariantTracks()
    const results: QualityLevel[] = []
    const seen = new Set<string>()

    for (const track of tracks) {
      const codec = getCodecFamily(track.videoCodec)
      if (
        this.selectedCodecFamily !== 'auto' &&
        codec &&
        codec !== this.selectedCodecFamily
      ) {
        continue
      }

      const id = String(track.id)
      if (seen.has(id)) continue
      seen.add(id)
      results.push({
        id,
        label: track.height ? `${track.height}p` : `${Math.round((track.bandwidth || 0) / 1000)}kbps`,
        width: track.width || undefined,
        height: track.height || undefined,
        bitrate: track.bandwidth || undefined,
        codec: codec || undefined,
      })
    }

    results.sort((left, right) => {
      const heightDelta = (right.height || 0) - (left.height || 0)
      if (heightDelta !== 0) return heightDelta
      return (right.bitrate || 0) - (left.bitrate || 0)
    })

    return results
  }

  private updateQualities(): void {
    const hinted = this.sourceQualityHints.length > 0
      ? this.sourceQualityHints
          .filter((quality) => quality && quality.id !== undefined && quality.id !== null)
          .map((quality) => ({
            id: quality.id,
            label: quality.label || (quality.height ? `${quality.height}p` : String(quality.id)),
            width: quality.width,
            height: quality.height,
            bitrate: quality.bitrate,
            codec: quality.codec || undefined,
            src: quality.src,
          }))
      : []

    const qualities = hinted.length > 0 ? hinted : this.buildQualitiesFromVariants()

    // Never push an empty list while we still have provider hints — that wipes
    // the menu seed and leaves only the "画质" chrome.
    if (qualities.length === 0 && this.sourceQualityHints.length > 0) {
      return
    }

    // Deliver the (possibly updated) quality list + the currently-playing id.
    // The engine records the list and applies its default-quality strategy on
    // first resolution. Shaka codec-family selection stays adapter-side; the
    // old enableAutoQuality / this.setQuality(default) self-recursion is gone
    // (option 3, ADR-0001).
    const current = this.getCurrentQualityTrack()
    this.sink?.qualitiesResolved(qualities, current ? String(current.id) : null)
    // Always push a concrete height on adaptation — qualitiesResolved alone can
    // miss when the active Shaka track id is not in the provider hint list.
    if (current?.label) {
      this.sink?.qualityChanged({
        id: current.id,
        label: current.label,
        auto: this.isAutoQuality(),
      })
    }
  }

  private getCurrentQualityTrack(): QualityLevel | null {
    const activeTrack = this.getVariantTracks().find((track) => track.active)
    if (!activeTrack) return null

    const activeHeight = activeTrack.height || 0
    const activeBandwidth = activeTrack.bandwidth || 0
    const activeCodec = getCodecFamily(activeTrack.videoCodec)

    // Prefer provider ladder rows so the chip/menu highlight a real menu id
    // (itag / quality_label), not a transient Shaka variant id.
    const byHeightAndCodec = this.sourceQualityHints.filter((quality) => {
      const heightMatches = (quality.height || 0) === activeHeight
      const codecMatches = !activeCodec || getCodecFamily(quality.codec) === activeCodec
      return heightMatches && codecMatches
    })
    const byHeightOnly = byHeightAndCodec.length > 0
      ? byHeightAndCodec
      : this.sourceQualityHints.filter((quality) => (quality.height || 0) === activeHeight)

    if (byHeightOnly.length > 0) {
      const best = [...byHeightOnly]
        .sort((left, right) => this.scoreTrackForHint(activeTrack, left) - this.scoreTrackForHint(activeTrack, right))[0]
      const height = best.height || activeHeight || undefined
      return {
        ...best,
        label: best.label || (height ? `${height}p` : String(best.id)),
        height,
        bitrate: best.bitrate || activeBandwidth || undefined,
        codec: best.codec || activeCodec || undefined,
      }
    }

    return {
      id: String(activeTrack.id),
      label: activeHeight ? `${activeHeight}p` : `${Math.round(activeBandwidth / 1000)}kbps`,
      width: activeTrack.width || undefined,
      height: activeTrack.height || undefined,
      bitrate: activeTrack.bandwidth || undefined,
      codec: activeCodec || undefined,
    }
  }

  getActiveQuality(): QualityLevel | null {
    return this.getCurrentQualityTrack()
  }

  private getSourceQualityHint(quality: QualitySelectionRequest): QualityLevel | null {
    const targetId = String(quality)
    return this.sourceQualityHints.find((hint) => String(hint.id) === targetId) || null
  }

  private scoreTrackForHint(track: ShakaVariantTrack, hint: QualityLevel): number {
    const heightDelta = Math.abs((track.height || 0) - (hint.height || 0))
    const widthDelta = Math.abs((track.width || 0) - (hint.width || 0))
    const codecDelta = getCodecFamily(track.videoCodec) === getCodecFamily(hint.codec) ? 0 : 1
    const bitrateDelta = Math.abs((track.bandwidth || 0) - (hint.bitrate || 0))
    return codecDelta * 1_000_000_000 + heightDelta * 1_000_000 + widthDelta * 1_000 + bitrateDelta
  }

  private getHintedTrackCandidates(tracks: ShakaVariantTrack[], hint: QualityLevel): ShakaVariantTrack[] {
    const hintCodec = getCodecFamily(hint.codec)
    const strictCandidates = tracks.filter((track) => {
      const heightMatches = !hint.height || track.height === hint.height
      const codecMatches = !hintCodec || getCodecFamily(track.videoCodec) === hintCodec
      return heightMatches && codecMatches
    })

    const candidates = strictCandidates.length > 0
      ? strictCandidates
      : tracks.filter((track) => !hint.height || track.height === hint.height)

    return [...(candidates.length > 0 ? candidates : tracks)]
      .sort((left, right) => this.scoreTrackForHint(left, hint) - this.scoreTrackForHint(right, hint))
  }

  private isAutoQuality(): boolean {
    if (!this.player) return true
    return this.player.getConfiguration().abr.enabled !== false
  }

  getAvailableCodecFamilies(): string[] {
    const qualities = this.sourceQualityHints.length > 0
      ? this.sourceQualityHints
      : this.buildQualitiesFromVariants()

    return Array.from(new Set(
      qualities
        .map((quality) => getCodecFamily(quality.codec))
        .filter((family): family is string => !!family && family !== 'aac' && family !== 'opus')
    )).sort((left, right) => compareCodecFamilies(left, right))
  }

  getSelectedCodecFamily(): string {
    return this.selectedCodecFamily
  }

  getCurrentCodecFamily(): string | null {
    return this.activeCodecFamily
  }

  setCodecFamily(codecFamily: string): void {
    const normalized = getCodecFamily(codecFamily)
    this.selectedCodecFamily = normalized || 'auto'
    this.updateQualities()
  }

  setQuality(quality: QualitySelectionRequest): void {
    if (!this.player) return

    const qualityText = String(quality).toLowerCase()
    if (quality === 'auto' || quality === -1 || qualityText === '自动') {
      this.player.configure({ abr: { enabled: true } })
      return
    }

    this.player.configure({ abr: { enabled: false } })

    const tracks = this.getVariantTracks().filter(isApplicationAllowedTrack)
    if (tracks.length === 0) return

    const targetId = String(quality)
    const hintedQuality = this.getSourceQualityHint(quality)
    let candidates = hintedQuality
      ? this.getHintedTrackCandidates(tracks, hintedQuality)
      : tracks.filter((track) => String(track.id) === targetId)

    if (candidates.length === 0) {
      const numericHeight = Number.parseInt(targetId.replace(/[^0-9]/g, ''), 10)
      if (Number.isFinite(numericHeight)) {
        candidates = tracks.filter((track) => (track.height || 0) === numericHeight)
      }
    }

    if (this.selectedCodecFamily !== 'auto') {
      const codecFiltered = candidates.filter((track) => getCodecFamily(track.videoCodec) === this.selectedCodecFamily)
      if (codecFiltered.length > 0) {
        candidates = codecFiltered
      }
    }

    if (candidates.length === 0) {
      candidates = tracks
    }

    if (!hintedQuality) {
      candidates.sort((left, right) => (right.bandwidth || 0) - (left.bandwidth || 0))
    }
    const selected = candidates[0]
    if (!selected) return

    try {
      this.isSelectingQuality = true
      this.player.selectVariantTrack(selected, true, 0)
      this.updateActiveCodecFamily()
      this.updateQualities()
    } catch (error) {
      this.context.logger.warn('[ShakaDashAdapter] Failed to select quality', error)
    } finally {
      this.isSelectingQuality = false
    }
  }

  /**
   * After rebuffer, undo a stale Shaka rate=0 without changing paused state.
   * The engine tracks whether a pre-seek playing session should resume; keeping
   * that decision out of the adapter preserves intentional pauses.
   */
  private restorePlaybackRateAfterRebuffer(): void {
    const video = this.context.videoElement()
    if (!video || video.ended) return

    const stillBuffering = this.player?.isBuffering?.() ?? false
    if (stillBuffering) return

    // User-selected rates are always > 0 in our UI; 0 is only Shaka's starve flag.
    if (video.playbackRate !== 0) return

    try {
      const defaultRate = Number(video.defaultPlaybackRate)
      video.playbackRate = Number.isFinite(defaultRate) && defaultRate > 0 ? defaultRate : 1
    } catch (e) {
      this.context.logger.warn('[ShakaDashAdapter] restore playbackRate after rebuffer failed', e)
    }
  }

  /**
   * Seek via the media element so Shaka's StreamingEngine observes the time
   * change and rebuffers SegmentBase ranges without reloading the MPD
   * (reload would rewind the playhead to 0).
   *
   * FreeTube sets video.currentTime only — the loading symbol tracks
   * player "buffering". After scrub we re-publish isBuffering() so the engine
   * spinner cannot stick when Shaka never re-fires a buffering edge.
   */
  seek(time: number): Promise<StreamSeekResult | void> {
    const target = Number(time)
    if (!Number.isFinite(target)) return Promise.resolve()
    const clamped = Math.max(0, target)
    // Seek-triggered HTTP 4xx recovery window starts here; each new seek may
    // retry one SABR-session refresh before degrading to the DASH fallback.
    this.lastSeekAt = Date.now()
    this.sabrRefreshAttemptedSinceSeek = false
    const video = this.context.videoElement()
    if (!video) return Promise.resolve()
    const seekPlayer = this.player
    const baselineDecodedFrames = this.getDecodedVideoFrameCount(video)
    try {
      // Avoid no-op seeks that still thrash the segment pipeline.
      if (Math.abs((video.currentTime || 0) - clamped) < 0.05) {
        this.cancelPostSeekVideoWatchdog()
        this.syncBufferingToSink()
        return Promise.resolve({ visuallyReady: true })
      }
      video.currentTime = clamped
    } catch (e) {
      this.context.logger.warn('[ShakaDashAdapter] seek failed', e)
      return Promise.resolve()
    }
    // Microtask: Shaka updates buffering state after the seek is observed.
    const syncCurrentSeek = () => {
      if (this.player !== seekPlayer) return
      this.syncBufferingToSink()
    }
    queueMicrotask(syncCurrentSeek)
    // Second pass after the segment pipeline has a chance to go STARVING/SATISFIED.
    window.setTimeout(syncCurrentSeek, 50)
    window.setTimeout(syncCurrentSeek, 250)

    // Paused seeks have no advancing audio/video clock to verify. Their native
    // seeked/canplay events remain authoritative; the frozen-video failure only
    // occurs while playback continues after the seek.
    if (!seekPlayer || video.paused || video.ended) return Promise.resolve()

    return new Promise<StreamSeekResult>((resolve) => {
      this.armPostSeekVideoWatchdog(
        seekPlayer,
        video,
        clamped,
        baselineDecodedFrames,
        (visuallyReady) => resolve({ visuallyReady }),
      )
    })
  }

  private getDecodedVideoFrameCount(video: HTMLVideoElement): number | null {
    try {
      const total = video.getVideoPlaybackQuality?.().totalVideoFrames
      if (Number.isFinite(total)) return Number(total)
    } catch {
      // Fall through to Chromium's legacy counter.
    }

    const legacyCount = (video as VideoWithDecodedFrameCount).webkitDecodedFrameCount
    return Number.isFinite(legacyCount) ? Number(legacyCount) : null
  }

  private clearPostSeekVideoWatchdogResources(): void {
    if (this.postSeekWatchdogTimer !== null) {
      window.clearTimeout(this.postSeekWatchdogTimer)
      this.postSeekWatchdogTimer = null
    }
    if (this.postSeekFrameCallbackId !== null && this.postSeekFrameCallbackVideo?.cancelVideoFrameCallback) {
      this.postSeekFrameCallbackVideo.cancelVideoFrameCallback(this.postSeekFrameCallbackId)
    }
    this.postSeekFrameCallbackId = null
    this.postSeekFrameCallbackVideo = null
  }

  private cancelPostSeekVideoWatchdog(visuallyReady = false): void {
    this.postSeekWatchdogSeq += 1
    this.clearPostSeekVideoWatchdogResources()
    const complete = this.postSeekCompletion
    this.postSeekCompletion = null
    complete?.(visuallyReady)
  }

  private armPostSeekVideoWatchdog(
    player: shaka.Player,
    video: HTMLVideoElement,
    targetTime: number,
    baselineDecodedFrames: number | null,
    complete: (visuallyReady: boolean) => void,
  ): void {
    this.cancelPostSeekVideoWatchdog()
    this.postSeekCompletion = complete
    const watchdogSeq = this.postSeekWatchdogSeq
    this.schedulePostSeekVideoCheck(
      player,
      video,
      targetTime,
      baselineDecodedFrames,
      watchdogSeq,
      'clear-video-buffer',
    )
  }

  private schedulePostSeekVideoCheck(
    player: shaka.Player,
    video: HTMLVideoElement,
    targetTime: number,
    baselineDecodedFrames: number | null,
    watchdogSeq: number,
    recoveryStage: 'clear-video-buffer' | 'reload-manifest' | 'verify-reload',
  ): void {
    this.clearPostSeekVideoWatchdogResources()
    let lastPresentedFrameMediaTime: number | null = null
    const frameCallbackSupported = typeof video.requestVideoFrameCallback === 'function'

    const observeNextFrame = (): void => {
      if (!frameCallbackSupported || this.postSeekWatchdogSeq !== watchdogSeq) return
      this.postSeekFrameCallbackVideo = video
      this.postSeekFrameCallbackId = video.requestVideoFrameCallback((_now, metadata) => {
        this.postSeekFrameCallbackId = null
        this.postSeekFrameCallbackVideo = null
        if (this.postSeekWatchdogSeq !== watchdogSeq || this.player !== player) return
        if (Number.isFinite(metadata.mediaTime)) {
          lastPresentedFrameMediaTime = metadata.mediaTime
        }
        // Keep observing until a frame from the seek destination arrives. The
        // first callback can still describe the old frame that was on screen.
        if (hasPresentedVideoFrameAfterSeek({
          hasActiveVideoTrack: true,
          paused: video.paused,
          ended: video.ended,
          targetTime,
          currentTime: video.currentTime,
          frameCallbackSupported,
          lastPresentedFrameMediaTime,
          baselineDecodedFrames,
          decodedFrames: this.getDecodedVideoFrameCount(video),
        })) {
          this.cancelPostSeekVideoWatchdog(true)
          return
        }
        observeNextFrame()
      })
    }
    observeNextFrame()

    this.postSeekWatchdogTimer = window.setTimeout(() => {
      this.postSeekWatchdogTimer = null
      if (
        this.postSeekWatchdogSeq !== watchdogSeq
        || this.player !== player
        || this.context.videoElement() !== video
      ) {
        return
      }

      const activeTrack = this.getVariantTracks().find((track) => track.active)
      const hasActiveVideoTrack = Boolean(
        activeTrack
        && (activeTrack.videoCodec || activeTrack.height || activeTrack.width),
      )
      const shouldRecover = shouldRecoverVideoAfterSeek({
        hasActiveVideoTrack,
        paused: video.paused,
        ended: video.ended,
        targetTime,
        currentTime: video.currentTime,
        frameCallbackSupported,
        lastPresentedFrameMediaTime,
        baselineDecodedFrames,
        decodedFrames: this.getDecodedVideoFrameCount(video),
      })

      if (!shouldRecover) {
        const visuallyReady = hasPresentedVideoFrameAfterSeek({
          hasActiveVideoTrack,
          paused: video.paused,
          ended: video.ended,
          targetTime,
          currentTime: video.currentTime,
          frameCallbackSupported,
          lastPresentedFrameMediaTime,
          baselineDecodedFrames,
          decodedFrames: this.getDecodedVideoFrameCount(video),
        })
        this.cancelPostSeekVideoWatchdog(visuallyReady)
        return
      }

      if (recoveryStage === 'clear-video-buffer' && activeTrack) {
        this.context.logger.warn('[ShakaDashAdapter] Video frame froze after seek; rebuilding active variant', {
          targetTime,
          currentTime: video.currentTime,
          trackId: activeTrack.id,
        })
        try {
          // Shaka force-reselects even the same variant when clearBuffer=true.
          // This rebuilds the SourceBuffer/decoder state at the audio playhead.
          player.selectVariantTrack(activeTrack, true, 0)
          player.retryStreaming?.(0.1)
        } catch (e) {
          this.context.logger.warn('[ShakaDashAdapter] Failed to rebuild frozen video variant', e)
        }

        const retryTarget = video.currentTime
        this.schedulePostSeekVideoCheck(
          player,
          video,
          retryTarget,
          this.getDecodedVideoFrameCount(video),
          watchdogSeq,
          'reload-manifest',
        )
        return
      }

      if (recoveryStage === 'reload-manifest') {
        this.reloadManifestAfterFrozenSeek(player, video, watchdogSeq)
        return
      }

      this.context.logger.warn('[ShakaDashAdapter] Video frame remained frozen after manifest reload', {
        targetTime,
        currentTime: video.currentTime,
      })
      this.cancelPostSeekVideoWatchdog(false)
      this.sink?.error({
        code: 'POST_SEEK_VIDEO_FROZEN',
        message: 'Video frames did not resume after seek recovery',
        fatal: false,
      })
    }, POST_SEEK_FRAME_CHECK_DELAY_MS)
  }

  private reloadManifestAfterFrozenSeek(
    player: shaka.Player,
    video: HTMLVideoElement,
    watchdogSeq: number,
  ): void {
    const source = this.currentSource
    if (!source || this.player !== player || this.postSeekWatchdogSeq !== watchdogSeq) return

    const resumeTime = Number.isFinite(video.currentTime) ? Math.max(0, video.currentTime) : 0
    const shouldResume = !video.paused && !video.ended
    const loadRequestSeq = this.loadRequestSeq
    this.clearPostSeekVideoWatchdogResources()
    this.context.logger.warn('[ShakaDashAdapter] Video frame still frozen; reloading DASH at playhead', {
      resumeTime,
    })

    void player.load(source, resumeTime, 'application/dash+xml').then(() => {
      if (
        this.player !== player
        || this.loadRequestSeq !== loadRequestSeq
        || this.postSeekWatchdogSeq !== watchdogSeq
      ) {
        return
      }
      this.updateActiveCodecFamily()
      this.updateQualities()
      this.syncBufferingToSink()
      if (shouldResume && !video.ended) {
        void video.play().catch((e) => {
          this.context.logger.warn('[ShakaDashAdapter] Play after frozen-video reload failed', e)
        })
      }
      this.schedulePostSeekVideoCheck(
        player,
        video,
        resumeTime,
        this.getDecodedVideoFrameCount(video),
        watchdogSeq,
        'verify-reload',
      )
    }).catch((e) => {
      if (this.postSeekWatchdogSeq === watchdogSeq) {
        this.cancelPostSeekVideoWatchdog()
      }
      this.context.logger.warn('[ShakaDashAdapter] Frozen-video manifest reload failed', e)
    })
  }

  /** Publish current Shaka buffering flag to the engine spinner. */
  private syncBufferingToSink(): void {
    if (!this.player || !this.sink) return
    let buffering = false
    try {
      buffering = Boolean(this.player.isBuffering())
    } catch {
      buffering = false
    }
    this.sink.loadingStateChanged(buffering)
    if (!buffering) {
      this.restorePlaybackRateAfterRebuffer()
    }
  }

  /**
   * Soft stall recovery for YouTube DASH:
   * NEVER re-seek to the same time on the first attempts — that aborts in-flight
   * googlevideo segment fetches and leaves Shaka permanently STARVING (spinner,
   * rate=0, no A/V). FreeTube relies on shaka's own streaming engine; we nudge
   * via retryStreaming and post-buffer rate restoration instead.
   */
  recoverPlayback(error: PlayerError, context: PlaybackRecoveryContext): PlaybackRecoveryAction {
    const signature = String(error.code || error.message || '').toUpperCase()
    const video = this.context.videoElement()
    const player = this.player

    if (signature.includes('STALL') || signature.includes('BUFFER')) {
      let retried = false
      try {
        // Kick segment pipeline without moving the playhead.
        if (player && typeof player.retryStreaming === 'function') {
          retried = Boolean(player.retryStreaming(0.1))
        }
      } catch (e) {
        this.context.logger.warn('[ShakaDashAdapter] retryStreaming failed', e)
      }

      // Restore rate=0 starve flag + re-arm play; never soft re-seek first.
      this.restorePlaybackRateAfterRebuffer()

      // Only after several soft retries: micro-nudge the playhead so shaka
      // re-evaluates the segment map without a full reload.
      if (!retried && context.retryCount >= 2 && video && Number.isFinite(video.currentTime)) {
        try {
          const t = video.currentTime
          video.currentTime = Math.max(0, t + 0.001)
        } catch (e) {
          this.context.logger.warn('[ShakaDashAdapter] stall micro-nudge failed', e)
        }
      }

      this.context.logger.debug('[ShakaDashAdapter] Stall recovery soft-handled', {
        code: error.code,
        retryCount: context.retryCount,
        retried,
        buffering: player?.isBuffering?.() ?? null,
        paused: video?.paused ?? null,
        rate: video?.playbackRate ?? null,
      })
      return 'handled'
    }

    if (context.retryCount <= 2) {
      try {
        player?.retryStreaming?.(0.1)
      } catch {
        // ignore
      }
      return 'handled'
    }

    if (player && this.currentSource) {
      try {
        // FreeTube reload: load(src, playbackPosition, mimeType) — startTime in load
        // restores SegmentBase state without a second currentTime race.
        const resumeTime = video?.currentTime ?? context.currentTime ?? 0
        const startAt = Number.isFinite(resumeTime) && resumeTime > 0 ? resumeTime : null
        const shouldResume = Boolean(video && !video.paused && !video.ended)
        void player.load(this.currentSource, startAt, 'application/dash+xml').then(() => {
          const el = this.context.videoElement()
          // Preserve the intent captured before load; never start content that
          // was already paused when recovery began.
          if (shouldResume && el && !el.ended && this.player === player) {
            void el.play().catch((e) => {
              this.context.logger.warn('[ShakaDashAdapter] play after reload failed', e)
            })
          }
        }).catch((e) => {
          this.context.logger.warn('[ShakaDashAdapter] recover load failed', e)
        })
        return 'handled'
      } catch (e) {
        this.context.logger.warn('[ShakaDashAdapter] recoverPlayback failed', e)
      }
    }

    return 'reload-source'
  }

  destroy(): void {
    this.cancelPostSeekVideoWatchdog()
    this.loadRequestSeq += 1
    void this.destroyPlayer()
    this.currentSource = null
    this.sink = null
  }

  private async destroyPlayer(): Promise<void> {
    this.cancelPostSeekVideoWatchdog()
    this.disposeSabrAdapter()
    const player = this.player
    this.player = null
    if (player) {
      await player.destroy().catch((e) => {
        this.context.logger.warn('[ShakaDashAdapter] Failed to destroy player', e)
      })
    }
    this.activeCodecFamily = null
  }
}

export default ShakaDashAdapter
