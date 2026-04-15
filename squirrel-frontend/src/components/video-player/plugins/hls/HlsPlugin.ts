/**
 * HLS 插件
 * 基于 hls.js 提供 HLS 流播放支持
 */

import Hls, { type HlsConfig, type Level, type ErrorData } from 'hls.js'
import type {
  PlayerPlugin,
  PluginContext,
  QualityLevel,
  PlayerError,
  MediaSource,
  PlaybackRecoveryAction,
  PlaybackRecoveryContext
} from '../../core/types'

export interface HlsPluginOptions {
  /** hls.js 配置 */
  config?: Partial<HlsConfig>
  /** 最大重连次数 */
  maxRetries?: number
  /** 重连间隔(ms) */
  retryInterval?: number
  /** 是否启用自动质量 */
  enableAutoQuality?: boolean
  /** 带宽采样回调 */
  onBandwidthSample?: (loaded: number, durationSec: number) => void
}

export class HlsPlugin implements PlayerPlugin {
  readonly name = 'hls'
  readonly version = '1.0.0'

  private hls: Hls | null = null
  private context: PluginContext | null = null
  private options: HlsPluginOptions = {}
  private retryCount = 0
  private currentSource: string | null = null
  private retryTimer: ReturnType<typeof setTimeout> | null = null
  private reloadTimer: ReturnType<typeof setTimeout> | null = null
  private qualityIdByLevelIndex = new Map<number, string>()
  private levelIndexByQualityId = new Map<string, number>()

  private clearRetryTimers(): void {
    if (this.retryTimer) {
      clearTimeout(this.retryTimer)
      this.retryTimer = null
    }

    if (this.reloadTimer) {
      clearTimeout(this.reloadTimer)
      this.reloadTimer = null
    }
  }

  private applyLevelSwitch(targetLevel: number): void {
    if (!this.hls) return

    const video = this.context?.videoElement
    const canPreloadBeforeSwitch = !!video && !video.paused && !video.ended && video.readyState > 0

    if (canPreloadBeforeSwitch) {
      this.hls.nextLevel = targetLevel
      this.context?.logger.debug('[HlsPlugin] Quality switch scheduled via nextLevel', targetLevel)
      return
    }

    this.hls.currentLevel = targetLevel
    this.context?.logger.debug('[HlsPlugin] Quality switch applied via currentLevel', targetLevel)
  }

  private buildStableQualityId(level: Level, index: number): string {
    const parts = [
      level.height ?? 0,
      level.width ?? 0,
      level.bitrate ?? 0,
      level.videoCodec ?? '',
      level.audioCodec ?? '',
      level.name ?? '',
      Array.isArray(level.url) ? level.url.join(',') : '',
      index,
    ]
    return `hls:${parts.join('|')}`
  }

  private registerStableQualityIds(levels: Level[]): void {
    this.qualityIdByLevelIndex.clear()
    this.levelIndexByQualityId.clear()

    levels.forEach((level, index) => {
      const stableId = this.buildStableQualityId(level, index)
      this.qualityIdByLevelIndex.set(index, stableId)
      this.levelIndexByQualityId.set(stableId, index)
    })
  }

  private getStableQualityId(level: Level | undefined, index: number): string {
    if (!level) return `hls:level:${index}`
    const cachedId = this.qualityIdByLevelIndex.get(index)
    if (cachedId) return cachedId

    const stableId = this.buildStableQualityId(level, index)
    this.qualityIdByLevelIndex.set(index, stableId)
    this.levelIndexByQualityId.set(stableId, index)
    return stableId
  }

  /**
   * 检测是否支持 HLS
   */
  static isSupported(): boolean {
    return Hls.isSupported()
  }

  /**
   * 检测是否为 HLS 源
   */
  static isHlsSource(src: string): boolean {
    const url = src.toLowerCase()
    // 支持多种 HLS URL 格式：
    // - xxx.m3u8
    // - xxx.m3u8?query
    // - format=m3u8
    return /\.m3u8($|\?)/i.test(src) || 
           url.includes('format=m3u8')
  }

  /**
   * 检测是否原生支持 HLS
   */
  static hasNativeSupport(): boolean {
    const video = document.createElement('video')
    return video.canPlayType('application/vnd.apple.mpegurl') !== ''
  }

  install(context: PluginContext, options?: HlsPluginOptions): void {
    this.context = context
    this.options = {
      maxRetries: 3,
      retryInterval: 3000,
      enableAutoQuality: false,
      ...options
    }
  }

  onSourceChange(source: MediaSource): void {
    if (!this.context) return

    // 检查是否为 HLS 源
    const isHls = source.type === 'hls' || 
                  (source.type === 'auto' && HlsPlugin.isHlsSource(source.src))
    
    if (!isHls) {
      this.destroyHls()
      this.currentSource = null
      return
    }

    this.loadSource(source.src)
  }

