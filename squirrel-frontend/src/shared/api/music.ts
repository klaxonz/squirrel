import { get, post, request } from '@/shared/lib/request'

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
  id: string
  name: string
  cover: string
  intro: string
  creator: string
  play_count: number
  collect_count: number
  tags: string[]
  list_create_userid: string
  list_create_listid: string
  list_create_gid: string
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
  id: string
  name: string
  cover: string
  song_count: number
  is_default: boolean
  is_collected: boolean
  list_create_userid: string
  list_create_listid: string
  list_create_gid: string
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
  return get<MusicSearchResult>('/api/music/search', params)
}

export const searchMusicArtists = (params: {
  query: string
  page?: number
  page_size?: number
}) => {
  return get<MusicArtistResult>('/api/music/search/artists', params)
}

export const searchMusicAlbums = (params: {
  query: string
  page?: number
  page_size?: number
}) => {
  return get<MusicAlbumResult>('/api/music/search/albums', params)
}

export const getMusicDefaultSearch = () => {
  return get<MusicSearchDefaultResult>('/api/music/search/default')
}

export const getMusicHotSearch = () => {
  return get<MusicHotSearchResult>('/api/music/search/hot')
}

export const getMusicSearchSuggestions = (query: string) => {
  return get<MusicSearchSuggestionResult>('/api/music/search/suggest', { query })
}

export const getMusicRanks = () => {
  return get<MusicRankResult>('/api/music/ranks')
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
  return get<MusicSearchResult>('/api/music/recommend', params)
}

export const getMusicRecommendCard = (params?: {
  card_id?: number
  page_size?: number
}) => {
  return get<MusicRecommendCardResult>('/api/music/recommend/card', params)
}

export const getMusicDailyRecommend = (params?: {
  page_size?: number
}) => {
  return get<MusicDailyRecommendResult>('/api/music/recommend/daily', params)
}

export const reportFmGarbage = (params: {
  hash: string
  songid?: string
  playtime?: number
  mode?: string
  song_pool_id?: string
}) => {
  return get<MusicSearchResult>('/api/music/fm/garbage', params)
}

export const getMusicRankTracks = (params: {
  rank_id: string
  rank_cid?: string
  page?: number
  page_size?: number
}) => {
  return get<MusicSearchResult>('/api/music/rank/tracks', params)
}

export const getMusicPlaylists = (params: {
  category_id?: number
  page?: number
  page_size?: number
}) => {
  return get<MusicPlaylistResult>('/api/music/playlists', params)
}

export const getMusicPlaylistTags = () => {
  return get<MusicPlaylistTagResult>('/api/music/playlist/tags')
}

export const getMusicSimilarPlaylists = (playlist_id: string) => {
  return get<MusicPlaylistResult>('/api/music/playlist/similar', { playlist_id })
}

export const getMusicPlaylistTracks = (params: {
  playlist_id: string
  page?: number
  page_size?: number
}) => {
  return get<MusicSearchResult>('/api/music/playlist/tracks', params)
}

export const getMusicUserPlaylists = (params?: {
  page?: number
  page_size?: number
}) => {
  return get<MusicUserPlaylistResult>('/api/music/user/playlists', params)
}

export const getMusicUserPlaylistTracks = (params: {
  list_id: string
  page?: number
  page_size?: number
}) => {
  return get<MusicSearchResult>('/api/music/user/playlist/tracks', params)
}

export const getMusicArtistDetail = (artist_id: string) => {
  return get<MusicArtist>('/api/music/artist/detail', { artist_id })
}

export const getMusicArtistTracks = (params: {
  artist_id: string
  page?: number
  page_size?: number
}) => {
  return get<MusicSearchResult>('/api/music/artist/tracks', params)
}

export const getMusicArtistAlbums = (params: {
  artist_id: string
  page?: number
  page_size?: number
}) => {
  return get<MusicAlbumResult>('/api/music/artist/albums', params)
}

export const getMusicAlbumDetail = (album_id: string) => {
  return get<MusicAlbum>('/api/music/album/detail', { album_id })
}

export const getMusicAlbumTracks = (params: {
  album_id: string
  page?: number
  page_size?: number
}) => {
  return get<MusicSearchResult>('/api/music/album/tracks', params)
}

