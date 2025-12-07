/**
 * 错误恢复机制
 * 网络断线重试、清晰度降级、播放失败恢复
 */

import { ref, computed, type Ref } from 'vue'
import type { PlayerError, QualityLevel } from './types'

export interface ErrorRecoveryOptions {
  maxRetries?: number
  retryDelay?: number
  enableQualityFallback?: boolean
  onRetry?: (attempt: number) => void
  onQualityFallback?: (quality: QualityLevel) => void
  onRecoveryFailed?: (error: PlayerError) => void
}

export interface ErrorRecoveryState {
  isRecovering: Ref<boolean>
  retryCount: Ref<number>
  currentStrategy: Ref<RecoveryStrategy | null>
  lastError: Ref<PlayerError | null>
}

export interface ErrorRecoveryActions {
  handleError: (error: PlayerError) => Promise<boolean>
  reset: () => void
  setQualities: (qualities: QualityLevel[]) => void
  getCurrentQuality: () => QualityLevel | null
}

export type RecoveryStrategy = 'retry' | 'quality-fallback' | 'reload' | 'none'

export type UseErrorRecoveryReturn = ErrorRecoveryState & ErrorRecoveryActions

/**
 * 错误恢复 Composable
 */
export function useErrorRecovery(options: ErrorRecoveryOptions = {}): UseErrorRecoveryReturn {
  const {
    maxRetries = 3,
    retryDelay = 2000,
    enableQualityFallback = true,
    onRetry,
    onQualityFallback,
    onRecoveryFailed
  } = options

  // 状态
  const isRecovering = ref(false)
  const retryCount = ref(0)
  const currentStrategy = ref<RecoveryStrategy | null>(null)
  const lastError = ref<PlayerError | null>(null)
  
  // 质量列表
  const qualities = ref<QualityLevel[]>([])
  const currentQualityIndex = ref(0)

  /**
   * 设置可用质量
   */
  const setQualities = (newQualities: QualityLevel[]): void => {
    qualities.value = newQualities
    currentQualityIndex.value = 0
  }

  /**
   * 获取当前质量
   */
  const getCurrentQuality = (): QualityLevel | null => {
    return qualities.value[currentQualityIndex.value] || null
  }

  /**
   * 获取下一个较低质量
   */
  const getNextLowerQuality = (): QualityLevel | null => {
    const current = currentQualityIndex.value
    const sorted = [...qualities.value].sort((a, b) => (b.height || 0) - (a.height || 0))
    
    // 找到当前质量在排序列表中的位置
    const currentInSorted = sorted.findIndex(q => 
      q.id === qualities.value[current]?.id
    )
    
    // 返回下一个较低质量
    if (currentInSorted >= 0 && currentInSorted < sorted.length - 1) {
      return sorted[currentInSorted + 1]
    }
    
    return null
  }

  /**
   * 确定恢复策略
   */
  const determineStrategy = (error: PlayerError): RecoveryStrategy => {
    // 网络错误 -> 重试
    if (error.code?.includes('NETWORK') || error.code?.includes('TIMEOUT')) {
      if (retryCount.value < maxRetries) {
        return 'retry'
      }
      // 重试耗尽后尝试降级
      if (enableQualityFallback && getNextLowerQuality()) {
        return 'quality-fallback'
      }
    }
    
    // 媒体错误 -> 尝试降级
    if (error.code?.includes('MEDIA') || error.code?.includes('DECODE')) {
      if (enableQualityFallback && getNextLowerQuality()) {
        return 'quality-fallback'
      }
    }
    
    // 缓冲问题 -> 降级
    if (error.code?.includes('BUFFER') || error.code?.includes('STALL')) {
      if (enableQualityFallback && getNextLowerQuality()) {
        return 'quality-fallback'
      }
    }
    
    // 非致命错误 -> 重试
    if (!error.fatal && retryCount.value < maxRetries) {
      return 'retry'
    }
    
    return 'none'
  }

  /**
   * 执行重试
   */
  const executeRetry = (): Promise<boolean> => {
    return new Promise((resolve) => {
      retryCount.value++
      onRetry?.(retryCount.value)
      
      console.log(`[ErrorRecovery] Retry attempt ${retryCount.value}/${maxRetries}`)
      
      setTimeout(() => {
        resolve(true)
      }, retryDelay)
    })
  }

  /**
   * 执行质量降级
   */
  const executeQualityFallback = (): Promise<boolean> => {
    return new Promise((resolve) => {
      const nextQuality = getNextLowerQuality()
      
      if (!nextQuality) {
        resolve(false)
        return
      }
      
      console.log(`[ErrorRecovery] Falling back to quality: ${nextQuality.label}`)
      
      // 更新当前质量索引
      const newIndex = qualities.value.findIndex(q => q.id === nextQuality.id)
      if (newIndex >= 0) {
        currentQualityIndex.value = newIndex
      }
      
      // 重置重试计数
      retryCount.value = 0
      
      onQualityFallback?.(nextQuality)
      resolve(true)
    })
  }

  /**
   * 处理错误
   */
  const handleError = async (error: PlayerError): Promise<boolean> => {
    lastError.value = error
    
    // 已在恢复中
    if (isRecovering.value) {
      console.log('[ErrorRecovery] Already recovering, skipping')
      return false
    }
    
    isRecovering.value = true
    
    try {
      const strategy = determineStrategy(error)
      currentStrategy.value = strategy
      
      console.log(`[ErrorRecovery] Strategy: ${strategy}, Error:`, error)
      
      let recovered = false
      
      switch (strategy) {
        case 'retry':
          recovered = await executeRetry()
          break
          
        case 'quality-fallback':
          recovered = await executeQualityFallback()
          break
          
        case 'reload':
          // 重新加载页面（最后手段）
          if (typeof window !== 'undefined') {
            window.location.reload()
          }
          recovered = false
          break
          
        case 'none':
        default:
          recovered = false
          break
      }
      
      if (!recovered) {
        console.log('[ErrorRecovery] Recovery failed')
        onRecoveryFailed?.(error)
      }
      
      return recovered
    } finally {
      isRecovering.value = false
    }
  }

  /**
   * 重置状态
   */
  const reset = (): void => {
    isRecovering.value = false
    retryCount.value = 0
    currentStrategy.value = null
    lastError.value = null
    currentQualityIndex.value = 0
  }

  return {
    // 状态
    isRecovering,
    retryCount,
    currentStrategy,
    lastError,
    
    // 操作
    handleError,
    reset,
    setQualities,
    getCurrentQuality
  }
}

export default useErrorRecovery
