export type MusicOperation =
  | 'searchTracks' | 'searchArtists' | 'searchAlbums' | 'defaultSearch' | 'hotSearch' | 'searchSuggest' | 'complexSearch'
  | 'recommendations' | 'recommendCard' | 'dailyRecommend' | 'ranks' | 'rankTracks'
  | 'playlists' | 'playlistTags' | 'similarPlaylists' | 'playlistTracks' | 'userPlaylists' | 'userPlaylistTracks'
  | 'artistDetail' | 'artistTracks' | 'artistAlbums' | 'albumDetail' | 'albumTracks' | 'newSongs' | 'newAlbums'
  | 'aiRecommend' | 'brushFeed' | 'everydayRecommend' | 'styleRecommend'
  | 'createUserPlaylist' | 'collectPlaylist' | 'deleteUserPlaylist' | 'addUserPlaylistTrack' | 'removeUserPlaylistTracks'
  | 'userHistory' | 'userListenRank' | 'latestListenSongs' | 'uploadPlayHistory' | 'favoriteCount'
  | 'playUrl' | 'lyric' | 'trackMv' | 'trackClimax' | 'relatedTracks'
  | 'authStatus' | 'createQrLogin' | 'checkQrLogin' | 'userProfile' | 'logout'
  | 'userVip' | 'vipClaimStatus' | 'claimDailyVip' | 'sendCaptcha' | 'loginCellphone'
  | 'songComments' | 'songCommentsClassify' | 'songCommentsHotword' | 'floorComments' | 'playlistComments' | 'albumComments' | 'commentCount'
  | 'followArtist' | 'unfollowArtist' | 'followedArtistNewSongs' | 'followedArtists'
  | 'videoDetail' | 'videoUrl' | 'videoPrivilege' | 'artistVideos' | 'artistHonour' | 'artistDirectory' | 'rankDetail' | 'banner'

export type MusicTrackInput = { title: string; hash: string; album_id: string; album_audio_id: string }

export type MusicOperationPayloads = {
  searchTracks: { query: string; page?: number; page_size?: number }; searchArtists: { query: string; page?: number; page_size?: number }; searchAlbums: { query: string; page?: number; page_size?: number }; searchSuggest: { query: string }; complexSearch: { query: string }
  recommendations: Record<string, unknown> | undefined; recommendCard: { card_id?: number; page_size?: number } | undefined; dailyRecommend: { page_size?: number } | undefined
  rankTracks: { rank_id: string; rank_cid?: string; page?: number; page_size?: number }; playlists: { category_id?: number; page?: number; page_size?: number }; similarPlaylists: { playlist_id: string }; playlistTracks: { playlist_id: string; playlist_kind?: 'playlist' | 'theme'; page?: number; page_size?: number }
  userPlaylists: { page?: number; page_size?: number } | undefined; userPlaylistTracks: { list_id: string; page?: number; page_size?: number }; artistDetail: { artist_id: string }; artistTracks: { artist_id: string; page?: number; page_size?: number }; artistAlbums: { artist_id: string; page?: number; page_size?: number }; albumDetail: { album_id: string }; albumTracks: { album_id: string; page?: number; page_size?: number }; newSongs: { type?: number; page?: number; page_size?: number } | undefined; newAlbums: { page?: number; page_size?: number } | undefined
  aiRecommend: { page_size?: number } | undefined; brushFeed: { page_size?: number } | undefined; createUserPlaylist: { name: string; is_private?: boolean }; collectPlaylist: { playlist_id: string }; deleteUserPlaylist: { list_id: string }; addUserPlaylistTrack: { list_id: string; track: MusicTrackInput }; removeUserPlaylistTracks: { list_id: string; file_ids: string }
  userHistory: { bp?: string } | undefined; userListenRank: { type?: 0 | 1 } | undefined; latestListenSongs: { page_size?: number } | undefined; uploadPlayHistory: { album_audio_id: string; played_at?: number; play_count?: number }; favoriteCount: { mixsongids: string }; playUrl: { hash: string; album_id?: string; album_audio_id?: string; quality?: string }; lyric: { title: string; artist?: string; hash: string; album_audio_id?: string; duration?: number }; trackMv: { album_audio_id: string }; trackClimax: { hash: string }; relatedTracks: { album_audio_id: string; page?: number; page_size?: number; sort?: 'all' | 'hot' | 'new'; type?: string }
  checkQrLogin: { key: string }; claimDailyVip: { receive_day?: string } | undefined; sendCaptcha: { phone: string }; loginCellphone: { phone: string; captcha: string }
  songComments: { mixsongid: string; page?: number; page_size?: number }; songCommentsClassify: { mixsongid: string; type_id: string; page?: number; page_size?: number }; songCommentsHotword: { mixsongid: string }; floorComments: { special_id: string; mixsongid?: string; page?: number; page_size?: number }; playlistComments: { playlist_id: string; page?: number; page_size?: number }; albumComments: { album_id: string; page?: number; page_size?: number }; commentCount: { hash: string }
  followArtist: { artist_id: string }; unfollowArtist: { artist_id: string }; videoDetail: { video_id: string }; videoUrl: { video_id: string }; videoPrivilege: { video_id: string }; artistVideos: { artist_id: string; page?: number; page_size?: number }; artistHonour: { artist_id: string }; artistDirectory: { page?: number; page_size?: number } | undefined; rankDetail: { rank_id: string }
  defaultSearch: undefined; hotSearch: undefined; ranks: undefined; playlistTags: undefined; everydayRecommend: undefined; styleRecommend: undefined; authStatus: undefined; createQrLogin: undefined; userProfile: undefined; logout: undefined; userVip: undefined; vipClaimStatus: undefined; followedArtistNewSongs: undefined; followedArtists: undefined; banner: undefined
}
