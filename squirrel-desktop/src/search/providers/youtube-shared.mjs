import { findBalancedJson, parseDuration, pickText, pickThumbnail, normalizeUrl } from './shared.mjs'
import { desktopChromeUserAgent } from '../../constants.mjs'

const DESKTOP_USER_AGENT = desktopChromeUserAgent
export const YOUTUBE_ORIGIN = 'https://www.youtube.com'

export const collectVideoRenderers = (node, output) => {
  if (!node || typeof node !== 'object') return
  if (node.videoRenderer) { output.push(node.videoRenderer); return }
  if (Array.isArray(node)) { node.forEach((item) => collectVideoRenderers(item, output)); return }
  Object.values(node).forEach((value) => collectVideoRenderers(value, output))
}

export const collectLockupViewModels = (node, output) => {
  if (!node || typeof node !== 'object') return
  if (node.lockupViewModel) { output.push(node.lockupViewModel); return }
  if (Array.isArray(node)) { node.forEach((item) => collectLockupViewModels(item, output)); return }
  Object.values(node).forEach((value) => collectLockupViewModels(value, output))
}

export const findWatchVideoId = (node) => {
  if (!node || typeof node !== 'object') return ''
  const videoId = node?.watchEndpoint?.videoId
  if (videoId) return String(videoId)
  if (Array.isArray(node)) {
    for (const item of node) { const id = findWatchVideoId(item); if (id) return id }
    return ''
  }
  for (const value of Object.values(node)) { const id = findWatchVideoId(value); if (id) return id }
  return ''
}

export const extractApiKey = (html) => {
  return String(html.match(/"INNERTUBE_API_KEY"\s*:\s*"([^"]+)"/)?.[1] || '').trim()
}

export const extractContext = (html) => {
  const jsonText = findBalancedJson(html, 'INNERTUBE_CONTEXT')
  if (!jsonText) throw new Error('YouTube context payload not found')
  return JSON.parse(jsonText)
}

export const findContinuationToken = (node) => {
  if (!node || typeof node !== 'object') return ''
  const token = node?.continuationCommand?.token
    || node?.nextContinuationData?.continuation
    || node?.reloadContinuationData?.continuation
  if (token) return String(token)
  if (Array.isArray(node)) {
    for (const item of node) { const t = findContinuationToken(item); if (t) return t }
    return ''
  }
  for (const value of Object.values(node)) { const t = findContinuationToken(value); if (t) return t }
  return ''
}

export const buildCursor = (continuation, apiKey, context) => {
  if (!continuation) return null
  const client = context?.client || {}
  return {
    continuation,
    api_key: apiKey,
    client: {
      clientName: client.clientName || 'WEB',
      clientVersion: client.clientVersion || '',
      hl: client.hl || 'en',
      gl: client.gl || 'US',
      userAgent: client.userAgent || DESKTOP_USER_AGENT,
      visitorData: client.visitorData || '',
    },
  }
}

export const buildContinuationContext = (cursor) => {
  const client = cursor?.client || cursor?.context?.client || {}
  return {
    client: {
      clientName: client.clientName || 'WEB',
      clientVersion: client.clientVersion || '',
      hl: client.hl || 'en',
      gl: client.gl || 'US',
      userAgent: client.userAgent || DESKTOP_USER_AGENT,
      visitorData: client.visitorData || '',
    },
  }
}

export const getLockupMetadataParts = (lockup) => {
  const rows = lockup?.metadata?.lockupMetadataViewModel?.metadata?.contentMetadataViewModel?.metadataRows || []
  return rows.flatMap((row) => row?.metadataParts || [])
}

export const findLockupOwnerRun = (lockup) => {
  const parts = getLockupMetadataParts(lockup)
  for (const part of parts) {
    const commandRuns = part?.text?.commandRuns || []
    const ownerRun = commandRuns.find((run) => run?.onTap?.innertubeCommand?.browseEndpoint)
    if (ownerRun) return ownerRun
  }
  return null
}

const durationTextPattern = /(?:^|\D)(\d{1,2}:\d{2}(?::\d{2})?)(?:\D|$)/

const extractDurationFromText = (value) => {
  const text = String(value || '')
  const duration = durationTextPattern.exec(text)?.[1] || ''
  return parseDuration(duration)
}

