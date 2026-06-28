import { createRequire } from 'node:module'

import {
  clearMusicAuthCookie as clearMusicAuthCookieDefault,
  readMusicAuthCookie as readMusicAuthCookieDefault,
  writeMusicAuthCookie as writeMusicAuthCookieDefault,
} from './auth-store.mjs'
import {
  firstList,
  formatImageUrl,
  normalizeAlbum,
  normalizeAlbumFromTrack,
  normalizeArtist,
  normalizeArtistSearch,
  normalizeComment,
  normalizeHotSearch,
  normalizeMv,
  normalizePlaylist,
  normalizePlaylistTags,
  normalizeRank,
  normalizeSuggestionItems,
  normalizeTrack,
  normalizeVideo,
  parseLrc,
} from './normalizers.mjs'

const require = createRequire(import.meta.url)
process.env.platform = process.env.KUGOU_MUSIC_PLATFORM || process.env.platform || 'lite'
let kugou = require('kugoumusicapi/main')
let authStore = {
  read: readMusicAuthCookieDefault,
  write: writeMusicAuthCookieDefault,
  clear: clearMusicAuthCookieDefault,
}

const DEFAULT_COOKIE = String(process.env.KUGOU_MUSIC_COOKIE || '')

export class DesktopMusicServiceError extends Error {
  constructor(message, details = undefined) {
    super(message)
    this.name = 'DesktopMusicServiceError'
    this.details = details
  }
}

const bodyFromResponse = (response, moduleName) => {
  const body = response?.body
  if (!body || typeof body !== 'object') {
    throw new DesktopMusicServiceError(`KuGouMusicApi ${moduleName} returned invalid payload`, response)
  }
  const status = body.status
  if (![undefined, null, '', 0, 1, '0', '1'].includes(status)) {
    throw new DesktopMusicServiceError(String(body.error || body.message || body.msg || body.error_msg || body.errmsg || 'KuGouMusicApi rejected request'))
  }
  const errorCode = body.error_code ?? body.errcode
  if (![undefined, null, '', 0, '0', 200, '200'].includes(errorCode)) {
    throw new DesktopMusicServiceError(String(body.error || body.message || body.msg || body.error_msg || body.errmsg || 'KuGouMusicApi rejected request'))
  }
  return body
}

const responseFromKugou = async (moduleName, params = {}, { useAuth = true } = {}) => {
  const fn = kugou[moduleName]
  if (typeof fn !== 'function') {
    throw new DesktopMusicServiceError(`KuGouMusicApi module not found: ${moduleName}`)
  }
  const requestParams = { ...params }
  if (useAuth) {
    const cookie = await effectiveCookie()
    if (cookie) requestParams.cookie = cookie
  }

  try {
    const response = await fn(requestParams)
    bodyFromResponse(response, moduleName)
    return response
  } catch (error) {
    if (error instanceof DesktopMusicServiceError) throw error
    const body = error?.body
    if (body && typeof body === 'object') {
      const message = body.message || body.msg || body.error || body.error_msg
      if (message) throw new DesktopMusicServiceError(String(message), error)
    }
    throw new DesktopMusicServiceError(`KuGouMusicApi request failed: ${error?.message || String(error)}`, error)
  }
}

const cookieValue = (cookie, key) => {
  const prefix = `${key}=`
  for (const item of String(cookie || '').split(';')) {
    const normalized = item.trim()
    if (normalized.startsWith(prefix)) return normalized.slice(prefix.length)
  }
  return ''
}

const effectiveCookie = async () => (await authStore.read()) || DEFAULT_COOKIE

const requestKugou = async (moduleName, params = {}, { useAuth = true } = {}) => {
  return bodyFromResponse(await responseFromKugou(moduleName, params, { useAuth }), moduleName)
}

const ok = () => ({ ok: true })

const playlistTrackData = (track = {}) => [track.title, track.hash, track.album_id, track.album_audio_id].join('|')

