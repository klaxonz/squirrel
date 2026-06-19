/**
 * DASH stream adapter — based on dash.js.
 *
 * Stream-adapter form of the former DashPlugin. See docs/adr/0001-stream-adapter-and-sink.md.
 * The internal loading / quality / codec-family / recovery logic is byte-identical
 * to the pre-refactor plugin; only the shell changed (constructor injection of
 * StreamContext, no PlayerPlugin lifecycle hooks, videoElement via lazy getter).
 */

// ponytail: dash.js ships incomplete TypeScript declarations — its MediaPlayerClass
// exposes many runtime methods (getInitialPlaybackSettings, getTracksFor,
// getCurrentTrackFor, updateSettings, ...) that are missing or loosely typed in
// the .d.ts. Rather than maintain a parallel hand-written type overlay (cost >
// value, and would drift with every dash.js bump), this adapter narrows to the
// typed surface where cheap and casts to `any` for the rest. Each `as any` here
// is a deliberate interop boundary, not loose internal code.

import dashjs, { type MediaPlayerClass, type MediaPlayerSettingClass } from 'dashjs'
import { getCodecFamily, compareCodecFamilies } from '../core/codec'
import type { StreamAdapter, StreamContext } from '../core/StreamAdapter'
import type {
  QualityLevel,
  QualitySelectionRequest,
  PlayerError,
  MediaSource,
  PlaybackRecoveryAction,
  PlaybackRecoveryContext
} from '../core/types'

export interface DashAdapterOptions {
  /** dash.js 配置 */
  settings?: Partial<MediaPlayerSettingClass>
  /** 最大重连次数 */
  maxRetries?: number
  /** 重连间隔(ms) */
  retryInterval?: number
  /** 是否启用自动质量 */
  enableAutoQuality?: boolean
  /** 带宽采样回调 */
  onBandwidthSample?: (loaded: number, durationSec: number) => void
}

type DashQualitySelection = {
  trackIndex: number
  qualityIndex: number
}

export class DashAdapter implements StreamAdapter {
  private player: MediaPlayerClass | null = null
  private context: StreamContext
  private options: DashAdapterOptions
  private currentSource: string | null = null
  private sourceQualityHints: QualityLevel[] = []
  private selectedCodecFamily: string = 'auto'
  private currentVisibleCodecFamily: string | null = null
  private hintedSelectionsById = new Map<string, DashQualitySelection>()
  private currentTrackIndex: number | null = null
  private pendingHintedSelection: DashQualitySelection | null = null
  private lastKnownPlaybackQualityId: string | number | null = null

  constructor(context: StreamContext, options?: DashAdapterOptions) {
    this.context = context
    this.options = {
      maxRetries: 3,
      retryInterval: 3000,
      enableAutoQuality: false,
      ...options
    }
  }

  private buildErrorSignature(error: unknown): string {
    if (!error) return ''
    try {
      return JSON.stringify(error).toUpperCase()
    } catch {
      return String(error).toUpperCase()
    }
  }

  private isUnrecoverableDashError(signature: string): boolean {
    return signature.includes('NOT_SUPPORTED') || signature.includes('CAPABILITY')
  }

  private isTransientDashError(signature: string): boolean {
    return [
      'NETWORK',
      'TIMEOUT',
      'FRAGMENT',
      'SEGMENT',
      'DOWNLOAD',
      'BUFFER',
      'STALL',
      'MEDIA',
      'DECODE',
      'APPEND',
    ].some((token) => signature.includes(token))
  }

  /**
   * 检测是否为 DASH 源
   */
  static isDashSource(src: string): boolean {
    const url = src.toLowerCase()
    // 支持多种 DASH URL 格式：
    // - xxx.mpd
    // - xxx.mpd?query
    // - /mpd/xxx 或 /mpd?xxx
    // - format=mpd
    return /\.mpd($|\?)/i.test(src) ||
           url.includes('/mpd') ||
           url.includes('format=mpd')
  }

