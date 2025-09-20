import Hls from 'hls.js';

export default function useHlsPlayer({
  playerState,
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

    // 当清单解析完成后，更新可用清晰度列表并设置默认为最高清晰度
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
          
          // 自动选择最高清晰度
          const currentQuality = playerState?.media?.currentQuality
          if (!currentQuality) {
            const highestQuality = qualities[0]
            if (highestQuality) {
              playerState.media.currentQuality = highestQuality.value
              setQuality(highestQuality.value)
            }
          } else {
            // 复用 setQuality 内的回退逻辑
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
            if (playerState.network.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
              playerState.network.reconnectAttempts++;
              hlsRef.value.startLoad();
            } else {
              onError?.({ type: 'network', message: 'Network connection failed' });
            }
            break;
          case Hls.ErrorTypes.MEDIA_ERROR:
            hlsRef.value.recoverMediaError();
            break;
          default:
            if (playerState.network.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
              playerState.network.reconnectAttempts++;
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
    playerState.media.currentQuality = quality;
    if (!hlsRef.value) return;
    
    const levels = hlsRef.value.levels || []
    let target = levels.findIndex(level =>
      level.height === parseInt(quality) || level.name === quality || (String(level.height) + 'p' === String(quality))
    );
    if (target === -1 && levels.length) {
      // 回退：选择最高可用清晰度
      let maxH = -1, maxI = 0
      for (let i = 0; i < levels.length; i++) {
        const h = levels[i]?.height || 0
        if (h > maxH) { maxH = h; maxI = i }
      }
      target = maxI
    }
    hlsRef.value.currentLevel = target;
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