const service = {
  async searchTracks({ query, page = 1, page_size = 20 }) {
    const payload = await requestKugou('search', {
      keywords: String(query || '').trim(),
      page,
      pagesize: page_size,
      type: 'song',
    })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    const rows = Array.isArray(data.lists) ? data.lists : []
    return { items: rows.map(normalizeTrack), page, page_size, total: data.total || data.total_count || rows.length }
  },

  async searchArtists({ query, page = 1, page_size = 10 }) {
    const payload = await requestKugou('search', {
      keywords: String(query || '').trim(),
      page,
      pagesize: page_size,
      type: 'author',
    })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    const rows = Array.isArray(data.lists) ? data.lists : []
    return { items: rows.map(normalizeArtistSearch), page, page_size, total: data.total || rows.length }
  },

  async searchAlbums({ query, page = 1, page_size = 12 }) {
    const payload = await requestKugou('search', {
      keywords: String(query || '').trim(),
      page,
      pagesize: Math.min(page_size * 3, 50),
      type: 'song',
    })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    const rows = Array.isArray(data.lists) ? data.lists : []
    const albums = []
    const seen = new Set()
    for (const row of rows) {
      if (!row || typeof row !== 'object') continue
      const album = normalizeAlbumFromTrack(row)
      if (!album.id || seen.has(album.id)) continue
      seen.add(album.id)
      albums.push(album)
      if (albums.length >= page_size) break
    }
    return { items: albums, page, page_size, total: albums.length }
  },

  async defaultSearch() {
    const payload = await requestKugou('search_default', {})
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    return { keyword: data && typeof data === 'object' ? String(data.keyword || data.show_keyword || data.word || '') : '' }
  },

  async hotSearch() {
    const payload = await requestKugou('search_hot', {})
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    return { items: firstList(data, ['info', 'list', 'lists', 'items', 'data']).map(normalizeHotSearch) }
  },

  async searchSuggest({ query }) {
    const payload = await requestKugou('search_suggest', {
      keywords: String(query || '').trim(),
      albumTipCount: 6,
      correctTipCount: 6,
      mvTipCount: 6,
      musicTipCount: 10,
    })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    return { items: normalizeSuggestionItems(data) }
  },

  async complexSearch({ query }) {
    const normalizedQuery = String(query || '').trim()
    const [songPayload, artistPayload] = await Promise.all([
      requestKugou('search', { keywords: normalizedQuery, page: 1, pagesize: 50, type: 'song' }),
      requestKugou('search', { keywords: normalizedQuery, page: 1, pagesize: 12, type: 'author' }),
    ])
    const songData = songPayload.data && typeof songPayload.data === 'object' ? songPayload.data : {}
    const artistData = artistPayload.data && typeof artistPayload.data === 'object' ? artistPayload.data : {}
    const songRows = Array.isArray(songData.lists) ? songData.lists : []
    const artistRows = Array.isArray(artistData.lists) ? artistData.lists : []
    const albums = []
    const seenAlbumIds = new Set()
    for (const row of songRows) {
      if (!row || typeof row !== 'object') continue
      const album = normalizeAlbumFromTrack(row)
      if (!album.id || seenAlbumIds.has(album.id)) continue
      seenAlbumIds.add(album.id)
      albums.push(album)
      if (albums.length >= 12) break
    }
    return {
      songs: songRows.filter((row) => row && typeof row === 'object').map(normalizeTrack).slice(0, 50),
      artists: artistRows.filter((row) => row && typeof row === 'object').map(normalizeArtistSearch).slice(0, 12),
      albums,
    }
  },

  async recommendations(params = {}) {
    const requestParams = { mode: params.mode || 'normal' }
    for (const key of ['song_pool_id', 'action', 'hash', 'songid', 'playtime']) {
      if (params[key] !== undefined && params[key] !== null) requestParams[key] = params[key]
    }
    if (params.is_overplay) requestParams.is_overplay = 1
    if (Number(params.remain_songcnt || 0) > 0) requestParams.remain_songcnt = params.remain_songcnt
    const payload = await requestKugou('personal_fm', requestParams)
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    const rows = Array.isArray(data.song_list) ? data.song_list : []
    return { items: rows.map(normalizeTrack), page: 1, page_size: rows.length, total: rows.length }
  },

  async recommendCard({ card_id = 1, page_size = 10 }) {
    const payload = await requestKugou('top_card', { card_id })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    let rows = firstList(data, ['song_list', 'songs', 'songlist', 'info', 'list', 'data'])
    if (page_size > 0) rows = rows.slice(0, page_size)
    return {
      items: rows.map(normalizeTrack),
      page: 1,
      page_size,
      total: data && typeof data === 'object' ? data.song_list_size || data.total || rows.length : rows.length,
      card_id,
      title: data && typeof data === 'object' ? String(data.rec_desc || data.title || '').replace(/^「|」$/g, '') : '',
    }
  },

  async dailyRecommend({ page_size = 10 }) {
    const payload = await requestKugou('recommend_songs', {})
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    let rows = firstList(data, ['song_list', 'songs', 'songlist', 'info', 'list', 'data'])
    if (page_size > 0) rows = rows.slice(0, page_size)
    return {
      items: rows.map(normalizeTrack),
      page: 1,
      page_size,
      total: data && typeof data === 'object' ? data.song_list_size || data.total || rows.length : rows.length,
      cover: data && typeof data === 'object' ? formatImageUrl(String(data.cover_img_url || data.cover || '')) : '',
    }
  },

  async ranks() {
    const payload = await requestKugou('rank_list', { withsong: 0 })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    const rows = Array.isArray(data.info) ? data.info : []
    return { items: rows.map(normalizeRank), total: data.total || rows.length }
  },

  async rankTracks({ rank_id, rank_cid = null, page = 1, page_size = 20 }) {
    const params = { rankid: rank_id, page, pagesize: page_size }
    if (rank_cid) params.rank_cid = rank_cid
    const payload = await requestKugou('rank_audio', params)
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    const rows = firstList(data, ['songlist', 'songs', 'list', 'info', 'data'])
    return { items: rows.map(normalizeTrack), page, page_size, total: data.total || payload.total || rows.length }
  },

  async playlists({ category_id = 0, page = 1, page_size = 20 }) {
    const payload = await requestKugou('top_playlist', { category_id, page, pagesize: page_size, withsong: 0 })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    const rows = Array.isArray(data.special_list) ? data.special_list : []
    return { items: rows.map(normalizePlaylist), page, page_size, has_more: Boolean(data.has_next) }
  },

  async playlistTags() {
    const payload = await requestKugou('playlist_tags', {})
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    return { items: normalizePlaylistTags(firstList(data, ['info', 'list', 'tags', 'data'])) }
  },

  async similarPlaylists({ playlist_id }) {
    const payload = await requestKugou('playlist_similar', { ids: playlist_id })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    return { items: firstList(data, ['info', 'list', 'lists', 'special_list', 'data']).map(normalizePlaylist) }
  },

  async playlistTracks({ playlist_id, page = 1, page_size = 20 }) {
    const payload = await requestKugou('playlist_track_all', { id: playlist_id, page, pagesize: page_size })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    const rows = Array.isArray(data.songs) ? data.songs : []
    return { items: rows.map(normalizeTrack), page, page_size, total: data.count || rows.length }
  },

  async userPlaylists({ page = 1, page_size = 30 } = {}) {
    const payload = await requestKugou('user_playlist', { page, pagesize: page_size })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    const rows = firstList(data, ['info', 'lists', 'list', 'data'])
    const total = data && typeof data === 'object' ? data.total || data.count || rows.length : rows.length
    return { items: rows, page, page_size, total }
  },

  async userPlaylistTracks({ list_id, page = 1, page_size = 30 }) {
    const payload = await requestKugou('playlist_track_all_new', { listid: list_id, page, pagesize: page_size })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    const rows = firstList(data, ['info', 'songs', 'list', 'files', 'data'])
    const total = data && typeof data === 'object' ? data.total || data.count || rows.length : rows.length
    return { items: rows.map(normalizeTrack), page, page_size, total }
  },

  async artistDetail({ artist_id }) {
    const payload = await requestKugou('artist_detail', { id: artist_id })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    return normalizeArtist(data)
  },

  async artistTracks({ artist_id, page = 1, page_size = 30 }) {
    const payload = await requestKugou('artist_audios', { id: artist_id, page, pagesize: page_size })
    const rows = Array.isArray(payload.data) ? payload.data : []
    return { items: rows.map(normalizeTrack), page, page_size, total: payload.total || rows.length }
  },

  async artistAlbums({ artist_id, page = 1, page_size = 20 }) {
    const payload = await requestKugou('artist_albums', { id: artist_id, page, pagesize: page_size })
    const rows = Array.isArray(payload.data) ? payload.data : []
    return { items: rows.map(normalizeAlbum), page, page_size, total: payload.total || rows.length }
  },

  async albumDetail({ album_id }) {
    const payload = await requestKugou('album_detail', { id: album_id })
    const rows = Array.isArray(payload.data) ? payload.data : []
    return normalizeAlbum(rows.find((row) => row && typeof row === 'object') || {})
  },

  async albumTracks({ album_id, page = 1, page_size = 30 }) {
    const payload = await requestKugou('album_songs', { id: album_id, page, pagesize: page_size })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    const rows = Array.isArray(data.songs) ? data.songs : []
    return { items: rows.map(normalizeTrack), page, page_size, total: data.total || payload.total || rows.length }
  },

  async newSongs({ type = null, page = 1, page_size = 30 } = {}) {
    const params = { page, pagesize: page_size }
    if (type !== null && type !== undefined) params.type = type
    const payload = await requestKugou('top_song', params)
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    const rows = firstList(data, ['songs', 'songlist', 'info', 'list', 'data'])
    const total = data && typeof data === 'object' ? data.total || data.count || rows.length : rows.length
    return { items: rows.map(normalizeTrack), page, page_size, total }
  },

  async newAlbums({ page = 1, page_size = 20 } = {}) {
    const payload = await requestKugou('top_album', {})
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    const rows = []
    for (const key of ['chn', 'eur', 'jpn', 'kor']) {
      if (Array.isArray(data[key])) rows.push(...data[key].filter((item) => item && typeof item === 'object'))
    }
    const start = (page - 1) * page_size
    return { items: rows.slice(start, start + page_size).map(normalizeAlbum), page, page_size, total: data.total || data.count || rows.length }
  },

  async aiRecommend({ page_size = 20 } = {}) {
    const payload = await requestKugou('ai_recommend', { pagesize: page_size })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    return { items: firstList(data, ['songs', 'song_list', 'info', 'list', 'data']).map(normalizeTrack) }
  },

  async brushFeed({ page_size = 20 } = {}) {
    const payload = await requestKugou('brush', { pagesize: page_size })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    return { items: firstList(data, ['songs', 'song_list', 'info', 'list', 'data']).map(normalizeTrack) }
  },

  async everydayRecommend() {
    const payload = await requestKugou('everyday_recommend', {})
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    return { items: firstList(data, ['songs', 'song_list', 'info', 'list', 'data']).map(normalizeTrack) }
  },

  async styleRecommend() {
    const payload = await requestKugou('everyday_style_recommend', {})
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    return { items: firstList(data, ['songs', 'song_list', 'info', 'list', 'data']).map(normalizeTrack) }
  },

  async createUserPlaylist({ name, is_private = false }) {
    await requestKugou('playlist_add', {
      name,
      type: 0,
      is_pri: is_private ? 1 : 0,
      list_create_userid: '',
      list_create_listid: '',
    })
    return ok()
  },

  async collectPlaylist({ playlist_id }) {
    const detailPayload = await requestKugou('playlist_detail', { ids: playlist_id })
    const rows = Array.isArray(detailPayload.data) ? detailPayload.data : []
    const detail = rows.find((row) => row && typeof row === 'object') || {}
    const listCreateUserid = String(detail.list_create_userid || '')
    const listCreateListid = String(detail.list_create_listid || '')
    const name = String(detail.name || '')
    if (!listCreateUserid || !listCreateListid || !name) {
      throw new DesktopMusicServiceError('KuGouMusicApi playlist detail missed collect fields')
    }
    await requestKugou('playlist_add', {
      name,
      type: 1,
      source: detail.source || 1,
      list_create_userid: listCreateUserid,
      list_create_listid: listCreateListid,
      list_create_gid: detail.list_create_gid || playlist_id,
    })
    return ok()
  },

  async deleteUserPlaylist({ list_id }) {
    await requestKugou('playlist_del', { listid: list_id })
    return ok()
  },

  async addUserPlaylistTrack({ list_id, track }) {
    await requestKugou('playlist_tracks_add', { listid: list_id, data: playlistTrackData(track) })
    return ok()
  },

  async removeUserPlaylistTracks({ list_id, file_ids }) {
    await requestKugou('playlist_tracks_del', { listid: list_id, fileids: file_ids })
    return ok()
  },

  async userHistory({ bp = null } = {}) {
    const params = {}
    if (bp) params.bp = bp
    const payload = await requestKugou('user_history', params)
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    const rows = firstList(data, ['songs', 'info', 'list', 'data'])
    return { items: rows.map(normalizeTrack), bp: data && typeof data === 'object' ? data.bp || data.next_bp || '' : '' }
  },

  async userListenRank({ type = 0 } = {}) {
    const payload = await requestKugou('user_listen', { type })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    return { items: firstList(data, ['lists', 'songs', 'info', 'list', 'data']).map(normalizeTrack) }
  },

  async latestListenSongs({ page_size = 30 } = {}) {
    const payload = await requestKugou('lastest_songs_listen', { pagesize: page_size })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    return { items: firstList(data, ['songs', 'info', 'list', 'data']).map(normalizeTrack) }
  },

  async uploadPlayHistory({ album_audio_id, played_at = null, play_count = 1 }) {
    const params = { mxid: album_audio_id, pc: play_count }
    if (played_at) params.time = played_at
    await requestKugou('playhistory_upload', params)
    return ok()
  },

  async favoriteCount({ mixsongids }) {
    const payload = await requestKugou('favorite_count', { mixsongids }, { useAuth: false })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    const rows = Array.isArray(data.list) ? data.list : []
    return {
      items: rows.filter((row) => row && typeof row === 'object').map((row) => ({
        mixsongid: String(row.mixsongid || ''),
        count: Number.parseInt(row.count || 0, 10),
        count_text: String(row.count_text || ''),
      })),
    }
  },

  async playUrl({ hash, album_id = null, album_audio_id = null, quality = '128' }) {
    const params = { hash, quality }
    if (album_id) params.album_id = album_id
    if (album_audio_id) params.album_audio_id = album_audio_id
    const payload = await requestKugou('song_url', params)
    const trackerUrl = payload.url
    let url = ''
    if (typeof trackerUrl === 'string') url = trackerUrl
    else if (Array.isArray(trackerUrl)) url = trackerUrl.find((item) => typeof item === 'string' && item) || ''
    return { url, quality: String(payload.bitRate || payload.quality || quality), expires_at: payload.expire }
  },

  async lyric({ title, artist = '', hash, album_audio_id = null, duration = 0 }) {
    const keyword = artist ? `${artist} - ${title}` : title
    const lyricSearch = await requestKugou('search_lyric', {
      keywords: keyword,
      hash,
      album_audio_id: album_audio_id || 0,
      duration,
      man: 'no',
    })
    const candidates = Array.isArray(lyricSearch.candidates) ? lyricSearch.candidates : []
    const lyricCandidate = candidates.find((item) => item && typeof item === 'object') || {}
    const lyricId = String(lyricCandidate.id || '')
    const accessKey = String(lyricCandidate.accesskey || '')
    if (!lyricId || !accessKey) return { lines: [] }
    const lyricPayload = await requestKugou('lyric', { id: lyricId, accesskey: accessKey, fmt: 'lrc', decode: 'true' })
    return { lines: parseLrc(String(lyricPayload.decodeContent || '')) }
  },

  async trackMv({ album_audio_id }) {
    const payload = await requestKugou('kmr_audio_mv', {
      album_audio_id,
      fields: 'mkv,tags,h264,h265,authors',
    })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    return { items: firstList(data, ['info', 'list', 'lists', 'mvs', 'data']).map(normalizeMv) }
  },

  async trackClimax({ hash }) {
    const payload = await requestKugou('song_climax', { hash }, { useAuth: false })
    const rows = Array.isArray(payload.data) ? payload.data : []
    return {
      items: rows.filter((row) => row && typeof row === 'object').map((row) => ({
        hash: String(row.hash || ''),
        start: Number.parseInt(row.start || row.start_time || 0, 10),
        duration: Number.parseInt(row.duration || row.time || 0, 10),
      })),
    }
  },

  async relatedTracks({ album_audio_id, page = 1, page_size = 30, sort = 'all', type = null }) {
    const params = { album_audio_id, page, pagesize: page_size, sort }
    if (type) params.type = type
    const payload = await requestKugou('audio_related', params, { useAuth: false })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    const rows = firstList(data, ['info', 'list', 'lists', 'songs', 'data'])
    const total = data && typeof data === 'object' ? data.total || data.count || rows.length : rows.length
    return { items: rows.map(normalizeTrack), page, page_size, total }
  },

  async authStatus() {
    const userCookie = await authStore.read()
    const cookie = userCookie || DEFAULT_COOKIE
    return {
      logged_in: Boolean(cookieValue(cookie, 'token') && cookieValue(cookie, 'userid')),
      source: userCookie ? 'desktop' : (DEFAULT_COOKIE ? 'env' : ''),
      userid: cookieValue(cookie, 'userid'),
    }
  },

  async createQrLogin() {
    const keyPayload = await requestKugou('login_qr_key', {})
    const keyData = keyPayload.data && typeof keyPayload.data === 'object' ? keyPayload.data : {}
    const key = keyData.qrcode || keyData.key || keyData.qr_code || keyData.qrcode_txt
    if (!key) throw new DesktopMusicServiceError('KuGouMusicApi did not return QR login key')
    const qrPayload = await requestKugou('login_qr_create', { key, qrimg: 1 })
    const qrData = qrPayload.data && typeof qrPayload.data === 'object' ? qrPayload.data : {}
    return { key, url: qrData.url || '', base64: qrData.base64 || '' }
  },

  async checkQrLogin({ key }) {
    const response = await responseFromKugou('login_qr_check', { key, timestamp: Date.now() })
    const payload = response.body
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    const status = Number.parseInt(data.status || 0, 10)
    if (status === 4) await saveUserCookieFromLogin(data, response.cookie)
    return { status, logged_in: status === 4, auth: await service.authStatus() }
  },

  async userProfile() {
    const payload = await requestKugou('user_detail', {})
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    return {
      userid: String(data.userid || data.user_id || ''),
      nickname: data.nickname || data.k_nickname || data.user_name || '',
      avatar: formatImageUrl(data.pic || data.k_pic || data.fx_pic || ''),
      level: Number.parseInt(data.p_grade || data.level || 0, 10),
      gender: String(data.gender || ''),
      register_time: String(data.rtime || data.register_time || ''),
      follow_count: Number.parseInt(data.follows || 0, 10),
      fan_count: Number.parseInt(data.fans || 0, 10),
      listen_count: Number.parseInt(data.duration || 0, 10),
    }
  },

  async logout() {
    await authStore.clear()
    return ok()
  },

  async userVip() {
    const payload = await requestKugou('user_vip_detail', {})
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    return {
      is_vip: Boolean(data.is_vip || data.vip_type),
      vip_type: Number.parseInt(data.vip_type || 0, 10),
      vip_expire_time: String(data.vip_expire_time || data.expire_time || ''),
      vip_level: Number.parseInt(data.vip_level || 0, 10),
    }
  },

  async sendCaptcha({ phone }) {
    const payload = await requestKugou('captcha_sent', { mobile: phone }, { useAuth: false })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    return { ok: Boolean(data.ok || payload.ok || payload.status === 1) }
  },

  async loginCellphone({ phone, captcha }) {
    const response = await responseFromKugou('login_cellphone', { mobile: phone, code: captcha }, { useAuth: false })
    const payload = response.body
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    if (payload.ok || payload.status === 1 || data.token) {
      await saveUserCookieFromLogin(data, response.cookie)
      return { ok: true, logged_in: true, auth: await service.authStatus() }
    }
    throw new DesktopMusicServiceError(payload.message || payload.msg || 'Login failed')
  },

  async songComments({ mixsongid, page = 1, page_size = 20 }) {
    const payload = await requestKugou('comment_music', { mixsongid, p: page, pagesize: page_size })
    return commentPage(payload, page, page_size)
  },

  async songCommentsClassify({ mixsongid, type_id, page = 1, page_size = 20 }) {
    const payload = await requestKugou('comment_music_classify', { mixsongid, type_id, page, pagesize: page_size })
    return commentPage(payload, page, page_size)
  },

  async songCommentsHotword({ mixsongid }) {
    const payload = await requestKugou('comment_music_hotword', { mixsongid })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    return {
      items: firstList(data, ['cmtlist', 'list', 'lists', 'comments', 'info', 'items', 'data']).map((row) => ({
        keyword: String(row.keyword || row.word || row.hotword || ''),
        count: Number.parseInt(row.count || row.num || 0, 10),
      })),
    }
  },

  async floorComments({ special_id, mixsongid = null, page = 1, page_size = 20 }) {
    const params = { special_id, p: page, pagesize: page_size }
    if (mixsongid) params.mixsongid = mixsongid
    return commentPage(await requestKugou('comment_floor', params), page, page_size)
  },

  async playlistComments({ playlist_id, page = 1, page_size = 20 }) {
    return commentPage(await requestKugou('comment_playlist', { id: playlist_id, p: page, pagesize: page_size }), page, page_size)
  },

  async albumComments({ album_id, page = 1, page_size = 20 }) {
    return commentPage(await requestKugou('comment_album', { id: album_id, p: page, pagesize: page_size }), page, page_size)
  },

  async commentCount({ hash }) {
    const payload = await requestKugou('comment_count', { hash }, { useAuth: false })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload.data
    if (data && typeof data === 'object') return { count: Number.parseInt(data.count || data.cmtcount || data.num || 0, 10) }
    return { count: Number.parseInt(data || 0, 10) }
  },

  async followArtist({ artist_id }) {
    await requestKugou('artist_follow', { id: artist_id })
    return ok()
  },

  async unfollowArtist({ artist_id }) {
    await requestKugou('artist_unfollow', { id: artist_id })
    return ok()
  },

  async followedArtistNewSongs() {
    const payload = await requestKugou('artist_follow_newsongs', {})
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    return { items: firstList(data, ['songs', 'info', 'list', 'data']).map(normalizeTrack) }
  },

  async followedArtists() {
    const payload = await requestKugou('user_follow', {})
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    return { items: firstList(data, ['info', 'list', 'lists', 'data']).map(normalizeArtist) }
  },

  async videoDetail({ video_id }) {
    const payload = await requestKugou('video_detail', { id: video_id })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    return normalizeVideo(data)
  },

  async videoUrl({ video_id }) {
    const payload = await requestKugou('video_url', { id: video_id })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    return { url: data && typeof data === 'object' ? String(data.url || data.play_url || data.video_url || '') : '' }
  },

  async videoPrivilege({ video_id }) {
    const payload = await requestKugou('video_privilege', { id: video_id })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    return {
      id: String(data.id || data.video_id || ''),
      playable: Boolean(data.playable || data.can_play),
      downloadable: Boolean(data.downloadable || data.can_download),
      quality: String(data.quality || data.bitrate || ''),
    }
  },

  async artistVideos({ artist_id, page = 1, page_size = 20 }) {
    const payload = await requestKugou('artist_videos', { id: artist_id, page, pagesize: page_size })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    const rows = firstList(data, ['info', 'list', 'lists', 'videos', 'data'])
    const total = data && typeof data === 'object' ? data.total || data.count || rows.length : rows.length
    return { items: rows.map(normalizeVideo), page, page_size, total }
  },

  async artistHonour({ artist_id }) {
    const payload = await requestKugou('artist_honour', { id: artist_id })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    return {
      items: firstList(data, ['info', 'list', 'lists', 'honours', 'data']).map((row) => ({
        title: String(row.title || row.name || ''),
        description: String(row.desc || row.description || ''),
        date: String(row.date || row.time || ''),
      })),
    }
  },

  async artistDirectory({ page = 1, page_size = 30 } = {}) {
    const payload = await requestKugou('artist_lists', { page, pagesize: page_size })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    const rows = firstList(data, ['info', 'list', 'lists', 'data'])
    const total = data && typeof data === 'object' ? data.total || data.count || rows.length : rows.length
    return { items: rows.map(normalizeArtist), page, page_size, total }
  },

  async rankDetail({ rank_id }) {
    const payload = await requestKugou('rank_info', { rankid: rank_id })
    const data = payload.data && typeof payload.data === 'object' ? payload.data : {}
    return {
      id: String(data.rankid || rank_id),
      name: String(data.name || data.rankname || ''),
      cover: formatImageUrl(String(data.img || data.cover || data.banner || '')),
      intro: String(data.intro || data.description || ''),
      update_frequency: String(data.update_frequency || data.update || ''),
      song_count: Number.parseInt(data.song_count || data.total || 0, 10),
    }
  },

  async banner() {
    const payload = await requestKugou('yueku_banner', {})
    const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
    return {
      items: firstList(data, ['banner', 'banners', 'list', 'data']).map((row) => ({
        id: String(row.id || row.banner_id || ''),
        title: String(row.title || row.name || ''),
        cover: formatImageUrl(String(row.img || row.image || row.cover || '')),
        type: String(row.type || row.action_type || ''),
        target_id: String(row.target_id || row.id_extra || ''),
      })),
    }
  },
}

