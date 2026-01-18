import dashjs, { type MediaPlayerClass } from 'dashjs'
import type { Ref } from 'vue'
import type { PlayerStore } from '../stores/playerStore'
import type { QualityOption, VideoInfo } from '../types/video-player'

/**
 * DASH 播放器配置选项
 */
export interface UseDashPlayerOptions {
  store: PlayerStore
  videoRef: Ref<HTMLVideoElement | null>
  props: {
    video?: VideoInfo & { 
      qualities?: (QualityOption & { index?: number })[]
      mpd_url?: string 
    }
  }
  onProgress?: (sample?: { loaded: number; durationSec: number }) => void
  onError?: (error: DashError) => void
  onQualitiesUpdate?: (qualities: QualityOption[]) => void
}

/**
 * DASH 错误类型
 */
export interface DashError {
  type: 'network' | 'media' | 'fatal'
  message: string
  code?: string
}

/**
 * DASH 播放器返回类型
 */
export interface UseDashPlayerReturn {
  dashRef: { value: MediaPlayerClass | null }
  initializeDash: () => void
  destroyDash: () => void
  setQuality: (quality: string | number) => void
}

/**
 * DASH 播放器 Composable
 */
export default function useDashPlayer({
  store,
  videoRef,
  props,
  onProgress,
  onError,
  onQualitiesUpdate
}: UseDashPlayerOptions): UseDashPlayerReturn {
  
  const dashRef: { value: MediaPlayerClass | null } = { value: null }

  /**
   * 初始化 DASH 播放器
   */
  const initializeDash = (): void => {
    const mpdUrl = props.video?.mpd_url || props.video?.stream_video_url
    
    // 解析 MPD URL
    const resolvedMpdUrl = (() => {
      try {
        return new URL(mpdUrl!, window.location.origin).toString()
      } catch (_) {
        return mpdUrl
      }
    })()

    // 清理现有实例
    if (dashRef.value) {
      try {
        dashRef.value.reset()
      } catch (_) {
        // Ignore reset errors
      }
      dashRef.value = null
    }

    // 创建 DASH 播放器实例
    const player = dashjs.MediaPlayer().create()

    // 配置播放器
    player.updateSettings({
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
        manifestRequestTimeout: 60000
      }
    })

    // 错误处理
    player.on('error', (e: any) => {
      const fatal = e?.error === 'capability' || e?.event?.type === 'critical'
      const err: DashError = {
        type: fatal ? 'fatal' : 'media',
        message: e?.event?.message || 'dash error',
        code: e?.event?.id
      }
      onError?.(err)
    })

    // 缓冲事件
    player.on('bufferingStarted', () => {
      store.setLoading(true, 'buffering')
    })
    
    player.on('bufferingCompleted', () => {
      store.setLoading(false, 'ready')
    })

    // 片段加载完成，报告带宽
    player.on('fragmentLoadingCompleted', (data: any) => {
      try {
        const loaded = data?.request?.bytesLoaded || 0
        const t0 = data?.request?.requestStartDate?.getTime?.() || 0
        const t1 = data?.request?.requestEndDate?.getTime?.() || 0
        const durationSec = Math.max(0.001, (t1 - t0) / 1000)
        
        if (loaded > 0 && durationSec > 0) {
          onProgress?.({ loaded, durationSec })
        }
      } catch (_) {
        // Ignore sampling errors
      }
    })

    // 初始化播放器
    player.initialize(videoRef.value!, resolvedMpdUrl!, store.autoplay)

    dashRef.value = player
  }

  /**
   * 销毁 DASH 播放器
   */
  const destroyDash = (): void => {
    if (dashRef.value) {
      try {
        dashRef.value.reset()
      } catch (_) {
        // Ignore reset errors
      }
      dashRef.value = null
    }
  }

  /**
   * 设置清晰度
   */
  const setQuality = (quality: string): void => {
    if (!dashRef.value) return

    const player = dashRef.value
    const qualityInfo = (props?.video?.qualities || []).find(q => q.value === quality) as 
      (QualityOption & { index?: number }) | undefined

    const qStr = String(quality || '').toLowerCase()
    const isAutoValue = qStr === 'auto' || qStr === '自动'

    // 自动模式或无效索引时启用 ABR
    if (!qualityInfo || isAutoValue || typeof qualityInfo.index !== 'number' || qualityInfo.index < 0) {
      console.log('[DASH] Switching to AUTO quality, enable ABR. quality=', quality)
      try {
        player.updateSettings({
          streaming: { abr: { autoSwitchBitrate: { video: true } } }
        })
      } catch (_) {
        // Ignore settings update errors
      }
      return
    }

    const targetIndex = qualityInfo.index
    console.log('[DASH] Switching quality to', quality, 'index=', targetIndex)

    // 禁用 ABR
    try {
      player.updateSettings({
        streaming: { abr: { autoSwitchBitrate: { video: false } } }
      })
    } catch (_) {
      // Ignore settings update errors
    }

    // 设置清晰度
    try {
      if (typeof (player as any).setQualityFor === 'function') {
        (player as any).setQualityFor('video', targetIndex)
      } else if (typeof (player as any).setRepresentationForTypeByIndex === 'function') {
        (player as any).setRepresentationForTypeByIndex('video', targetIndex, true)
      }
      
      const currentIndex = typeof (player as any).getQualityFor === 'function' 
        ? (player as any).getQualityFor('video') 
        : null
      console.log('[DASH] After switch, current quality index =', currentIndex)
    } catch (e) {
      console.warn('[DASH] setQualityFor failed', e)
    }
  }

  return {
    dashRef,
    initializeDash,
    destroyDash,
    setQuality
  }
}
