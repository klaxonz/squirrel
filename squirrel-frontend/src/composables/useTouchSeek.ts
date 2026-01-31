import type { Ref } from 'vue'
import type { PlayerState } from '@/types/video-player'

type Refs = {
  videoRef: Ref<HTMLVideoElement | null>
}

type Setters = {
  setVideoTime: (time: number) => void
}

type UiControls = {
  showControls?: () => void
  scheduleHideControls?: (ms: number) => void
}

export default function useTouchSeek(
  playerState: PlayerState,
  refs: Refs,
  setters: Setters,
  uiControls: UiControls = {}
) {
  const { videoRef } = refs
  const { setVideoTime } = setters
  const { showControls = () => {}, scheduleHideControls = () => {} } = uiControls

  const touchStartTime = { value: 0 }

  const handleTouchStart = (e: TouchEvent) => {
    const touch = e.touches[0]
    touchStartTime.value = Date.now()

    playerState.ui.seeking.startX = touch.clientX
    playerState.ui.seeking.currentX = touch.clientX
    playerState.ui.volume.startY = touch.clientY
    playerState.ui.volume.startVolume = playerState.media.volume

    playerState.ui.seeking.active = false
    playerState.ui.volume.adjusting = false
  }

  const handleTouchMove = (e: TouchEvent) => {
    if (e.touches.length !== 1) return
    const touch = e.touches[0]
    const deltaX = Math.abs(touch.clientX - playerState.ui.seeking.startX)
    const deltaY = Math.abs(touch.clientY - playerState.ui.volume.startY)

    if (!playerState.ui.seeking.active && !playerState.ui.volume.adjusting) {
      if (deltaX > 5 || deltaY > 5) {
        if (deltaX > deltaY) {
          playerState.ui.seeking.active = true
          playerState.ui.seeking.wasPlaying = playerState.media.playing
          if (playerState.media.playing && videoRef.value) {
            videoRef.value.pause()
          }
        } else {
          playerState.ui.volume.adjusting = true
          playerState.ui.volume.showIndicator = true
        }
      }
    }

    if (playerState.ui.volume.adjusting) {
      e.preventDefault()
      const volumeChange = ((playerState.ui.volume.startY - touch.clientY) / 200) * 100
      const newVolume = Math.min(Math.max(playerState.ui.volume.startVolume + volumeChange, 0), 100)
      playerState.media.volume = newVolume
      return
    }

    if (playerState.ui.seeking.active) {
      e.preventDefault()
      const touchX = touch.clientX
      playerState.ui.seeking.currentX = touchX
      const diffX = touchX - playerState.ui.seeking.startX
      const absDiffX = Math.abs(diffX)
      if (absDiffX > 20) {
        playerState.ui.seeking.distance = diffX
        playerState.ui.seeking.direction = diffX > 0 ? 'forward' : 'backward'
        const baseSpeed = 2
        const maxSpeed = 30
        const acceleration = Math.pow(absDiffX / 30, 1.5)
        const seekSeconds = Math.min(baseSpeed * acceleration, maxSpeed)
        if (playerState.ui.seeking.direction === 'forward') {
          playerState.ui.seeking.seekTime = Math.min(playerState.media.currentTime + seekSeconds, playerState.media.duration)
        } else {
          playerState.ui.seeking.seekTime = Math.max(playerState.media.currentTime - seekSeconds, 0)
        }
        if (videoRef.value) {
          videoRef.value.currentTime = playerState.ui.seeking.seekTime
        }
      }
    }
  }

  const handleTouchEnd = () => {
    if (playerState.ui.volume.adjusting) {
      playerState.ui.volume.adjusting = false
      setTimeout(() => {
        playerState.ui.volume.showIndicator = false
      }, 1000)
      return
    }

    if (playerState.ui.seeking.active) {
      setVideoTime(playerState.ui.seeking.seekTime)
      playerState.ui.seeking.active = false
      playerState.ui.seeking.distance = 0
      playerState.ui.seeking.direction = null
      if (playerState.ui.seeking.wasPlaying && videoRef.value) {
        videoRef.value.play()
      }
      return
    }

    const isTap = Date.now() - touchStartTime.value < 200
    if (isTap) {
      showControls()
      scheduleHideControls(3000)
    }
  }

  return { handleTouchStart, handleTouchMove, handleTouchEnd }
}


