import { Logger } from '@/utils/logger'
import type { Ref } from 'vue'

export default function useOptionsMenu(videoRef: Ref<any>) {
  const copyVideoLink = () => {
    const url = String(videoRef.value?.url || '')
    if (!url) return

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url)
        .catch(err => {
          fallbackCopyTextToClipboard(url)
        })
    } else {
      fallbackCopyTextToClipboard(url)
    }
  }

  const fallbackCopyTextToClipboard = (text: string) => {
    const textArea = document.createElement('textarea')
    textArea.value = text
    textArea.style.position = 'fixed'
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()

    try {
      document.execCommand('copy')
    } catch (err) {
      Logger.error('Fallback copy failed', err)
    }

    document.body.removeChild(textArea)
  }

  return {
    copyVideoLink,
  };
}