  onSourceChange(source: MediaSource): void {
    this.sourceQualityHints = Array.isArray(source.qualities) ? source.qualities : []
    this.selectedCodecFamily = 'auto'
    this.currentVisibleCodecFamily = null
    this.hintedSelectionsById.clear()
    this.currentTrackIndex = null
    this.pendingHintedSelection = null

    // 检查是否为 DASH 源
    const isDash = source.type === 'dash' ||
                   (source.type === 'auto' && DashAdapter.isDashSource(source.src))
    const wantsDashJs = source.playbackEngine !== 'shaka'

    if (!isDash || !wantsDashJs) {
      this.destroyPlayer()
      this.currentSource = null
      return
    }

    this.loadSource(source.src)
  }

  /**
   * 加载 DASH 源
   */
  private loadSource(src: string): void {
    const video = this.context.videoElement()
    if (!video) return

    // 解析 URL
    let resolvedUrl: string
    try {
      resolvedUrl = new URL(src, window.location.origin).toString()
    } catch {
      resolvedUrl = src
    }

    this.currentSource = resolvedUrl
    this.destroyPlayer()
    this.initializePlayer(resolvedUrl)
  }

  /**
   * 初始化 DASH 播放器
   */
  private initializePlayer(src: string): void {
    const video = this.context.videoElement()
    if (!video) return

    const player = dashjs.MediaPlayer().create()
    const customSettings = this.options.settings ?? {}
    const {
      streaming: customStreaming = {},
      errors: customErrors = {},
      ...otherCustomSettings
    } = customSettings as any

    // 配置播放器
    const settings: Partial<MediaPlayerSettingClass> = {
      streaming: {
        abr: {
          autoSwitchBitrate: { video: this.options.enableAutoQuality !== false },
          initialBitrate: { video: 20000 },
          initialRepresentationRatio: 1,
          maxBitrate: { video: -1 },
          bandwidthSafetyFactor: 0.95,
          usePixelRatioInLimitBitrateByPortal: false
        } as any,
        buffer: {
          stableBufferTime: 12,
          bufferTimeAtTopQuality: 20,
          bufferTimeAtTopQualityLongForm: 30,
          longFormContentDurationThreshold: 600,
          bufferToKeep: 12,
          bufferPruningInterval: 10,
          fastSwitchEnabled: true,
          flushBufferAtTrackSwitch: true
        },
        fragmentRequestTimeout: 20000,
        fragmentRequestProgressTimeout: 5000,
        manifestRequestTimeout: 60000,
        retryIntervals: {
          MediaSegment: 1000,
          InitializationSegment: 1000,
          IndexSegment: 1000,
          other: 2000,
        },
        retryAttempts: {
          MediaSegment: 5,
          InitializationSegment: 5,
          IndexSegment: 3,
          other: 3,
        },
        ...customStreaming
      },
      errors: {
        ...customErrors,
        recoverAttempts: {
          mediaErrorDecode: 4,
          ...customErrors?.recoverAttempts
        }
      },
      ...otherCustomSettings
    }

    player.updateSettings(settings)
    this.setupEventListeners(player)
    this.player = player
    player.initialize(video, src, this.context.getState().playing)
  }

