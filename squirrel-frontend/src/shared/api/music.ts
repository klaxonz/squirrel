import { get, post, request } from '@/shared/lib/request'

const desktopMusic = <T>(operation: string, payload?: unknown): Promise<T> | null => {
  const bridge = window.desktopApp
  if (bridge?.isDesktop === true && typeof bridge.callMusic === 'function') {
    return bridge.callMusic<T>(operation, payload)
  }
  return null
}

const musicGet = <T>(operation: string, url: string, params?: unknown) => {
  return desktopMusic<T>(operation, params) ?? get<T>(url, params)
}

const musicPost = <T>(operation: string, url: string, data?: unknown) => {
  return desktopMusic<T>(operation, data) ?? post<T>(url, data)
}

const musicDelete = <T>(operation: string, url: string, params?: unknown) => {
  return desktopMusic<T>(operation, params) ?? request<T>({ url, method: 'delete', params })
}

export type MusicTrack = {
  id: string
  title: string
  artist: string
  artist_id?: string
  album: string
  hash: string
  album_id: string
  album_audio_id: string
  duration: number
  cover: string
  file_id?: string
}

export type MusicArtist = {
  id: string
  name: string
  avatar: string
  intro: string
  song_count: number
  album_count: number
  fan_count: number
}

export type MusicAlbum = {
  id: string
  name: string
  cover: string
  intro: string
  artist: string
  artist_id: string
  publish_date: string
  language: string
  type: string
  heat: number
}

export type MusicAlbumResult = {
  items: MusicAlbum[]
  page: number
  page_size: number
  total: number
}

export type MusicHotSearch = {
  keyword: string
  score: number
  jump_url: string
}

export type MusicHotSearchResult = {
  items: MusicHotSearch[]
}

export type MusicSearchDefaultResult = {
  keyword: string
}

export type MusicSearchSuggestion = {
  keyword: string
  type: string
}

export type MusicSearchSuggestionResult = {
  items: MusicSearchSuggestion[]
}

export type MusicArtistResult = {
  items: MusicArtist[]
  page: number
  page_size: number
  total: number
}

export type MusicSearchResult = {
  items: MusicTrack[]
  page: number
  page_size: number
  total: number
}

export type MusicRecommendCardResult = MusicSearchResult & {
  card_id: number
  title: string
}

export type MusicDailyRecommendResult = MusicSearchResult & {
  cover: string
}

export type MusicRank = {
  id: string
  rank_cid: string
  name: string
  cover: string
  intro: string
  update_frequency: string
  play_count: number
}

export type MusicRankResult = {
  items: MusicRank[]
  total: number
}

export type MusicPlaylist = {
  specialid?: string
  global_collection_id?: string
  id?: string
  specialname?: string
  name?: string
  imgurl?: string
  cover?: string
  intro?: string
  nickname?: string
  creator?: string
  play_count?: number
  collectcount?: number
  collect_count?: number
  tags?: Array<{ tag_name: string }>
  list_create_userid?: string
  list_create_listid?: string
  list_create_gid?: string
}

export type MusicPlaylistResult = {
  items: MusicPlaylist[]
  page: number
  page_size: number
  has_more: boolean
}

export type MusicPlaylistTag = {
  id: string
  name: string
  parent_name: string
}

export type MusicPlaylistTagResult = {
  items: MusicPlaylistTag[]
}

export type MusicUserPlaylist = {
  listid: number | string
  name: string
  pic?: string
  type?: number | string
  is_def?: number | string
  m_count?: number | string
  count?: number | string
  list_create_userid?: number | string
  list_create_listid?: number | string
  list_create_gid?: string
}

export type MusicUserPlaylistResult = {
  items: MusicUserPlaylist[]
  page: number
  page_size: number
  total: number
}

export type MusicPlayUrl = {
  url: string
  quality: string
  expires_at?: string | null
}

export type MusicLyricLine = {
  time: number
  text: string
}

export type MusicLyricResult = {
  lines: MusicLyricLine[]
}

export type MusicAuthStatus = {
  logged_in: boolean
  source: string
  userid: string
}

export type MusicQrLogin = {
  key: string
  url: string
  base64: string
}

export type MusicQrLoginStatus = {
  status: number
  logged_in: boolean
  auth: MusicAuthStatus
}

export type MusicFavoriteCount = {
  mixsongid: string
  count: number
  count_text: string
}

export type MusicFavoriteCountResult = {
  items: MusicFavoriteCount[]
}

export type MusicTrackClimax = {
  hash: string
  start: number
  duration: number
}

export type MusicTrackClimaxResult = {
  items: MusicTrackClimax[]
}

export type MusicTrackMv = {
  id: string
  name: string
  hash: string
  cover: string
  duration: number
}

export type MusicTrackMvResult = {
  items: MusicTrackMv[]
}

