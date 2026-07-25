import { computed, getCurrentScope, nextTick, onScopeDispose, ref, watch } from 'vue'
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
  // Original-article overlay: desktop uses an embedded WebContentsView host;
  // non-desktop falls back to iframe (subject to X-Frame-Options).
  const showInAppBrowser = ref(false)
  const iframeLoading = ref(false)
  const iframeLoadKey = ref(0)
  const iframeRef = ref<HTMLIFrameElement | null>(null)
  const inAppWebViewHostRef = ref<HTMLElement | null>(null)
  const isElectron = computed(() => getDesktopBridge()?.isDesktop === true)
  const usesNativeInAppWebView = computed(() => {
    const bridge = getDesktopBridge()
    return Boolean(bridge?.isDesktop && bridge.openInAppWebView)
  })
  const activeLightboxImg = ref<string | null>(null)
  const lightboxScale = ref(1)
  let contentRequestToken = 0
  let hostResizeObserver: ResizeObserver | null = null

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

  const readHostBounds = () => {
    const host = inAppWebViewHostRef.value
    if (!host) return null
    const rect = host.getBoundingClientRect()
    const width = Math.round(rect.width)
    const height = Math.round(rect.height)
    if (width <= 0 || height <= 0) return null
    return {
      x: Math.round(rect.left),
      y: Math.round(rect.top),
      width,
      height,
    }
  }

  const syncNativeInAppWebViewBounds = async () => {
    if (!showInAppBrowser.value || !usesNativeInAppWebView.value) return false
    const bridge = getDesktopBridge()
    const bounds = readHostBounds()
    if (!bridge?.setInAppWebViewBounds || !bounds) return false
    try {
      return Boolean(await bridge.setInAppWebViewBounds(bounds))
    } catch {
      return false
    }
  }

  const stopHostBoundsTracking = () => {
    hostResizeObserver?.disconnect()
    hostResizeObserver = null
    window.removeEventListener('resize', handleWindowResizeForInAppWebView)
  }

  function handleWindowResizeForInAppWebView() {
    void syncNativeInAppWebViewBounds()
  }

  const startHostBoundsTracking = () => {
    stopHostBoundsTracking()
    if (!usesNativeInAppWebView.value) return
    const host = inAppWebViewHostRef.value
    if (host && typeof ResizeObserver === 'function') {
      hostResizeObserver = new ResizeObserver(() => {
        void syncNativeInAppWebViewBounds()
      })
      hostResizeObserver.observe(host)
    }
    window.addEventListener('resize', handleWindowResizeForInAppWebView)
  }

  const hideNativeInAppWebView = async () => {
    stopHostBoundsTracking()
    const bridge = getDesktopBridge()
    if (!bridge?.hideInAppWebView) return
    try {
      await bridge.hideInAppWebView()
    } catch {
      // Ignore hide failures during teardown.
    }
  }

  const openNativeInAppWebView = async (url: string) => {
    const bridge = getDesktopBridge()
    if (!bridge?.openInAppWebView) return false
    await nextTick()
    let bounds = readHostBounds()
    if (!bounds) {
      await nextTick()
      bounds = readHostBounds()
    }
    if (!bounds) return false
    try {
      const opened = await bridge.openInAppWebView({ url, bounds })
      if (!opened) return false
      startHostBoundsTracking()
      iframeLoading.value = false
      return true
    } catch {
      return false
    }
  }

  const refreshIframe = async () => {
    if (!showInAppBrowser.value || !originalArticleUrl.value) return
    iframeLoading.value = true
    if (usesNativeInAppWebView.value) {
      const bridge = getDesktopBridge()
      try {
        const reloaded = await bridge?.reloadInAppWebView?.()
        if (reloaded) {
          iframeLoading.value = false
          return
        }
      } catch {
        // Fall through to re-open.
      }
      const reopened = await openNativeInAppWebView(originalArticleUrl.value)
      if (!reopened) iframeLoading.value = false
      return
    }
    iframeLoadKey.value += 1
  }
  const openInAppBrowser = async () => {
    const url = originalArticleUrl.value
    if (!url) {
      options.onStatus?.('文章链接无效', true)
      return false
    }

    // Entry switches schedule closeInAppBrowser via watch; settle that first so
    // a follow-up open (e.g. feed open_method=app_browser) is not clobbered.
    await nextTick()

    showInAppBrowser.value = true
    iframeLoading.value = true

    if (usesNativeInAppWebView.value) {
      const opened = await openNativeInAppWebView(url)
      if (!opened) {
        showInAppBrowser.value = false
        iframeLoading.value = false
        options.onStatus?.('无法在应用内打开原文', true)
        return false
      }
      return true
    }

    // Browser / non-desktop: iframe best-effort (sites may still block framing).
    iframeLoadKey.value += 1
    return true
  }

  const closeInAppBrowser = () => {
    showInAppBrowser.value = false
    iframeLoading.value = false
    void hideNativeInAppWebView()
  }

  const handleIframeLoad = (event: Event) => {
    if (usesNativeInAppWebView.value) return
    const target = event.currentTarget
    if (!(target instanceof HTMLIFrameElement)) return
    if (target.dataset.loadKey !== String(iframeLoadKey.value)) return
    iframeLoading.value = false
  }

  if (getCurrentScope()) {
    onScopeDispose(() => {
      void hideNativeInAppWebView()
    })
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
    inAppWebViewHostRef,
    isElectron,
    usesNativeInAppWebView,
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
