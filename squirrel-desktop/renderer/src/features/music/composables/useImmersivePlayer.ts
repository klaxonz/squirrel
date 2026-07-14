import { onBeforeUnmount, ref, type Ref } from 'vue'

/**
 * Full-screen immersive-player overlay toggle + body scroll lock.
 *
 * Owns the overlay's open/close state and the `document.body.style.overflow`
 * lock that prevents background scrolling while it's open. The lock is always
 * released on close and on unmount, so the overlay can't leak a locked body if
 * the host component tears down while open.
 *
 * Extracted from GlobalMusicPlayerBar.vue so the scroll-lock lifecycle + the
 * "always release on unmount" invariant live in one reusable place — this is
 * the same overlay pattern any full-screen music surface would want.
 */
export interface UseImmersivePlayerReturn {
  showImmersive: Ref<boolean>
  openImmersive: () => void
  closeImmersive: () => void
}

export function useImmersivePlayer(): UseImmersivePlayerReturn {
  const showImmersive = ref(false)

  const openImmersive = () => {
    showImmersive.value = true
    document.body.style.overflow = 'hidden'
  }

  const closeImmersive = () => {
    showImmersive.value = false
    document.body.style.overflow = ''
  }

  // Defensive: if the host unmounts while the overlay is open, release the lock
  // so the rest of the app isn't left with a scroll-locked body.
  onBeforeUnmount(() => {
    document.body.style.overflow = ''
  })

  return {
    showImmersive,
    openImmersive,
    closeImmersive,
  }
}
