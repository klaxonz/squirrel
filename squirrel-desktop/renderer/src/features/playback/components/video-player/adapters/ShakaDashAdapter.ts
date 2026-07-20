/**
 * DASH stream adapter — based on shaka-player.
 *
 * Stream-adapter form of the former ShakaDashPlugin. See docs/adr/0001-stream-adapter-and-sink.md.
 * The internal loading / quality / codec-family / recovery logic is byte-identical
 * to the pre-refactor plugin; only the shell changed (constructor injection of
 * StreamContext, no PlayerPlugin lifecycle hooks, videoElement via lazy getter).
 */

import shaka from 'shaka-player'
import { errorMessage } from '@/shared/lib/errorMessage'

// ponytail: shaka-player's TypedEvent<->detail surface and track.allowedByApplication
// field are runtime-only or loosely declared. The few `as any` reads below are
// deliberate interop casts at the shaka boundary, not loose internal typing.

import { getCodecFamily, compareCodecFamilies } from '../core/codec'
import type { StreamAdapter, StreamContext } from '../core/StreamAdapter'
import type { StreamSink } from '../core/StreamSink'
import type {
  MediaSource,
  PlaybackRecoveryAction,
  PlaybackRecoveryContext,
  PlayerError,
  QualityLevel,
  QualitySelectionRequest,
} from '../core/types'

export interface ShakaDashAdapterOptions {
  enableAutoQuality?: boolean
}

type ShakaVariantTrack = shaka.extern.Track

/** FreeTube: body of a googlevideo alr=yes redirect starts with ASCII "http". */
const HTTP_IN_HEX = 0x68747470
const RequestType = shaka.net.NetworkingEngine.RequestType

export class ShakaDashAdapter implements StreamAdapter {
  private context: StreamContext
  private options: ShakaDashAdapterOptions
  // The sink handed to onSourceChange; the only channel back to the engine.
  private sink: StreamSink | null = null
  private player: shaka.Player | null = null
  private currentSource: string | null = null
  private sourceQualityHints: QualityLevel[] = []
  private selectedCodecFamily = 'auto'
  private activeCodecFamily: string | null = null
  private hasInstalledPolyfills = false
  private loadRequestSeq = 0
  private isSelectingQuality = false

  constructor(context: StreamContext, options?: ShakaDashAdapterOptions) {
    this.context = context
    this.options = {
      // Match FreeTube / official players: ABR on, climb after start.
      enableAutoQuality: true,
      ...options,
    }
  }

  onSourceChange(source: MediaSource, sink: StreamSink): void {
    this.sink = sink
    this.sourceQualityHints = Array.isArray(source.qualities) ? source.qualities : []

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
    void this.loadSource(source.src, requestSeq)
  }