  /**
   * 设置事件监听
   */
  private setupEventListeners(player: MediaPlayerClass): void {
    // 错误处理
    player.on('error', (e: any) => {
      if (this.player !== player) return
      const signature = this.buildErrorSignature({
        code: e?.event?.id,
        error: e?.error,
        message: e?.event?.message,
        details: e,
      })
      const transient = this.isTransientDashError(signature)
      const fatal = this.isUnrecoverableDashError(signature)
        || (!transient && (e?.error === 'capability' || e?.event?.type === 'critical'))
      const error: PlayerError = {
        code: `DASH_${e?.event?.id || 'UNKNOWN'}`,
        message: e?.event?.message || 'DASH playback error',
        fatal,
        details: e
      }

      if (transient) {
        this.context.logger.warn('[DashAdapter] Transient dash error observed', {
          code: error.code,
          message: error.message,
        })
        this.context.reportError({ ...error, fatal: false })
      } else if (fatal) {
        this.context.reportError(error)
      } else {
        this.context.logger.warn('[DashAdapter] Non-fatal error', error)
      }
    })

    // 缓冲事件
    player.on('bufferingStarted', () => {
      this.context.emit('waiting', undefined)
    })

    player.on('bufferingCompleted', () => {
      this.context.emit('canplay', undefined)
    })

    // 质量变化
    player.on('qualityChangeRendered', (e: any) => {
      if (this.player !== player) return
      if (e?.mediaType === 'video') {
        const qualities = this.getAvailableQualities()
        const currentTrackIndex = this.getCurrentPlaybackTrackIndex(this.player as any)
        const quality = this.findQualityForPlaybackSelection(currentTrackIndex, e.newQuality, qualities)
        const qualityId = quality?.id ?? (typeof e.newQuality === 'number' ? e.newQuality : undefined)
        this.lastKnownPlaybackQualityId = qualityId ?? null
        this.context.emit('qualitychange', {
          quality: quality?.label || `level_${e.newQuality}`,
          auto: this.isAutoQuality(),
          id: qualityId
        })
        this.context.registerCurrentQualityId?.(qualityId)
        this.updateQualities()
      }
    })

    player.on('trackChangeRendered', (e: any) => {
      if (this.player !== player) return
      if (e?.mediaType === 'video') {
        this.currentTrackIndex = this.resolveTrackIndex(e.newMediaInfo)
        this.applyPendingHintedSelection(player)
        this.updateQualities()
      }
    })

    // 清单加载完成
    player.on('streamInitialized', () => {
      if (this.player !== player) return
      this.updateQualities()
    })

    // 片段加载完成 - 带宽采样
    player.on('fragmentLoadingCompleted', (data: any) => {
      if (this.player !== player) return
      if (this.options.onBandwidthSample) {
        try {
          const loaded = data?.request?.bytesLoaded || 0
          const t0 = data?.request?.requestStartDate?.getTime?.() || 0
          const t1 = data?.request?.requestEndDate?.getTime?.() || 0
          const durationSec = Math.max(0.001, (t1 - t0) / 1000)

          if (loaded > 0 && durationSec > 0) {
            this.options.onBandwidthSample(loaded, durationSec)
          }
        } catch (err) {
          this.context.logger.warn('[DashAdapter] Failed to sample bandwidth', err)
        }
      }
    })
  }

  recoverPlayback(error: PlayerError, context: PlaybackRecoveryContext): PlaybackRecoveryAction {
    const signature = this.buildErrorSignature({
      code: error.code,
      message: error.message,
      details: error.details,
    })

    if (this.isUnrecoverableDashError(signature)) {
      return 'unrecoverable'
    }

    if (this.isTransientDashError(signature)) {
      if (context.retryCount <= 2) {
        this.context.logger.debug('[DashAdapter] Transient recovery handled without source reload', {
          code: error.code,
          retryCount: context.retryCount,
        })
        return 'handled'
      }

      if (this.player && this.currentSource) {
        try {
          this.player.attachSource(this.currentSource)
          this.context.logger.debug('[DashAdapter] Escalated transient recovery via attachSource', {
            code: error.code,
            retryCount: context.retryCount,
          })
          return 'handled'
        } catch (recoverError) {
          this.context.logger.warn('[DashAdapter] Failed to escalate transient recovery via attachSource', recoverError)
        }
      }

      return 'reload-source'
    }

    this.context.logger.debug('[DashAdapter] Requesting source reload for recovery', {
      code: error.code,
      source: this.currentSource
    })
    return 'reload-source'
  }

