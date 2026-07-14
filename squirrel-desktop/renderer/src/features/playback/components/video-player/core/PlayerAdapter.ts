/**
 * 播放器适配器
 * 抽象业务代码依赖，允许外部注入实现
 */

import { playerLogger, type PlayerLogger } from './logger'

// 播放进度数据
export interface PlaybackProgress {
  progressKey: string
  currentTime: number
  duration: number
  progress: number // 0-100
  timestamp: number
}

// 用户配置
export interface UserConfig {
  autoplay?: boolean
  autoplayNext?: boolean
  loop?: boolean
  volume?: number
  muted?: boolean
  playbackRate?: number
  subtitleEnabled?: boolean
  subtitleTrackId?: string
  subtitleLanguage?: string
  quality?: string
}

// 历史记录条目
export interface HistoryEntry {
  progressKey: string
  lastPosition: number
  duration: number
  progress: number
  lastWatched: number
  title?: string
  thumbnail?: string
}

// 错误报告数据
export interface ErrorReport {
  progressKey?: string
  sourceUrl?: string
  errorCode?: string
  errorMessage?: string
  playerState?: {
    currentTime: number
    duration: number
    volume: number
    playbackRate: number
  }
  userAction?: string
  timestamp: number
}

/**
 * 播放器适配器接口
 * 定义所有可被外部实现的功能
 */
export interface IPlayerAdapter {
  // 用户配置
  loadConfig(): Promise<UserConfig>
  saveConfig(config: Partial<UserConfig>): Promise<void>

  // 播放历史
  saveProgress(progress: PlaybackProgress): Promise<void>
  loadProgress(progressKey: string): Promise<PlaybackProgress | null>
  getHistory(limit?: number): Promise<HistoryEntry[]>
  clearHistory(): Promise<void>

  // 错误报告
  reportError(report: ErrorReport): Promise<void>
}

export type LocalStorageAdapterOptions = {
  storage?: Storage
  configKey?: string
  historyKey?: string
  progressPrefix?: string
}

/**
 * 默认适配器实现 - 使用 localStorage
 */
export class LocalStorageAdapter implements IPlayerAdapter {
  private storage: Storage
  private configKey: string
  private historyKey: string
  private progressPrefix: string
  private logger: PlayerLogger

  constructor(options: LocalStorageAdapterOptions = {}) {
    this.storage = options.storage ?? localStorage
    this.configKey = options.configKey ?? 'sp-player-config'
    this.historyKey = options.historyKey ?? 'sp-player-history'
    this.progressPrefix = options.progressPrefix ?? 'sp-progress-'
    this.logger = playerLogger
  }

  async loadConfig(): Promise<UserConfig> {
    try {
      const data = this.storage.getItem(this.configKey)
      return data ? JSON.parse(data) : {}
    } catch {
      return {}
    }
  }

  async saveConfig(config: Partial<UserConfig>): Promise<void> {
    try {
      const existing = await this.loadConfig()
      const merged = { ...existing, ...config }
      this.storage.setItem(this.configKey, JSON.stringify(merged))
    } catch (e) {
      this.logger.warn('[LocalStorageAdapter] Failed to save config', e)
    }
  }

  async saveProgress(progress: PlaybackProgress): Promise<void> {
    try {
      const key = this.progressPrefix + progress.progressKey
      this.storage.setItem(key, JSON.stringify(progress))

      // 同时更新历史记录
      await this.updateHistory(progress)
    } catch (e) {
      this.logger.warn('[LocalStorageAdapter] Failed to save progress', e)
    }
  }

  async loadProgress(progressKey: string): Promise<PlaybackProgress | null> {
    try {
      const key = this.progressPrefix + progressKey
      const data = this.storage.getItem(key)
      return data ? JSON.parse(data) : null
    } catch {
      return null
    }
  }

  private async updateHistory(progress: PlaybackProgress): Promise<void> {
    const history = await this.getHistory()
    const index = history.findIndex(h => h.progressKey === progress.progressKey)

    const entry: HistoryEntry = {
      progressKey: progress.progressKey,
      lastPosition: progress.currentTime,
      duration: progress.duration,
      progress: progress.progress,
      lastWatched: progress.timestamp
    }

    if (index >= 0) {
      history[index] = { ...history[index], ...entry }
    } else {
      history.unshift(entry)
    }

    // 限制历史记录数量
    const limited = history.slice(0, 100)
    this.storage.setItem(this.historyKey, JSON.stringify(limited))
  }

  async getHistory(limit = 50): Promise<HistoryEntry[]> {
    try {
      const data = this.storage.getItem(this.historyKey)
      const history: HistoryEntry[] = data ? JSON.parse(data) : []
      return history.slice(0, limit)
    } catch {
      return []
    }
  }

  async clearHistory(): Promise<void> {
    this.storage.removeItem(this.historyKey)

    // 清除所有进度数据
    const keys: string[] = []
    for (let i = 0; i < this.storage.length; i++) {
      const key = this.storage.key(i)
      if (key) keys.push(key)
    }

    keys.forEach(key => {
      if (key.startsWith(this.progressPrefix)) {
        this.storage.removeItem(key)
      }
    })
  }

  async reportError(report: ErrorReport): Promise<void> {
    // 本地适配器只记录到控制台
    this.logger.warn('[LocalStorageAdapter] Error report', report)
  }
}
