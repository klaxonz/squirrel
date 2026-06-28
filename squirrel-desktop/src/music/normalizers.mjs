export const formatImageUrl = (value) => value ? String(value).replace('{size}', '240') : ''

export const millisecondsToSeconds = (value) => {
  const milliseconds = Number.parseInt(value || 0, 10)
  if (!Number.isFinite(milliseconds)) return 0
  return milliseconds > 1000 ? Math.round(milliseconds / 1000) : milliseconds
}

export const firstList = (data, keys) => {
  if (Array.isArray(data)) return data.filter((item) => item && typeof item === 'object')
  if (!data || typeof data !== 'object') return []
  for (const key of keys) {
    const value = data[key]
    if (Array.isArray(value)) return value.filter((item) => item && typeof item === 'object')
  }
  return []
}

const artistNames = (row) => {
  for (const key of ['authors', 'singerinfo']) {
    const rows = row[key]
    if (!Array.isArray(rows)) continue
    const names = rows
      .filter((item) => item && typeof item === 'object')
      .map((item) => item.author_name || item.name)
      .filter(Boolean)
    if (names.length) return names.join('、')
  }
  return ''
}

const artistId = (row) => {
  for (const key of ['SingerId', 'author_id', 'singerid']) {
    if (row[key]) return String(row[key])
  }
  for (const key of ['authors', 'singerinfo']) {
    const rows = row[key]
    if (!Array.isArray(rows)) continue
    for (const item of rows) {
      if (item && typeof item === 'object' && (item.author_id || item.id)) {
        return String(item.author_id || item.id)
      }
    }
  }
  return ''
}

export const normalizeTrack = (row = {}) => {
  if (row.info && typeof row.info === 'object') {
    row = { ...row, ...row.info, mxid: row.mxid || row.info.mxid }
  }
  const audioInfo = row.audio_info && typeof row.audio_info === 'object' ? row.audio_info : {}
  const albumInfo = row.album_info && typeof row.album_info === 'object' ? row.album_info : {}
  const albuminfo = row.albuminfo && typeof row.albuminfo === 'object' ? row.albuminfo : {}
  const base = row.base && typeof row.base === 'object' ? row.base : {}
  const transParam = row.trans_param && typeof row.trans_param === 'object' ? row.trans_param : {}
  const artist = row.SingerName || row.author_name || base.author_name || row.singername || artistNames(row) || ''
  let title = row.SongName || row.FileName || row.songname || base.audio_name || row.audio_name || row.name || ''

  if (title && artist) {
    title = String(title).trim()
    for (const suffix of ['.mp3', '.flac', '.m4a', '.aac', '.wav', '.ogg']) {
      if (title.toLowerCase().endsWith(suffix)) {
        title = title.slice(0, -suffix.length).trim()
        break
      }
    }
    for (const artistName of [String(artist), ...String(artist).split('、')]) {
      const prefix = `${artistName} - `
      if (title.startsWith(prefix)) {
        title = title.slice(prefix.length).trim()
        break
      }
    }
  }

  const duration = row.Duration
    || row.time_length
    || millisecondsToSeconds(row.duration)
    || millisecondsToSeconds(row.timelen)
    || millisecondsToSeconds(audioInfo.duration_128 || audioInfo.duration || row.timelength_128)

  const payload = {
    id: String(
      row.AlbumAudioID
      || row.MixSongID
      || row.album_audio_id
      || row.add_mixsongid
      || row.mixsongid
      || base.album_audio_id
      || row.Audioid
      || row.audio_id
      || row.FileHash
      || row.hash
      || ''
    ),
    title,
    artist,
    album: row.AlbumName || albumInfo.album_name || albuminfo.name || row.album_name || row.remark || '',
    hash: row.FileHash || row.hash || audioInfo.hash_128 || audioInfo.hash || '',
    album_id: String(row.AlbumID || row.album_id || base.album_id || albuminfo.id || ''),
    album_audio_id: String(
      row.AlbumAudioID
      || row.MixSongID
      || row.album_audio_id
      || row.add_mixsongid
      || row.mixsongid
      || base.album_audio_id
      || ''
    ),
    duration: Number.parseInt(duration || 0, 10),
    cover: formatImageUrl(
      row.Image
      || row.image
      || row.cover
      || row.pic
      || row.img
      || row.imgurl
      || row.sizable_cover
      || albumInfo.sizable_cover
      || albumInfo.cover
      || albumInfo.imgurl
      || albuminfo.sizable_cover
      || albuminfo.cover
      || albuminfo.imgurl
      || transParam.union_cover
      || ''
    ),
  }
  const currentArtistId = artistId(row)
  if (currentArtistId) payload.artist_id = currentArtistId
  const fileId = String(row.fileid || row.file_id || '')
  if (fileId) payload.file_id = fileId
  return payload
}

