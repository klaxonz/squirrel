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
          // 使用较保守的初始码率，避免起播阶段错误估计带宽导致瞬时卡顿
          initialBitrate: { video: 3000, audio: 192 },
          initialRepresentationRatio: 1,
          maxBitrate: { video: -1, audio: -1 },
          bandwidthSafetyFactor: 0.95,
          usePixelRatioInLimitBitrateByPortal: false
        },
        buffer: {
          stableBufferTime: 12,
          bufferTimeAtTopQuality: 20,
          bufferTimeAtTopQualityLongForm: 30,
          longFormContentDurationThreshold: 600,
          bufferToKeep: 12,
          bufferPruningInterval: 10,
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

    const qStr = String(quality || '').toLowerCase()
    const isAutoValue = qStr === 'auto' || qStr === '自动'

    // 自动档位或没有可用 index 时，交给 ABR
    if (!qualityInfo || isAutoValue || typeof qualityInfo.index !== 'number' || qualityInfo.index < 0) {
      console.log('[DASH] Switching to AUTO quality, enable ABR. quality=', quality)
      try {
        player.updateSettings({
          streaming: {
            abr: {
              autoSwitchBitrate: { video: true }
            }
          }
        })
      } catch (_) {}
      return
    }

    const targetIndex = qualityInfo.index
    console.log('[DASH] Switching quality to', quality, 'index=', targetIndex)

    try {
      player.updateSettings({
        streaming: {
          abr: {
            autoSwitchBitrate: { video: false }
          }
        }
      })
    } catch (_) {}

    try {
      if (typeof player.setQualityFor === 'function') {
        player.setQualityFor('video', targetIndex)
      } else if (typeof player.setRepresentationForTypeByIndex === 'function') {
        player.setRepresentationForTypeByIndex('video', targetIndex, true)
      }
      const currentIndex = typeof player.getQualityFor === 'function'
        ? player.getQualityFor('video')
        : null
      console.log('[DASH] After switch, current quality index =', currentIndex)
    } catch (e) {
      console.warn('[DASH] setQualityFor failed', e)
    }
  }

  return { dashRef, initializeDash, destroyDash, setQuality }
}

