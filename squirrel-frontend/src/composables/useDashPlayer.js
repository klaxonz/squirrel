import dashjs from 'dashjs'

export default function useDashPlayer({ playerState, videoRef, props, onProgress, onError, onQualitiesUpdate }) {
  const dashRef = { value: null }

  const initializeDash = () => {
    const mpdUrl = props.video?.mpd_url || props.video?.stream_video_url
    const resolvedMpdUrl = (() => { try { return new URL(mpdUrl, window.location.origin).toString() } catch (_) { return mpdUrl } })()
    
    console.log('[DASH] initializeDash called', {
      mpdUrl,
      resolvedMpdUrl,
      hasVideoRef: !!videoRef.value,
      hasPreviousDashInstance: !!dashRef.value,
      stackTrace: new Error().stack
    })
    
    if (!resolvedMpdUrl) { console.warn('[Debug] 4.X No MPD URL provided to dash'); return }
    if (!videoRef.value) { console.warn('[Debug] 4.X videoRef is not ready, skip init'); return }

    // Destroy previous instance
    if (dashRef.value) {
      console.log('[DASH] Destroying previous dash.js instance')
      try { dashRef.value.reset() } catch (_) {}
      dashRef.value = null
    }

    const player = dashjs.MediaPlayer().create()
    
    player.updateSettings({
      streaming: {
        abr: {
          autoSwitchBitrate: { video: false, audio: false },
          initialBitrate: { video: 50000, audio: 320 },
          initialRepresentationRatio: 1,
          limitBitrateByPortal: true,
          maxBitrate: { video: -1, audio: -1 },
          bandwidthSafetyFactor: 0.95,
          maxRepresentationRatio: 1,
          fetchThroughputCalculationMode: 'manual',
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
        retryAttempts: {
          MPD: 1,
          XLinkExpansion: 1,
          MediaSegment: 3,
          InitializationSegment: 2,
          BitstreamSwitchingSegment: 2,
          IndexSegment: 2,
          FragmentInfoSegment: 2,
          license: 1,
          other: 1
        },
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

    // 1) 尝试按 itag 精确切换（通过 dash.js tracks）
    const qStr = String(quality)
    if (/^\d+$/.test(qStr) && typeof player.getTracksFor === 'function') {
      try {
        const tracks = player.getTracksFor('video') || []
        let targetTrack = null
        for (const t of tracks) {
          const tid = String(t?.id ?? t?.Id ?? t?.representationId ?? '')
          if (tid && tid === qStr) { targetTrack = t; break }
        }
        if (targetTrack) {
          const qi = targetTrack.qualityIndex ?? targetTrack.quality ?? targetTrack.index
          if (Number.isInteger(qi)) {
            player.updateSettings({ streaming: { abr: { autoSwitchBitrate: { video: false } } } })
            player.setQualityFor('video', qi)
            return
          }
        }
      } catch (_) {}
    }

    // 2) 退化为按高度匹配（兼容无 track id 暴露的情况）
    const list = player.getBitrateInfoListFor('video') || []

    // map itag -> height from props.video.qualities
    let targetHeight = NaN
    if (/^\d+$/.test(qStr)) {
      const fromQualities = (props?.video?.qualities || []).find(q => String(q.id) === qStr)
      if (fromQualities && fromQualities.height) targetHeight = parseInt(fromQualities.height, 10)
    }
    // fallback: parse like '1080p'
    if (!Number.isFinite(targetHeight)) {
      targetHeight = parseInt(qStr.replace(/[^0-9]/g, ''), 10)
    }

    let targetIndex = -1
    for (let i = 0; i < list.length; i++) {
      const h = list[i]?.height || 0
      if (h === targetHeight) { targetIndex = i; break }
    }
    if (targetIndex === -1 && list.length && Number.isFinite(targetHeight)) {
      // fallback to closest lower height
      let closest = null
      for (let i = 0; i < list.length; i++) {
        const h = list[i]?.height || 0
        if (h <= targetHeight && (!closest || h > closest.h)) closest = { i, h }
      }
      if (closest) targetIndex = closest.i
    }
    if (targetIndex >= 0) {
      player.updateSettings({ streaming: { abr: { autoSwitchBitrate: { video: false } } } })
      player.setQualityFor('video', targetIndex)
    }
  }

  return { dashRef, initializeDash, destroyDash, setQuality }
}

