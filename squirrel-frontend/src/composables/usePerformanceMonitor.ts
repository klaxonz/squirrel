import type { Ref } from 'vue'

type HlsConfigLike = Record<string, any>
type HlsLike = { config?: HlsConfigLike }

type PerformanceState = {
  bandwidth: { samples: number[]; average: number; current: number }
  memory: { used: number; peak: number; lastCleanup: number }
  loading: { startTime: number; duration: number; bytesLoaded: number }
}

type Options = {
  hlsRef?: Ref<HlsLike | null>
  videoRef?: Ref<HTMLVideoElement | null>
  externalPerformanceState?: PerformanceState
}

export default function usePerformanceMonitor({ hlsRef, videoRef, externalPerformanceState }: Options) {
  const MEMORY_CLEANUP_INTERVAL = 30000
  const BANDWIDTH_SAMPLE_SIZE = 5

  const performanceState: PerformanceState =
    externalPerformanceState || {
      bandwidth: { samples: [], average: 0, current: 0 },
      memory: { used: 0, peak: 0, lastCleanup: 0 },
      loading: { startTime: 0, duration: 0, bytesLoaded: 0 },
    }

  const updateBandwidth = (bytesLoaded: number, duration: number) => {
    if (duration <= 0) return
    const bandwidth = (bytesLoaded * 8) / duration
    performanceState.bandwidth.current = bandwidth

    performanceState.bandwidth.samples.push(bandwidth)
    if (performanceState.bandwidth.samples.length > BANDWIDTH_SAMPLE_SIZE) {
      performanceState.bandwidth.samples.shift()
    }

    performanceState.bandwidth.average =
      performanceState.bandwidth.samples.reduce((a, b) => a + b, 0) / performanceState.bandwidth.samples.length
  }

  const monitorNetworkSpeed = () => {
    if (!videoRef?.value || videoRef.value.buffered.length === 0) return
    const buffered = videoRef.value.buffered

    let totalBufferedBytes = 0
    for (let i = 0; i < buffered.length; i++) {
      const start = buffered.start(i)
      const end = buffered.end(i)
      const duration = end - start
      const estimatedBitrate = 5 * 1024 * 1024
      totalBufferedBytes += (duration * estimatedBitrate) / 8
    }

    const loadingDuration = (Date.now() - performanceState.loading.startTime) / 1000
    if (loadingDuration > 0) updateBandwidth(totalBufferedBytes, loadingDuration)
  }

  const optimizeBufferSize = () => {
    if (!hlsRef?.value || performanceState.bandwidth.average <= 0) return
    const bandwidth = performanceState.bandwidth.average
    const mbps = bandwidth / 1000000

    let targetBuffer: number
    if (mbps >= 10) targetBuffer = 120
    else if (mbps >= 5) targetBuffer = 90
    else if (mbps >= 2) targetBuffer = 60
    else targetBuffer = 30

    if (hlsRef.value.config) {
      hlsRef.value.config.maxBufferLength = targetBuffer
      hlsRef.value.config.maxMaxBufferLength = targetBuffer * 1.5
      if (mbps < 2) {
        hlsRef.value.config.abrBandWidthFactor = 0.6
        hlsRef.value.config.abrBandWidthUpFactor = 0.4
      } else {
        hlsRef.value.config.abrBandWidthFactor = 0.8
        hlsRef.value.config.abrBandWidthUpFactor = 0.6
      }
    }
  }

  const cleanupMemory = () => {
    const now = Date.now()
    if (now - performanceState.memory.lastCleanup <= MEMORY_CLEANUP_INTERVAL) return

    if (videoRef?.value && videoRef.value.buffered.length > 0) {
      const currentTime = videoRef.value.currentTime
      const buffered = videoRef.value.buffered
      for (let i = 0; i < buffered.length; i++) {
        if (buffered.end(i) < currentTime - 30) {
          break
        }
      }
    }

    performanceState.memory.lastCleanup = now
    const gc = (window as any).gc
    if (typeof gc === 'function') gc()
  }

  const monitorPerformance = () => {
    if (!videoRef?.value) return

    const memory = (performance as any).memory
    if (memory) {
      performanceState.memory.used = memory.usedJSHeapSize
      performanceState.memory.peak = Math.max(performanceState.memory.peak, performanceState.memory.used)
    }

    optimizeBufferSize()
    cleanupMemory()
  }

  return {
    performanceState,
    monitorNetworkSpeed,
    monitorPerformance,
    updateBandwidth,
  }
}


