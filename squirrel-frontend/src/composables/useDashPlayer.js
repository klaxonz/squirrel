import dashjs from 'dashjs'

export default function useDashPlayer({ playerState, videoRef, props, onProgress, onError}) {
  const dashRef = { value: null }

  const initializeDash = () => {
    const mpdUrl = props.video?.mpd_url || props.video?.stream_video_url
    const resolvedMpdUrl = (() => { try { return new URL(mpdUrl, window.location.origin).toString() } catch (_) { return mpdUrl } })()
    
    if (dashRef.value) {
      try { dashRef.value.reset() } catch (_) {}
      dashRef.value = null
    }

    const player = dashjs.MediaPlayer().create()
    
    player.updateSettings({
      streaming: {
        abr: {
          initialBitrate: { video: 50000, audio: 320 },
          initialRepresentationRatio: 1,
          maxBitrate: { video: -1, audio: -1 },
          bandwidthSafetyFactor: 0.95,
          usePixelRatioInLimitBitrateByPortal: false
        },
        buffer: {
          stableBufferTime: 40,
          bufferTimeAtTopQuality: 60,
          bufferTimeAtTopQualityLongForm: 90,
          longFormContentDurationThreshold: 600,
          bufferToKeep: 30,
          bufferPruningInterval: 30,
          fastSwitchEnabled: true
        },
        manifestRequestTimeout: 60000,
      }
    })

    player.on('error', (e) => {
      const fatal = e?.error === 'capability' || e?.event?.type === 'critical'
      const err = { type: fatal ? 'fatal' : 'media', message: e?.event?.message || 'dash error', code: e?.event?.id }
      onError?.(err)
    })

    player.on('bufferingStarted', () => {
      playerState.media.loading = true
      playerState.media.loadingStage = 'buffering'
    })
    player.on('bufferingCompleted', () => {
      playerState.media.loading = false
      playerState.media.loadingStage = 'ready'
    })

    player.on('fragmentLoadingCompleted', (data) => {
      try {
        const loaded = data?.request?.bytesLoaded || 0
        const t0 = data?.request?.requestStartDate?.getTime?.() || 0
        const t1 = data?.request?.requestEndDate?.getTime?.() || 0
        const durationSec = Math.max(0.001, (t1 - t0) / 1000)
        if (loaded > 0 && durationSec > 0) onProgress?.({ loaded, durationSec })
      } catch (_) {}
    })

    player.initialize(videoRef.value, resolvedMpdUrl, !!props.playerState?.media?.autoplay)

    dashRef.value = player
  }

  const destroyDash = () => {
    if (dashRef.value) {
      try { dashRef.value.reset() } catch (_) {}
      dashRef.value = null
    }
  }

  const setQuality = (quality) => {
    if (!dashRef.value) return
    const player = dashRef.value

    const qualityInfo = (props?.video?.qualities || []).find(q => q.value === quality)
    if (qualityInfo && typeof qualityInfo.index === 'number' && qualityInfo.index >= 0) {
      player.setQualityFor('video', qualityInfo.index, true)
    }
  }

  return { dashRef, initializeDash, destroyDash, setQuality }
}

