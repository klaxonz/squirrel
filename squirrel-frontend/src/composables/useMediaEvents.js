/**
 * 处理视频/音频元素的事件
 * - 视频加载状态管理
 * - 缓冲进度更新
 * - 音视频同步
 */
export default function useMediaEvents(playerState, videoElement, audioElement, isHlsStream, clearError) {
  // 视频事件处理
  const handleVideoSeeking = () => {
    playerState.media.loading = true
    playerState.media.loadingStage = 'buffering'
    playerState.media.seeking.video = true
    // 在非HLS模式下，视频开始seek时暂停独立音频
    if (!isHlsStream && audioElement?.value && !audioElement.value.paused) {
      try { audioElement.value.pause() } catch (e) {}
    }
  }

  const handleVideoSeeked = () => {
    playerState.media.loading = false
    playerState.media.loadingStage = 'ready'
    playerState.media.seeking.video = false
  }

  const handleVideoCanplay = () => {
    if (videoElement?.value) {
      playerState.media.duration = videoElement.value.duration
    }
    playerState.media.loading = false
    playerState.media.loadingStage = 'ready'
    playerState.media.canPlay.video = true
    playerState.media.seeking.video = false
    // 一旦可播放，隐藏错误覆盖层
    if (clearError) clearError()
  }

  const handleVideoCanplaythrough = () => {
    playerState.media.loading = false
    playerState.media.loadingStage = 'ready'
    // 缓冲结束后，如需要，恢复音频播放
    if (!isHlsStream && audioElement?.value && playerState.media.playing) {
      try { audioElement.value.play().catch(() => {}) } catch (e) {}
    }
  }

  const handleVideoWaiting = () => {
    playerState.media.loading = true
    playerState.media.loadingStage = 'buffering'
    // 缓冲时暂停独立音频
    if (!isHlsStream && audioElement?.value && !audioElement.value.paused) {
      try { audioElement.value.pause() } catch (e) {}
    }
  }

  const handleVideoProgress = () => {
    if (videoElement?.value && videoElement.value.buffered.length > 0) {
      const buffered = videoElement.value.buffered
      let bufferedEnd = 0

      for (let i = 0; i < buffered.length; i++) {
        if (
          buffered.start(i) <= playerState.media.currentTime &&
          buffered.end(i) >= playerState.media.currentTime
        ) {
          bufferedEnd = buffered.end(i)
          break
        }
        if (buffered.end(i) > bufferedEnd) {
          bufferedEnd = buffered.end(i)
        }
      }

      playerState.media.bufferedProgress =
        (bufferedEnd / playerState.media.duration) * 100
    }
  }

  const handleVideoLoadstart = () => {
    playerState.media.loading = true
    playerState.media.loadingStage = 'fetching'
  }

  const handleVideoLoadedmetadata = () => {
    playerState.media.loading = true
    playerState.media.loadingStage = playerState.media.hasStartedPlayback
      ? 'buffering'
      : 'fetching'
    if (videoElement?.value) {
      playerState.media.duration = videoElement.value.duration
    }
  }

  const handleVideoLoadeddata = () => {
    playerState.media.loadingStage = 'ready'
    playerState.media.loading = false
  }

  const handleVideoStalled = () => {
    playerState.media.loading = true
    playerState.media.loadingStage = 'buffering'
  }

  const handleVideoSuspend = () => {
    // 网络空闲时暂停下载
  }

  const handleVideoAbort = () => {
    playerState.media.loading = false
  }

  // 音频事件处理
  const handleAudioSeeking = () => {
    playerState.media.seeking.audio = true
  }

  const handleAudioCanplay = () => {
    playerState.media.canPlay.audio = true
    playerState.media.seeking.audio = false
  }

  const handleAudioError = () => {
    console.error('Audio playback error')
  }

  return {
    // 视频事件
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
    // 音频事件
    handleAudioSeeking,
    handleAudioCanplay,
    handleAudioError
  }
}
