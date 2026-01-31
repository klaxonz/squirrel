/**
 * 播放器适配器 Composable
 * 在 Vue 组件中使用适配器
 */

import { ref, onMounted, type Ref } from 'vue'
import {
  LocalStorageAdapter,
  ApiAdapter,
  type IPlayerAdapter,
  type UserConfig,
  type PlaybackProgress,
  type HistoryEntry,
  type ErrorReport
} from './PlayerAdapter'
import { noopLogger, type PlayerLogger } from './logger'

export interface UsePlayerAdapterOptions {
  /** 自定义适配器 */
  adapter?: IPlayerAdapter
  /** 自动加载配置 */
  autoLoadConfig?: boolean
  /** 进度保存间隔(ms) */
  progressSaveInterval?: number
  /** 进度变化阈值(秒) */
  progressThreshold?: number
  logger?: PlayerLogger
}

export interface UsePlayerAdapterReturn {
  // 适配器实例
  adapter: IPlayerAdapter
  
  // 配置
  config: Ref<UserConfig>
  loadConfig: () => Promise<void>
  saveConfig: (config: Partial<UserConfig>) => Promise<void>
  
  // 进度
  saveProgress: (videoId: string, currentTime: number, duration: number) => void
  loadProgress: (videoId: string) => Promise<PlaybackProgress | null>
  
  // 历史
  history: Ref<HistoryEntry[]>
  loadHistory: (limit?: number) => Promise<void>
  clearHistory: () => Promise<void>
  
  // 错误
  reportError: (report: Omit<ErrorReport, 'timestamp'>) => Promise<void>
  
  // 事件跟踪
  trackEvent: (eventName: string, data?: Record<string, any>) => void
}

/**
 * 播放器适配器 Composable
 */
export function usePlayerAdapter(options: UsePlayerAdapterOptions = {}): UsePlayerAdapterReturn {
  const {
    adapter: customAdapter,
    autoLoadConfig = true,
    progressSaveInterval = 2000,
    progressThreshold = 5,
    logger = noopLogger
  } = options

  // 设置适配器
  const adapter = customAdapter || new LocalStorageAdapter({ logger })

  // 状态
  const config = ref<UserConfig>({})
  const history = ref<HistoryEntry[]>([])
  
  // 进度保存节流
  let lastSavedTime = 0
  let saveTimer: ReturnType<typeof setTimeout> | null = null

  /**
   * 加载配置
   */
  const loadConfig = async (): Promise<void> => {
    try {
      config.value = await adapter.loadConfig()
    } catch (e) {
      logger.warn('[usePlayerAdapter] Failed to load config', e)
    }
  }

  /**
   * 保存配置
   */
  const saveConfig = async (newConfig: Partial<UserConfig>): Promise<void> => {
    try {
      await adapter.saveConfig(newConfig)
      config.value = { ...config.value, ...newConfig }
    } catch (e) {
      logger.warn('[usePlayerAdapter] Failed to save config', e)
    }
  }

  /**
   * 保存播放进度（带节流）
   */
  const saveProgress = (videoId: string, currentTime: number, duration: number): void => {
    // 检查是否超过阈值
    if (Math.abs(currentTime - lastSavedTime) < progressThreshold) {
      return
    }

    // 清除之前的定时器
    if (saveTimer) {
      clearTimeout(saveTimer)
    }

    // 延迟保存
    saveTimer = setTimeout(async () => {
      try {
        const progress: PlaybackProgress = {
          videoId,
          currentTime,
          duration,
          progress: duration > 0 ? (currentTime / duration) * 100 : 0,
          timestamp: Date.now()
        }
        
        await adapter.saveProgress(progress)
        lastSavedTime = currentTime
      } catch (e) {
        logger.warn('[usePlayerAdapter] Failed to save progress', e)
      }
    }, progressSaveInterval)
  }

  /**
   * 加载播放进度
   */
  const loadProgress = async (videoId: string): Promise<PlaybackProgress | null> => {
    try {
      return await adapter.loadProgress(videoId)
    } catch {
      return null
    }
  }

  /**
   * 加载历史记录
   */
  const loadHistory = async (limit = 50): Promise<void> => {
    try {
      history.value = await adapter.getHistory(limit)
    } catch (e) {
      logger.warn('[usePlayerAdapter] Failed to load history', e)
    }
  }

  /**
   * 清除历史记录
   */
  const clearHistory = async (): Promise<void> => {
    try {
      await adapter.clearHistory()
      history.value = []
    } catch (e) {
      logger.warn('[usePlayerAdapter] Failed to clear history', e)
    }
  }

  /**
   * 报告错误
   */
  const reportError = async (report: Omit<ErrorReport, 'timestamp'>): Promise<void> => {
    try {
      await adapter.reportError({
        ...report,
        timestamp: Date.now()
      })
    } catch (e) {
      logger.warn('[usePlayerAdapter] Failed to report error', e)
    }
  }

  /**
   * 跟踪事件
   */
  const trackEvent = (eventName: string, data?: Record<string, any>): void => {
    adapter.trackEvent?.(eventName, data)
  }

  // 自动加载配置
  onMounted(async () => {
    if (autoLoadConfig) {
      await loadConfig()
    }
  })

  return {
    adapter,
    config,
    loadConfig,
    saveConfig,
    saveProgress,
    loadProgress,
    history,
    loadHistory,
    clearHistory,
    reportError,
    trackEvent
  }
}

// 便捷函数：创建本地存储适配器
export function createLocalAdapter(): IPlayerAdapter {
  return new LocalStorageAdapter()
}

// 便捷函数：创建 API 适配器
export function createApiAdapter(baseUrl?: string): IPlayerAdapter {
  return new ApiAdapter({ baseUrl })
}

export default usePlayerAdapter
