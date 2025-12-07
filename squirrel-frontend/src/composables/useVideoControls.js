import { ref, watch, isRef } from 'vue'

// store: Pinia player store
// videoCore: ref to video core component
// videoParam: reactive video object (e.g., props.video)
export default function useVideoControls(store, videoCore, videoParam) {

  const getVideoParam = () => (isRef(videoParam) ? videoParam.value : videoParam)
  
  const playbackRates = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2]
  const availableQualities = ref([])

  const DEFAULT_FALLBACK = [
    { value: '1080p', label: '1080p' },
    { value: '720p', label: '720p' },
    { value: '480p', label: '480p' },
    { value: '360p', label: '360p' }
  ]

  const applyQualitiesFromVideo = (v) => {
    try {
      const list = Array.isArray(v?.qualities) ? v.qualities : []
      if (list.length > 0) {
        const mapped = list.map(q => ({
          value: q.value || (q.height ? `${q.height}p` : `${q.bandwidth || 0}k`),
          label: q.label || (q.height ? `${q.height}p` : `${q.bandwidth || 0}k`),
          height: q.height || undefined,
          bandwidth: q.bandwidth || undefined,
          id: q.id || undefined
        }))
        const uniq = {}
        mapped.forEach(q => { uniq[q.value] = q })
        const arr = Object.values(uniq)
        arr.sort((a, b) => (b.height || 0) - (a.height || 0))
        availableQualities.value = arr
        try {
          if (!store.currentQuality) {
            const highestQuality = arr[0]
            if (highestQuality) store.setCurrentQuality(highestQuality.value)
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

  const togglePlay = () => {
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
        if (videoCore.value.audioElement) {
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

  const skipForward = () => {
    const newTime = Math.min(store.currentTime + 10, store.duration)
    setVideoTime(newTime)
  }

  const skipBackward = () => {
    const newTime = Math.max(store.currentTime - 10, 0)
    setVideoTime(newTime)
  }

  const setVideoTime = (time) => {
    if (!videoCore.value?.videoElement) return

    videoCore.value.videoElement.currentTime = time
    if (videoCore.value.audioElement) {
      videoCore.value.audioElement.currentTime = time
    }
    store.setCurrentTime(time)
  }

  const toggleMute = () => {
    if (!videoCore.value?.videoElement) return
    store.toggleMute()
  }

  const toggleFullscreen = async () => {
    const videoElement = videoCore.value?.videoElement
    if (!videoElement) return

    let container = videoElement.parentElement
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
        } else if (container.webkitRequestFullscreen) {
          await container.webkitRequestFullscreen()
        } else if (container.mozRequestFullScreen) {
          await container.mozRequestFullScreen()
        }
        store.setFullscreen(true)
      }
    } catch (error) {
      console.error('Fullscreen error:', error)
    }
  }

  const togglePictureInPicture = async () => {
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

  const toggleSubtitles = () => {
    store.toggleSubtitles()
  }

  const setPlaybackRate = (rate) => {
    store.setPlaybackRate(rate)

    if (videoCore.value?.videoElement) {
      videoCore.value.videoElement.playbackRate = rate
    }

    if (videoCore.value?.audioElement) {
      videoCore.value.audioElement.playbackRate = rate
    }

    store.showPlaybackRateMenu = false
  }

  const setQuality = (quality) => {
    store.setCurrentQuality(quality)
    store.showQualityMenu = false
    store.showSettingsMenu = false
    console.debug('Quality changed to:', quality)
  }

  const setSubtitle = (subtitle) => {
    store.setCurrentSubtitle(subtitle)
    store.setSubtitlesEnabled(!!subtitle)
    store.showSettingsMenu = false
  }

  const adjustVolume = (delta) => {
    const newVolume = Math.min(Math.max(store.volume + delta, 0), 100)
    store.setVolume(newVolume)

    store.updateVolumeState({ showIndicator: true })
    setTimeout(() => {
      store.updateVolumeState({ showIndicator: false })
    }, 1000)
  }

  const adjustPlaybackRate = (delta) => {
    const currentRate = store.playbackRate
    const newRate = Math.min(Math.max(currentRate + delta, 0.25), 2)
    setPlaybackRate(newRate)
  }

  const seekToPercentage = (percentage) => {
    const seekTime = (percentage / 100) * store.duration
    setVideoTime(seekTime)
  }

  const toggleTheaterMode = () => {
    store.toggleTheaterMode()
  }

  const toggleKeyboardHelp = () => {
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
