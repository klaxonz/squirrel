/**
 * 播放器适配器
 * 抽象业务代码依赖，允许外部注入实现
 */

// 播放进度数据
export interface PlaybackProgress {
  videoId: string
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
  subtitleLanguage?: string
  quality?: string
}

// 历史记录条目
export interface HistoryEntry {
  videoId: string
  lastPosition: number
  duration: number
  progress: number
  lastWatched: number
  title?: string
  thumbnail?: string
}

// 错误报告数据
export interface ErrorReport {
  videoId?: string
  videoUrl?: string
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
  loadProgress(videoId: string): Promise<PlaybackProgress | null>
  getHistory(limit?: number): Promise<HistoryEntry[]>
  clearHistory(): Promise<void>
  
  // 错误报告
  reportError(report: ErrorReport): Promise<void>
  
  // 分析/统计（可选）
  trackEvent?(eventName: string, data?: Record<string, any>): void
}

/**
 * 默认适配器实现 - 使用 localStorage
 */
export class LocalStorageAdapter implements IPlayerAdapter {
  private configKey = 'sp-player-config'
  private historyKey = 'sp-player-history'
  private progressPrefix = 'sp-progress-'

  async loadConfig(): Promise<UserConfig> {
    try {
      const data = localStorage.getItem(this.configKey)
      return data ? JSON.parse(data) : {}
    } catch {
      return {}
    }
  }

  async saveConfig(config: Partial<UserConfig>): Promise<void> {
    try {
      const existing = await this.loadConfig()
      const merged = { ...existing, ...config }
      localStorage.setItem(this.configKey, JSON.stringify(merged))
    } catch (e) {
      console.warn('[LocalStorageAdapter] Failed to save config:', e)
    }
  }

  async saveProgress(progress: PlaybackProgress): Promise<void> {
    try {
      const key = this.progressPrefix + progress.videoId
      localStorage.setItem(key, JSON.stringify(progress))
      
      // 同时更新历史记录
      await this.updateHistory(progress)
    } catch (e) {
      console.warn('[LocalStorageAdapter] Failed to save progress:', e)
    }
  }

  async loadProgress(videoId: string): Promise<PlaybackProgress | null> {
    try {
      const key = this.progressPrefix + videoId
      const data = localStorage.getItem(key)
      return data ? JSON.parse(data) : null
    } catch {
      return null
    }
  }

  private async updateHistory(progress: PlaybackProgress): Promise<void> {
    const history = await this.getHistory()
    const index = history.findIndex(h => h.videoId === progress.videoId)
    
    const entry: HistoryEntry = {
      videoId: progress.videoId,
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
    localStorage.setItem(this.historyKey, JSON.stringify(limited))
  }

  async getHistory(limit = 50): Promise<HistoryEntry[]> {
    try {
      const data = localStorage.getItem(this.historyKey)
      const history: HistoryEntry[] = data ? JSON.parse(data) : []
      return history.slice(0, limit)
    } catch {
      return []
    }
  }

  async clearHistory(): Promise<void> {
    localStorage.removeItem(this.historyKey)
    
    // 清除所有进度数据
    const keys = Object.keys(localStorage)
    keys.forEach(key => {
      if (key.startsWith(this.progressPrefix)) {
        localStorage.removeItem(key)
      }
    })
  }

  async reportError(report: ErrorReport): Promise<void> {
    // 本地适配器只记录到控制台
    console.warn('[LocalStorageAdapter] Error report:', report)
  }

  trackEvent(eventName: string, data?: Record<string, any>): void {
    console.log('[LocalStorageAdapter] Event:', eventName, data)
  }
}

/**
 * API 适配器实现 - 通过 HTTP 请求
 */
export class ApiAdapter implements IPlayerAdapter {
  private baseUrl: string
  private fetcher: typeof fetch

  constructor(options: { baseUrl?: string; fetcher?: typeof fetch } = {}) {
    this.baseUrl = options.baseUrl || '/api'
    this.fetcher = options.fetcher || fetch.bind(window)
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const response = await this.fetcher(`${this.baseUrl}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    })
    
    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`)
    }
    
