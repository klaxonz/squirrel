import Hls, { type HlsConfig, type Level } from 'hls.js'
import type { Ref } from 'vue'
import type { PlayerStore } from '../stores/playerStore'
import type { QualityOption, VideoInfo } from '../types/video-player'

/**
 * HLS 播放器配置选项
 */
export interface UseHlsPlayerOptions {
  store: PlayerStore
  videoRef: Ref<HTMLVideoElement | null>
  props: {
    video?: VideoInfo & { qualities?: QualityOption[] }
  }
  getOptimizedHlsConfig?: () => Partial<HlsConfig>
  onProgress?: (sample?: { loaded: number; durationSec: number }) => void
  onError?: (error: HlsError) => void
  onQualitiesUpdate?: (qualities: QualityOption[]) => void
}

/**
 * HLS 错误类型
 */
export interface HlsError {
  type: 'network' | 'media' | 'fatal'
  message: string
  code?: string
}

/**
 * HLS 播放器返回类型
 */
export interface UseHlsPlayerReturn {
  hlsRef: { value: Hls | null }
  initializeHls: () => void
  reinitializeHls: () => void
  destroyHls: () => void
  setQuality: (quality: string) => void
  MAX_RECONNECT_ATTEMPTS: number
  RECONNECT_INTERVAL: number
}

/**
 * HLS 播放器 Composable
 */
