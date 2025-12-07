import Hls from 'hls.js';

// store: Pinia player store
export default function useHlsPlayer({
  store,
  videoRef,
  props,
  getOptimizedHlsConfig,
  onProgress,
  onError,
  onQualitiesUpdate,
}) {
  const hlsRef = { value: null };
  const MAX_RECONNECT_ATTEMPTS = 3;
  const RECONNECT_INTERVAL = 3000;

  const initializeHls = () => {
    if (!props.video?.stream_video_url) return;
    if (!Hls.isSupported()) {
      if (videoRef.value?.canPlayType('application/vnd.apple.mpegurl')) {
        videoRef.value.src = props.video.stream_video_url;
      }
      return;
    }

    const hlsConfig = typeof getOptimizedHlsConfig === 'function' ? getOptimizedHlsConfig() : {};
    hlsRef.value = new Hls(hlsConfig);
    hlsRef.value.attachMedia(videoRef.value);

    hlsRef.value.on(Hls.Events.MEDIA_ATTACHED, () => {
      hlsRef.value.loadSource(props.video.stream_video_url);
    });

    // 当清单解析完成后，更新可用清晰度列表
    hlsRef.value.on(Hls.Events.MANIFEST_PARSED, () => {
      try {
        const levels = hlsRef.value.levels || []
        if (levels.length > 0) {
          // 构建清晰度选项列表
          const mapped = levels
            .map((level, index) => ({
              value: level.height ? `${level.height}p` : `level_${index}`,
              label: level.height ? `${level.height}p` : `Level ${index}`,
              height: level.height || 0,
              bandwidth: level.bitrate || 0,
              index: index
            }))
          
          // 去重并排序（高到低）
          const uniq = {}
          mapped.forEach(q => { uniq[q.value] = q })
          const qualities = Object.values(uniq)
          qualities.sort((a, b) => b.height - a.height)
          
          // 通知外部更新可用清晰度
          if (typeof onQualitiesUpdate === 'function') {
            onQualitiesUpdate(qualities)
          }
          
          // 如果已有用户选择的清晰度，则尊重该选择；否则交给 HLS 自己通过 ABR 决定
          const currentQuality = store?.currentQuality
          if (currentQuality) {
            setQuality(currentQuality)
          }
        }
      } catch (_) {}
    });

    hlsRef.value.on(Hls.Events.FRAG_BUFFERED, () => {
      onProgress?.();
    });

    // 片段已加载，报告带宽样本
    hlsRef.value.on(Hls.Events.FRAG_LOADED, (event, data) => {
      try {
        const stats = data?.stats || {};
        const loadedBytes = stats.loaded ?? 0;
        const tfirst = stats.tfirst ?? stats.trequest ?? stats.loading?.first ?? 0;
        const tload = stats.tload ?? stats.tend ?? stats.loading?.end ?? 0;
        const durationSec = Math.max(0.001, (tload - tfirst) / 1000);
        if (loadedBytes > 0 && durationSec > 0) {
          onProgress?.({ loaded: loadedBytes, durationSec });
        }
      } catch (e) {
        // ignore single sample errors
      }
    });

    hlsRef.value.on(Hls.Events.ERROR, (event, data) => {
      if (data.fatal) {
        switch (data.type) {
          case Hls.ErrorTypes.NETWORK_ERROR:
            if (store.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
              store.incrementReconnectAttempts();
              hlsRef.value.startLoad();
            } else {
              onError?.({ type: 'network', message: 'Network connection failed' });
            }
            break;
          case Hls.ErrorTypes.MEDIA_ERROR:
            hlsRef.value.recoverMediaError();
            break;
          default:
            if (store.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
              store.incrementReconnectAttempts();
              reinitializeHls();
            } else {
              onError?.({ type: 'fatal', message: 'Cannot play video' });
            }
            break;
        }
      }
    });
  };

  const reinitializeHls = () => {
    if (hlsRef.value) {
      hlsRef.value.destroy();
    }
    initializeHls();
  };

  const destroyHls = () => {
    if (hlsRef.value) {
      hlsRef.value.destroy();
      hlsRef.value = null;
    }
  };

  const setQuality = (quality) => {
    if (!hlsRef.value) return;
    
    console.log('[HLS] Switching quality to:', quality);
    
    // 1. 优先使用后端提供的index（一一对应，无需匹配）
    const qualityInfo = (props?.video?.qualities || []).find(q => q.value === quality)
    if (qualityInfo && typeof qualityInfo.index === 'number' && qualityInfo.index >= 0) {
      console.log('[HLS] Using backend-provided index:', qualityInfo.index)
      hlsRef.value.currentLevel = qualityInfo.index
      console.log('[HLS] ✓ Quality switched to level:', qualityInfo.index)
      return
    }

    // 2. 降级方案：手动匹配（适用于旧版本后端或其他情况）
    console.warn('[HLS] No index provided, falling back to manual matching')
    const levels = hlsRef.value.levels || []
    if (!levels.length) {
      console.warn('[HLS] No levels available')
      return
    }

    const qualityStr = String(quality)
    const targetHeight = parseInt(qualityStr.replace(/[^0-9]/g, ''), 10)
    
    let targetLevel = levels.findIndex(level => 
      level.height === targetHeight || 
      level.name === qualityStr || 
      String(level.height) + 'p' === qualityStr
    )
    
    if (targetLevel === -1) {
      targetLevel = levels.reduce((closest, level, i) => {
        if (level.height <= targetHeight && (closest === -1 || level.height > levels[closest].height)) {
          return i
        }
        return closest
      }, -1)
      
      if (targetLevel === -1) {
        targetLevel = levels.reduce((max, level, i) => 
          level.height > levels[max].height ? i : max, 0
        )
      }
    }
    
    if (targetLevel >= 0) {
      hlsRef.value.currentLevel = targetLevel
      console.log('[HLS] ✓ Quality switched to fallback level:', targetLevel)
    } else {
      console.warn('[HLS] ✗ No valid level found for:', quality)
    }
  };

  return {
    hlsRef,
    initializeHls,
    reinitializeHls,
    destroyHls,
    setQuality,
    MAX_RECONNECT_ATTEMPTS,
    RECONNECT_INTERVAL,
  };
}