  /**
   * 获取可用质量列表
   */
  private getAvailableQualities(): QualityLevel[] {
    if (!this.player) return []

    try {
      const player = this.player as any
      const bitrateList = player.getBitrateInfoListFor?.('video') || []
      this.currentTrackIndex = this.getCurrentPlaybackTrackIndex(player)
      this.updateHintSelections()

      const hintedQualities = this.getHintedQualities()
      if (hintedQualities.length > 0) {
        const visibleCodecFamily = this.resolveVisibleCodecFamily()
        if (visibleCodecFamily) {
          const activeCodecQualities = hintedQualities.filter(
              (hint) => getCodecFamily(hint.codec) === visibleCodecFamily
          )
          if (activeCodecQualities.length > 0) {
            return activeCodecQualities
          }
        }
        return hintedQualities
      }

      const qualities: QualityLevel[] = bitrateList.map((info: any, index: number) => ({
        id: typeof info?.qualityIndex === 'number' ? info.qualityIndex : index,
        label: info.height ? `${info.height}p` : `${Math.round(info.bitrate / 1000)}kbps`,
        width: info.width,
        height: info.height,
        bitrate: info.bitrate,
        codec: player.getCurrentTrackFor?.('video')?.codec || undefined,
        runtimeSelection: this.currentTrackIndex !== null
          ? this.toRuntimeSelection({
              trackIndex: this.currentTrackIndex,
              qualityIndex: typeof info?.qualityIndex === 'number' ? info.qualityIndex : index
            })
          : undefined
      }))

      const heightCounts = new Map<number, number>()
      qualities.forEach((q) => {
        const height = q.height || 0
        heightCounts.set(height, (heightCounts.get(height) || 0) + 1)
      })

      qualities.forEach((q) => {
        if (!q.height) return
        const count = heightCounts.get(q.height) || 0
        if (count > 1 && q.bitrate) {
          const kbps = Math.round(q.bitrate / 1000)
          q.label = `${q.height}p ${kbps}kbps`
        }
      })

      return qualities
    } catch {
      return []
    }
  }

  /**
   * 更新质量列表到上下文
   */
  private updateQualities(): void {
    const qualities = this.getAvailableQualities()
    this.currentVisibleCodecFamily = this.resolveVisibleCodecFamily()
    const currentPlaybackQuality = this.getCurrentPlaybackQuality(qualities)

    // 按高度、码率降序排列
    qualities.sort((a, b) => {
      const heightDelta = (b.height || 0) - (a.height || 0)
      if (heightDelta !== 0) return heightDelta
      return (b.bitrate || 0) - (a.bitrate || 0)
    })


    this.context.registerQualities(qualities)
    this.context.emit('qualitiesloaded', qualities)

    if (currentPlaybackQuality) {
      this.context.registerCurrentQualityId?.(currentPlaybackQuality.id)
      this.lastKnownPlaybackQualityId = currentPlaybackQuality.id
      if (!this.context.getState().quality) {
        this.context.emit('qualitychange', {
          quality: currentPlaybackQuality.label,
          auto: this.isAutoQuality(),
          id: currentPlaybackQuality.id
        })
      }
    }

    if (!this.options.enableAutoQuality && !this.context.getState().quality && qualities.length > 0) {
      const defaultQuality = qualities[0]
      if (this.canApplyDefaultQuality(defaultQuality)) {
        this.context.setQuality(defaultQuality.id ?? defaultQuality.label)
      } else {
        this.context.logger.debug('[DashAdapter] Skipping eager default quality selection that would require a track switch', {
          qualityId: defaultQuality.id,
          currentTrackIndex: this.currentTrackIndex
        })
      }
    }
  }

  getAvailableCodecFamilies(): string[] {
    const hintedFamilies = Array.from(new Set(
      this.getHintedQualities()
        .map((hint) => getCodecFamily(hint.codec))
        .filter((family): family is string => !!family)
    ))
    if (hintedFamilies.length > 0) {
      return hintedFamilies.sort((left, right) => compareCodecFamilies(left, right))
    }

    const trackFamilies = Array.from(new Set(
      this.getVideoTracks()
        .map((track) => getCodecFamily(track?.codec))
        .filter((family): family is string => !!family)
    ))
    return trackFamilies.sort((left, right) => compareCodecFamilies(left, right))
  }

  getSelectedCodecFamily(): string {
    return this.selectedCodecFamily
  }

  getCurrentCodecFamily(): string | null {
    return this.getActiveCodecFamily() || this.currentVisibleCodecFamily || this.resolveVisibleCodecFamily()
  }