export default function useHlsPlayer({
  store,
  videoRef,
  props,
  getOptimizedHlsConfig,
  onProgress,
  onError,
  onQualitiesUpdate
}: UseHlsPlayerOptions): UseHlsPlayerReturn {
  
  const hlsRef: { value: Hls | null } = { value: null }
  const MAX_RECONNECT_ATTEMPTS = 3
  const RECONNECT_INTERVAL = 3000

  /**
   * 初始化 HLS 播放器
   */
  const initializeHls = (): void => {
    if (!props.video?.stream_video_url) return

    // 检查 HLS.js 支持
    if (!Hls.isSupported()) {
      // 对于原生支持 HLS 的浏览器（如 Safari）
      if (videoRef.value?.canPlayType('application/vnd.apple.mpegurl')) {
        videoRef.value.src = props.video.stream_video_url
      }
      return
    }

    // 获取配置
    const hlsConfig = typeof getOptimizedHlsConfig === 'function' 
      ? getOptimizedHlsConfig() 
      : {}

    // 创建 HLS 实例
    hlsRef.value = new Hls(hlsConfig)
    hlsRef.value.attachMedia(videoRef.value!)

    // 媒体附加完成后加载源
    hlsRef.value.on(Hls.Events.MEDIA_ATTACHED, () => {
      hlsRef.value!.loadSource(props.video!.stream_video_url)
    })

    // 清单解析完成后，更新可用清晰度列表
    hlsRef.value.on(Hls.Events.MANIFEST_PARSED, () => {
      try {
        const levels: Level[] = hlsRef.value?.levels || []
        
        if (levels.length > 0) {
          // 构建清晰度选项列表
          const mapped: QualityOption[] = levels.map((level, index) => ({
            value: level.height ? `${level.height}p` : `level_${index}`,
            label: level.height ? `${level.height}p` : `Level ${index}`,
            height: level.height || 0,
            bandwidth: level.bitrate || 0,
            index: index
          } as QualityOption & { height: number; bandwidth: number; index: number }))

          // 去重并排序（高到低）
          const uniq: Record<string, QualityOption & { height: number }> = {}
          mapped.forEach(q => { 
            uniq[q.value] = q as QualityOption & { height: number }
          })
          
          const qualities = Object.values(uniq)
          qualities.sort((a, b) => (b.height || 0) - (a.height || 0))

          // 通知外部更新可用清晰度
          if (typeof onQualitiesUpdate === 'function') {
            onQualitiesUpdate(qualities)
          }

          // 如果已有用户选择的清晰度，则尊重该选择
          const currentQuality = store?.currentQuality
          if (currentQuality) {
            setQuality(currentQuality)
          }
        }
      } catch (_) {
        // Ignore errors during manifest parsing
      }
    })

    // 片段缓冲完成
    hlsRef.value.on(Hls.Events.FRAG_BUFFERED, () => {
      onProgress?.()
    })

    // 片段加载完成，报告带宽样本
    hlsRef.value.on(Hls.Events.FRAG_LOADED, (_event, data: any) => {
      try {
        const stats = data?.frag?.stats || data?.stats || {}
        const loadedBytes = stats.loaded ?? stats.total ?? 0
        const tfirst = stats.tfirst ?? stats.trequest ?? stats.loading?.first ?? 0
        const tload = stats.tload ?? stats.tend ?? stats.loading?.end ?? 0
        const durationSec = Math.max(0.001, (tload - tfirst) / 1000)
        
        if (loadedBytes > 0 && durationSec > 0) {
          onProgress?.({ loaded: loadedBytes, durationSec })
        }
      } catch (e) {
        // Ignore single sample errors
      }
    })

    // 错误处理
    hlsRef.value.on(Hls.Events.ERROR, (_event, data) => {
      if (data.fatal) {
        switch (data.type) {
          case Hls.ErrorTypes.NETWORK_ERROR:
            if (store.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
              store.incrementReconnectAttempts()
              hlsRef.value?.startLoad()
            } else {
              onError?.({ type: 'network', message: 'Network connection failed' })
            }
            break
            
          case Hls.ErrorTypes.MEDIA_ERROR:
            hlsRef.value?.recoverMediaError()
            break
            
          default:
            if (store.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
              store.incrementReconnectAttempts()
              reinitializeHls()
            } else {
              onError?.({ type: 'fatal', message: 'Cannot play video' })
            }
            break
        }
      }
    })
  }

  /**
   * 重新初始化 HLS 播放器
   */
  const reinitializeHls = (): void => {
    if (hlsRef.value) {
      hlsRef.value.destroy()
    }
    initializeHls()
  }

  /**
   * 销毁 HLS 播放器
   */
  const destroyHls = (): void => {
    if (hlsRef.value) {
      hlsRef.value.destroy()
      hlsRef.value = null
    }
  }

  /**
   * 设置清晰度
   */
  const setQuality = (quality: string): void => {
    if (!hlsRef.value) return

    console.log('[HLS] Switching quality to:', quality)

    // 1. 优先使用后端提供的 index
    const qualityInfo = (props?.video?.qualities || []).find(q => q.value === quality) as 
      (QualityOption & { index?: number }) | undefined
      
    if (qualityInfo && typeof qualityInfo.index === 'number' && qualityInfo.index >= 0) {
      console.log('[HLS] Using backend-provided index:', qualityInfo.index)
      hlsRef.value.currentLevel = qualityInfo.index
      console.log('[HLS] ✓ Quality switched to level:', qualityInfo.index)
      return
    }

    // 2. 降级方案：手动匹配
    console.warn('[HLS] No index provided, falling back to manual matching')
    const levels = hlsRef.value.levels || []
    
    if (!levels.length) {
      console.warn('[HLS] No levels available')
      return
    }

    const qualityStr = String(quality)
    const targetHeight = parseInt(qualityStr.replace(/[^0-9]/g, ''), 10)

    let targetLevel = levels.findIndex(level =>
      level.height === targetHeight ||
      level.name === qualityStr ||
      String(level.height) + 'p' === qualityStr
    )

    if (targetLevel === -1) {
      // 找最接近但不超过目标高度的
      targetLevel = levels.reduce((closest, level, i) => {
        if (level.height <= targetHeight && (closest === -1 || level.height > levels[closest].height)) {
          return i
        }
        return closest
      }, -1)

      if (targetLevel === -1) {
        // 找最高清晰度
        targetLevel = levels.reduce((max, level, i) =>
          level.height > levels[max].height ? i : max, 0
        )
      }
    }

    if (targetLevel >= 0) {
      hlsRef.value.currentLevel = targetLevel
      console.log('[HLS] ✓ Quality switched to fallback level:', targetLevel)
    } else {
      console.warn('[HLS] ✗ No valid level found for:', quality)
    }
  }

  return {
    hlsRef,
    initializeHls,
    reinitializeHls,
    destroyHls,
    setQuality,
    MAX_RECONNECT_ATTEMPTS,
    RECONNECT_INTERVAL
  }
}
