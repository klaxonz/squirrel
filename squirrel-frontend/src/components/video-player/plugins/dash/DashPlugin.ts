/**
 * DASH 插件
 * 基于 dash.js 提供 MPEG-DASH 流播放支持
 */

import dashjs, { type MediaPlayerClass, type MediaPlayerSettingClass } from 'dashjs'
import type { PlayerPlugin, PluginContext, QualityLevel, PlayerError, MediaSource } from '../../core/types'

export interface DashPluginOptions {
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

export class DashPlugin implements PlayerPlugin {
  readonly name = 'dash'
  readonly version = '1.0.0'

  private player: MediaPlayerClass | null = null
  private context: PluginContext | null = null
  private options: DashPluginOptions = {}
  private currentSource: string | null = null

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

  install(context: PluginContext, options?: DashPluginOptions): void {
    this.context = context
    this.options = {
      maxRetries: 3,
      retryInterval: 3000,
      enableAutoQuality: true,
      ...options
    }
  }

  onSourceChange(source: MediaSource): void {
    if (!this.context) return

    // 检查是否为 DASH 源
    const isDash = source.type === 'dash' || 
                   (source.type === 'auto' && DashPlugin.isDashSource(source.src))
    
    if (!isDash) {
      this.destroy()
      return
    }

    this.loadSource(source.src)
  }

  /**
   * 加载 DASH 源
   */
  private loadSource(src: string): void {
    if (!this.context?.videoElement) return

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
    if (!this.context?.videoElement) return

    const player = dashjs.MediaPlayer().create()

    // 配置播放器
    const settings: Partial<MediaPlayerSettingClass> = {
      streaming: {
        abr: {
          initialBitrate: { video: 3000 },
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
          fastSwitchEnabled: true
        },
        manifestRequestTimeout: 60000,
        ...this.options.settings?.streaming
      },
      ...this.options.settings
    }

    player.updateSettings(settings)
    this.setupEventListeners(player)
    player.initialize(this.context.videoElement, src, this.context.state.playing)

    this.player = player
  }

  /**
   * 设置事件监听
   */
  private setupEventListeners(player: MediaPlayerClass): void {
    // 错误处理
    player.on('error', (e: any) => {
      const fatal = e?.error === 'capability' || e?.event?.type === 'critical'
      const error: PlayerError = {
        code: `DASH_${e?.event?.id || 'UNKNOWN'}`,
        message: e?.event?.message || 'DASH playback error',
        fatal,
        details: e
      }

      if (fatal) {
        this.context?.reportError(error)
      } else {
        console.warn('[DashPlugin] Non-fatal error:', error)
      }
    })

    // 缓冲事件
    player.on('bufferingStarted', () => {
      this.context?.emit('waiting', undefined)
    })

    player.on('bufferingCompleted', () => {
      this.context?.emit('canplay', undefined)
    })

    // 质量变化
    player.on('qualityChangeRendered', (e: any) => {
      if (e?.mediaType === 'video') {
        const qualities = this.getAvailableQualities()
        const quality = qualities.find(q => q.id === e.newQuality)
        this.context?.emit('qualitychange', {
          quality: quality?.label || `level_${e.newQuality}`,
          auto: this.isAutoQuality()
        })
      }
    })

    // 清单加载完成
    player.on('streamInitialized', () => {
      this.updateQualities()
    })

    // 片段加载完成 - 带宽采样
    player.on('fragmentLoadingCompleted', (data: any) => {
      if (this.options.onBandwidthSample) {
        try {
          const loaded = data?.request?.bytesLoaded || 0
          const t0 = data?.request?.requestStartDate?.getTime?.() || 0
          const t1 = data?.request?.requestEndDate?.getTime?.() || 0
          const durationSec = Math.max(0.001, (t1 - t0) / 1000)
          
          if (loaded > 0 && durationSec > 0) {
            this.options.onBandwidthSample(loaded, durationSec)
          }
        } catch {
          // Ignore
        }
      }
    })
  }

  /**
   * 获取可用质量列表
   */
  private getAvailableQualities(): QualityLevel[] {
    if (!this.player) return []

    try {
      const bitrateList = (this.player as any).getBitrateInfoListFor?.('video') || []
      return bitrateList.map((info: any, index: number) => ({
        id: index,
        label: info.height ? `${info.height}p` : `${Math.round(info.bitrate / 1000)}kbps`,
        width: info.width,
        height: info.height,
        bitrate: info.bitrate
      }))
    } catch {
      return []
    }
  }

  /**
   * 更新质量列表到上下文
   */
  private updateQualities(): void {
    if (!this.context) return

    const qualities = this.getAvailableQualities()
    
    // 按高度降序排列
    qualities.sort((a, b) => (b.height || 0) - (a.height || 0))

    // 添加自动选项
    if (this.options.enableAutoQuality) {
      qualities.unshift({
        id: 'auto',
        label: '自动'
      })
    }

    this.context.registerQualities(qualities)
    this.context.emit('qualitiesloaded', qualities)
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
  setQuality(quality: string | number): void {
    if (!this.player) return

    const qStr = String(quality).toLowerCase()
    const isAuto = quality === 'auto' || quality === -1 || qStr === '自动'

    if (isAuto) {
      // 启用自动质量
      try {
        this.player.updateSettings({
          streaming: { abr: { autoSwitchBitrate: { video: true } } }
        })
        console.log('[DashPlugin] Quality set to auto')
      } catch (e) {
        console.warn('[DashPlugin] Failed to enable auto quality:', e)
      }
      return
    }

    // 禁用自动质量
    try {
      this.player.updateSettings({
        streaming: { abr: { autoSwitchBitrate: { video: false } } }
      })
    } catch {
      // Ignore
    }

    // 设置指定质量
    let targetIndex: number = -1

    if (typeof quality === 'number' && quality >= 0) {
      targetIndex = quality
    } else {
      // 按高度匹配
      const height = parseInt(String(quality).replace(/[^0-9]/g, ''), 10)
      const qualities = this.getAvailableQualities()
      const found = qualities.find(q => q.height === height)
      if (found && typeof found.id === 'number') {
        targetIndex = found.id
      }
    }

    if (targetIndex >= 0) {
      try {
        const p = this.player as any
        if (typeof p.setQualityFor === 'function') {
          p.setQualityFor('video', targetIndex)
        } else if (typeof p.setRepresentationForTypeByIndex === 'function') {
          p.setRepresentationForTypeByIndex('video', targetIndex, true)
        }
        console.log('[DashPlugin] Quality set to level:', targetIndex)
      } catch (e) {
        console.warn('[DashPlugin] Failed to set quality:', e)
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
        const quality = qualities.find(q => q.id === index)
        return quality?.label || `level_${index}`
      }
    } catch {
      // Ignore
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
      } catch {
        // Ignore reset errors
      }
      this.player = null
    }
  }

  onDestroy(): void {
    this.destroyPlayer()
  }

  destroy(): void {
    this.destroyPlayer()
    this.context = null
    this.currentSource = null
  }
}

export default DashPlugin
