import shaka from 'shaka-player'

import { getCodecFamily, compareCodecFamilies } from '../../core/codec'
import type {
  MediaSource,
  PlaybackRecoveryAction,
  PlaybackRecoveryContext,
  PlayerError,
  PlayerPlugin,
  PluginContext,
  QualityLevel,
  QualitySelectionRequest,
} from '../../core/types'

export interface ShakaDashPluginOptions {
  enableAutoQuality?: boolean
}

type ShakaVariantTrack = shaka.extern.Track

const QUALITY_CODEC_FAMILY_ORDER = ['av1', 'vp9', 'avc']

export class ShakaDashPlugin implements PlayerPlugin {
  readonly name = 'shaka-dash'
  readonly version = '1.0.0'

  private context: PluginContext | null = null
  private options: ShakaDashPluginOptions = {}
  private player: shaka.Player | null = null
  private currentSource: string | null = null
  private sourceQualityHints: QualityLevel[] = []
  private selectedCodecFamily = 'auto'
  private activeCodecFamily: string | null = null
  private hasInstalledPolyfills = false
  private loadRequestSeq = 0
  private isSelectingQuality = false

  install(context: PluginContext, options?: ShakaDashPluginOptions): void {
    this.context = context
    this.options = {
      enableAutoQuality: false,
      ...options,
    }
  }

  onSourceChange(source: MediaSource): void {
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
    if (!this.context?.videoElement) return

    if (!this.hasInstalledPolyfills) {
      shaka.polyfill.installAll()
      this.hasInstalledPolyfills = true
    }

    await this.destroyPlayer()
    if (requestSeq !== this.loadRequestSeq || !this.context?.videoElement) return
    this.currentSource = src

    const player = new shaka.Player()
    this.player = player

    await player.attach(this.context.videoElement)
    if (requestSeq !== this.loadRequestSeq || this.player !== player) {
      await player.destroy().catch((e) => {
        this.context?.logger.warn('[ShakaDashPlugin] Failed to destroy player on attach race', e)
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
          this.context?.logger.warn('[ShakaDashPlugin] Failed to destroy player on load race', e)
        })
        return
      }
      this.updateActiveCodecFamily()
      this.updateQualities()
    } catch (error) {
      this.context?.reportError({
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
      this.context?.reportError({
        code: `SHAKA_${detail?.code || 'UNKNOWN'}`,
        message: detail?.message || 'Shaka playback error',
        fatal: false,
        details: detail,
      })
    })

    player.addEventListener('buffering', (event: Event) => {
      const detail = (event as CustomEvent<any>).detail
      const buffering = Boolean(detail?.buffering ?? (event as any)?.buffering)
      if (buffering) {
        this.context?.emit('waiting', undefined)
      } else {
        this.context?.emit('canplay', undefined)
      }
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
    if (!this.context) return

    const hinted = this.sourceQualityHints.length > 0
      ? this.sourceQualityHints.map((quality) => ({
          ...quality,
          codec: quality.codec || undefined,
        }))
      : []

    const qualities = hinted.length > 0 ? hinted : this.buildQualitiesFromVariants()
    this.context.registerQualities(qualities)
    this.context.emit('qualitiesloaded', qualities)

    if (!this.isSelectingQuality && !this.options.enableAutoQuality && !this.context.state.quality && qualities.length > 0) {
      this.setQuality(qualities[0].id ?? qualities[0].label)
      return
    }

    const current = this.getCurrentQualityTrack()
    if (!current) return

    const qualityId = String(current.id)
    this.context.registerCurrentQualityId?.(qualityId)
    this.context.emit('qualitychange', {
      quality: current.label,
      auto: this.isAutoQuality(),
      id: qualityId,
    })
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
      this.context?.logger.warn('[ShakaDashPlugin] Failed to select quality', error)
    } finally {
      this.isSelectingQuality = false
    }
  }

  recoverPlayback(_error: PlayerError, _context: PlaybackRecoveryContext): PlaybackRecoveryAction {
    return 'reload-source'
  }

  onDestroy(): void {
    this.destroyPlayer()
  }

  destroy(): void {
    this.loadRequestSeq += 1
    void this.destroyPlayer()
    this.context = null
    this.currentSource = null
  }

  private async destroyPlayer(): Promise<void> {
    const player = this.player
    this.player = null
    if (player) {
      await player.destroy().catch((e) => {
        this.context?.logger.warn('[ShakaDashPlugin] Failed to destroy player', e)
      })
    }
    this.activeCodecFamily = null
  }
}

export default ShakaDashPlugin
