import { computed, onUnmounted, ref, watch, type ComputedRef, type Ref } from 'vue'
import type { IconName } from '../core/useIcons'

export interface UseVideoRotationOptions {
  /** Container element whose aspect ratio drives the rotation scale. */
  containerRef: Ref<HTMLElement | null>
  /** When this changes, rotation resets to 0 (new video). */
  videoId: Ref<string | number | null | undefined>
  showCentralHud: (type: string, value: string, icon: IconName) => void
  closeMenus: () => void
}

export interface UseVideoRotationReturn {
  videoRotation: Ref<number>
  videoRotationStyle: ComputedRef<{ transform: string }>
  rotateVideo: () => void
  handleRotationSelect: (rotation: number) => void
}

/**
 * Owns the video rotation state (0/90/180/270) and the auto-scale that keeps a
 * rotated video fitting inside its container without letterbox gaps.
 */
export function useVideoRotation(options: UseVideoRotationOptions): UseVideoRotationReturn {
  const { containerRef, videoId, showCentralHud, closeMenus } = options

  const videoRotation = ref(0)
  const videoRotationScale = ref(1)
  const videoRotationStyle = computed(() => ({
    transform: `rotate(${videoRotation.value}deg) scale(${videoRotationScale.value})`,
  }))

  let resizeObserver: ResizeObserver | null = null
  let scaleRafId: number | null = null

  const updateScale = () => {
    if (scaleRafId !== null) return
    scaleRafId = requestAnimationFrame(() => {
      scaleRafId = null
      const container = containerRef.value
      if (!container || videoRotation.value % 180 === 0) {
        videoRotationScale.value = 1
        return
      }

      const rect = container.getBoundingClientRect()
      if (rect.width <= 0 || rect.height <= 0) {
        videoRotationScale.value = 1
        return
      }

      videoRotationScale.value = Math.min(rect.width / rect.height, rect.height / rect.width)
    })
  }

  const rotateVideo = () => {
    videoRotation.value = (videoRotation.value + 90) % 360
    showCentralHud('rotation', `${videoRotation.value}°`, 'rotate')
  }

  const handleRotationSelect = (rotation: number) => {
    videoRotation.value = rotation
    showCentralHud('rotation', `${videoRotation.value}°`, 'rotate')
    closeMenus()
  }

  watch(videoRotation, updateScale)
  watch(videoId, () => {
    videoRotation.value = 0
  })
  watch(containerRef, (container) => {
    resizeObserver?.disconnect()
    resizeObserver = null

    if (container) {
      resizeObserver = new ResizeObserver(updateScale)
      resizeObserver.observe(container)
    }

    updateScale()
  }, { immediate: true })

  onUnmounted(() => {
    resizeObserver?.disconnect()
    if (scaleRafId !== null) cancelAnimationFrame(scaleRafId)
  })

  return {
    videoRotation,
    videoRotationStyle,
    rotateVideo,
    handleRotationSelect,
  }
}