export type MusicActionResult = {
  ok: boolean
}

export const searchMusic = (params: {
  query: string
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicSearchResult>('searchTracks', '/api/music/search', params)
}

export const searchMusicArtists = (params: {
  query: string
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicArtistResult>('searchArtists', '/api/music/search/artists', params)
}

export const searchMusicAlbums = (params: {
  query: string
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicAlbumResult>('searchAlbums', '/api/music/search/albums', params)
}

export const getMusicDefaultSearch = () => {
  return musicGet<MusicSearchDefaultResult>('defaultSearch', '/api/music/search/default')
}

export const getMusicHotSearch = () => {
  return musicGet<MusicHotSearchResult>('hotSearch', '/api/music/search/hot')
}

export const getMusicSearchSuggestions = (query: string) => {
  return musicGet<MusicSearchSuggestionResult>('searchSuggest', '/api/music/search/suggest', { query })
}

export const getMusicRanks = () => {
  return musicGet<MusicRankResult>('ranks', '/api/music/ranks')
}

export type FmParams = {
  mode?: 'normal' | 'small' | 'peak'
  song_pool_id?: string
  action?: string
  hash?: string
  songid?: string
  playtime?: number
  is_overplay?: boolean
  remain_songcnt?: number
}

export const getMusicRecommendations = (params?: FmParams) => {
  return musicGet<MusicSearchResult>('recommendations', '/api/music/recommend', params)
}

export const getMusicRecommendCard = (params?: {
  card_id?: number
  page_size?: number
}) => {
  return musicGet<MusicRecommendCardResult>('recommendCard', '/api/music/recommend/card', params)
}

export const getMusicDailyRecommend = (params?: {
  page_size?: number
}) => {
  return musicGet<MusicDailyRecommendResult>('dailyRecommend', '/api/music/recommend/daily', params)
}

export const reportFmGarbage = (params: {
  hash: string
  songid?: string
  playtime?: number
  mode?: string
  song_pool_id?: string
}) => {
  return musicGet<MusicSearchResult>('recommendations', '/api/music/fm/garbage', { ...params, action: 'garbage', is_overplay: true })
}

export const getMusicRankTracks = (params: {
  rank_id: string
  rank_cid?: string
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicSearchResult>('rankTracks', '/api/music/rank/tracks', params)
}

export const getMusicPlaylists = (params: {
  category_id?: number
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicPlaylistResult>('playlists', '/api/music/playlists', params)
}

export const getMusicPlaylistTags = () => {
  return musicGet<MusicPlaylistTagResult>('playlistTags', '/api/music/playlist/tags')
}

export const getMusicSimilarPlaylists = (playlist_id: string) => {
  return musicGet<MusicPlaylistResult>('similarPlaylists', '/api/music/playlist/similar', { playlist_id })
}

export const getMusicPlaylistTracks = (params: {
  playlist_id: string
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicSearchResult>('playlistTracks', '/api/music/playlist/tracks', params)
}

export const getMusicUserPlaylists = (params?: {
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicUserPlaylistResult>('userPlaylists', '/api/music/user/playlists', params)
}

export const getMusicUserPlaylistTracks = (params: {
  list_id: string
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicSearchResult>('userPlaylistTracks', '/api/music/user/playlist/tracks', params)
}

export const getMusicArtistDetail = (artist_id: string) => {
  return musicGet<MusicArtist>('artistDetail', '/api/music/artist/detail', { artist_id })
}

export const getMusicArtistTracks = (params: {
  artist_id: string
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicSearchResult>('artistTracks', '/api/music/artist/tracks', params)
}

export const getMusicArtistAlbums = (params: {
  artist_id: string
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicAlbumResult>('artistAlbums', '/api/music/artist/albums', params)
}

export const getMusicAlbumDetail = (album_id: string) => {
  return musicGet<MusicAlbum>('albumDetail', '/api/music/album/detail', { album_id })
}

export const getMusicAlbumTracks = (params: {
  album_id: string
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicSearchResult>('albumTracks', '/api/music/album/tracks', params)
}

export const getMusicNewSongs = (params?: {
  type?: number
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicSearchResult>('newSongs', '/api/music/songs/new', params)
}

export const createMusicUserPlaylist = (data: {
  name: string
  is_private?: boolean
}) => {
  return musicPost<MusicActionResult>('createUserPlaylist', '/api/music/user/playlists', data)
}

export const collectMusicPlaylist = (playlist_id: string) => {
  return musicPost<MusicActionResult>('collectPlaylist', '/api/music/user/playlists/collect', { playlist_id })
}

export const deleteMusicUserPlaylist = (list_id: string) => {
  return musicDelete<MusicActionResult>('deleteUserPlaylist', '/api/music/user/playlists', { list_id })
}

export const addMusicUserPlaylistTrack = (data: {
  list_id: string
  track: Pick<MusicTrack, 'title' | 'hash' | 'album_id' | 'album_audio_id'>
}) => {
  return musicPost<MusicActionResult>('addUserPlaylistTrack', '/api/music/user/playlist/tracks', data)
}

export const removeMusicUserPlaylistTracks = (params: {
  list_id: string
  file_ids: string
}) => {
  return musicDelete<MusicActionResult>('removeUserPlaylistTracks', '/api/music/user/playlist/tracks', params)
}

export const getMusicUserHistory = (params?: {
  bp?: string
}) => {
  return musicGet<MusicSearchResult & { bp?: string }>('userHistory', '/api/music/user/history', params)
}

export const getMusicUserListenRank = (params?: {
  type?: 0 | 1
}) => {
  return musicGet<MusicSearchResult>('userListenRank', '/api/music/user/listen-rank', params)
}

export const getMusicLatestListenSongs = (params?: {
  page_size?: number
}) => {
  return musicGet<MusicSearchResult>('latestListenSongs', '/api/music/latest-songs/listen', params)
}

export const uploadMusicPlayHistory = (data: {
  album_audio_id: string
  played_at?: number
  play_count?: number
}) => {
  return musicPost<MusicActionResult>('uploadPlayHistory', '/api/music/playhistory', data)
}

export const getMusicFavoriteCount = (mixsongids: string) => {
  return musicGet<MusicFavoriteCountResult>('favoriteCount', '/api/music/favorite/count', { mixsongids })
}

export const getMusicPlayUrl = (params: {
  hash: string
  album_id?: string
  album_audio_id?: string
  quality?: string
}) => {
  return musicGet<MusicPlayUrl>('playUrl', '/api/music/play-url', params)
}

export const getMusicTrackClimax = (hash: string) => {
  return musicGet<MusicTrackClimaxResult>('trackClimax', '/api/music/song/climax', { hash })
}

export const getMusicRelatedTracks = (params: {
  album_audio_id: string
  page?: number
  page_size?: number
  sort?: 'all' | 'hot' | 'new'
  type?: string
}) => {
  return musicGet<MusicSearchResult>('relatedTracks', '/api/music/song/related', params)
}

export const getMusicTrackMv = (album_audio_id: string) => {
  return musicGet<MusicTrackMvResult>('trackMv', '/api/music/song/mv', { album_audio_id })
}

export const getMusicLyric = (params: {
  title: string
  artist?: string
  hash: string
  album_audio_id?: string
  duration?: number
}) => {
  return musicGet<MusicLyricResult>('lyric', '/api/music/lyric', params)
}

export type MusicUserProfile = {
  userid: string
  nickname: string
  avatar: string
  level: number
  gender: string
  register_time: string
  follow_count: number
  fan_count: number
  listen_count: number
}

export const getMusicUserProfile = () => {
  return musicGet<MusicUserProfile>('userProfile', '/api/music/user/profile')
}

export const logoutMusicUser = () => {
  return musicPost<{ ok: boolean }>('logout', '/api/music/user/logout')
}

export const getMusicAuthStatus = () => {
  return musicGet<MusicAuthStatus>('authStatus', '/api/music/auth/status')
}

export const createMusicQrLogin = () => {
  return musicPost<MusicQrLogin>('createQrLogin', '/api/music/auth/qr')
}

export const checkMusicQrLogin = (key: string) => {
  return musicGet<MusicQrLoginStatus>('checkQrLogin', '/api/music/auth/qr/check', { key })
}

export const logoutMusic = () => {
  return musicPost<MusicActionResult>('logout', '/api/music/auth/logout')
}

// --- Comments ---

export type MusicComment = {
  id: string
  content: string
  user_name: string
  user_avatar: string
  user_id: string
  like_count: number
  reply_count: number
  created_at: string
}

export type MusicCommentResult = {
  items: MusicComment[]
  page: number
  page_size: number
  total: number
}

export type MusicCommentHotword = {
  keyword: string
  count: number
}

export type MusicCommentHotwordResult = {
  items: MusicCommentHotword[]
}

export type MusicCommentCount = {
  count: number
}

export const getMusicSongComments = (params: {
  mixsongid: string
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicCommentResult>('songComments', '/api/music/comment/song', params)
}

export const getMusicSongCommentsClassify = (params: {
  mixsongid: string
  type_id: string
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicCommentResult>('songCommentsClassify', '/api/music/comment/song/classify', params)
}

export const getMusicSongCommentsHotword = (mixsongid: string) => {
  return musicGet<MusicCommentHotwordResult>('songCommentsHotword', '/api/music/comment/song/hotword', { mixsongid })
}

export const getMusicFloorComments = (params: {
  special_id: string
  mixsongid?: string
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicCommentResult>('floorComments', '/api/music/comment/floor', params)
}

export const getMusicPlaylistComments = (params: {
  playlist_id: string
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicCommentResult>('playlistComments', '/api/music/comment/playlist', params)
}

export const getMusicAlbumComments = (params: {
  album_id: string
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicCommentResult>('albumComments', '/api/music/comment/album', params)
}

export const getMusicCommentCounts = (hash: string) => {
  return musicGet<MusicCommentCount>('commentCount', '/api/music/comment/count', { hash })
}

// --- Artist Follow ---

export const followMusicArtist = (artist_id: string) => {
  return musicPost<MusicActionResult>('followArtist', `/api/music/artist/follow?artist_id=${encodeURIComponent(artist_id)}`, { artist_id })
}

export const unfollowMusicArtist = (artist_id: string) => {
  return musicDelete<MusicActionResult>('unfollowArtist', '/api/music/artist/follow', { artist_id })
}

export const getMusicFollowedArtistNewSongs = () => {
  return musicGet<MusicSearchResult>('followedArtistNewSongs', '/api/music/artist/follow/newsongs')
}

export const getMusicFollowedArtists = () => {
  return musicGet<MusicArtistResult>('followedArtists', '/api/music/user/followed-artists')
}

// --- Video / MV ---

export type MusicVideo = {
  id: string
  name: string
  cover: string
  duration: number
  play_count: number
  artist: string
  artist_id: string
}

export type MusicVideoResult = {
  items: MusicVideo[]
  page: number
  page_size: number
  total: number
}

export type MusicVideoUrl = {
  url: string
}

export type MusicVideoPrivilege = {
  id: string
  playable: boolean
  downloadable: boolean
  quality: string
}

export const getMusicVideoDetail = (video_id: string) => {
  return musicGet<MusicVideo>('videoDetail', '/api/music/video/detail', { video_id })
}

export const getMusicVideoUrl = (video_id: string) => {
  return musicGet<MusicVideoUrl>('videoUrl', '/api/music/video/url', { video_id })
}

export const getMusicVideoPrivilege = (video_id: string) => {
  return musicGet<MusicVideoPrivilege>('videoPrivilege', '/api/music/video/privilege', { video_id })
}

// --- Discovery & Recommendation Enhancements ---

export const getMusicNewAlbums = (params?: {
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicAlbumResult>('newAlbums', '/api/music/albums/new', params)
}

export const getMusicAiRecommend = (params?: {
  page_size?: number
}) => {
  return musicGet<MusicSearchResult>('aiRecommend', '/api/music/recommend/ai', params)
}

export const getMusicEverydayRecommend = () => {
  return musicGet<MusicSearchResult>('everydayRecommend', '/api/music/recommend/everyday')
}

export const getMusicStyleRecommend = () => {
  return musicGet<MusicSearchResult>('styleRecommend', '/api/music/recommend/style')
}

export const getMusicArtistVideos = (params: {
  artist_id: string
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicVideoResult>('artistVideos', '/api/music/artist/videos', params)
}

export type MusicArtistHonour = {
  title: string
  description: string
  date: string
}

export type MusicArtistHonourResult = {
  items: MusicArtistHonour[]
}

export const getMusicArtistHonour = (artist_id: string) => {
  return musicGet<MusicArtistHonourResult>('artistHonour', '/api/music/artist/honour', { artist_id })
}

export const getMusicArtistDirectory = (params?: {
  page?: number
  page_size?: number
}) => {
  return musicGet<MusicArtistResult>('artistDirectory', '/api/music/artists/directory', params)
}

export const getMusicRankDetail = (rank_id: string) => {
  return musicGet<{
    id: string
    name: string
    cover: string
    intro: string
    update_frequency: string
    song_count: number
  }>('rankDetail', '/api/music/rank/detail', { rank_id })
}

export const getMusicBanner = () => {
  return musicGet<{
    items: Array<{
      id: string
      title: string
      cover: string
      type: string
      target_id: string
    }>
  }>('banner', '/api/music/banner')
}

export const searchMusicComplex = (query: string) => {
  return musicGet<{
    songs: MusicTrack[]
    artists: MusicArtist[]
    albums: MusicAlbum[]
  }>('complexSearch', '/api/music/search/complex', { query })
}

export const getMusicUserVip = () => {
  return musicGet<{
    is_vip: boolean
    vip_type: number
    vip_expire_time: string
    vip_level: number
  }>('userVip', '/api/music/user/vip')
}

export const sendMusicCaptcha = (phone: string) => {
  return musicPost<{ ok: boolean }>('sendCaptcha', '/api/music/auth/captcha', { phone })
}

export const loginMusicCellphone = (phone: string, captcha: string) => {
  return musicPost<{
    ok: boolean
    logged_in: boolean
    auth: MusicAuthStatus
  }>('loginCellphone', '/api/music/auth/login', { phone, captcha })
}
