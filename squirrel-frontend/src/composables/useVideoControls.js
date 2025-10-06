import { ref, watch, isRef } from 'vue'

// videoParam: reactive video object (e.g., props.video)
export default function useVideoControls(playerState, videoCore, videoParam) {

  const getVideoParam = () => (isRef(videoParam) ? videoParam.value : videoParam)
  
  const playbackRates = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2]
  const availableQualities = ref([])

  const DEFAULT_FALLBACK = [
    { value: '1080p', label: '1080p' },
    { value: '720p', label: '720p' },
    { value: '480p', label: '480p' },
    { value: '360p', label: '360p' }
  ]

  // 根据视频对象的 qualities 动态更新可选清晰度
  const applyQualitiesFromVideo = (v) => {
    try {
      const list = Array.isArray(v?.qualities) ? v.qualities : []
      if (list.length > 0) {
        // 规范化数据结构
        const mapped = list.map(q => ({
          value: q.value || (q.height ? `${q.height}p` : `${q.bandwidth || 0}k`),
          label: q.label || (q.height ? `${q.height}p` : `${q.bandwidth || 0}k`),
          height: q.height || undefined,
          bandwidth: q.bandwidth || undefined,
          id: q.id || undefined
        }))
        // 去重并排序（高到低）
        const uniq = {}
        mapped.forEach(q => { uniq[q.value] = q })
        const arr = Object.values(uniq)
        arr.sort((a, b) => (b.height || 0) - (a.height || 0))
        availableQualities.value = arr
        try {
          if (!playerState?.media?.currentQuality) {
            const highestQuality = arr[0]
            if (highestQuality) playerState.media.currentQuality = highestQuality.value
          }
        } catch (_) {}
      } else {
        availableQualities.value = DEFAULT_FALLBACK
      }
    } catch (_) {
      availableQualities.value = DEFAULT_FALLBACK
    }
  }


  watch(() => {
    const currentVideo = getVideoParam()
    return currentVideo ? [currentVideo.id, currentVideo?.qualities] : null
  }, () => {
    applyQualitiesFromVideo(getVideoParam())
  }, { deep: false, immediate: true })

  const updateAvailableQualities = (qualities) => {
    if (Array.isArray(qualities) && qualities.length > 0) {
      availableQualities.value = qualities
      const currentQuality = playerState?.media?.currentQuality
      const isCurrentQualityValid = qualities.some(q => q.value === currentQuality)
      
      if (!currentQuality || !isCurrentQualityValid) {
        const highestQuality = qualities[0]
        if (highestQuality) {
          playerState.media.currentQuality = highestQuality.value
        }
      }
    }
  }

  // 播放控制
  const togglePlay = () => {
    if (!videoCore.value?.videoElement) return

    if (playerState.media.playing) {
      // 暂停播放 - 状态由事件处理器更新
      videoCore.value.videoElement.pause()
      if (videoCore.value.audioElement) {
        videoCore.value.audioElement.pause()
      }
    } else {
      // 开始播放 - 状态由事件处理器更新
      if (playerState.network.firstInteraction) {
        playerState.network.firstInteraction = false
      }

      videoCore.value.videoElement.play().then(() => {
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

    // 只修改状态，让watch处理DOM更新
    playerState.media.muted = !playerState.media.muted
  }

  // 全屏控制
  const toggleFullscreen = async () => {
    // 找到包含整个视频播放器的容器（包括控件）
    const videoElement = videoCore.value?.videoElement
    if (!videoElement) return

    // 向上查找到 video-player-container
    let container = videoElement.parentElement
    while (container && !container.classList.contains('video-player-container')) {
      container = container.parentElement
    }

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
    playerState.ui.showQualityMenu = false
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

  // 键盘帮助控制
  const toggleKeyboardHelp = () => {
    playerState.ui.showKeyboardHelp = !playerState.ui.showKeyboardHelp
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
    toggleKeyboardHelp,

    // 字幕控制
    toggleSubtitles,
    setSubtitle,

    // 播放设置
    setPlaybackRate,
    adjustPlaybackRate,
    setQuality,

    // 导航
    seekToPercentage,

    // 清晰度更新
    updateAvailableQualities
  }
}
