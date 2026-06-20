import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'
import { useToast } from '@/shared/components/toast/useToast'
import { Logger } from '@/shared/lib/logger'

/**
 * "More" dropdown menu + share action for the video play view.
 *
 * Owns the dropdown open/close state, its template ref, the document-level
 * click-outside listener that closes it (lifecycle-managed), and the share
 * action (build the permalink from the video id, copy to clipboard, toast).
 * Extracted from VideoPlay.vue so the click-outside lifecycle + the clipboard
 * fallback live in one place rather than alongside playback wiring.
 */
export interface UseVideoShareMenuOptions {
  /** Current video id; used to build the share permalink. */
  videoId: Ref<string | number | null | undefined>
}

export interface UseVideoShareMenuReturn {
  moreMenuOpen: Ref<boolean>
  /** Template ref: attach to the menu's positioning wrapper. */
  moreMenuRef: Ref<HTMLElement | null>
  handleShare: () => Promise<void>
}

export function useVideoShareMenu(options: UseVideoShareMenuOptions): UseVideoShareMenuReturn {
  const { videoId } = options
  const toast = useToast()

  const moreMenuOpen = ref(false)
  const moreMenuRef = ref<HTMLElement | null>(null)

  const handleShare = async () => {
    const url = `${window.location.origin}/video/${videoId.value}`
    try {
      await navigator.clipboard.writeText(url)
      toast.success('链接已复制到剪贴板')
    } catch (err) {
      Logger.warn('[VideoPlay] Failed to copy share link', err)
      toast.error('复制失败，请手动复制链接')
    }
  }

  const handleClickOutside = (e: MouseEvent) => {
    if (moreMenuRef.value && !moreMenuRef.value.contains(e.target as Node)) {
      moreMenuOpen.value = false
    }
  }

  onMounted(() => {
    document.addEventListener('click', handleClickOutside)
  })

  onBeforeUnmount(() => {
    document.removeEventListener('click', handleClickOutside)
  })

  return {
    moreMenuOpen,
    moreMenuRef,
    handleShare,
  }
}