export const normalizeAlbum = (row = {}) => {
  const authors = Array.isArray(row.authors) ? row.authors : []
  const firstAuthor = authors.find((item) => item && typeof item === 'object') || {}
  const publishDate = row.publish_date || row.publishtime || ''
  return {
    id: String(row.album_id || row.albumid || ''),
    name: row.album_name || row.albumname || '',
    cover: formatImageUrl(row.sizable_cover || row.imgurl || ''),
    intro: row.intro || '',
    artist: row.author_name || row.singername || firstAuthor.author_name || '',
    artist_id: String(row.singerid || firstAuthor.author_id || ''),
    publish_date: publishDate ? String(publishDate).split(' ')[0] : '',
    language: row.language || '',
    type: row.type || '',
    heat: Number.parseInt(row.heat || 0, 10),
  }
}

export const normalizeAlbumFromTrack = (row = {}) => {
  const albumInfo = row.album_info && typeof row.album_info === 'object' ? row.album_info : {}
  return {
    id: String(row.AlbumID || row.album_id || ''),
    name: row.AlbumName || albumInfo.album_name || row.album_name || '',
    cover: formatImageUrl(row.Image || row.cover || albumInfo.sizable_cover || ''),
    intro: '',
    artist: row.SingerName || row.author_name || artistNames(row),
    artist_id: artistId(row),
    publish_date: '',
    language: '',
    type: '',
    heat: 0,
  }
}

export const normalizeArtist = (row = {}) => ({
  id: String(row.author_id || ''),
  name: row.author_name || '',
  avatar: formatImageUrl(row.sizable_avatar || ''),
  intro: row.intro || '',
  song_count: Number.parseInt(row.song_count || 0, 10),
  album_count: Number.parseInt(row.album_count || 0, 10),
  fan_count: Number.parseInt(row.fansnums || 0, 10),
})

export const normalizeArtistSearch = (row = {}) => ({
  id: String(row.AuthorId || row.author_id || ''),
  name: row.AuthorName || row.author_name || '',
  avatar: formatImageUrl(row.Avatar || row.sizable_avatar || ''),
  intro: row.Auxiliary || row.intro || '',
  song_count: Number.parseInt(row.AudioCount || row.song_count || 0, 10),
  album_count: Number.parseInt(row.AlbumCount || row.album_count || 0, 10),
  fan_count: Number.parseInt(row.FansNum || row.fansnums || 0, 10),
})

export const normalizeRank = (row = {}) => ({
  id: String(row.rankid || row.id || ''),
  rank_cid: String(row.rank_cid || ''),
  name: row.rankname || '',
  cover: formatImageUrl(row.imgurl || row.album_img_9 || row.banner_9 || ''),
  intro: row.intro || '',
  update_frequency: row.update_frequency || '',
  play_count: Number.parseInt(row.play_times || 0, 10),
})

export const normalizePlaylist = (row = {}) => {
  const tags = Array.isArray(row.tags) ? row.tags : []
  return {
    id: String(row.global_collection_id || ''),
    name: row.specialname || '',
    cover: formatImageUrl(row.flexible_cover || row.imgurl || ''),
    intro: row.intro || '',
    creator: row.nickname || '',
    play_count: Number.parseInt(row.play_count || 0, 10),
    collect_count: Number.parseInt(row.collectcount || 0, 10),
    tags: tags.filter((tag) => tag && typeof tag === 'object' && tag.tag_name).map((tag) => tag.tag_name),
    list_create_userid: String(row.list_create_userid || row.suid || ''),
    list_create_listid: String(row.list_create_listid || row.specialid || ''),
    list_create_gid: String(row.list_create_gid || row.global_collection_id || ''),
  }
}

export const normalizePlaylistTags = (rows) => {
  const tags = []
  for (const group of rows) {
    let children = Array.isArray(group.children) ? group.children : group.tags
    if (!Array.isArray(children)) children = [group]
    for (const row of children) {
      if (!row || typeof row !== 'object') continue
      const tagId = String(row.tag_id || row.id || row.category_id || '')
      const name = String(row.tag_name || row.name || row.category_name || '')
      if (!tagId || !name) continue
      tags.push({
        id: tagId,
        name,
        parent_id: String(group.tag_id || group.id || ''),
        parent_name: String(group.tag_name || group.name || ''),
      })
    }
  }
  return tags
}