  /**
   * 加载 HLS 源
   */
  private loadSource(src: string): void {
    if (!this.context?.videoElement) return

    this.currentSource = src
    this.retryCount = 0

    // 销毁旧实例
    this.destroyHls()

    // 检查支持情况
    if (!Hls.isSupported()) {
      // Safari 等原生支持 HLS 的浏览器
      if (HlsPlugin.hasNativeSupport()) {
        this.context.videoElement.src = src
        return
      }
      this.context.reportError({
        code: 'HLS_NOT_SUPPORTED',
        message: 'HLS is not supported in this browser',
        fatal: true
      })
      return
    }

    this.initializeHls(src)
  }

  /**
   * 初始化 HLS 实例
   */
  private initializeHls(src: string): void {
    if (!this.context?.videoElement) return

    const config: Partial<HlsConfig> = {
      enableWorker: true,
      lowLatencyMode: false,
      backBufferLength: 90,
      ...this.options.config
    }

    this.hls = new Hls(config)
    this.hls.attachMedia(this.context.videoElement)
    this.setupEventListeners()
    this.hls.loadSource(src)
  }

  /**
   * 设置事件监听
   */
  private setupEventListeners(): void {
    if (!this.hls) return

    // 媒体附加完成
    this.hls.on(Hls.Events.MEDIA_ATTACHED, () => {
      this.context?.logger.debug('[HlsPlugin] Media attached')
    })

    // 清单解析完成
    this.hls.on(Hls.Events.MANIFEST_PARSED, (_event, data) => {
      this.context?.logger.debug('[HlsPlugin] Manifest parsed, levels', data.levels.length)
      this.updateQualities(data.levels)
    })

    // 级别切换
    this.hls.on(Hls.Events.LEVEL_SWITCHED, (_event, data) => {
      const level = this.hls?.levels[data.level]
      if (level) {
        const quality = level.height ? `${level.height}p` : `level_${data.level}`
        const qualityId = this.getStableQualityId(level, data.level)
        this.context?.registerCurrentQualityId?.(qualityId)
        this.context?.emit('qualitychange', { 
          quality, 
          auto: this.hls?.autoLevelEnabled ?? false,
          id: qualityId
        })
      }
    })

    // 片段加载完成 - 带宽采样
    this.hls.on(Hls.Events.FRAG_LOADED, (_event, data) => {
      this.retryCount = 0
      if (this.options.onBandwidthSample) {
        try {
          const stats: any = data.frag?.stats || (data as any).stats || {}
          const loaded = stats.loaded ?? stats.total ?? 0
          const tfirst = stats.tfirst ?? stats.trequest ?? 0
          const tload = stats.tload ?? stats.tend ?? 0
          const durationSec = Math.max(0.001, (tload - tfirst) / 1000)
          
          if (loaded > 0 && durationSec > 0) {
            this.options.onBandwidthSample(loaded, durationSec)
          }
        } catch (e) {
          // Ignore
        }
      }
    })

    // 错误处理
    this.hls.on(Hls.Events.ERROR, (_event, data) => {
      this.handleError(data)
    })
  }

