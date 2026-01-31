import { Logger } from '../utils/logger'

export default function useOptionsMenu(videoRef) {
  const copyVideoLink = () => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(videoRef.value.url)
        .catch(err => {
          fallbackCopyTextToClipboard(videoRef.value.url)
        })
    } else {
      fallbackCopyTextToClipboard(videoRef.value.url)
    }
  }

  const fallbackCopyTextToClipboard = (text) => {
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
