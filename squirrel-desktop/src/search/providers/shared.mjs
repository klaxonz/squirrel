const HTML_ENTITY_MAP = {
  amp: '&',
  lt: '<',
  gt: '>',
  quot: '"',
  apos: "'",
  '#39': "'",
}

export const clampLimit = (limit, defaultLimit = 20) => {
  const value = Number(limit)
  if (!Number.isFinite(value)) return defaultLimit
  return Math.max(1, Math.min(Math.floor(value), 50))
}

export const clampPage = (page) => {
  const value = Number(page)
  if (!Number.isFinite(value)) return 1
  return Math.max(1, Math.floor(value))
}

export const normalizeQuery = (query) => {
  return String(query || '').trim()
}

export const decodeHtml = (value) => {
  return String(value || '').replace(/&([^;]+);/g, (match, entity) => {
    if (HTML_ENTITY_MAP[entity]) return HTML_ENTITY_MAP[entity]
    if (entity.startsWith('#x')) {
      const codePoint = Number.parseInt(entity.slice(2), 16)
      return Number.isFinite(codePoint) ? String.fromCodePoint(codePoint) : match
    }
    if (entity.startsWith('#')) {
      const codePoint = Number.parseInt(entity.slice(1), 10)
      return Number.isFinite(codePoint) ? String.fromCodePoint(codePoint) : match
    }
    return match
  })
}

export const stripHtml = (value) => {
  return decodeHtml(String(value || '').replace(/<[^>]*>/g, '')).trim()
}

export const normalizeUrl = (value, origin) => {
  const rawValue = String(value || '').trim()
  if (!rawValue) return ''
  if (rawValue.startsWith('//')) return `https:${rawValue}`
  try {
    return new URL(rawValue, origin).toString()
  } catch {
    return ''
  }
}

export const parseDuration = (value) => {
  const parts = String(value || '')
    .trim()
    .split(':')
    .map((part) => Number.parseInt(part, 10))
  if (!parts.length || parts.some((part) => !Number.isFinite(part))) return null
  return parts.reduce((total, part) => total * 60 + part, 0)
}

export const pickText = (value) => {
  if (!value) return ''
  if (typeof value === 'string') return value
  if (typeof value?.simpleText === 'string') return value.simpleText
  if (Array.isArray(value?.runs)) {
    return value.runs.map((run) => run?.text || '').join('').trim()
  }
  return ''
}

export const pickThumbnail = (thumbnails) => {
  const items = Array.isArray(thumbnails) ? thumbnails : []
  const selected = items[items.length - 1] || items[0]
  return normalizeUrl(selected?.url || '', 'https://www.youtube.com')
}

export const uniqueByUrl = (items) => {
  const seen = new Set()
  const result = []
  for (const item of items) {
    const key = String(item?.url || '').trim()
    if (!key || seen.has(key)) continue
    seen.add(key)
    result.push(item)
  }
  return result
}

export const extractAttribute = (source, name) => {
  const match = String(source || '').match(new RegExp(`${name}=["']([^"']+)["']`, 'i'))
  return match ? match[1] : ''
}

export const fetchText = async (fetchImpl, targetUrl, options = {}) => {
  const response = await fetchImpl(targetUrl, options)
  if (!response.ok) {
    throw new Error(`Search request failed: ${response.status}`)
  }
  return response.text()
}

export const findBalancedJson = (source, marker) => {
  const markerIndex = source.indexOf(marker)
  if (markerIndex < 0) return null
  const startIndex = source.indexOf('{', markerIndex)
  if (startIndex < 0) return null

  let depth = 0
  let inString = false
  let escapeNext = false
  for (let index = startIndex; index < source.length; index++) {
    const char = source[index]
    if (escapeNext) {
      escapeNext = false
      continue
    }
    if (char === '\\') {
      escapeNext = true
      continue
    }
    if (char === '"') {
      inString = !inString
      continue
    }
    if (inString) continue
    if (char === '{') depth++
    if (char === '}') depth--
    if (depth === 0) return source.slice(startIndex, index + 1)
  }

  return null
}