const commentPage = (payload, page, page_size) => {
  const data = payload.data && typeof payload.data === 'object' ? payload.data : payload
  const rows = firstList(data, ['cmtlist', 'list', 'lists', 'comments', 'info', 'items', 'data'])
  const total = data && typeof data === 'object'
    ? data.total || data.count || data.cmtcount || rows.length
    : rows.length
  return { items: rows.map(normalizeComment), page, page_size, total }
}

const cookieValueFromList = (cookies, key) => {
  if (!Array.isArray(cookies)) return ''
  for (const cookie of cookies) {
    const value = cookieValue(cookie, key)
    if (value) return value
  }
  return ''
}

const saveUserCookieFromLogin = async (data, cookies = []) => {
  const token = String(data.token || cookieValueFromList(cookies, 'token') || '')
  const kugouUserid = String(data.userid || cookieValueFromList(cookies, 'userid') || '')
  if (!token || !kugouUserid) {
    throw new DesktopMusicServiceError('KuGouMusicApi login response missed token or userid')
  }
  let dfid = cookieValue(await effectiveCookie(), 'dfid')
  if (!dfid) dfid = cookieValueFromList(cookies, 'dfid')
  const authCookie = [`token=${token}`, `userid=${kugouUserid}`]
  if (dfid) authCookie.push(`dfid=${dfid}`)
  await authStore.write(authCookie.join(';'))
}

export const callDesktopMusic = async (operation, payload = {}) => {
  const fn = service[operation]
  if (typeof fn !== 'function') {
    throw new DesktopMusicServiceError(`Unsupported music operation: ${operation}`)
  }
  return fn(payload || {})
}

export const __desktopMusicServiceForTests = service

export const __setDesktopMusicKugouForTests = (nextKugou) => {
  kugou = nextKugou || require('kugoumusicapi/main')
}

export const __setDesktopMusicAuthStoreForTests = (nextAuthStore) => {
  authStore = nextAuthStore || {
    read: readMusicAuthCookieDefault,
    write: writeMusicAuthCookieDefault,
    clear: clearMusicAuthCookieDefault,
  }
}