    const data = await response.json()
    return data.data ?? data
  }

  async loadConfig(): Promise<UserConfig> {
    try {
      return await this.request<UserConfig>('/users/me/config')
    } catch {
      return {}
    }
  }

  async saveConfig(config: Partial<UserConfig>): Promise<void> {
    try {
      await this.request('/users/me/config', {
        method: 'PUT',
        body: JSON.stringify({ settings: config, merge: true })
      })
    } catch (e) {
      console.warn('[ApiAdapter] Failed to save config:', e)
    }
  }

  async saveProgress(progress: PlaybackProgress): Promise<void> {
    try {
      await this.request('/history/progress', {
        method: 'POST',
        body: JSON.stringify(progress)
      })
    } catch (e) {
      console.warn('[ApiAdapter] Failed to save progress:', e)
    }
  }

  async loadProgress(videoId: string): Promise<PlaybackProgress | null> {
    try {
      return await this.request<PlaybackProgress>(`/history/progress/${videoId}`)
    } catch {
      return null
    }
  }

  async getHistory(limit = 50): Promise<HistoryEntry[]> {
    try {
      return await this.request<HistoryEntry[]>(`/history?limit=${limit}`)
    } catch {
      return []
    }
  }

  async clearHistory(): Promise<void> {
    try {
      await this.request('/history', { method: 'DELETE' })
    } catch (e) {
      console.warn('[ApiAdapter] Failed to clear history:', e)
    }
  }

  async reportError(report: ErrorReport): Promise<void> {
    try {
      await this.request('/errors/report', {
        method: 'POST',
        body: JSON.stringify(report)
      })
    } catch (e) {
      console.warn('[ApiAdapter] Failed to report error:', e)
    }
  }

  trackEvent(eventName: string, data?: Record<string, any>): void {
    // 可以发送到分析服务
    this.request('/analytics/event', {
      method: 'POST',
      body: JSON.stringify({ event: eventName, data, timestamp: Date.now() })
    }).catch(() => {})
  }
}

/**
 * 组合适配器 - 支持多个适配器同时工作
 */
export class CompositeAdapter implements IPlayerAdapter {
  private adapters: IPlayerAdapter[]
  private primary: IPlayerAdapter

  constructor(adapters: IPlayerAdapter[]) {
    if (adapters.length === 0) {
      throw new Error('At least one adapter is required')
    }
    this.adapters = adapters
    this.primary = adapters[0]
  }

  async loadConfig(): Promise<UserConfig> {
    return this.primary.loadConfig()
  }

  async saveConfig(config: Partial<UserConfig>): Promise<void> {
    await Promise.all(this.adapters.map(a => a.saveConfig(config)))
  }

  async saveProgress(progress: PlaybackProgress): Promise<void> {
    await Promise.all(this.adapters.map(a => a.saveProgress(progress)))
  }

  async loadProgress(videoId: string): Promise<PlaybackProgress | null> {
    return this.primary.loadProgress(videoId)
  }

  async getHistory(limit?: number): Promise<HistoryEntry[]> {
    return this.primary.getHistory(limit)
  }

  async clearHistory(): Promise<void> {
    await Promise.all(this.adapters.map(a => a.clearHistory()))
  }

  async reportError(report: ErrorReport): Promise<void> {
    await Promise.all(this.adapters.map(a => a.reportError(report)))
  }

  trackEvent(eventName: string, data?: Record<string, any>): void {
    this.adapters.forEach(a => a.trackEvent?.(eventName, data))
  }
}

// 全局适配器实例
let globalAdapter: IPlayerAdapter | null = null

/**
 * 设置全局适配器
 */
export function setPlayerAdapter(adapter: IPlayerAdapter): void {
  globalAdapter = adapter
}

/**
 * 获取全局适配器
 */
export function getPlayerAdapter(): IPlayerAdapter {
  if (!globalAdapter) {
    globalAdapter = new LocalStorageAdapter()
  }
  return globalAdapter
}

export default {
  LocalStorageAdapter,
  ApiAdapter,
  CompositeAdapter,
  setPlayerAdapter,
  getPlayerAdapter
}
