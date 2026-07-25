import { computed, nextTick, ref, watch } from 'vue'
import { usePointerOutside } from '@/shared/composables/usePointerOutside'
import { getDesktopBridge } from '@/shared/composables/useDesktopBridge'
import { formatDate } from '@/shared/lib/dateFormat'
import { normalizeHttpUrl, openExternalUrl } from '@/shared/lib/externalUrl'
import { errorMessage } from '@/shared/lib/errorMessage'
import { getRssEntry } from '@/shared/api'
import { rssHtmlToText, sanitizeRssHtml } from '@/features/rss/lib/rssContent'
import type { RecentEntry, RssEntry } from '@/features/rss/types/rss'

type ReaderFontFamily = 'sans' | 'serif'

const clampFontSize = (value: unknown) => {
  // localStorage miss is null; Number(null) === 0 would wrongly clamp to 14.
  if (value === null || value === undefined || value === '') return 18
  const parsed = Number(value)
  return Number.isFinite(parsed) ? Math.max(14, Math.min(24, parsed)) : 18
}

const loadFontFamily = (): ReaderFontFamily => {
  const stored = localStorage.getItem('rss_reader_font_family')
  if (stored === 'serif') return 'serif'
  // Default to sans — serif stacks render poorly for mixed CJK feeds on Windows.
  return 'sans'
}

const countCjkChars = (text: string) => (text.match(/[\u3400-\u9fff\uf900-\ufaff]/g) || []).length

export function useRssReader(options: {
  onStatus?: (message: string, isError?: boolean) => void
}) {
  const readingEntry = ref<RssEntry | null>(null)
  const articleContent = ref<string | null>(null)
  const loadingArticleContent = ref(false)
  const readerScrollContainer = ref<HTMLElement | null>(null)
  const readerFontSize = ref(clampFontSize(localStorage.getItem('rss_reader_font_size')))
  const readerFontFamily = ref<ReaderFontFamily>(loadFontFamily())
  const showReaderSettings = ref(false)
  const readerSettingsRef = ref<HTMLElement | null>(null)
  // Reeder-style original-article overlay (iframe), not a separate OS window.
  const showInAppBrowser = ref(false)
  const iframeLoading = ref(false)
  const iframeLoadKey = ref(0)
  const iframeRef = ref<HTMLIFrameElement | null>(null)
  const isElectron = computed(() => getDesktopBridge()?.isDesktop === true)
  const activeLightboxImg = ref<string | null>(null)
  const lightboxScale = ref(1)
  let contentRequestToken = 0

  usePointerOutside(readerSettingsRef, () => {
    showReaderSettings.value = false
  })

  const readerFontClass = computed(() => {
    return readerFontFamily.value === 'serif' ? 'font-serif' : 'font-sans'
  })
  const sanitizedArticleHtml = computed(() => sanitizeRssHtml(articleContent.value ?? readingEntry.value?.summary))
  const isCjkArticle = computed(() => {
    const source = articleContent.value ?? readingEntry.value?.summary ?? readingEntry.value?.excerpt ?? ''
    const plain = source.replace(/<[^>]+>/g, ' ')
    const cjk = countCjkChars(plain)
    if (cjk < 12) return false
    const letters = (plain.match(/[A-Za-z\u3400-\u9fff\uf900-\ufaff]/g) || []).length
    return letters === 0 ? true : cjk / letters >= 0.35
  })
  const readerContentClass = computed(() => [
    'reader-content',
    readerFontClass.value,
    isCjkArticle.value ? 'is-cjk' : '',
  ])

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

  const originalArticleUrl = computed(() => normalizeHttpUrl(readingEntry.value?.canonical_url))

  const refreshIframe = () => {
    if (!showInAppBrowser.value || !originalArticleUrl.value) return
    iframeLoading.value = true
    iframeLoadKey.value += 1
  }

  const openInAppBrowser = () => {
    const url = originalArticleUrl.value
    if (!url) {
      options.onStatus?.('文章链接无效', true)
      return false
    }
    showInAppBrowser.value = true
    iframeLoading.value = true
    iframeLoadKey.value += 1
    return true
  }

  const closeInAppBrowser = () => {
    showInAppBrowser.value = false
    iframeLoading.value = false
  }

  const handleIframeLoad = (event: Event) => {
    const target = event.currentTarget
    if (!(target instanceof HTMLIFrameElement)) return
    if (target.dataset.loadKey !== String(iframeLoadKey.value)) return
    iframeLoading.value = false
  }

  const entryPreviewText = (entry: Pick<RssEntry, 'excerpt' | 'summary'> | null | undefined) => {
    if (!entry) return ''
    if (entry.excerpt) return entry.excerpt
    return rssHtmlToText(entry.summary)
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

  const loadArticleContent = async (entry: RssEntry) => {
    // List rows omit full HTML; detail fetch hydrates the reader body.
    if (entry.summary) {
      articleContent.value = entry.summary
      loadingArticleContent.value = false
      return
    }

    const requestToken = ++contentRequestToken
    loadingArticleContent.value = true
    articleContent.value = null
    try {
      const detail = await getRssEntry(entry.id)
      if (requestToken !== contentRequestToken) return
      if (!readingEntry.value || String(readingEntry.value.id) !== String(entry.id)) return
      if (!detail) {
        articleContent.value = null
        return
      }
      articleContent.value = detail.summary ?? null
      // Mutate in place so the readingEntry ref identity stays stable and the
      // watch does not re-enter loadArticleContent in a loop.
      Object.assign(readingEntry.value, {
        ...detail,
        summary: detail.summary ?? null,
        excerpt: detail.excerpt ?? readingEntry.value.excerpt ?? null,
      })
    } catch (err) {
      if (requestToken !== contentRequestToken) return
      options.onStatus?.(errorMessage(err, '加载正文失败'), true)
      articleContent.value = null
    } finally {
      if (requestToken === contentRequestToken) loadingArticleContent.value = false
    }
  }

  const openRecentEntry = (recent: RecentEntry) => {
    if (String(readingEntry.value?.id) === String(recent.id)) return
    readingEntry.value = recent
  }

  watch(
    () => readingEntry.value?.id ?? null,
    (entryId) => {
      showReaderSettings.value = false
      closeInAppBrowser()
      nextTick(() => {
        if (readerScrollContainer.value) readerScrollContainer.value.scrollTop = 0
      })
      const entry = readingEntry.value
      if (entryId == null || !entry) {
        contentRequestToken += 1
        articleContent.value = null
        loadingArticleContent.value = false
        return
      }
      void loadArticleContent(entry)
    },
  )

  return {
    readingEntry,
    loadingArticleContent,
    readerScrollContainer,
    readerFontSize,
    readerFontFamily,
    showReaderSettings,
    readerSettingsRef,
    showInAppBrowser,
    iframeLoading,
    iframeLoadKey,
    iframeRef,
    isElectron,
    originalArticleUrl,
    activeLightboxImg,
    lightboxScale,
    readerFontClass,
    readerContentClass,
    sanitizedArticleHtml,
    setReaderFontSize,
    saveReaderPrefs,
    handleContentClick,
    closeLightbox,
    handleKeyDown,
    refreshIframe,
    openInAppBrowser,
    closeInAppBrowser,
    handleIframeLoad,
    entryPreviewText,
    stripHtmlTags,
    formatRelativeTime,
    openRecentEntry,
  }
}
