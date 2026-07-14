/**
 * 播放分析插件
 * 收集播放质量指标、缓冲事件、错误统计
 */

import type { PlayerPlugin, PluginContext, PlayerError } from '../../core/types'

export interface PlaybackMetrics {
  // 播放时长
  totalPlayTime: number
  totalPauseTime: number
  totalBufferTime: number
  
  // 缓冲统计
  bufferCount: number
  bufferEvents: BufferEvent[]
  
  // 质量统计
  qualityChanges: QualityChange[]
  averageBitrate: number
  
  // 错误统计
  errorCount: number
  errors: ErrorEvent[]
  
  // 带宽
  bandwidthSamples: BandwidthSample[]
  averageBandwidth: number
  
  // 用户交互
  seekCount: number
  volumeChanges: number
  
  // 时间戳
  sessionStart: number
  lastUpdate: number
}

export interface BufferEvent {
  timestamp: number
  duration: number
  position: number
}

export interface QualityChange {
  timestamp: number
  from: string
  to: string
  reason: 'user' | 'auto' | 'error'
}

export interface ErrorEvent {
  timestamp: number
  code: string
  message: string
  fatal: boolean
}

export interface BandwidthSample {
  timestamp: number
  bytesLoaded: number
  duration: number
  bandwidth: number // bps
}

export interface AnalyticsPluginOptions {
  /** 是否启用调试日志 */
  debug?: boolean
  /** 采样间隔(ms) */
  sampleInterval?: number
  /** 最大保存的事件数 */
  maxEvents?: number
  /** 上报回调 */
  onReport?: (metrics: PlaybackMetrics) => void
  /** 上报间隔(ms) */
  reportInterval?: number
}

export class AnalyticsPlugin implements PlayerPlugin {
  readonly name = 'analytics'
  readonly version = '1.0.0'

  private context: PluginContext | null = null
  private options: Required<AnalyticsPluginOptions>
  private metrics: PlaybackMetrics
  private reportTimer: ReturnType<typeof setInterval> | null = null
  private bufferStartTime: number | null = null
  private lastPlayTime: number = 0
  private lastPauseTime: number = 0
  private isPlaying = false

  constructor() {
    this.options = {
      debug: false,
      sampleInterval: 1000,
      maxEvents: 100,
      reportInterval: 30000,
      onReport: () => {}
    }
    this.metrics = this.createInitialMetrics()
  }

  private createInitialMetrics(): PlaybackMetrics {
    return {
      totalPlayTime: 0,
      totalPauseTime: 0,
      totalBufferTime: 0,
      bufferCount: 0,
      bufferEvents: [],
      qualityChanges: [],
      averageBitrate: 0,
      errorCount: 0,
      errors: [],
      bandwidthSamples: [],
      averageBandwidth: 0,
      seekCount: 0,
      volumeChanges: 0,
      sessionStart: Date.now(),
      lastUpdate: Date.now()
    }
  }

  install(context: PluginContext, options?: AnalyticsPluginOptions): void {
    this.context = context
    this.options = { ...this.options, ...options }
    this.metrics = this.createInitialMetrics()

    this.log('Analytics plugin installed')

    // 启动定期上报
    if (this.options.reportInterval > 0) {
      this.reportTimer = setInterval(() => {
        this.report()
      }, this.options.reportInterval)
    }
  }

  onPlay(): void {
    this.isPlaying = true
    this.lastPlayTime = Date.now()
    
    // 如果之前在暂停状态，累计暂停时间
    if (this.lastPauseTime > 0) {
      this.metrics.totalPauseTime += Date.now() - this.lastPauseTime
      this.lastPauseTime = 0
    }
    
    this.log('Play event')
  }

  onPause(): void {
    this.isPlaying = false
    this.lastPauseTime = Date.now()
    
    // 累计播放时间
    if (this.lastPlayTime > 0) {
      this.metrics.totalPlayTime += Date.now() - this.lastPlayTime
      this.lastPlayTime = 0
    }
    
    this.log('Pause event')
  }

  onSeek(time: number): void {
    this.metrics.seekCount++
    this.log(`Seek to ${time}`)
  }

  onVolumeChange(): void {
    this.metrics.volumeChanges++
  }

  onQualityChange(quality: string): void {
    const lastChange = this.metrics.qualityChanges[this.metrics.qualityChanges.length - 1]
    
    this.addEvent(this.metrics.qualityChanges, {
      timestamp: Date.now(),
      from: lastChange?.to || 'auto',
      to: quality,
      reason: 'user'
    })
    
    this.log(`Quality changed to ${quality}`)
  }

