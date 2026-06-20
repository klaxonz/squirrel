import type { MusicAlbum, MusicArtist, MusicTrack } from '@/shared/api/music'

/**
 * Shared music presentation formatters + lightweight entity synthesis.
 *
 * These were previously copy-pasted across five music components
 * (MusicSearchView, MusicTrackList, GlobalMusicPlayerBar, MusicImmersivePlayer,
 * MusicProgressBar). The duplication had silently diverged — list/search views
 * render `m:ss` with a `--:--` empty marker, while the player surfaces render
 * zero-padded `mm:ss` with a `00:00` empty marker. Both behaviours are
 * intentional UX, so this module exposes both variants rather than collapsing
 * to one and silently changing four components' rendered output.
 */

/**
 * List/search duration: `m:ss`, `--:--` when empty/NaN.
 * Used by MusicSearchView and MusicTrackList.
 */
export function formatDuration(seconds: number): string {
  if (!seconds || Number.isNaN(seconds)) return '--:--'
  const minutes = Math.floor(seconds / 60)
  const remainSeconds = Math.floor(seconds % 60)
  return `${minutes}:${String(remainSeconds).padStart(2, '0')}`
}

/**
 * Player-surface duration: zero-padded `mm:ss`, `00:00` when empty/NaN.
 * Used by GlobalMusicPlayerBar, MusicImmersivePlayer, MusicProgressBar.
 */
export function formatPlaybackTime(seconds: number): string {
  if (!seconds || Number.isNaN(seconds)) return '00:00'
  const rounded = Math.floor(seconds)
  const minutes = Math.floor(rounded / 60)
  const rest = rounded % 60
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}

/** "N 首歌 · N 张专辑" metadata line for an artist card; '歌手' fallback. */
export function formatArtistMeta(artist: MusicArtist): string {
  const parts: string[] = []
  if (artist.song_count) parts.push(`${artist.song_count} 首歌`)
  if (artist.album_count) parts.push(`${artist.album_count} 张专辑`)
  return parts.join(' · ') || '歌手'
}

/** Synthesise a minimal artist entity from a track's artist fields. */
export function createArtistFromTrack(track: MusicTrack): MusicArtist {
  return {
    id: track.artist_id || '',
    name: track.artist || '未知歌手',
    avatar: '',
    intro: '',
    song_count: 0,
    album_count: 0,
    fan_count: 0,
  }
}

/** Synthesise a minimal album entity from a track's album fields. */
export function createAlbumFromTrack(track: MusicTrack): MusicAlbum {
  return {
    id: track.album_id,
    name: track.album || '未知专辑',
    cover: track.cover || '',
    intro: '',
    artist: track.artist || '未知歌手',
    artist_id: track.artist_id || '',
    publish_date: '',
    language: '',
    type: '',
    heat: 0,
  }
}

/**
 * Format a Kugou user registration time into a `YYYY-MM-DD` string.
 *
 * The profile API returns registration times in two shapes: epoch-seconds
 * (numeric string) or a full datetime string (`YYYY-MM-DD HH:mm:ss`). This
 * normalises both to a date-only string, returning '' when empty.
 */
export function formatRegTime(val: string): string {
  if (!val) return ''
  if (/^\d+$/.test(val)) {
    const d = new Date(Number(val) * 1000)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  }
  return val.split(' ')[0] || val
}
