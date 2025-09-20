import { reactive } from 'vue';

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


  // 获取优化的HLS配置
  const getOptimizedHlsConfig = () => {
    return {
      maxBufferLength: 30,
      maxMaxBufferLength: 60,
      enableWorker: true,
      enableSoftwareAES: true,
      progressive: true,
      fragLoadingTimeOut: 45000,
      manifestLoadingTimeOut: 20000,
      levelLoadingTimeOut: 20000,
      abrBandWidthFactor: 0.7,
      abrBandWidthUpFactor: 0.5,

      maxBufferLength: 30,

      manifestLoadingTimeOut: 60000,
      manifestLoadingMaxRetry: 3,
      manifestLoadingRetryDelay: 1000,
    
      levelLoadingTimeOut: 60000,
      levelLoadingMaxRetry: 3,
      levelLoadingRetryDelay: 1000,
    
      fragLoadingTimeOut: 60000,
      fragLoadingMaxRetry: 3,
      fragLoadingRetryDelay: 1000,

      xhrSetup: function(xhr, url) {
        xhr.timeout = 20000;
      }
    };
  };


  return {
    preloadState,
    getOptimizedHlsConfig,
  };
}
