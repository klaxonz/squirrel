import { ref, computed } from 'vue'

export default function useVideoControls(playerState, videoCore) {
  // 播放速度选项
  const playbackRates = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2]
  
  // 质量选项
  const availableQualities = ref([
    { value: 'auto', label: '自动' },
    { value: '1080p', label: '1080p' },
    { value: '720p', label: '720p' },
    { value: '480p', label: '480p' },
    { value: '360p', label: '360p' }
  ])

  // 播放控制
  const togglePlay = () => {
    if (!videoCore.value?.videoElement) return

    if (playerState.media.playing) {
      // 暂停播放
      videoCore.value.videoElement.pause()
      if (videoCore.value.audioElement) {
        videoCore.value.audioElement.pause()
      }
      playerState.media.playing = false
    } else {
      // 开始播放
      if (playerState.network.firstInteraction) {
        playerState.network.firstInteraction = false
      }
      
      videoCore.value.videoElement.play().then(() => {
        playerState.media.playing = true
        if (videoCore.value.audioElement) {
          videoCore.value.audioElement.play().catch(err => {
            console.error('Failed to play audio:', err)
          })
        }
      }).catch(err => {
        console.error('Failed to play video:', err)
      })
    }
    
    // 显示播放状态指示器
    playerState.ui.showPlayIndicator = true
    setTimeout(() => {
      playerState.ui.showPlayIndicator = false
    }, 500)
  }

  const skipForward = () => {
    const newTime = Math.min(
      playerState.media.currentTime + 10, 
      playerState.media.duration
    )
    setVideoTime(newTime)
  }

  const skipBackward = () => {
    const newTime = Math.max(playerState.media.currentTime - 10, 0)
    setVideoTime(newTime)
  }

  const setVideoTime = (time) => {
    if (!videoCore.value?.videoElement) return
    
    videoCore.value.videoElement.currentTime = time
    if (videoCore.value.audioElement) {
      videoCore.value.audioElement.currentTime = time
    }
    playerState.media.currentTime = time
  }

  // 音量控制
  const toggleMute = () => {
    if (!videoCore.value?.videoElement) return
    
    const newMutedState = !videoCore.value.videoElement.muted
    videoCore.value.videoElement.muted = newMutedState
    
    if (videoCore.value.audioElement) {
      videoCore.value.audioElement.muted = newMutedState
    }
    
    playerState.media.muted = newMutedState
  }

  // 全屏控制
  const toggleFullscreen = async () => {
    const container = videoCore.value?.videoElement?.parentElement
    if (!container) return

    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen()
        playerState.ui.fullscreen = false
      } else {
        if (container.requestFullscreen) {
          await container.requestFullscreen()
        } else if (container.webkitRequestFullscreen) {
          await container.webkitRequestFullscreen()
        } else if (container.mozRequestFullScreen) {
          await container.mozRequestFullScreen()
        }
        playerState.ui.fullscreen = true
      }
    } catch (error) {
      console.error('Fullscreen error:', error)
    }
  }

  // 画中画控制
  const togglePictureInPicture = async () => {
    if (!document.pictureInPictureEnabled || !videoCore.value?.videoElement) return

    try {
      if (document.pictureInPictureElement) {
        await document.exitPictureInPicture()
        playerState.media.pictureInPicture = false
      } else {
        await videoCore.value.videoElement.requestPictureInPicture()
        playerState.media.pictureInPicture = true
      }
    } catch (error) {
      console.error('Picture-in-Picture error:', error)
    }
  }

  // 字幕控制
  const toggleSubtitles = () => {
    playerState.media.subtitlesEnabled = !playerState.media.subtitlesEnabled
    // 这里需要与字幕组合函数集成
  }

  // 播放速度控制
  const setPlaybackRate = (rate) => {
    playerState.media.playbackRate = rate
    
    if (videoCore.value?.videoElement) {
      videoCore.value.videoElement.playbackRate = rate
    }
    
    if (videoCore.value?.audioElement) {
      videoCore.value.audioElement.playbackRate = rate
    }
    
    playerState.ui.showPlaybackRateMenu = false
  }

  // 质量控制
  const setQuality = (quality) => {
    playerState.media.currentQuality = quality
    // 这里需要与HLS播放器集成
    playerState.ui.showSettingsMenu = false
    console.debug('Quality changed to:', quality)
  }

  // 字幕设置
  const setSubtitle = (subtitle) => {
    playerState.media.currentSubtitle = subtitle
    playerState.media.subtitlesEnabled = !!subtitle
    // 这里需要与字幕组合函数集成
    playerState.ui.showSettingsMenu = false
  }

  // 音量调节
  const adjustVolume = (delta) => {
    const newVolume = Math.min(Math.max(playerState.media.volume + delta, 0), 100)
    playerState.media.volume = newVolume
    
    // 显示音量指示器
    playerState.ui.volume.showIndicator = true
    setTimeout(() => {
      playerState.ui.volume.showIndicator = false
    }, 1000)
  }

  // 播放速度调节
  const adjustPlaybackRate = (delta) => {
    const currentRate = playerState.media.playbackRate
    const newRate = Math.min(Math.max(currentRate + delta, 0.25), 2)
    setPlaybackRate(newRate)
  }

  // 跳转到指定百分比位置
  const seekToPercentage = (percentage) => {
    const seekTime = (percentage / 100) * playerState.media.duration
    setVideoTime(seekTime)
  }

  // 剧场模式控制
  const toggleTheaterMode = () => {
    playerState.ui.theaterMode = !playerState.ui.theaterMode
  }

  return {
    // 配置
    availableQualities,
    playbackRates,
    
    // 播放控制
    togglePlay,
    skipForward,
    skipBackward,
    setVideoTime,
    
    // 音量控制
    toggleMute,
    adjustVolume,
    
    // 显示控制
    toggleFullscreen,
    toggleTheaterMode,
    togglePictureInPicture,
    
    // 字幕控制
    toggleSubtitles,
    setSubtitle,
    
    // 播放设置
    setPlaybackRate,
    adjustPlaybackRate,
    setQuality,
    
    // 导航
    seekToPercentage
  }
}
