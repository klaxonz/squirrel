import fs from 'node:fs'
import {
  pornhubCookieFilePath,
  youpornCookieFilePath,
  pornhubAgeGateCookieHeader,
  youpornAgeGateCookieHeader,
} from './constants.mjs'

export const normalizeTargetUrl = (targetUrl) => {
  const value = String(targetUrl || '').trim()
  if (!value) {
    return ''
  }

  try {
    return new URL(value).toString()
  } catch {
    return ''
  }
}

export const isJavdbCookieTarget = (targetUrl) => {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    return false
  }

  try {
    const hostname = new URL(normalizedUrl).hostname.toLowerCase()
    return hostname === 'javdb.com' || hostname.endsWith('.javdb.com')
  } catch {
    return false
  }
}

export const isMissavDocumentTarget = (targetUrl) => {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    return false
  }

  try {
    const hostname = new URL(normalizedUrl).hostname.toLowerCase()
    return hostname === 'missav.ai' || hostname.endsWith('.missav.ai')
  } catch {
    return false
  }
}

export const isBilibiliCookieTarget = (targetUrl) => {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    return false
  }

  try {
    const hostname = new URL(normalizedUrl).hostname.toLowerCase()
    return hostname === 'bilibili.com'
      || hostname.endsWith('.bilibili.com')
      || hostname === 'b23.tv'
      || hostname.endsWith('.bilivideo.com')
      || hostname.endsWith('.bilivideo.cn')
      || hostname.endsWith('.hdslb.com')
      || hostname.endsWith('.acgvideo.com')
  } catch {
    return false
  }
}

export const isPornhubCookieTarget = (targetUrl) => {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    return false
  }

  try {
    const hostname = new URL(normalizedUrl).hostname.toLowerCase()
    return hostname === 'pornhub.com'
      || hostname.endsWith('.pornhub.com')
      || hostname.endsWith('.phncdn.com')
  } catch {
    return false
  }
}

export const isYouPornCookieTarget = (targetUrl) => {
  const normalizedUrl = normalizeTargetUrl(targetUrl)
  if (!normalizedUrl) {
    return false
  }

  try {
    const hostname = new URL(normalizedUrl).hostname.toLowerCase()
    return hostname === 'youporn.com'
      || hostname.endsWith('.youporn.com')
      || hostname.endsWith('.ypncdn.com')
  } catch {
    return false
  }
}

export const readNetscapeCookieFileHeader = (cookieFilePath, domainSuffixes) => {
  if (!fs.existsSync(cookieFilePath)) {
    return ''
  }

  try {
    const raw = fs.readFileSync(cookieFilePath, 'utf8')
    const pairs = []

    for (const rawLine of raw.split(/\r?\n/)) {
      const line = rawLine.trim()
      if (!line) {
        continue
      }

      const normalizedLine = line.startsWith('#HttpOnly_')
        ? line.slice('#HttpOnly_'.length)
        : line

      if (normalizedLine.startsWith('#')) {
        continue
      }

      const parts = normalizedLine.split('\t')
      if (parts.length < 7) {
        continue
      }

      const domain = String(parts[0] || '').replace(/^\./, '').toLowerCase()
      const name = String(parts[5] || '').trim()
      const value = String(parts[6] || '').trim()

      if (!name || !domainSuffixes.some((suffix) => domain.endsWith(suffix))) {
        continue
      }

      pairs.push(`${name}=${value}`)
    }

    return pairs.join('; ')
  } catch {
    return ''
  }
}

export const readPornhubCookieFileHeader = () => {
  return readNetscapeCookieFileHeader(pornhubCookieFilePath, [
    'pornhub.com',
    'phncdn.com',
  ])
}

export const readYouPornCookieFileHeader = () => {
  return readNetscapeCookieFileHeader(youpornCookieFilePath, [
    'youporn.com',
    'ypncdn.com',
  ])
}

export const mergeCookieHeaders = (...cookieHeaders) => {
  const cookieMap = new Map()

  for (const header of cookieHeaders) {
    const normalizedHeader = String(header || '').trim()
    if (!normalizedHeader) {
      continue
    }

    for (const segment of normalizedHeader.split(';')) {
      const pair = segment.trim()
      if (!pair) {
        continue
      }

      const equalsIndex = pair.indexOf('=')
      if (equalsIndex <= 0) {
        continue
      }

      const name = pair.slice(0, equalsIndex).trim()
      const value = pair.slice(equalsIndex + 1).trim()
      if (!name) {
        continue
      }

      cookieMap.set(name, value)
    }
  }

  return Array.from(cookieMap.entries())
    .map(([name, value]) => `${name}=${value}`)
    .join('; ')
}