  setCodecFamily(codecFamily: string): void {
    this.selectedCodecFamily = this.normalizeCodecFamilySelection(codecFamily)
    this.updateQualities()

    const targetCodecFamily = this.resolveVisibleCodecFamily()
    if (!targetCodecFamily) return

    const targetHint = this.pickCodecFamilyHint(targetCodecFamily)
    if (!targetHint) return

    this.setQuality(String(targetHint.id))
  }

  /**
   * 检查是否为自动质量模式
   */
  private isAutoQuality(): boolean {
    if (!this.player) return true
    try {
      const settings = (this.player as any).getSettings?.()
      return settings?.streaming?.abr?.autoSwitchBitrate?.video !== false
    } catch {
      return true
    }
  }

  /**
   * 设置质量
   */
  setQuality(quality: QualitySelectionRequest): void {
    if (!this.player) return

    const player = this.player as any
    const qStr = String(quality).toLowerCase()
    const isAuto = quality === 'auto' || quality === -1 || qStr === '自动'

    if (isAuto) {
      // 启用自动质量
      try {
        this.player.updateSettings({
          streaming: { abr: { autoSwitchBitrate: { video: true } } }
        })
        this.context.logger.debug('[DashAdapter] Quality set to auto')
      } catch (e) {
        this.context.logger.warn('[DashAdapter] Failed to enable auto quality', e)
      }
      return
    }

    // 禁用自动质量
    try {
      this.player.updateSettings({
        streaming: { abr: { autoSwitchBitrate: { video: false } } }
      })
    } catch (e) {
      this.context.logger.warn('[DashAdapter] Failed to disable auto quality', e)
    }

    // 设置指定质量
    let targetIndex: number = -1

    if (typeof quality === 'object' && quality?.kind === 'dash-selection') {
      if (this.applyHintedSelection(player, {
        trackIndex: quality.trackIndex,
        qualityIndex: quality.qualityIndex
      })) {
        return
      }
    }

    if (typeof quality === 'string') {
      const hintedSelection = this.getHintedSelection(quality)
      if (hintedSelection && this.applyHintedSelection(player, hintedSelection)) {
        return
      }

      try {
        const numericQuality = Number.parseInt(String(quality), 10)
        if (Number.isFinite(numericQuality)) {
          targetIndex = numericQuality
        }
      } catch (e) {
        this.context.logger.warn('[DashAdapter] Failed to parse quality index', e)
      }
    }

    if (typeof quality === 'number' && quality >= 0) {
      targetIndex = quality
    } else {
      // 按高度匹配，优先选择同分辨率中最高码率
      const height = parseInt(String(quality).replace(/[^0-9]/g, ''), 10)
      const qualities = this.getAvailableQualities()
      const matches = qualities.filter(q => q.height === height)
      if (matches.length) {
        const best = matches.reduce((prev, next) => {
          const prevBitrate = prev.bitrate ?? 0
          const nextBitrate = next.bitrate ?? 0
          return nextBitrate >= prevBitrate ? next : prev
        })
        if (typeof best.id === 'number') {
          targetIndex = best.id
        }
      }
    }

    if (targetIndex >= 0) {
      try {
        const p = this.player as any
        if (typeof p.setQualityFor === 'function') {
          p.setQualityFor('video', targetIndex, true)
        } else if (typeof p.setRepresentationForTypeByIndex === 'function') {
          p.setRepresentationForTypeByIndex('video', targetIndex, true)
        }
        this.context.logger.debug('[DashAdapter] Quality set to level', targetIndex)
      } catch (e) {
        this.context.logger.warn('[DashAdapter] Failed to set quality', e)
      }
    }
  }