  onError(error: PlayerError): void {
    this.metrics.errorCount++
    
    this.addEvent(this.metrics.errors, {
      timestamp: Date.now(),
      code: error.code,
      message: error.message,
      fatal: error.fatal
    })
    
    this.log(`Error: ${error.code} - ${error.message}`)
  }

  /**
   * 记录缓冲开始
   */
  onBufferStart(): void {
    if (this.bufferStartTime === null) {
      this.bufferStartTime = Date.now()
      this.metrics.bufferCount++
      this.log('Buffer start')
    }
  }

  /**
   * 记录缓冲结束
   */
  onBufferEnd(): void {
    if (this.bufferStartTime !== null) {
      const duration = Date.now() - this.bufferStartTime
      this.metrics.totalBufferTime += duration
      
      this.addEvent(this.metrics.bufferEvents, {
        timestamp: this.bufferStartTime,
        duration,
        position: this.context?.state.currentTime || 0
      })
      
      this.bufferStartTime = null
      this.log(`Buffer end, duration: ${duration}ms`)
    }
  }

  /**
   * 记录带宽采样
   */
  recordBandwidthSample(bytesLoaded: number, durationSec: number): void {
    if (bytesLoaded <= 0 || durationSec <= 0) return
    
    const bandwidth = (bytesLoaded * 8) / durationSec // bps
    
    this.addEvent(this.metrics.bandwidthSamples, {
      timestamp: Date.now(),
      bytesLoaded,
      duration: durationSec,
      bandwidth
    })
    
    // 更新平均带宽
    this.updateAverageBandwidth()
    
    this.log(`Bandwidth sample: ${(bandwidth / 1000000).toFixed(2)} Mbps`)
  }

  /**
   * 更新平均带宽
   */
  private updateAverageBandwidth(): void {
    const samples = this.metrics.bandwidthSamples
    if (samples.length === 0) return
    
    // 使用最近 10 个样本的加权平均
    const recentSamples = samples.slice(-10)
    const totalWeight = recentSamples.reduce((sum, _, i) => sum + i + 1, 0)
    const weightedSum = recentSamples.reduce((sum, sample, i) => {
      return sum + sample.bandwidth * (i + 1)
    }, 0)
    
    this.metrics.averageBandwidth = weightedSum / totalWeight
  }

  /**
   * 添加事件（限制数量）
   */
  private addEvent<T>(array: T[], event: T): void {
    array.push(event)
    if (array.length > this.options.maxEvents) {
      array.shift()
    }
  }

  /**
   * 获取当前指标
   */
  getMetrics(): PlaybackMetrics {
    // 更新实时数据
    const now = Date.now()
    
    if (this.isPlaying && this.lastPlayTime > 0) {
      this.metrics.totalPlayTime += now - this.lastPlayTime
      this.lastPlayTime = now
    }
    
    if (!this.isPlaying && this.lastPauseTime > 0) {
      this.metrics.totalPauseTime += now - this.lastPauseTime
      this.lastPauseTime = now
    }
    
    this.metrics.lastUpdate = now
    
    return { ...this.metrics }
  }

  /**
   * 上报指标
   */
  report(): void {
    const metrics = this.getMetrics()
    this.options.onReport(metrics)
    this.log('Metrics reported', metrics)
  }

  /**
   * 获取播放质量评分 (0-100)
   */
  getQualityScore(): number {
    const metrics = this.getMetrics()
    const totalTime = metrics.totalPlayTime + metrics.totalBufferTime
    
    if (totalTime === 0) return 100
    
    // 计算各项得分
    const bufferRatio = metrics.totalBufferTime / totalTime
    const bufferScore = Math.max(0, 100 - bufferRatio * 500) // 20%缓冲=0分
    
    const errorPenalty = Math.min(metrics.errorCount * 10, 50)
    
    const avgScore = (bufferScore * 0.7) + ((100 - errorPenalty) * 0.3)
    
    return Math.round(Math.max(0, Math.min(100, avgScore)))
  }

  private log(...args: unknown[]): void {
    if (this.options.debug) {
      this.context?.logger.debug('[AnalyticsPlugin]', ...args)
    }
  }

  onDestroy(): void {
    // 最后一次上报
    this.report()
    
    if (this.reportTimer) {
      clearInterval(this.reportTimer)
      this.reportTimer = null
    }
  }

  destroy(): void {
    this.onDestroy()
    this.context = null
  }
}

export default AnalyticsPlugin
