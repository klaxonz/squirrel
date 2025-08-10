import Hls from 'hls.js';

export default function useHlsPlayer({
  playerState,
  videoRef,
  props,
  getOptimizedHlsConfig,
  onProgress,
  onError,
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

    const hlsConfig = getOptimizedHlsConfig();
    hlsRef.value = new Hls(hlsConfig);
    hlsRef.value.attachMedia(videoRef.value);

    hlsRef.value.on(Hls.Events.MEDIA_ATTACHED, () => {
      hlsRef.value.loadSource(props.video.stream_video_url);
    });

    hlsRef.value.on(Hls.Events.FRAG_BUFFERED, () => {
      onProgress?.();
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

    // 缓冲提示
    hlsRef.value.on(Hls.Events.BUFFER_APPENDING, () => {
      playerState.media.loading = true;
      playerState.media.loadingStage = 'buffering';
    });
    hlsRef.value.on(Hls.Events.BUFFER_APPENDED, () => {
      playerState.media.loading = false;
      playerState.media.loadingStage = 'ready';
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
    if (quality === 'auto') {
      hlsRef.value.currentLevel = -1;
      return;
    }
    const target = hlsRef.value.levels.findIndex(level =>
      level.height === parseInt(quality) || level.name === quality
    );
    if (target !== -1) hlsRef.value.currentLevel = target;
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


