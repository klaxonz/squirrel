import { ref, reactive } from 'vue';

export default function useVideoPreload() {
  // 预加载状态
  const preloadState = reactive({
    isPreloading: false,
    preloadProgress: 0,
    networkType: 'unknown',
    shouldPreload: true,
    preloadedVideos: new Set(),
    preloadQueue: []
  });

  // 检测网络状况
  const detectNetworkCondition = () => {
    const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    
    if (connection) {
      preloadState.networkType = connection.effectiveType || 'unknown';
      
      // 根据网络类型和用户偏好决定预加载策略
      const saveData = connection.saveData;
      const effectiveType = connection.effectiveType;
      
      if (saveData) {
        preloadState.shouldPreload = false;
        return 'save-data';
      }
      
      switch (effectiveType) {
        case 'slow-2g':
        case '2g':
          preloadState.shouldPreload = false;
          return 'slow';
        case '3g':
          preloadState.shouldPreload = true;
          return 'medium';
        case '4g':
        default:
          preloadState.shouldPreload = true;
          return 'fast';
      }
    }
    
    // 默认假设中等网络
    preloadState.shouldPreload = true;
    return 'medium';
  };

  // 智能预加载策略
  const getPreloadStrategy = (networkCondition) => {
    const strategies = {
      'save-data': {
        preload: 'none',
        bufferSize: 5,
        quality: 'low'
      },
      'slow': {
        preload: 'metadata',
        bufferSize: 10,
        quality: 'low'
      },
      'medium': {
        preload: 'metadata',
        bufferSize: 30,
        quality: 'medium'
      },
      'fast': {
        preload: 'auto',
        bufferSize: 60,
        quality: 'high'
      }
    };
    
    return strategies[networkCondition] || strategies['medium'];
  };

  // 预加载视频
  const preloadVideo = async (videoElement, videoUrl, options = {}) => {
    if (!preloadState.shouldPreload || preloadState.preloadedVideos.has(videoUrl)) {
      return false;
    }

    const networkCondition = detectNetworkCondition();
    const strategy = getPreloadStrategy(networkCondition);
    
    try {
      preloadState.isPreloading = true;
      preloadState.preloadProgress = 0;

      // 设置预加载属性
      videoElement.preload = strategy.preload;
      
      if (strategy.preload === 'auto') {
        // 创建一个临时的video元素进行预加载
        const tempVideo = document.createElement('video');
        tempVideo.src = videoUrl;
        tempVideo.preload = 'auto';
        tempVideo.muted = true; // 静音预加载
        
        // 监听预加载进度
        tempVideo.addEventListener('progress', () => {
          if (tempVideo.buffered.length > 0) {
            const buffered = tempVideo.buffered.end(0);
            const duration = tempVideo.duration || 1;
            preloadState.preloadProgress = (buffered / duration) * 100;
          }
        });

        // 预加载完成
        tempVideo.addEventListener('canplaythrough', () => {
          preloadState.preloadedVideos.add(videoUrl);
          preloadState.isPreloading = false;
          preloadState.preloadProgress = 100;
          
          // 清理临时元素
          tempVideo.remove();
        });

        // 开始预加载
        tempVideo.load();
        
        // 预加载前几秒内容
        setTimeout(() => {
          if (tempVideo.readyState >= 2) {
            tempVideo.currentTime = Math.min(strategy.bufferSize, tempVideo.duration || 30);
          }
        }, 1000);
      }

      return true;
    } catch (error) {
      console.warn('Video preload failed:', error);
      preloadState.isPreloading = false;
      return false;
    }
  };

  // 批量预加载
  const batchPreload = async (videos, maxConcurrent = 2) => {
    if (!preloadState.shouldPreload) return;

    const networkCondition = detectNetworkCondition();
    if (networkCondition === 'slow' || networkCondition === 'save-data') {
      return; // 慢网络不进行批量预加载
    }

    const queue = videos.slice(0, 5); // 最多预加载5个视频
    const concurrent = Math.min(maxConcurrent, queue.length);
    
    for (let i = 0; i < concurrent; i++) {
      const video = queue[i];
      if (video?.stream_video_url) {
        setTimeout(() => {
          const tempElement = document.createElement('video');
          preloadVideo(tempElement, video.stream_video_url);
        }, i * 2000); // 错开预加载时间
      }
    }
  };

  // 清理预加载缓存
  const clearPreloadCache = () => {
    preloadState.preloadedVideos.clear();
    preloadState.preloadQueue = [];
    preloadState.preloadProgress = 0;
  };

  // 获取优化的HLS配置
  const getOptimizedHlsConfig = () => {
    const networkCondition = detectNetworkCondition();
    const strategy = getPreloadStrategy(networkCondition);
    
    const baseConfig = {
      maxBufferLength: strategy.bufferSize,
      maxMaxBufferLength: strategy.bufferSize * 2,
      enableWorker: true,
      enableSoftwareAES: true,
      progressive: true,
      // 增加超时配置以避免10秒超时问题
      fragLoadingTimeOut: 60000,        // 片段加载超时：60秒
      manifestLoadingTimeOut: 30000,    // 清单加载超时：30秒
      levelLoadingTimeOut: 30000,       // 级别加载超时：30秒
    };

    // 根据网络状况调整配置
    switch (networkCondition) {
      case 'slow':
        return {
          ...baseConfig,
          maxBufferLength: 10,
          maxMaxBufferLength: 20,
          abrBandWidthFactor: 0.5,
          abrBandWidthUpFactor: 0.3,
          fragLoadingTimeOut: 30000,
          manifestLoadingTimeOut: 15000,
        };
      case 'medium':
        return {
          ...baseConfig,
          maxBufferLength: 30,
          maxMaxBufferLength: 60,
          abrBandWidthFactor: 0.7,
          abrBandWidthUpFactor: 0.5,
          fragLoadingTimeOut: 45000,        // 中等网络：45秒
          manifestLoadingTimeOut: 20000,    // 清单加载：20秒
          levelLoadingTimeOut: 20000,       // 级别加载：20秒
        };
      case 'fast':
        return {
          ...baseConfig,
          maxBufferLength: 60,
          maxMaxBufferLength: 120,
          abrBandWidthFactor: 0.8,
          abrBandWidthUpFactor: 0.6,
          startFragPrefetch: true,
          testBandwidth: true,
          fragLoadingTimeOut: 30000,        // 快速网络：30秒
          manifestLoadingTimeOut: 15000,    // 清单加载：15秒
          levelLoadingTimeOut: 15000,       // 级别加载：15秒
        };
      default:
        return baseConfig;
    }
  };

  // 监听网络变化
  const setupNetworkListener = () => {
    const connection = navigator.connection;
    if (connection) {
      connection.addEventListener('change', () => {
        const newCondition = detectNetworkCondition();
        console.debug('Network condition changed to:', newCondition);
        
        // 网络变慢时清理预加载缓存
        if (newCondition === 'slow' || newCondition === 'save-data') {
          clearPreloadCache();
        }
      });
    }
  };

  return {
    preloadState,
    detectNetworkCondition,
    getPreloadStrategy,
    preloadVideo,
    batchPreload,
    clearPreloadCache,
    getOptimizedHlsConfig,
    setupNetworkListener
  };
}
