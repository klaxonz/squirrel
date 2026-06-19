/**
 * DASH stream adapter — based on shaka-player.
 *
 * Stream-adapter form of the former ShakaDashPlugin. See docs/adr/0001-stream-adapter-and-sink.md.
 * The internal loading / quality / codec-family / recovery logic is byte-identical
 * to the pre-refactor plugin; only the shell changed (constructor injection of
 * StreamContext, no PlayerPlugin lifecycle hooks, videoElement via lazy getter).
 */

import shaka from 'shaka-player'

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
      enableAutoQuality: false,
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

    player.configure({
      abr: {
        enabled: this.options.enableAutoQuality !== false,
      },
      streaming: {
        retryParameters: {
          maxAttempts: 4,
          baseDelay: 1000,
          backoffFactor: 2,
          fuzzFactor: 0.5,
          timeout: 30000,
        },
      },
      manifest: {
        retryParameters: {
          maxAttempts: 3,
          baseDelay: 1000,
          backoffFactor: 2,
          fuzzFactor: 0.5,
          timeout: 30000,
        },
      },
    })

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
      this.sink?.error({
        code: 'SHAKA_LOAD_FAILED',
        message: error instanceof Error ? error.message : 'Shaka failed to load DASH source',
        fatal: false,
        details: error,
      })
    }
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
      ? this.sourceQualityHints.map((quality) => ({
          ...quality,
          codec: quality.codec || undefined,
        }))
      : []

    const qualities = hinted.length > 0 ? hinted : this.buildQualitiesFromVariants()

    // Deliver the (possibly updated) quality list + the currently-playing id.
    // The engine records the list and applies its default-quality strategy on
    // first resolution. Shaka codec-family selection stays adapter-side; the
    // old enableAutoQuality / this.setQuality(default) self-recursion is gone
    // (option 3, ADR-0001).
    const current = this.getCurrentQualityTrack()
    this.sink?.qualitiesResolved(qualities, current ? String(current.id) : null)
  }

  private getCurrentQualityTrack(): QualityLevel | null {
    const activeTrack = this.getVariantTracks().find((track) => track.active)
    if (!activeTrack) return null

    const activeHeight = activeTrack.height || 0
    const activeBandwidth = activeTrack.bandwidth || 0

    const hintedMatches = this.sourceQualityHints.filter((quality) => {
      const heightMatches = (quality.height || 0) === activeHeight
      const codecMatches = getCodecFamily(quality.codec) === getCodecFamily(activeTrack.videoCodec)
      return heightMatches && codecMatches
    })
    if (hintedMatches.length > 0) {
      return [...hintedMatches]
        .sort((left, right) => this.scoreTrackForHint(activeTrack, left) - this.scoreTrackForHint(activeTrack, right))[0]
    }

    return {
      id: String(activeTrack.id),
      label: activeHeight ? `${activeHeight}p` : `${Math.round(activeBandwidth / 1000)}kbps`,
      width: activeTrack.width || undefined,
      height: activeTrack.height || undefined,
      bitrate: activeTrack.bandwidth || undefined,
      codec: getCodecFamily(activeTrack.videoCodec) || undefined,
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

  recoverPlayback(_error: PlayerError, _context: PlaybackRecoveryContext): PlaybackRecoveryAction {
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
