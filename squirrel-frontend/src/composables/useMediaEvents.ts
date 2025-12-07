import type { Ref } from 'vue'
import type { PlayerStore } from '../stores/playerStore'

/**
 * 媒体事件处理器返回类型
 */
export interface MediaEventHandlers {
  handleVideoSeeking: () => void
  handleVideoSeeked: () => void
  handleVideoCanplay: () => void
  handleVideoCanplaythrough: () => void
  handleVideoWaiting: () => void
  handleVideoProgress: () => void
  handleVideoLoadstart: () => void
  handleVideoLoadedmetadata: () => void
  handleVideoLoadeddata: () => void
  handleVideoStalled: () => void
  handleVideoSuspend: () => void
  handleVideoAbort: () => void
  handleAudioSeeking: () => void
  handleAudioCanplay: () => void
  handleAudioError: () => void
}

/**
 * 处理视频/音频元素的事件
 * 
 * @param store - Pinia player store
 * @param videoElement - 视频元素引用
 * @param audioElement - 音频元素引用
 * @param isHlsStream - 是否为 HLS 流（可以是布尔值或返回布尔值的函数）
 * @param clearError - 清除错误的回调函数
 */
export default function useMediaEvents(
  store: PlayerStore,
  videoElement: Ref<HTMLVideoElement | null> | undefined,
  audioElement: Ref<HTMLAudioElement | null> | undefined,
  isHlsStream: boolean | (() => boolean),
  clearError?: () => void
): MediaEventHandlers {
  
  const getIsHls = (): boolean => {
    return typeof isHlsStream === 'function' ? isHlsStream() : isHlsStream
  }

  const handleVideoSeeking = (): void => {
    store.setLoading(true, 'buffering')
    store.setSeeking('video', true)
    
    if (!getIsHls() && audioElement?.value && !audioElement.value.paused) {
      try { 
        audioElement.value.pause() 
      } catch (e) {
        // Ignore
      }
    }
  }

  const handleVideoSeeked = (): void => {
    store.setLoading(false, 'ready')
    store.setSeeking('video', false)
  }

  const handleVideoCanplay = (): void => {
    if (videoElement?.value) {
      store.setDuration(videoElement.value.duration)
    }
    store.setLoading(false, 'ready')
    store.setCanPlay('video', true)
    store.setSeeking('video', false)
    
    if (clearError) {
      clearError()
    }
  }

  const handleVideoCanplaythrough = (): void => {
    store.setLoading(false, 'ready')
    
    if (!getIsHls() && audioElement?.value && store.playing) {
      try { 
        audioElement.value.play().catch(() => {}) 
      } catch (e) {
        // Ignore
      }
    }
  }

  const handleVideoWaiting = (): void => {
    store.setLoading(true, 'buffering')
    
    if (!getIsHls() && audioElement?.value && !audioElement.value.paused) {
      try { 
        audioElement.value.pause() 
      } catch (e) {
        // Ignore
      }
    }
  }

  const handleVideoProgress = (): void => {
    if (videoElement?.value && videoElement.value.buffered.length > 0) {
      const buffered = videoElement.value.buffered
      let bufferedEnd = 0

      for (let i = 0; i < buffered.length; i++) {
        if (
          buffered.start(i) <= store.currentTime &&
          buffered.end(i) >= store.currentTime
        ) {
          bufferedEnd = buffered.end(i)
          break
        }
        if (buffered.end(i) > bufferedEnd) {
          bufferedEnd = buffered.end(i)
        }
      }

      store.setBufferedProgress((bufferedEnd / store.duration) * 100)
    }
  }

  const handleVideoLoadstart = (): void => {
    store.setLoading(true, 'fetching')
  }

  const handleVideoLoadedmetadata = (): void => {
    store.setLoading(true, store.hasStartedPlayback ? 'buffering' : 'fetching')
    
    if (videoElement?.value) {
      store.setDuration(videoElement.value.duration)
    }
  }

  const handleVideoLoadeddata = (): void => {
    store.setLoading(false, 'ready')
  }

  const handleVideoStalled = (): void => {
    store.setLoading(true, 'buffering')
  }

  const handleVideoSuspend = (): void => {
    // No action needed
  }

  const handleVideoAbort = (): void => {
    store.setLoading(false)
  }

  const handleAudioSeeking = (): void => {
    store.setSeeking('audio', true)
  }

  const handleAudioCanplay = (): void => {
    store.setCanPlay('audio', true)
    store.setSeeking('audio', false)
  }

  const handleAudioError = (): void => {
    console.error('Audio playback error')
  }

  return {
    handleVideoSeeking,
    handleVideoSeeked,
    handleVideoCanplay,
    handleVideoCanplaythrough,
    handleVideoWaiting,
    handleVideoProgress,
    handleVideoLoadstart,
    handleVideoLoadedmetadata,
    handleVideoLoadeddata,
    handleVideoStalled,
    handleVideoSuspend,
    handleVideoAbort,
    handleAudioSeeking,
    handleAudioCanplay,
    handleAudioError
  }
}