  /**
   * 更新可用质量列表
   */
  private updateQualities(levels: Level[]): void {
    if (!this.context || !levels.length) return

    this.registerStableQualityIds(levels)

    const qualities: QualityLevel[] = levels.map((level, index) => ({
      id: this.getStableQualityId(level, index),
      label: level.height ? `${level.height}p` : `Level ${index}`,
      width: level.width,
      height: level.height,
      bitrate: level.bitrate
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

    // 按高度、带宽降序排列
    qualities.sort((a, b) => {
      const heightDelta = (b.height || 0) - (a.height || 0)
      if (heightDelta !== 0) return heightDelta
      return (b.bitrate || 0) - (a.bitrate || 0)
    })


    this.context.registerQualities(qualities)
    this.context.emit('qualitiesloaded', qualities)

    if (!this.options.enableAutoQuality && !this.context.state.quality && qualities.length > 0) {
      this.context.setQuality(qualities[0].id ?? qualities[0].label)
    }
  }

  /**
   * 处理错误
   */
  private handleError(data: ErrorData): void {
    if (!data.fatal) return

    const error: PlayerError = {
      code: `HLS_${data.type}_${data.details}`,
      message: data.reason || 'HLS playback error',
      fatal: true,
      details: data
    }

    switch (data.type) {
      case Hls.ErrorTypes.NETWORK_ERROR:
        if (this.retryCount < (this.options.maxRetries || 3)) {
          this.retryCount++
          this.context?.logger.debug(`[HlsPlugin] Network error, retrying (${this.retryCount})...`)
          this.clearRetryTimers()
          this.retryTimer = setTimeout(() => {
            this.retryTimer = null
            this.hls?.startLoad()
          }, this.options.retryInterval || 3000)
          return
        }
        error.message = 'Network connection failed'
        break

      case Hls.ErrorTypes.MEDIA_ERROR:
        this.context?.logger.debug('[HlsPlugin] Media error, attempting recovery...')
        this.hls?.recoverMediaError()
        return

      default:
        if (this.retryCount < (this.options.maxRetries || 3)) {
          this.retryCount++
          this.context?.logger.debug(`[HlsPlugin] Fatal error, reinitializing (${this.retryCount})...`)
          this.clearRetryTimers()
          this.reloadTimer = setTimeout(() => {
            this.reloadTimer = null
            if (this.currentSource) {
              this.loadSource(this.currentSource)
            }
          }, this.options.retryInterval || 3000)
          return
        }
        error.message = 'Cannot play video'
    }

    this.context?.reportError(error)
  }

  recoverPlayback(error: PlayerError, _context: PlaybackRecoveryContext): PlaybackRecoveryAction {
    if (!this.hls) {
      return 'reload-source'
    }

    const code = String(error.code || '').toUpperCase()

    if (code.includes('NOT_SUPPORTED')) {
      return 'unrecoverable'
    }

    if (code.includes('NETWORK') || code.includes('TIMEOUT')) {
      try {
        this.hls.startLoad()
        this.context?.logger.debug('[HlsPlugin] Recovery handled via startLoad')
        return 'handled'
      } catch (recoverError) {
        this.context?.logger.warn('[HlsPlugin] Failed to recover network playback', recoverError)
        return 'reload-source'
      }
    }

    if (
      code.includes('MEDIA') ||
      code.includes('DECODE') ||
      code.includes('BUFFER') ||
      code.includes('STALL')
    ) {
      try {
        this.hls.recoverMediaError()
        this.context?.logger.debug('[HlsPlugin] Recovery handled via recoverMediaError')
        return 'handled'
      } catch (recoverError) {
        this.context?.logger.warn('[HlsPlugin] Failed to recover media playback', recoverError)
        return 'reload-source'
      }
    }

    return 'reload-source'
  }

  /**
   * 设置质量
   */
  setQuality(quality: string | number): void {
    if (!this.hls) return

    if (quality === 'auto' || quality === -1) {
      this.applyLevelSwitch(-1)
      this.context?.logger.debug('[HlsPlugin] Quality set to auto')
      return
    }

    const levels = this.hls.levels || []
    let targetLevel = -1

    // 直接使用索引
    if (typeof quality === 'number' && quality >= 0 && quality < levels.length) {
      targetLevel = quality
    } else {
      let resolvedFromStableId = false
      if (typeof quality === 'string') {
        const matchedLevelIndex = this.levelIndexByQualityId.get(quality)
        if (typeof matchedLevelIndex === 'number') {
          targetLevel = matchedLevelIndex
          resolvedFromStableId = true
        }
      }

      if (!resolvedFromStableId) {
        // 按高度匹配
        const height = parseInt(String(quality).replace(/[^0-9]/g, ''), 10)
        targetLevel = levels.findIndex(l => l.height === height)

        // 找不到则找最接近的
        if (targetLevel === -1 && height > 0) {
          targetLevel = levels.reduce((closest, level, i) => {
            if (level.height <= height &&
                (closest === -1 || level.height > levels[closest].height)) {
              return i
            }
            return closest
          }, -1)
        }
      }
    }

    if (targetLevel >= 0) {
      this.applyLevelSwitch(targetLevel)
      this.context?.logger.debug('[HlsPlugin] Quality set to level', targetLevel)
    }
  }

  /**
   * 获取当前质量
   */
  getCurrentQuality(): string | null {
    if (!this.hls) return null
    
    const level = this.hls.currentLevel
    if (level === -1) return 'auto'
    
    const levelData = this.hls.levels[level]
    return levelData?.height ? `${levelData.height}p` : `level_${level}`
  }

  /**
   * 销毁 HLS 实例
   */
  private destroyHls(): void {
    this.clearRetryTimers()
    this.qualityIdByLevelIndex.clear()
    this.levelIndexByQualityId.clear()
    if (this.hls) {
      this.hls.destroy()
      this.hls = null
    }
  }

  onDestroy(): void {
    this.destroyHls()
  }

  destroy(): void {
    this.destroyHls()
    this.context = null
    this.currentSource = null
  }
}

export default HlsPlugin