export const normalizeHotSearch = (row = {}) => ({
  keyword: String(row.keyword || row.word || row.name || row.search_word || ''),
  score: Number.parseInt(row.score || row.hot || row.heat || 0, 10),
  jump_url: String(row.jump_url || row.url || ''),
})

export const normalizeSuggestionItems = (data) => {
  let rows = firstList(data, ['info', 'list', 'lists', 'data'])
  if (!rows.length && data && typeof data === 'object' && !Array.isArray(data)) {
    rows = Object.values(data)
      .filter(Array.isArray)
      .flat()
      .filter((item) => item && typeof item === 'object')
  }
  return rows.map((row) => ({
    keyword: String(row.keyword || row.HintInfo || row.name || row.SongName || ''),
    type: String(row.type || row.search_type || row.RecordType || ''),
  }))
}

export const parseLrc = (content) => {
  const lines = []
  for (const rawLine of String(content || '').split(/\r?\n/)) {
    if (!rawLine.startsWith('[') || !rawLine.includes(']')) continue
    const lastBracket = rawLine.lastIndexOf(']')
    const text = rawLine.slice(lastBracket + 1).trim()
    for (const timestamp of rawLine.slice(0, lastBracket + 1).split(']')) {
      if (!timestamp.startsWith('[')) continue
      const seconds = parseLrcTimestamp(timestamp.slice(1))
      if (seconds >= 0) lines.push({ time: seconds, text })
    }
  }
  return lines.sort((a, b) => a.time - b.time)
}

const parseLrcTimestamp = (value) => {
  if (!value.includes(':')) return -1
  const [minutesText, secondsText] = value.split(':', 2)
  const minutes = Number.parseInt(minutesText, 10)
  const seconds = Number.parseFloat(secondsText)
  if (!Number.isFinite(minutes) || !Number.isFinite(seconds)) return -1
  return minutes * 60 + seconds
}

export const normalizeComment = (row = {}) => {
  const userInfo = row.user_info && typeof row.user_info === 'object' ? row.user_info : {}
  const user = row.user && typeof row.user === 'object' ? row.user : {}
  const mergedUser = Object.keys(user).length ? { ...user, ...userInfo } : userInfo
  return {
    id: String(row.id || row.comment_id || row.specialid || row.cmtid || ''),
    content: String(row.content || row.msg || row.message || row.cmtcontent || ''),
    user_name: String(
      mergedUser.nickname
      || mergedUser.user_name
      || mergedUser.user_nickname
      || row.user_name
      || row.nickname
      || row.nick_name
      || ''
    ),
    user_avatar: formatImageUrl(
      mergedUser.pic
      || mergedUser.avatar
      || mergedUser.user_pic
      || row.user_pic
      || row.avatar
      || row.user_avatar
      || ''
    ),
    user_id: String(mergedUser.userid || mergedUser.user_id || row.userid || ''),
    like_count: Number.parseInt(row.likecount || row.like_count || row.support || row.support_count || 0, 10),
    reply_count: Number.parseInt(row.replycount || row.reply_count || row.reply_num || 0, 10),
    created_at: String(row.addtime || row.add_time || row.create_time || row.creattime || ''),
  }
}

export const normalizeMv = (row = {}) => ({
  id: String(row.id || row.video_id || row.mv_id || ''),
  name: String(row.name || row.title || row.filename || ''),
  hash: String(row.hash || row.mv_hash || row.FileHash || ''),
  cover: formatImageUrl(row.cover || row.img || row.imgurl || ''),
  duration: Number.parseInt(row.duration || row.time_length || 0, 10),
})

export const normalizeVideo = (row = {}) => {
  const authors = Array.isArray(row.authors) ? row.authors : []
  const author = authors.find((item) => item && typeof item === 'object' && (item.author_name || item.name))
  return {
    id: String(row.id || row.video_id || row.mv_id || ''),
    name: String(row.name || row.title || row.filename || ''),
    cover: formatImageUrl(row.cover || row.img || row.imgurl || row.cover_url || ''),
    duration: Number.parseInt(row.duration || row.time_length || 0, 10),
    play_count: Number.parseInt(row.play_count || row.playcount || 0, 10),
    artist: (author && (author.author_name || author.name)) || String(row.author_name || row.singer_name || ''),
    artist_id: String(row.author_id || row.singer_id || ''),
  }
}
