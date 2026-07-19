import { computed, nextTick, ref, watch } from 'vue'
import { usePointerOutside } from '@/shared/composables/usePointerOutside'
import { getDesktopBridge } from '@/shared/composables/useDesktopBridge'
import { formatDate } from '@/shared/lib/dateFormat'
import { normalizeHttpUrl, openExternalUrl } from '@/shared/lib/externalUrl'
import { rssHtmlToText, sanitizeRssHtml } from '@/features/rss/lib/rssContent'
import type { RecentEntry, RssEntry } from '@/features/rss/types/rss'

type ReaderFontFamily = 'sans' | 'serif'

const clampFontSize = (value: unknown) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? Math.max(12, Math.min(24, parsed)) : 17
}

const loadFontFamily = (): ReaderFontFamily => {
  return localStorage.getItem('rss_reader_font_family') === 'sans' ? 'sans' : 'serif'
}

export function useRssReader(options: {
  onStatus?: (message: string, isError?: boolean) => void
}) {
  const readingEntry = ref<RssEntry | null>(null)
  const readerScrollContainer = ref<HTMLElement | null>(null)
  const readerFontSize = ref(clampFontSize(localStorage.getItem('rss_reader_font_size')))
  const readerFontFamily = ref<ReaderFontFamily>(loadFontFamily())
  const showReaderSettings = ref(false)
  const readerSettingsRef = ref<HTMLElement | null>(null)
  const activeLightboxImg = ref<string | null>(null)
  const lightboxScale = ref(1)

  usePointerOutside(readerSettingsRef, () => {
    showReaderSettings.value = false
  })

  const readerFontClass = computed(() => {
    return readerFontFamily.value === 'serif'
      ? 'font-serif tracking-normal leading-loose'
      : 'font-sans tracking-normal leading-loose'
  })
  const sanitizedArticleHtml = computed(() => sanitizeRssHtml(readingEntry.value?.summary))

  const setReaderFontSize = (size: number) => {
    readerFontSize.value = clampFontSize(size)
    localStorage.setItem('rss_reader_font_size', String(readerFontSize.value))
  }

  const saveReaderPrefs = () => {
    localStorage.setItem('rss_reader_font_family', readerFontFamily.value)
    localStorage.setItem('rss_reader_font_size', String(readerFontSize.value))
  }

  const handleContentClick = (event: MouseEvent) => {
    const target = event.target
    if (!(target instanceof Element)) return
    const anchor = target.closest('a')
    if (anchor) {
      event.preventDefault()
      event.stopPropagation()
      void openExternalUrl(anchor.getAttribute('href'))
      return
    }
    const image = target.closest('img')
    if (image instanceof HTMLImageElement) {
      const source = normalizeHttpUrl(image.currentSrc || image.src)
      if (!source) return
      activeLightboxImg.value = source
      lightboxScale.value = 1
    }
  }

  const closeLightbox = () => {
    activeLightboxImg.value = null
  }

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === 'Escape' && activeLightboxImg.value) {
      event.preventDefault()
      closeLightbox()
    }
  }

  const openInAppBrowser = async () => {
    const url = normalizeHttpUrl(readingEntry.value?.canonical_url)
    if (!url) {
      options.onStatus?.('文章链接无效', true)
      return false
    }
    const bridge = getDesktopBridge()
    if (bridge?.isDesktop && bridge.openWebContent) {
      let opened = false
      try {
        opened = await bridge.openWebContent(url)
      } catch {
        opened = false
      }
      if (!opened) options.onStatus?.('无法打开应用内浏览器', true)
      return opened
    }
    return openExternalUrl(url)
  }

  const stripHtmlTags = (html: string) => rssHtmlToText(html)

  const formatRelativeTime = (dateStr: string) => {
    const date = new Date(dateStr).getTime()
    if (!Number.isFinite(date)) return ''
    const diff = Date.now() - date
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

  const openRecentEntry = (recent: RecentEntry) => {
    if (String(readingEntry.value?.id) === String(recent.id)) return
    readingEntry.value = recent
  }

  watch(readingEntry, () => {
    showReaderSettings.value = false
    nextTick(() => {
      if (readerScrollContainer.value) readerScrollContainer.value.scrollTop = 0
    })
  })

  return {
    readingEntry,
    readerScrollContainer,
    readerFontSize,
    readerFontFamily,
    showReaderSettings,
    readerSettingsRef,
    activeLightboxImg,
    lightboxScale,
    readerFontClass,
    sanitizedArticleHtml,
    setReaderFontSize,
    saveReaderPrefs,
    handleContentClick,
    closeLightbox,
    handleKeyDown,
    openInAppBrowser,
    stripHtmlTags,
    formatRelativeTime,
    openRecentEntry,
  }
}