export const getMusicNewSongs = (params?: {
  type?: number
  page?: number
  page_size?: number
}) => {
  return get<MusicSearchResult>('/api/music/songs/new', params)
}

export const createMusicUserPlaylist = (data: {
  name: string
  is_private?: boolean
}) => {
  return post<MusicActionResult>('/api/music/user/playlists', data)
}

export const collectMusicPlaylist = (playlist_id: string) => {
  return post<MusicActionResult>('/api/music/user/playlists/collect', { playlist_id })
}

export const deleteMusicUserPlaylist = (list_id: string) => {
  return request<MusicActionResult>({ url: '/api/music/user/playlists', method: 'delete', params: { list_id } })
}

export const addMusicUserPlaylistTrack = (data: {
  list_id: string
  track: Pick<MusicTrack, 'title' | 'hash' | 'album_id' | 'album_audio_id'>
}) => {
  return post<MusicActionResult>('/api/music/user/playlist/tracks', data)
}

export const removeMusicUserPlaylistTracks = (params: {
  list_id: string
  file_ids: string
}) => {
  return request<MusicActionResult>({ url: '/api/music/user/playlist/tracks', method: 'delete', params })
}

export const getMusicUserHistory = (params?: {
  bp?: string
}) => {
  return get<MusicSearchResult & { bp?: string }>('/api/music/user/history', params)
}

export const getMusicUserListenRank = (params?: {
  type?: 0 | 1
}) => {
  return get<MusicSearchResult>('/api/music/user/listen-rank', params)
}

export const getMusicLatestListenSongs = (params?: {
  page_size?: number
}) => {
  return get<MusicSearchResult>('/api/music/latest-songs/listen', params)
}

export const uploadMusicPlayHistory = (data: {
  album_audio_id: string
  played_at?: number
  play_count?: number
}) => {
  return post<MusicActionResult>('/api/music/playhistory', data)
}

export const getMusicFavoriteCount = (mixsongids: string) => {
  return get<MusicFavoriteCountResult>('/api/music/favorite/count', { mixsongids })
}

export const addMusicFavorite = (album_audio_id: string) => {
  return post<MusicActionResult>('/api/music/favorite', { album_audio_id })
}

export const removeMusicFavorite = (album_audio_id: string) => {
  return request<MusicActionResult>({ url: '/api/music/favorite', method: 'delete', params: { album_audio_id } })
}

export const getMusicPlayUrl = (params: {
  hash: string
  album_audio_id?: string
  quality?: string
}) => {
  return get<MusicPlayUrl>('/api/music/play-url', params)
}

export const getMusicTrackClimax = (hash: string) => {
  return get<MusicTrackClimaxResult>('/api/music/song/climax', { hash })
}

export const getMusicRelatedTracks = (params: {
  album_audio_id: string
  page?: number
  page_size?: number
  sort?: 'all' | 'hot' | 'new'
  type?: string
}) => {
  return get<MusicSearchResult>('/api/music/song/related', params)
}

export const getMusicTrackMv = (album_audio_id: string) => {
  return get<MusicTrackMvResult>('/api/music/song/mv', { album_audio_id })
}

export const getMusicLyric = (params: {
  title: string
  artist?: string
  hash: string
  album_audio_id?: string
  duration?: number
}) => {
  return get<MusicLyricResult>('/api/music/lyric', params)
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
  return get<MusicUserProfile>('/api/music/user/profile')
}

export const logoutMusicUser = () => {
  return post<{ ok: boolean }>('/api/music/user/logout')
}

export const getMusicAuthStatus = () => {
  return get<MusicAuthStatus>('/api/music/auth/status')
}

export const createMusicQrLogin = () => {
  return post<MusicQrLogin>('/api/music/auth/qr')
}

export const checkMusicQrLogin = (key: string) => {
  return get<MusicQrLoginStatus>('/api/music/auth/qr/check', { key })
}

export const logoutMusic = () => {
  return post<MusicActionResult>('/api/music/auth/logout')
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
  return get<MusicCommentResult>('/api/music/comment/song', params)
}

export const getMusicSongCommentsClassify = (params: {
  mixsongid: string
  type_id: string
  page?: number
  page_size?: number
}) => {
  return get<MusicCommentResult>('/api/music/comment/song/classify', params)
}