  /**
   * 获取当前质量
   */
  getCurrentQuality(): string | null {
    if (!this.player) return null

    if (this.isAutoQuality()) return 'auto'

    try {
      const p = this.player as any
      const index = typeof p.getQualityFor === 'function' ? p.getQualityFor('video') : -1
      if (index >= 0) {
        const qualities = this.getAvailableQualities()
        const trackIndex = this.getCurrentPlaybackTrackIndex(p)
        const quality = this.findQualityForPlaybackSelection(trackIndex, index, qualities)
        return quality?.label || `level_${index}`
      }
    } catch (e) {
      this.context.logger.warn('[DashAdapter] Failed to get current quality label', e)
    }

    return null
  }

  /**
   * 销毁播放器实例
   */
  private destroyPlayer(): void {
    if (this.player) {
      try {
        this.player.reset()
      } catch (e) {
        this.context.logger.warn('[DashAdapter] Failed to reset player', e)
      }
      this.player = null
    }
    this.hintedSelectionsById.clear()
    this.currentVisibleCodecFamily = null
    this.currentTrackIndex = null
    this.pendingHintedSelection = null
    this.lastKnownPlaybackQualityId = null
  }

  private getVideoTracks(): any[] {
    if (!this.player) return []
    const player = this.player as any
    return player.getTracksFor?.('video') || []
  }

  private resolveTrackIndex(track: any): number | null {
    if (!track) return null
    const tracks = this.getVideoTracks()
    const directIndex = tracks.findIndex((item) => item === track)
    if (directIndex >= 0) return directIndex

    const matchedIndex = tracks.findIndex((item) =>
      item?.id === track?.id &&
      item?.codec === track?.codec &&
      item?.mimeType === track?.mimeType
    )
    return matchedIndex >= 0 ? matchedIndex : null
  }

  private getCurrentPlaybackTrackIndex(player: any = this.player as any): number | null {
    if (!player) return this.currentTrackIndex
    return this.resolveTrackIndex(player.getCurrentTrackFor?.('video')) ?? this.currentTrackIndex
  }

  private getHintedSelection(qualityId: string | number | null | undefined): DashQualitySelection | null {
    if (qualityId === null || qualityId === undefined) return null
    return this.hintedSelectionsById.get(String(qualityId)) || null
  }

  private toRuntimeSelection(selection: DashQualitySelection) {
    return {
      kind: 'dash-selection' as const,
      trackIndex: selection.trackIndex,
      qualityIndex: selection.qualityIndex
    }
  }

  private getHintedQualities(): QualityLevel[] {
    if (this.sourceQualityHints.length === 0) return []
    return this.sourceQualityHints.reduce<QualityLevel[]>((qualities, hint) => {
        const selection = this.getHintedSelection(hint.id)
        if (!selection) return qualities
        qualities.push({
          id: hint.id,
          label: hint.label,
          width: hint.width,
          height: hint.height,
          bitrate: hint.bitrate,
          codec: hint.codec,
          runtimeSelection: this.toRuntimeSelection(selection)
        })
        return qualities
      }, [])
  }

  private updateHintSelections(): void {
    this.hintedSelectionsById.clear()
    if (this.sourceQualityHints.length === 0) return

    const tracks = this.getVideoTracks()
    for (const hint of this.sourceQualityHints) {
      let bestMatch: { trackIndex: number; qualityIndex: number; score: number } | null = null
      const hintCodecFamily = getCodecFamily(hint.codec)

      for (const [trackIndex, track] of tracks.entries()) {
        const bitrateList = Array.isArray(track?.bitrateList) ? track.bitrateList : []
        const trackCodecFamily = getCodecFamily(track?.codec)
        for (const [index, bitrateInfo] of bitrateList.entries()) {
          const height = Number(bitrateInfo?.height || 0)
          const bitrate = Number(bitrateInfo?.bitrate || 0)
          const hintHeight = Number(hint.height || 0)
          const hintBitrate = Number(hint.bitrate || 0)
          const qualityIndex = typeof bitrateInfo?.qualityIndex === 'number' ? bitrateInfo.qualityIndex : index
          const codecPenalty = (
            hintCodecFamily &&
            trackCodecFamily &&
            hintCodecFamily !== trackCodecFamily
          ) ? 1_000_000_000 : 0
          const score = codecPenalty + Math.abs(height - hintHeight) * 1_000_000 + Math.abs(bitrate - hintBitrate)

          if (!bestMatch || score < bestMatch.score) {
            bestMatch = { trackIndex, qualityIndex, score }
          }
        }
      }

      if (bestMatch) {
        this.hintedSelectionsById.set(String(hint.id), {
          trackIndex: bestMatch.trackIndex,
          qualityIndex: bestMatch.qualityIndex
        })
      }
    }
  }

