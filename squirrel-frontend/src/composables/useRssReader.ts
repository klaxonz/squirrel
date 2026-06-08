import { computed, nextTick, ref, watch, type Ref } from 'vue'
import { onClickOutside } from '@vueuse/core'
import { unsubscribeRssFeed } from '@/api'
import { formatDate } from '../utils/dateFormat'
import type { ApiResult, RssEntry, RssFeed, RecentEntry } from './rssTypes'

export function useRssReader(options: {
  selectedAccountId: Ref<number | null>
  feeds: Ref<RssFeed[]>
  findFeedByEntry: (feedId: number) => RssFeed | undefined
  getFeedTitle: (feedId: number) => string
  getFeedCategory: (feedId: number) => string
  getFeedIconUrl: (feedId: number) => string | null
  onStatus?: (message: string, isError?: boolean) => void
  onRefreshFeeds?: () => Promise<void>
  onRefreshEntries?: (isReset?: boolean) => Promise<void>
}) {
  const readingEntry = ref<RssEntry | null>(null)
  const readerScrollContainer = ref<HTMLElement | null>(null)

  // Reader Customization State
  const readerFontSize = ref(Number(localStorage.getItem('rss_reader_font_size')) || 17)
  const readerFontFamily = ref(localStorage.getItem('rss_reader_font_family') || 'serif')
  const showReaderSettings = ref(false)
  const readerSettingsRef = ref<HTMLElement | null>(null)
  // In-App Browser Overlay
  const showInAppBrowser = ref(false)
  const iframeLoading = ref(false)
  const iframeLoadKey = ref(0)
  const iframeProgress = ref(0)
  const isElectron = computed(() => window.desktopApp?.isDesktop === true)
  const iframeRef = ref<HTMLIFrameElement | null>(null)

  // Image Lightbox
  const activeLightboxImg = ref<string | null>(null)
  const lightboxScale = ref(1)

  let progressTimer: number | null = null

  onClickOutside(readerSettingsRef, () => {
    showReaderSettings.value = false
  })
  const readerFontClass = computed(() => {
    switch (readerFontFamily.value) {
      case 'outfit':
        return 'font-outfit tracking-wide leading-loose'
      case 'serif':
        return 'font-serif tracking-normal leading-loose'
      case 'lora':
        return 'font-lora tracking-normal leading-loose'
      case 'sans':
      default:
        return 'font-sans tracking-normal leading-loose'
    }
  })

  const setReaderFontSize = (size: number) => {
    readerFontSize.value = Math.max(12, Math.min(24, size))
    localStorage.setItem('rss_reader_font_size', String(readerFontSize.value))
  }

  const saveReaderPrefs = () => {
    localStorage.setItem('rss_reader_font_family', readerFontFamily.value)
  }

  const handleContentClick = (e: MouseEvent) => {
    const target = e.target as HTMLElement
    if (target.tagName === 'IMG') {
      activeLightboxImg.value = (target as HTMLImageElement).src
      lightboxScale.value = 1
    }
  }

  const closeLightbox = () => {
    activeLightboxImg.value = null
  }

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && activeLightboxImg.value) {
      closeLightbox()
    }
  }

  const startProgress = () => {
    if (progressTimer) {
      clearInterval(progressTimer)
    }
    iframeProgress.value = 8
    progressTimer = window.setInterval(() => {
      if (iframeProgress.value < 75) {
        iframeProgress.value += Math.floor(Math.random() * 8 + 4)
      } else if (iframeProgress.value < 90) {
        iframeProgress.value += Math.floor(Math.random() * 3 + 1)
      } else if (iframeProgress.value < 98) {
        iframeProgress.value += 0.2
      }
    }, 120)
  }

  const completeProgress = () => {
    if (progressTimer) {
      clearInterval(progressTimer)
      progressTimer = null
    }
    iframeProgress.value = 100
  }

  const resetIframeState = () => {
    if (progressTimer) {
      clearInterval(progressTimer)
      progressTimer = null
    }
    iframeProgress.value = 0
  }

  const getDisplayDomain = (urlStr?: string | null) => {
    if (!urlStr) return ''
    try {
      return new URL(urlStr).hostname
    } catch {
      return urlStr || ''
    }
  }

  const refreshIframe = () => {
    if (!showInAppBrowser.value || !readingEntry.value?.canonical_url) return
    iframeLoading.value = true
    iframeLoadKey.value += 1
    startProgress()
  }

  const openInAppBrowser = () => {
    showInAppBrowser.value = true
    iframeLoading.value = true
    iframeLoadKey.value += 1
    startProgress()
  }

  const handleIframeLoad = (event: Event) => {
    const target = event.currentTarget as HTMLIFrameElement | null
    if (!target || target.dataset.loadKey !== String(iframeLoadKey.value)) return
    completeProgress()
    iframeLoading.value = false
  }

  const decodeHtmlEntities = (str: string) => {
    if (!str) return ''
    const txt = document.createElement('textarea')
    txt.innerHTML = str
    return txt.value
  }

  const cleanAndDecodeHtml = (html: string | null | undefined): string => {
    if (!html) return ''
    let decoded = html
    const escapedHtmlRegex = /&(amp;)?lt;\/?(p|div|h[1-6]|a|span|br|strong|em|ul|ol|li|blockquote|img|table|tr|td|th|section|article|pre|code)\b/i
    let iterations = 0
    while (escapedHtmlRegex.test(decoded) && iterations < 3) {
      decoded = decodeHtmlEntities(decoded)
      iterations++
    }
    return decoded
  }

  const stripHtmlTags = (html: string) => {
    if (!html) return ''
    const decodedHtml = cleanAndDecodeHtml(html)
    let text = decodedHtml.replace(/<(script|style)\b[^>]*>([\s\S]*?)<\/\1>/gi, '')
    text = text.replace(/<[^>]+>/g, ' ')
    text = text
      .replace(/&nbsp;/g, ' ')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&amp;/g, '&')
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'")
    return text.replace(/\s+/g, ' ').trim()
  }

  const formatRelativeTime = (dateStr: string) => {
    const now = Date.now()
    const date = new Date(dateStr).getTime()
    const diff = now - date
    if (diff < 0) return '刚刚'
    const minutes = Math.floor(diff / 60000)
    if (minutes < 1) return '刚刚'
    if (minutes < 60) return `${minutes} 分钟前`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours} 小时前`
    const days = Math.floor(hours / 24)
    if (days < 7) return `${days} 天前`
    return formatDate(dateStr)
  }

  const closeReader = () => {
    readingEntry.value = null
  }

  const openRecentEntry = (recent: RecentEntry) => {
    if (readingEntry.value && String(readingEntry.value.id) === String(recent.id)) return
    const existing = options.feeds.value.length > 0
    if (existing) {
      readingEntry.value = recent as unknown as RssEntry
    }
  }

  const unsubscribeCurrentFeedFromReader = async () => {
    if (!readingEntry.value) return
    const feed = options.findFeedByEntry(readingEntry.value.feed_id)
    if (!feed) {
      options?.onStatus?.('未找到对应的订阅源', true)
      return
    }
    if (!options.selectedAccountId.value) return
    const response = await unsubscribeRssFeed(feed.id, options.selectedAccountId.value)
    if (response.error) {
      options?.onStatus?.(response.error.message || '取消订阅失败', true)
      return
    }
    readingEntry.value = null
    options?.onStatus?.(`已取消订阅「${feed.title}」`)
    await options?.onRefreshFeeds?.()
    await options?.onRefreshEntries?.(true)
  }

  watch(readingEntry, () => {
    showReaderSettings.value = false
    showInAppBrowser.value = false
    iframeLoading.value = false
    resetIframeState()
    nextTick(() => {
      if (readerScrollContainer.value) {
        readerScrollContainer.value.scrollTop = 0
      }
    })
  })

  return {
    readingEntry,
    readerScrollContainer,
    readerFontSize,
    readerFontFamily,
    showReaderSettings,
    readerSettingsRef,
    showInAppBrowser,
    iframeLoading,
    iframeLoadKey,
    iframeProgress,
    isElectron,
    iframeRef,
    activeLightboxImg,
    lightboxScale,
    readerFontClass,
    setReaderFontSize,
    saveReaderPrefs,
    handleContentClick,
    closeLightbox,
    handleKeyDown,
    startProgress,
    completeProgress,
    resetIframeState,
    getDisplayDomain,
    refreshIframe,
    openInAppBrowser,
    handleIframeLoad,
    cleanAndDecodeHtml,
    stripHtmlTags,
    formatRelativeTime,
    closeReader,
    openRecentEntry,
    unsubscribeCurrentFeedFromReader,
  }
}