export const extractLockupDuration = (lockup) => {
  const badges = lockup?.contentImage?.thumbnailViewModel?.overlays
    ?.flatMap((overlay) => overlay?.thumbnailBottomOverlayViewModel?.badges || [])
    || []
  for (const badge of badges) {
    const duration = parseDuration(badge?.thumbnailBadgeViewModel?.text)
    if (duration) return duration
  }
  const texts = getLockupMetadataParts(lockup).map((part) => part?.text?.content || '').filter(Boolean)
  for (const text of texts) {
    const duration = extractDurationFromText(text)
    if (duration) return duration
  }
  return null
}

export const extractLockupPublishedText = (lockup) => {
  const texts = getLockupMetadataParts(lockup).map((part) => part?.text?.content || '').filter(Boolean)
  return texts.findLast((text) => /\b(?:ago|premiered|streamed|minutes?|hours?|days?|weeks?|months?|years?)\b/i.test(text)) || ''
}

export const pickLockupThumbnail = (lockup) => {
  return pickThumbnail(
    lockup?.contentImage?.thumbnailViewModel?.image?.sources
    || lockup?.contentImage?.collectionThumbnailViewModel?.primaryThumbnail?.thumbnailViewModel?.image?.sources
  )
}

export const buildChannelUrl = (browseEndpoint) => {
  const browseId = String(browseEndpoint?.browseId || '').trim()
  if (browseId.startsWith('UC')) return `${YOUTUBE_ORIGIN}/channel/${encodeURIComponent(browseId)}`
  return normalizeUrl(browseEndpoint?.canonicalBaseUrl || '', YOUTUBE_ORIGIN)
}

export const extractOwnerProfile = (renderer) => {
  const ownerText = renderer?.ownerText || renderer?.longBylineText || renderer?.shortBylineText
  const name = pickText(ownerText)
  const ownerRun = Array.isArray(ownerText?.runs) ? ownerText.runs.find((run) => run?.navigationEndpoint) : null
  const browseEndpoint = ownerRun?.navigationEndpoint?.browseEndpoint
  const avatar = pickThumbnail(
    renderer?.channelThumbnailSupportedRenderers?.channelThumbnailWithLinkRenderer?.thumbnail?.thumbnails
  )
  if (!name) return null
  return {
    id: browseEndpoint?.browseId || null,
    type: 'CHANNEL',
    name,
    url: buildChannelUrl(browseEndpoint),
    avatar,
    is_nsfw: false,
  }
}

export const extractLockupOwnerProfile = (lockup) => {
  const ownerRun = findLockupOwnerRun(lockup)
  const browseEndpoint = ownerRun?.onTap?.innertubeCommand?.browseEndpoint
  const name = String(ownerRun?.text || '').trim()
  if (!name) return null
  return {
    id: browseEndpoint?.browseId || null,
    type: 'CHANNEL',
    name,
    url: buildChannelUrl(browseEndpoint),
    avatar: '',
    is_nsfw: false,
  }
}

export const mapVideoRenderer = (renderer) => {
  const videoId = String(renderer?.videoId || '').trim()
  const ownerProfile = extractOwnerProfile(renderer)
  return {
    source: 'remote',
    site: 'youtube',
    id: videoId,
    title: pickText(renderer?.title),
    url: videoId ? `${YOUTUBE_ORIGIN}/watch?v=${encodeURIComponent(videoId)}` : '',
    thumbnail: pickThumbnail(renderer?.thumbnail?.thumbnails),
    duration: parseDuration(pickText(renderer?.lengthText)),
    publish_date: null,
    published_text: pickText(renderer?.publishedTimeText),
    uploader: ownerProfile?.name || pickText(renderer?.ownerText),
    uploader_url: ownerProfile?.url || '',
    uploader_avatar: ownerProfile?.avatar || '',
    subscriptions: ownerProfile ? [ownerProfile] : [],
    description: pickText(renderer?.detailedMetadataSnippets?.[0]?.snippetText),
  }
}

export const mapLockupViewModel = (lockup) => {
  const videoId = findWatchVideoId(lockup)
  const ownerProfile = extractLockupOwnerProfile(lockup)
  return {
    source: 'remote',
    site: 'youtube',
    id: videoId,
    title: lockup?.metadata?.lockupMetadataViewModel?.title?.content || '',
    url: videoId ? `${YOUTUBE_ORIGIN}/watch?v=${encodeURIComponent(videoId)}` : '',
    thumbnail: pickLockupThumbnail(lockup),
    duration: extractLockupDuration(lockup),
    publish_date: null,
    published_text: extractLockupPublishedText(lockup),
    uploader: ownerProfile?.name || '',
    uploader_url: ownerProfile?.url || '',
    uploader_avatar: ownerProfile?.avatar || '',
    subscriptions: ownerProfile ? [ownerProfile] : [],
    description: '',
  }
}
