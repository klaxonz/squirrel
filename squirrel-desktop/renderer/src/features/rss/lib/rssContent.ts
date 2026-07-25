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
  'cite',
  'colspan',
  'datetime',
  'href',
  'rowspan',
  'src',
  'title',
] as const

const BLOCK_SELECTOR = [
  'address',
  'article',
  'aside',
  'blockquote',
  'div',
  'dl',
  'fieldset',
  'figure',
  'footer',
  'form',
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
  'header',
  'hr',
  'main',
  'nav',
  'ol',
  'p',
  'pre',
  'section',
  'table',
  'ul',
].join(',')

const hasMeaningfulAttributes = (element: Element) =>
  Array.from(element.attributes).some((attribute) => {
    const name = attribute.name.toLowerCase()
    return name !== 'class' && name !== 'id' && name !== 'style' && !name.startsWith('data-')
  })

const unwrapElement = (element: Element) => {
  const parent = element.parentNode
  if (!parent) return
  while (element.firstChild) parent.insertBefore(element.firstChild, element)
  parent.removeChild(element)
}

const replaceElementTag = (element: Element, tagName: string) => {
  const replacement = document.createElement(tagName)
  while (element.firstChild) replacement.appendChild(element.firstChild)
  element.replaceWith(replacement)
  return replacement
}

const isWhitespaceText = (node: Node) =>
  node.nodeType === Node.TEXT_NODE && !((node.textContent || '').trim())

const nodeLooksBlocky = (node: Node) => {
  if (node.nodeType !== Node.ELEMENT_NODE) return false
  const element = node as Element
  return element.matches(BLOCK_SELECTOR)
}

const splitPlainTextIntoParagraphs = (text: string) => {
  const normalized = text.replace(/\r\n?/g, '\n').trim()
  if (!normalized) return []
  const chunks = normalized
    .split(/\n{2,}/)
    .map((chunk) => chunk.replace(/\n+/g, ' ').replace(/\s+/g, ' ').trim())
    .filter(Boolean)
  return chunks.length > 0 ? chunks : [normalized.replace(/\s+/g, ' ').trim()]
}

const wrapBareRootContent = (root: HTMLElement) => {
  const significantChildren = Array.from(root.childNodes).filter((node) => !isWhitespaceText(node))
  if (significantChildren.length === 0) return
  if (significantChildren.some(nodeLooksBlocky)) return

  const hasNonBrElements = significantChildren.some(
    (node) => node.nodeType === Node.ELEMENT_NODE && (node as Element).tagName !== 'BR',
  )

  // Pure text / <br> feeds — rebuild as paragraphs.
  if (!hasNonBrElements) {
    const html = root.innerHTML.trim()
    if (!html) return

    if (/<br\s*\/?>/i.test(html)) {
      const parts = html
        .split(/(?:<br\s*\/?>\s*){2,}/i)
        .map((part) => part.replace(/(?:<br\s*\/?>)+/gi, ' ').replace(/\s+/g, ' ').trim())
        .filter(Boolean)
      root.innerHTML = parts.map((part) => `<p>${part}</p>`).join('')
      return
    }

    const text = root.textContent || ''
    if (!text.trim()) return
    root.innerHTML = splitPlainTextIntoParagraphs(text)
      .map((part) => `<p>${part}</p>`)
      .join('')
    return
  }

  // Mixed root: keep images/links/etc., wrap consecutive bare text runs into <p>.
  const fragment = document.createDocumentFragment()
  let pending: ChildNode[] = []

  const flushPending = () => {
    if (pending.length === 0) return
    const hasText = pending.some(
      (node) => node.nodeType === Node.TEXT_NODE && (node.textContent || '').trim(),
    )
    if (!hasText) {
      for (const node of pending) fragment.appendChild(node)
      pending = []
      return
    }
    const paragraph = document.createElement('p')
    for (const node of pending) paragraph.appendChild(node)
    fragment.appendChild(paragraph)
    pending = []
  }

  for (const node of Array.from(root.childNodes)) {
    if (isWhitespaceText(node) && pending.length === 0) continue
    if (
      node.nodeType === Node.TEXT_NODE ||
      (node.nodeType === Node.ELEMENT_NODE && (node as Element).tagName === 'BR')
    ) {
      pending.push(node)
      continue
    }
    flushPending()
    fragment.appendChild(node)
  }
  flushPending()

  root.replaceChildren(fragment)
}

/**
 * Turn feed junk into readable blocks:
 * - bare text / single-line feeds → `<p>`
 * - `div`/`span` wrappers with only phrasing content → `<p>`
 * Keeps real structure (lists, headings, pre, tables) intact.
 */
export const normalizeRssArticleHtml = (html: string): string => {
  if (!html || typeof document === 'undefined') return html

  const root = document.createElement('div')
  root.innerHTML = html

  // Bottom-up: unwrap decorative spans, promote leaf divs to paragraphs.
  const candidates = Array.from(root.querySelectorAll('div, span')).reverse()
  for (const element of candidates) {
    if (element.tagName === 'SPAN') {
      if (!hasMeaningfulAttributes(element)) unwrapElement(element)
      continue
    }

    // Nested block structure is real layout — leave it alone.
    if (element.querySelector(BLOCK_SELECTOR)) continue

    const onlyWhitespace = !element.textContent?.trim() && !element.querySelector('img, br, hr')
    if (onlyWhitespace) {
      element.remove()
      continue
    }

    replaceElementTag(element, 'p')
  }

  wrapBareRootContent(root)

  // Collapse empty paragraphs left by feed generators.
  for (const paragraph of Array.from(root.querySelectorAll('p'))) {
    if (!paragraph.textContent?.trim() && !paragraph.querySelector('img, br')) {
      paragraph.remove()
    }
  }

  return root.innerHTML.trim()
}

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

  return normalizeRssArticleHtml(container.innerHTML)
}

export const rssHtmlToText = (html: string | null | undefined): string => {
  const sanitized = sanitizeRssHtml(html)
  if (!sanitized) return ''
  const container = document.createElement('div')
  container.innerHTML = sanitized
  return (container.textContent || '').replace(/\s+/g, ' ').trim()
}