  private async loadSource(src: string, requestSeq: number): Promise<void> {
    if (!this.context.videoElement()) return

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
    player.configure({
      abr: {
        enabled: this.options.enableAutoQuality !== false,
        // Only affects auto quality — manual selection still free.
        restrictToElementSize: true,
        // Start ~720p-class then climb once throughput is known.
        defaultBandwidthEstimate: 2_000_000,
      },
      streaming: {
        bufferingGoal: 180,
        rebufferingGoal: 0.02,
        bufferBehind: 300,
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
      // Prefer variants that decode smoothly / with hardware when available.
      preferredDecodingAttributes: ['smooth', 'powerEfficient'],
    })

    // FreeTube ft-shaka-video-player: googlevideo videoplayback uses POST +
    // range= query + alr=yes, and follows textual http redirect bodies.
    this.installYouTubeNetworkingFilters(player)
    this.setupEventListeners(player)

    try {
      await player.load(src)
      if (requestSeq !== this.loadRequestSeq || this.player !== player) {
        await player.destroy().catch((e) => {
          this.context.logger.warn('[ShakaDashAdapter] Failed to destroy player on load race', e)
        })
        return
      }
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

  /**
   * FreeTube request/response filters for official youtubei.js DASH BaseURLs.
   * Without POST+alr, long googlevideo SegmentBase sessions often 403 mid-play.
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

      // Official player: POST with tiny protobuf body, Range → ?range=, alr=yes.
      request.method = 'POST'
      request.body = new Uint8Array([0x78, 0]) // protobuf: { 15: 0 }

      const rangeHeader = request.headers?.Range || request.headers?.range
      if (rangeHeader) {
        // FreeTube always uses &range= because youtubei BaseURLs already carry
        // a query string; keep a ? fallback for any bare path.
        const rangeValue = String(rangeHeader).includes('=')
          ? String(rangeHeader).split('=')[1]
          : String(rangeHeader)
        const joiner = request.uris[0].includes('?') ? '&' : '?'
        request.uris[0] += `${joiner}range=${rangeValue}`
        delete request.headers.Range
        delete request.headers.range
      }

      if (!request.uris[0].includes('alr=')) {
        const joiner = request.uris[0].includes('?') ? '&' : '?'
        request.uris[0] += `${joiner}alr=yes`
      }
    })

    networkingEngine.registerResponseFilter(async (type, response, context) => {
      if (type !== RequestType.SEGMENT || !response.data) return
      try {
        if (response.uri && new URL(response.uri).protocol === 'sabr:') return
      } catch {
        // continue — still try redirect body decode
      }

      // shaka.extern.Response.data is ArrayBuffer | ArrayBufferView; DataView
      // only accepts ArrayBufferLike, so normalize the view first.
      const rawData = response.data
      const dataView = ArrayBuffer.isView(rawData)
        ? new DataView(rawData.buffer, rawData.byteOffset, rawData.byteLength)
        : new DataView(rawData as ArrayBuffer)
      if (dataView.byteLength <= 4) return
      if (dataView.getUint32(0) !== HTTP_IN_HEX) return

      // googlevideo alr redirect: body is a plain URL string to the real media.
      const responseAsString = shaka.util.StringUtils.fromUTF8(rawData)
      if (!/^https?:\/\//i.test(responseAsString.trim())) return

      const retryParameters = player.getConfiguration().streaming.retryParameters
      const redirectRequest = shaka.net.NetworkingEngine.makeRequest(
        [responseAsString.trim()],
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
      const detail = (event as CustomEvent).detail
      this.sink?.error({
        code: `SHAKA_${detail?.code || 'UNKNOWN'}`,
        message: detail?.message || 'Shaka playback error',
        fatal: false,
        details: detail,
      })
    })

    player.addEventListener('buffering', (event: Event) => {
      const detail = (event as CustomEvent<any>).detail
      const buffering = Boolean(detail?.buffering ?? (event as any)?.buffering)
      this.sink?.loadingStateChanged(buffering)
    })

    const refresh = () => {
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

    const tracks = this.getVariantTracks().filter((track) => (track as any).allowedByApplication !== false)
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
   * Seek via shaka so the stream controller rebuffers at `time` without
   * reloading the MPD (which would rewind the playhead to 0).
   */
  seek(time: number): void {
    const target = Number(time)
    if (!Number.isFinite(target)) return
    const clamped = Math.max(0, target)
    const video = this.context.videoElement()
    if (video) {
      try {
        video.currentTime = clamped
      } catch (e) {
        this.context.logger.warn('[ShakaDashAdapter] seek failed', e)
      }
    }
  }

  recoverPlayback(error: PlayerError, context: PlaybackRecoveryContext): PlaybackRecoveryAction {
    const signature = String(error.code || error.message || '').toUpperCase()
    // Seek/buffer stalls: soft re-seek, never full source reload.
    if (signature.includes('STALL') || signature.includes('BUFFER')) {
      const resumeTime = Number.isFinite(context.currentTime)
        ? context.currentTime
        : (this.context.videoElement()?.currentTime ?? 0)
      this.seek(resumeTime)
      this.context.logger.debug('[ShakaDashAdapter] Stall recovery soft-handled', {
        code: error.code,
        retryCount: context.retryCount,
        resumeTime,
      })
      return 'handled'
    }

    if (context.retryCount <= 2) {
      return 'handled'
    }

    if (this.player && this.currentSource) {
      try {
        const resumeTime = this.context.videoElement()?.currentTime ?? context.currentTime ?? 0
        void this.player.load(this.currentSource).then(() => {
          const video = this.context.videoElement()
          if (video && Number.isFinite(resumeTime) && resumeTime > 0) {
            try {
              video.currentTime = Math.max(0, resumeTime)
            } catch (e) {
              this.context.logger.warn('[ShakaDashAdapter] restore time after reload failed', e)
            }
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
    this.loadRequestSeq += 1
    void this.destroyPlayer()
    this.currentSource = null
    this.sink = null
  }

  private async destroyPlayer(): Promise<void> {
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
