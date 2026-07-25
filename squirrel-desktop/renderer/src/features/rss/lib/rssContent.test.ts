// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'
import { decodeRssHtml, rssHtmlToText, sanitizeRssHtml } from './rssContent'

describe('RSS article content sanitization', () => {
  it('decodes escaped article markup before sanitizing it', () => {
    const sanitized = sanitizeRssHtml('&lt;p&gt;Hello &lt;strong&gt;RSS&lt;/strong&gt;&lt;/p&gt;')

    expect(sanitized).toBe('<p>Hello <strong>RSS</strong></p>')
    expect(decodeRssHtml('&lt;p&gt;Hello&lt;/p&gt;')).toBe('<p>Hello</p>')
  })

  it('removes executable tags, event handlers, inline styles, and unsafe protocols', () => {
    const sanitized = sanitizeRssHtml(`
      <script>window.pwned = true</script>
      <img src="https://cdn.example/image.jpg" onerror="window.pwned = true" style="position:fixed">
      <a href="javascript:alert(1)">bad</a>
      <a href="https://example.com/post">good</a>
      <iframe src="https://evil.example"></iframe>
    `)

    expect(sanitized).not.toContain('<script')
    expect(sanitized).not.toContain('onerror')
    expect(sanitized).not.toContain('style=')
    expect(sanitized).not.toContain('javascript:')
    expect(sanitized).not.toContain('<iframe')
    expect(sanitized).toContain('src="https://cdn.example/image.jpg"')
    expect(sanitized).toContain('href="https://example.com/post"')
  })

  it('promotes bare feed wrappers into readable paragraphs', () => {
    const sanitized = sanitizeRssHtml(`
      <div><span>第一段内容。</span></div>
      <div><span>第二段内容。</span></div>
    `)

    expect(sanitized).toContain('<p>第一段内容。</p>')
    expect(sanitized).toContain('<p>第二段内容。</p>')
    expect(sanitized).not.toContain('<div>')
    expect(sanitized).not.toContain('<span>')
  })

  it('wraps bare text articles into paragraphs', () => {
    const sanitized = sanitizeRssHtml('第一段。\n\n第二段。')
    expect(sanitized).toBe('<p>第一段。</p><p>第二段。</p>')
  })

  it('allows only HTTP(S) image resources and HTTP(S) or fragment links', () => {
    const sanitized = sanitizeRssHtml(`
      <img src="data:image/svg+xml,<svg onload=alert(1)></svg>" alt="unsafe">
      <img src="https://cdn.example/image.jpg" alt="safe">
      <a href="file:///etc/passwd">file</a>
      <a href="/relative">relative</a>
      <a href="#section">section</a>
    `)

    const container = document.createElement('div')
    container.innerHTML = sanitized
    expect(container.querySelector('img[alt="unsafe"]')?.hasAttribute('src')).toBe(false)
    expect(container.querySelector('img[alt="safe"]')?.getAttribute('src')).toBe('https://cdn.example/image.jpg')
    expect(container.querySelector('a[href="file:///etc/passwd"]')).toBeNull()
    expect(container.querySelector('a[href="/relative"]')).toBeNull()
    expect(container.querySelector('a[href="#section"]')).not.toBeNull()
  })

  it('drops active media elements and autoplay controls entirely', () => {
    const sanitized = sanitizeRssHtml(`
      <audio autoplay controls src="https://media.example/audio.mp3"></audio>
      <video autoplay muted><source src="https://media.example/video.mp4"></video>
      <track src="https://media.example/captions.vtt">
    `)

    expect(sanitized).not.toContain('<audio')
    expect(sanitized).not.toContain('<video')
    expect(sanitized).not.toContain('<source')
    expect(sanitized).not.toContain('<track')
    expect(sanitized).not.toContain('autoplay')
  })

  it('produces safe plain text for entry previews', () => {
    expect(rssHtmlToText('<p>Hello <strong>world</strong></p><script>bad()</script>')).toBe('Hello world')
  })

  it('keeps real list structure intact while cleaning wrappers', () => {
    const sanitized = sanitizeRssHtml('<ul><li><span>item one</span></li><li>item two</li></ul>')
    expect(sanitized).toContain('<ul>')
    expect(sanitized).toContain('<li>')
    expect(sanitized).toContain('item one')
    expect(sanitized).not.toContain('<span>')
  })
})
