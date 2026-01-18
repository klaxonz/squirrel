import { ref, watch, isRef, type Ref } from 'vue'
import type { PlayerStore, VideoPlayerCoreInstance } from './usePlayerContext'
import type { QualityOption, VideoInfo } from '../types/video-player'

/**
 * 视频控制函数返回类型
 */
export interface UseVideoControlsReturn {
  availableQualities: Ref<QualityOption[]>
  playbackRates: number[]
  togglePlay: () => void
  skipForward: () => void
  skipBackward: () => void
  setVideoTime: (time: number) => void
  toggleMute: () => void
  adjustVolume: (delta: number) => void
  toggleFullscreen: () => Promise<void>
  toggleTheaterMode: () => void
  togglePictureInPicture: () => Promise<void>
  toggleKeyboardHelp: () => void
  toggleSubtitles: () => void
  setSubtitle: (subtitle: any) => void
  setPlaybackRate: (rate: number) => void
  adjustPlaybackRate: (delta: number) => void
  setQuality: (quality: string) => void
  seekToPercentage: (percentage: number) => void
  updateAvailableQualities: (qualities: QualityOption[]) => void
}

// 默认播放速率选项
const DEFAULT_PLAYBACK_RATES = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2]

// 默认清晰度选项
const DEFAULT_QUALITY_OPTIONS: QualityOption[] = [
  { value: '1080p', label: '1080p' },
  { value: '720p', label: '720p' },
  { value: '480p', label: '480p' },
  { value: '360p', label: '360p' }
]

/**
 * 视频控制 Composable
 * 
 * @param store - Pinia player store
 * @param videoCore - ref to video core component
 * @param videoParam - reactive video object (e.g., props.video)
 */
