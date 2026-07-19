import DOMPurify from 'dompurify'
import { normalizeHttpUrl } from '@/shared/lib/externalUrl'

const ESCAPED_BLOCK_TAG = /&(amp;)?lt;\/?(p|div|h[1-6]|a|span|br|strong|em|ul|ol|li|blockquote|img|table|tr|td|th|section|article|pre|code)\b/i

const RSS_CONTENT_TAGS = [
  'a',
  'abbr',
  'article',
  'b',
  'blockquote',
  'br',
  'caption',
  'cite',
  'code',
  'dd',
  'del',
  'dfn',
  'div',
  'dl',
  'dt',
  'em',
  'figcaption',
  'figure',
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
  'hr',
  'i',
  'img',
  'kbd',
  'li',
  'mark',
  'ol',
  'p',
  'pre',
  'q',
  's',
  'samp',
  'section',
  'small',
  'span',
  'strong',
  'sub',
  'sup',
  'table',
  'tbody',
  'td',
  'tfoot',
  'th',
  'thead',
  'time',
  'tr',
  'u',
  'ul',
  'var',
  'wbr',
] as const

const RSS_CONTENT_ATTRIBUTES = [
  'alt',
  'colspan',
  'datetime',
  'dir',
  'height',
  'href',
  'lang',
  'rowspan',
  'scope',
  'src',
  'start',
  'title',
  'width',
] as const

export const decodeRssHtml = (html: string | null | undefined): string => {
  if (!html) return ''
  let decoded = html
  let iterations = 0
  while (ESCAPED_BLOCK_TAG.test(decoded) && iterations < 3) {
    const textarea = document.createElement('textarea')
    textarea.innerHTML = decoded
    decoded = textarea.value
    iterations += 1
  }
  return decoded
}

export const sanitizeRssHtml = (html: string | null | undefined): string => {
  const decoded = decodeRssHtml(html)
  if (!decoded) return ''

  const sanitized = DOMPurify.sanitize(decoded, {
    ALLOW_ARIA_ATTR: false,
    ALLOW_DATA_ATTR: false,
    ALLOWED_ATTR: [...RSS_CONTENT_ATTRIBUTES],
    ALLOWED_TAGS: [...RSS_CONTENT_TAGS],
    ALLOWED_URI_REGEXP: /^(?:https?:|#)/i,
  })

  // DOMPurify blocks executable markup; this second pass enforces the tighter
  // product rule that rendered article links and resources are absolute HTTP(S).
  const container = document.createElement('div')
  container.innerHTML = sanitized
  for (const element of container.querySelectorAll<HTMLElement>('[href], [src]')) {
    for (const attribute of ['href', 'src'] as const) {
      const value = element.getAttribute(attribute)
      if (value === null) continue
      const isFragmentLink = attribute === 'href' && value.startsWith('#')
      if (!isFragmentLink && !normalizeHttpUrl(value)) element.removeAttribute(attribute)
    }
  }
  return container.innerHTML
}

export const rssHtmlToText = (html: string | null | undefined): string => {
  const sanitized = sanitizeRssHtml(html)
  if (!sanitized) return ''
  const container = document.createElement('div')
  container.innerHTML = sanitized
  return (container.textContent || '').replace(/\s+/g, ' ').trim()
}