export const getMusicSongCommentsHotword = (mixsongid: string) => {
  return get<MusicCommentHotwordResult>('/api/music/comment/song/hotword', { mixsongid })
}

export const getMusicFloorComments = (params: {
  special_id: string
  mixsongid?: string
  page?: number
  page_size?: number
}) => {
  return get<MusicCommentResult>('/api/music/comment/floor', params)
}

export const getMusicPlaylistComments = (params: {
  playlist_id: string
  page?: number
  page_size?: number
}) => {
  return get<MusicCommentResult>('/api/music/comment/playlist', params)
}

export const getMusicAlbumComments = (params: {
  album_id: string
  page?: number
  page_size?: number
}) => {
  return get<MusicCommentResult>('/api/music/comment/album', params)
}

export const getMusicCommentCounts = (hash: string) => {
  return get<MusicCommentCount>('/api/music/comment/count', { hash })
}

// --- Artist Follow ---

export const followMusicArtist = (artist_id: string) => {
  return post<MusicActionResult>(`/api/music/artist/follow?artist_id=${encodeURIComponent(artist_id)}`)
}

export const unfollowMusicArtist = (artist_id: string) => {
  return request<MusicActionResult>({
    url: '/api/music/artist/follow',
    method: 'delete',
    params: { artist_id },
  })
}

export const getMusicFollowedArtistNewSongs = () => {
  return get<MusicSearchResult>('/api/music/artist/follow/newsongs')
}

export const getMusicFollowedArtists = () => {
  return get<MusicArtistResult>('/api/music/user/followed-artists')
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
  return get<MusicVideo>('/api/music/video/detail', { video_id })
}

export const getMusicVideoUrl = (video_id: string) => {
  return get<MusicVideoUrl>('/api/music/video/url', { video_id })
}

export const getMusicVideoPrivilege = (video_id: string) => {
  return get<MusicVideoPrivilege>('/api/music/video/privilege', { video_id })
}

// --- Discovery & Recommendation Enhancements ---

export const getMusicNewAlbums = (params?: {
  page?: number
  page_size?: number
}) => {
  return get<MusicAlbumResult>('/api/music/albums/new', params)
}

export const getMusicAiRecommend = (params?: {
  page_size?: number
}) => {
  return get<MusicSearchResult>('/api/music/recommend/ai', params)
}

export const getMusicEverydayRecommend = () => {
  return get<MusicSearchResult>('/api/music/recommend/everyday')
}

export const getMusicStyleRecommend = () => {
  return get<MusicSearchResult>('/api/music/recommend/style')
}

export const getMusicArtistVideos = (params: {
  artist_id: string
  page?: number
  page_size?: number
}) => {
  return get<MusicVideoResult>('/api/music/artist/videos', params)
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
  return get<MusicArtistHonourResult>('/api/music/artist/honour', { artist_id })
}

export const getMusicArtistDirectory = (params?: {
  page?: number
  page_size?: number
}) => {
  return get<MusicArtistResult>('/api/music/artists/directory', params)
}

export const getMusicRankDetail = (rank_id: string) => {
  return get<{
    id: string
    name: string
    cover: string
    intro: string
    update_frequency: string
    song_count: number
  }>('/api/music/rank/detail', { rank_id })
}

export const getMusicBanner = () => {
  return get<{
    items: Array<{
      id: string
      title: string
      cover: string
      type: string
      target_id: string
    }>
  }>('/api/music/banner')
}

export const searchMusicComplex = (query: string) => {
  return get<{
    songs: MusicTrack[]
    artists: MusicArtist[]
    albums: MusicAlbum[]
  }>('/api/music/search/complex', { query })
}

export const getMusicUserVip = () => {
  return get<{
    is_vip: boolean
    vip_type: number
    vip_expire_time: string
    vip_level: number
  }>('/api/music/user/vip')
}

export const sendMusicCaptcha = (phone: string) => {
  return post<{ ok: boolean }>('/api/music/auth/captcha', { phone })
}

export const loginMusicCellphone = (phone: string, captcha: string) => {
  return post<{
    ok: boolean
    logged_in: boolean
    auth: MusicAuthStatus
  }>('/api/music/auth/login', { phone, captcha })
}