  private findHintForSelection(trackIndex: number | null, qualityIndex: number): QualityLevel | null {
    if (trackIndex === null) return null
    for (const hint of this.sourceQualityHints) {
      const selection = this.getHintedSelection(hint.id)
      if (selection && selection.trackIndex === trackIndex && selection.qualityIndex === qualityIndex) {
        return hint
      }
    }
    return null
  }

  private findQualityForPlaybackSelection(
    trackIndex: number | null,
    qualityIndex: number,
    availableQualities: QualityLevel[] = this.getAvailableQualities()
  ): QualityLevel | null {
    return this.findHintForSelection(trackIndex, qualityIndex)
      || availableQualities.find((quality) => quality.id === qualityIndex)
      || null
  }

  private getCurrentPlaybackQuality(availableQualities: QualityLevel[] = this.getAvailableQualities()): QualityLevel | null {
    if (!this.player) return null

    try {
      const player = this.player as any
      const qualityIndex = typeof player.getQualityFor === 'function' ? player.getQualityFor('video') : -1
      if (qualityIndex >= 0) {
        const trackIndex = this.getCurrentPlaybackTrackIndex(player)
        return this.findQualityForPlaybackSelection(trackIndex, qualityIndex, availableQualities)
      }
    } catch (e) {
      this.context.logger.warn('[DashAdapter] Failed to get current quality', e)
    }

    if (this.lastKnownPlaybackQualityId === null) return null
    return availableQualities.find((quality) => quality.id === this.lastKnownPlaybackQualityId) || null
  }

  private canApplyDefaultQuality(quality: QualityLevel | null): boolean {
    if (!this.player || !quality) return false

    const hintedSelection = this.getHintedSelection(quality.id)
    if (!hintedSelection) return true

    const currentTrackIndex = this.getCurrentPlaybackTrackIndex(this.player as any)
    return currentTrackIndex !== null && currentTrackIndex === hintedSelection.trackIndex
  }

  private applyPendingHintedSelection(player: any): void {
    if (
      !this.pendingHintedSelection ||
      this.currentTrackIndex === null ||
      this.pendingHintedSelection.trackIndex !== this.currentTrackIndex
    ) {
      return
    }

    try {
      player.setQualityFor?.('video', this.pendingHintedSelection.qualityIndex, true)
      this.context.logger.debug('[DashAdapter] Applied pending quality after track change', this.pendingHintedSelection)
    } catch (error) {
      this.context.logger.warn('[DashAdapter] Failed to apply pending quality after track change', error)
    } finally {
      this.pendingHintedSelection = null
    }
  }

  private applyHintedSelection(player: any, hintedSelection: DashQualitySelection): boolean {
    try {
      const tracks = this.getVideoTracks()
      const targetTrack = tracks[hintedSelection.trackIndex]
      const currentTrackIndex = this.getCurrentPlaybackTrackIndex(player)
      if (targetTrack && typeof player.setCurrentTrack === 'function') {
        if (currentTrackIndex !== hintedSelection.trackIndex) {
          this.pendingHintedSelection = hintedSelection
          player.setCurrentTrack(targetTrack)
          this.context.logger.debug('[DashAdapter] Waiting for target track before applying quality', hintedSelection)
          return true
        }
        this.currentTrackIndex = hintedSelection.trackIndex
      }
      if (typeof player.setQualityFor === 'function') {
        player.setQualityFor('video', hintedSelection.qualityIndex, true)
      }
      this.pendingHintedSelection = null
      this.context.logger.debug('[DashAdapter] Quality set via hinted selection', hintedSelection)
      return true
    } catch (error) {
      this.pendingHintedSelection = null
      this.context.logger.warn('[DashAdapter] Failed to set hinted dash quality', error)
      return false
    }
  }