export default function useVideoControls(
  store: PlayerStore,
  videoCore: Ref<VideoPlayerCoreInstance | null>,
  videoParam?: VideoInfo | Ref<VideoInfo | undefined>
): UseVideoControlsReturn {

  const getVideoParam = (): VideoInfo | undefined => {
    if (!videoParam) return undefined
    return isRef(videoParam) ? videoParam.value : videoParam
  }

  const playbackRates = DEFAULT_PLAYBACK_RATES
  const availableQualities = ref<QualityOption[]>([])

  /**
   * 从视频对象中应用清晰度列表
   */
  const applyQualitiesFromVideo = (v: VideoInfo | undefined): void => {
    try {
      const list = Array.isArray((v as any)?.qualities) ? (v as any).qualities : []
      
      if (list.length > 0) {
        const mapped: QualityOption[] = list.map((q: any) => ({
          value: q.value || (q.height ? `${q.height}p` : `${q.bandwidth || 0}k`),
          label: q.label || (q.height ? `${q.height}p` : `${q.bandwidth || 0}k`),
          height: q.height || undefined,
          bandwidth: q.bandwidth || undefined,
          id: q.id || undefined
        }))
        
        // 去重
        const uniq: Record<string, QualityOption> = {}
        mapped.forEach(q => {
          const key = `${q.value || ''}|${q.bandwidth || ''}`
          uniq[key] = q
        })
        
        const arr = Object.values(uniq)
        // 按高度排序（高到低）
        arr.sort((a, b) => ((b as any).height || 0) - ((a as any).height || 0))
        
        availableQualities.value = arr
        
        // 设置默认清晰度
        try {
          if (!store.currentQuality) {
            const highestQuality = arr[0]
            if (highestQuality) {
              store.setCurrentQuality(highestQuality.value)
            }
          }
        } catch (_) {
          // Ignore
        }
      } else {
        availableQualities.value = DEFAULT_QUALITY_OPTIONS
      }
    } catch (_) {
      availableQualities.value = DEFAULT_QUALITY_OPTIONS
    }
  }

  // 监听视频变化，更新清晰度列表
  watch(
    () => {
      const currentVideo = getVideoParam()
      return currentVideo ? [currentVideo.id, (currentVideo as any)?.qualities] : null
    },
    () => {
      applyQualitiesFromVideo(getVideoParam())
    },
    { deep: false, immediate: true }
  )

  /**
   * 更新可用清晰度列表
   */
  const updateAvailableQualities = (qualities: QualityOption[]): void => {
    if (Array.isArray(qualities) && qualities.length > 0) {
      availableQualities.value = qualities
      
      const currentQuality = store.currentQuality
      const isCurrentQualityValid = qualities.some(q => q.value === currentQuality)

      if (!currentQuality || !isCurrentQualityValid) {
        const highestQuality = qualities[0]
        if (highestQuality) {
          store.setCurrentQuality(highestQuality.value)
        }
      }
    }
  }

  /**
   * 切换播放/暂停
   */
  const togglePlay = (): void => {
    if (!videoCore.value?.videoElement) return

    if (store.playing) {
      videoCore.value.videoElement.pause()
      if (videoCore.value.audioElement) {
        videoCore.value.audioElement.pause()
      }
    } else {
      if (store.networkFirstInteraction) {
        store.setNetworkFirstInteraction(false)
      }

      videoCore.value.videoElement.play().then(() => {
        if (videoCore.value?.audioElement) {
          videoCore.value.audioElement.play().catch(err => {
            console.error('Failed to play audio:', err)
          })
        }
      }).catch(err => {
        console.error('Failed to play video:', err)
      })
    }

    store.setShowPlayIndicator(true)
    setTimeout(() => store.setShowPlayIndicator(false), 500)
  }

  /**
   * 快进 10 秒
   */
  const skipForward = (): void => {
    const newTime = Math.min(store.currentTime + 10, store.duration)
    setVideoTime(newTime)
  }

  /**
   * 快退 10 秒
   */
  const skipBackward = (): void => {
    const newTime = Math.max(store.currentTime - 10, 0)
    setVideoTime(newTime)
  }

  /**
   * 设置视频时间
   */
  const setVideoTime = (time: number): void => {
    if (!videoCore.value?.videoElement) return

    videoCore.value.videoElement.currentTime = time
    if (videoCore.value.audioElement) {
      videoCore.value.audioElement.currentTime = time
    }
    store.setCurrentTime(time)
  }

  /**
   * 切换静音
   */
  const toggleMute = (): void => {
    if (!videoCore.value?.videoElement) return
    store.toggleMute()
  }

  /**
   * 切换全屏
   */
  const toggleFullscreen = async (): Promise<void> => {
    const videoElement = videoCore.value?.videoElement
    if (!videoElement) return

    let container: HTMLElement | null = videoElement.parentElement
    while (container && !container.classList.contains('video-player-container')) {
      container = container.parentElement
    }

    if (!container) return

    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen()
        store.setFullscreen(false)
      } else {
        if (container.requestFullscreen) {
          await container.requestFullscreen()
        } else if ((container as any).webkitRequestFullscreen) {
          await (container as any).webkitRequestFullscreen()
        } else if ((container as any).mozRequestFullScreen) {
          await (container as any).mozRequestFullScreen()
        }
        store.setFullscreen(true)
      }
    } catch (error) {
      console.error('Fullscreen error:', error)
    }
  }

  /**
   * 切换画中画
   */
  const togglePictureInPicture = async (): Promise<void> => {
    if (!document.pictureInPictureEnabled || !videoCore.value?.videoElement) return

    try {
      if (document.pictureInPictureElement) {
        await document.exitPictureInPicture()
        store.setPictureInPicture(false)
      } else {
        await videoCore.value.videoElement.requestPictureInPicture()
        store.setPictureInPicture(true)
      }
    } catch (error) {
      console.error('Picture-in-Picture error:', error)
    }
  }

  /**
   * 切换字幕
   */
  const toggleSubtitles = (): void => {
    store.toggleSubtitles()
  }

  /**
   * 设置播放速率
   */
  const setPlaybackRate = (rate: number): void => {
    store.setPlaybackRate(rate)

    if (videoCore.value?.videoElement) {
      videoCore.value.videoElement.playbackRate = rate
    }

    if (videoCore.value?.audioElement) {
      videoCore.value.audioElement.playbackRate = rate
    }

    store.showPlaybackRateMenu = false
  }

  /**
   * 设置清晰度
   */
  const setQuality = (quality: string): void => {
    store.setCurrentQuality(quality)
    store.showQualityMenu = false
    store.showSettingsMenu = false
    console.debug('Quality changed to:', quality)
  }

  /**
   * 设置字幕
   */
  const setSubtitle = (subtitle: any): void => {
    store.setCurrentSubtitle(subtitle)
    store.setSubtitlesEnabled(!!subtitle)
    store.showSettingsMenu = false
  }

  /**
   * 调整音量
   */
  const adjustVolume = (delta: number): void => {
    const newVolume = Math.min(Math.max(store.volume + delta, 0), 100)
    store.setVolume(newVolume)

    store.updateVolumeState({ showIndicator: true })
    setTimeout(() => {
      store.updateVolumeState({ showIndicator: false })
    }, 1000)
  }

  /**
   * 调整播放速率
   */
  const adjustPlaybackRate = (delta: number): void => {
    const currentRate = store.playbackRate
    const newRate = Math.min(Math.max(currentRate + delta, 0.25), 2)
    setPlaybackRate(newRate)
  }

  /**
   * 跳转到百分比位置
   */
  const seekToPercentage = (percentage: number): void => {
    const seekTime = (percentage / 100) * store.duration
    setVideoTime(seekTime)
  }

  /**
   * 切换剧场模式
   */
  const toggleTheaterMode = (): void => {
    store.toggleTheaterMode()
  }

  /**
   * 切换键盘帮助
   */
  const toggleKeyboardHelp = (): void => {
    store.setShowKeyboardHelp(!store.showKeyboardHelp)
  }

  return {
    availableQualities,
    playbackRates,
    togglePlay,
    skipForward,
    skipBackward,
    setVideoTime,
    toggleMute,
    adjustVolume,
    toggleFullscreen,
    toggleTheaterMode,
    togglePictureInPicture,
    toggleKeyboardHelp,
    toggleSubtitles,
    setSubtitle,
    setPlaybackRate,
    adjustPlaybackRate,
    setQuality,
    seekToPercentage,
    updateAvailableQualities
  }
}
