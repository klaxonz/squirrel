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
    };
  };

  // 监听网络变化
  const setupNetworkListener = () => {};

  return {
    preloadState,
    getOptimizedHlsConfig,
    setupNetworkListener
  };
}