  private resolveVisibleCodecFamily(): string | null {
    const availableFamilies = this.getAvailableCodecFamilies()
    if (availableFamilies.length === 0) {
      return this.getActiveCodecFamily()
    }

    if (this.selectedCodecFamily !== 'auto' && availableFamilies.includes(this.selectedCodecFamily)) {
      return this.selectedCodecFamily
    }

    const activeCodecFamily = this.getActiveCodecFamily()
    if (activeCodecFamily && availableFamilies.includes(activeCodecFamily)) {
      return activeCodecFamily
    }

    for (const family of ['av1', 'vp9', 'avc']) {
      if (availableFamilies.includes(family) && this.isCodecFamilySupported(family)) {
        return family
      }
    }

    return availableFamilies[0] || this.getActiveCodecFamily()
  }

  private normalizeCodecFamilySelection(codecFamily: string | null | undefined): string {
    if (!codecFamily) return 'auto'
    const normalized = String(codecFamily).toLowerCase()
    if (normalized === 'auto' || normalized === '自动') return 'auto'
    return getCodecFamily(normalized) || normalized
  }

  private pickCodecFamilyHint(codecFamily: string): QualityLevel | null {
    const candidates = this.sourceQualityHints
      .filter((hint) => this.hintedSelectionsById.has(String(hint.id)))
      .filter((hint) => getCodecFamily(hint.codec) === codecFamily)

    if (candidates.length === 0) return null

    const currentHint = this.getCurrentHint()
    if (currentHint?.height) {
      return [...candidates].sort((left, right) => {
        const heightDistance = Math.abs((left.height || 0) - currentHint.height!) - Math.abs((right.height || 0) - currentHint.height!)
        if (heightDistance !== 0) return heightDistance
        return (right.bitrate || 0) - (left.bitrate || 0)
      })[0] || null
    }

    return [...candidates].sort((left, right) => {
      const heightDelta = (right.height || 0) - (left.height || 0)
      if (heightDelta !== 0) return heightDelta
      return (right.bitrate || 0) - (left.bitrate || 0)
    })[0] || null
  }

  private getCurrentHint(): QualityLevel | null {
    if (!this.player) return null

    try {
      const player = this.player as any
      const qualityIndex = typeof player.getQualityFor === 'function' ? player.getQualityFor('video') : -1
      if (qualityIndex < 0) return null
      const trackIndex = this.resolveTrackIndex(player.getCurrentTrackFor?.('video')) ?? this.currentTrackIndex
      return this.findHintForSelection(trackIndex, qualityIndex)
    } catch {
      return null
    }
  }

  private isCodecFamilySupported(codecFamily: string): boolean {
    if (typeof window === 'undefined') return true
    const mediaSourceCtor = window.MediaSource as typeof MediaSource | undefined
    if (!mediaSourceCtor?.isTypeSupported) return true

    const mimeTypeByCodecFamily: Record<string, string> = {
      av1: 'video/mp4; codecs="av01.0.08M.08"',
      vp9: 'video/webm; codecs="vp09.00.10.08"',
      avc: 'video/mp4; codecs="avc1.640028"'
    }
    const mimeType = mimeTypeByCodecFamily[codecFamily]
    return mimeType ? mediaSourceCtor.isTypeSupported(mimeType) : true
  }

  private getActiveCodecFamily(): string | null {
    if (!this.player) return null
    const player = this.player as any
    const currentTrack = player.getCurrentTrackFor?.('video')
    const currentTrackCodecFamily = getCodecFamily(currentTrack?.codec)
    if (currentTrackCodecFamily) return currentTrackCodecFamily

    if (this.currentTrackIndex === null) return null
    const track = this.getVideoTracks()[this.currentTrackIndex]
    return getCodecFamily(track?.codec)
  }

  destroy(): void {
    this.destroyPlayer()
    this.currentSource = null
  }
}

export default DashAdapter
