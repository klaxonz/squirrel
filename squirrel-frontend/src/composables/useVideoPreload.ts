import { reactive } from 'vue'

export default function useVideoPreload() {
  type VideoId = string | number

  type PreloadState = {
    isPreloading: boolean
    preloadProgress: number
    networkType: string
    shouldPreload: boolean
    preloadedVideos: Set<VideoId>
    preloadQueue: unknown[]
  }

  const preloadState = reactive<PreloadState>({
    isPreloading: false,
    preloadProgress: 0,
    networkType: 'unknown',
    shouldPreload: true,
    preloadedVideos: new Set(),
    preloadQueue: []
  })

  const getOptimizedHlsConfig = () => {
    return {
      maxBufferLength: 45,
      maxMaxBufferLength: 90,
      maxBufferSize: 80 * 1000 * 1000,
      maxBufferHole: 0.5,
      enableWorker: true,
      enableSoftwareAES: true,
      lowLatencyMode: false,
      backBufferLength: 60,
      
      abrBandWidthFactor: 0.7,
      abrBandWidthUpFactor: 0.5,
      abrEwmaFastLive: 3.0,
      abrEwmaSlowLive: 9.0,

      manifestLoadingTimeOut: 30000,
      manifestLoadingMaxRetry: 3,
      manifestLoadingRetryDelay: 1000,
    
      levelLoadingTimeOut: 30000,
      levelLoadingMaxRetry: 3,
      levelLoadingRetryDelay: 1000,
    
      fragLoadingTimeOut: 30000,
      fragLoadingMaxRetry: 3,
      fragLoadingRetryDelay: 1000,

      xhrSetup: function (xhr: any) {
        xhr.timeout = 30000
      }
    }
  }

  return {
    preloadState,
    getOptimizedHlsConfig,
  }
}
