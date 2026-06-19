<template>
  <div class="music-search">
    <div v-if="!hasSearched" class="music-search-home">
      <section v-if="history.length" class="music-search-section">
        <div class="music-search-section-header">
          <h3 class="music-search-section-title">搜索历史</h3>
          <button class="music-search-clear-btn" @click="clearHistory">
            <AppIcon name="trash" class="h-4 w-4" />
            清空
          </button>
        </div>
        <div class="music-history-list">
          <button
            v-for="(item, index) in history"
            :key="index"
            class="music-history-item"
            @click="searchByKeyword(item)"
          >
            <AppIcon name="history" class="h-4 w-4" />
            <span>{{ item }}</span>
          </button>
        </div>
      </section>

      <section v-if="hotSearches.length" class="music-search-section">
        <h3 class="music-search-section-title">热搜榜</h3>
        <div class="music-hot-list">
          <button
            v-for="(item, index) in hotSearches.slice(0, 20)"
            :key="item.keyword"
            class="music-hot-item"
            @click="searchByKeyword(item.keyword)"
          >
            <span class="music-hot-index" :class="{ 'music-hot-index--top': index < 3 }">{{ index + 1 }}</span>
            <span class="music-hot-keyword">{{ item.keyword }}</span>
            <span v-if="item.score" class="music-hot-score">{{ formatScore(item.score) }}</span>
          </button>
        </div>
      </section>
    </div>

    <div v-else class="music-search-results">
      <MusicLoadingState v-if="loading" :loading="true" text="搜索中..." />

      <template v-else-if="result">
        <section v-if="result.songs.length || result.artists.length || result.albums.length" class="music-search-all">
          <header class="music-search-summary">
            <div>
              <span class="music-search-summary-label">搜索结果</span>
              <h3 class="music-search-summary-title">{{ searchQuery }}</h3>
            </div>
            <div class="music-search-summary-counts">
              <span v-if="result.songs.length">{{ result.songs.length }} 首歌</span>
              <span v-if="result.artists.length">{{ result.artists.length }} 位歌手</span>
              <span v-if="result.albums.length">{{ result.albums.length }} 张专辑</span>
            </div>
          </header>

          <div class="music-search-layout">
            <section v-if="result.songs.length" class="music-search-group music-search-group--songs">
              <div class="music-search-table-head">
                <span class="music-search-col music-search-col--index">#</span>
                <span class="music-search-col music-search-col--cover"></span>
                <span class="music-search-col music-search-col--title">歌曲</span>
                <span class="music-search-col music-search-col--album">专辑</span>
                <span class="music-search-col music-search-col--duration">时长</span>
              </div>
              <article
                v-for="(track, index) in result.songs"
                :key="track.hash || index"
                class="music-search-song-row"
                @click="handlePlaySong(track)"
              >
                <span class="music-search-col music-search-col--index music-search-song-index">{{ index + 1 }}</span>
                <div class="music-search-col music-search-col--cover music-search-song-cover">
                  <img v-if="track.cover" :src="track.cover" :alt="track.title" loading="lazy" />
                  <AppIcon v-else name="playlistMusic" class="h-3.5 w-3.5" />
                </div>
                <div class="music-search-col music-search-col--title music-search-song-title-cell">
                  <span class="music-search-song-title">{{ track.title || '未知歌曲' }}</span>
                  <button
                    class="music-search-song-artist"
                    :disabled="!track.artist_id"
                    @click.stop="$emit('select-artist', createArtistFromTrack(track))"
                  >
                    {{ track.artist || '未知歌手' }}
                  </button>
                </div>
                <button
                  class="music-search-col music-search-col--album music-search-song-album"
                  :disabled="!track.album_id"
                  @click.stop="$emit('select-album', createAlbumFromTrack(track))"
                >
                  {{ track.album || '未知专辑' }}
                </button>
                <span class="music-search-col music-search-col--duration">{{ formatDuration(track.duration) }}</span>
              </article>
            </section>

            <aside class="music-search-side">
              <section v-if="result.artists.length" class="music-search-group">
                <div class="music-search-group-header">
                  <h4 class="music-search-group-title">歌手 <span>{{ result.artists.length }}</span></h4>
                </div>
                <div class="music-search-artists">
                  <article
                    v-for="artist in result.artists"
                    :key="artist.id"
                    class="music-search-artist-item"
                    @click="$emit('select-artist', artist)"
                  >
                    <div class="music-search-artist-avatar">
                      <img v-if="artist.avatar" :src="artist.avatar" :alt="artist.name" loading="lazy" />
                      <AppIcon v-else name="user" class="h-4 w-4" />
                    </div>
                    <div class="music-search-artist-info">
                      <span class="music-search-artist-name">{{ artist.name }}</span>
                      <span class="music-search-artist-meta">{{ formatArtistMeta(artist) }}</span>
                    </div>
                  </article>
                </div>
              </section>

              <section v-if="result.albums.length" class="music-search-group">
                <div class="music-search-group-header">
                  <h4 class="music-search-group-title">专辑 <span>{{ result.albums.length }}</span></h4>
                </div>
                <div class="music-search-albums">
                  <article
                    v-for="album in result.albums"
                    :key="album.id"
                    class="music-search-album-item"
                    @click="$emit('select-album', album)"
                  >
                    <img v-if="album.cover" :src="album.cover" :alt="album.name" loading="lazy" class="music-search-album-cover" />
                    <div v-else class="music-search-album-cover music-search-album-cover--empty">
                      <AppIcon name="disc" class="h-4 w-4" />
                    </div>
                    <div class="music-search-album-info">
                      <span class="music-search-album-name">{{ album.name }}</span>
                      <span class="music-search-album-artist">{{ album.artist || '未知歌手' }}</span>
                    </div>
                  </article>
                </div>
              </section>
            </aside>
          </div>
        </section>

        <MusicEmptyState v-else icon="search" :text="`未找到「${searchQuery}」相关结果`" />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import MusicLoadingState from './shared/MusicLoadingState.vue'
import MusicEmptyState from './shared/MusicEmptyState.vue'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import type { MusicTrack, MusicArtist, MusicAlbum, MusicHotSearch } from '@/shared/api/music'

const HISTORY_KEY = 'squirrel_music_search_history'
const MAX_HISTORY = 15

const props = defineProps<{
  hotSearches: MusicHotSearch[]
  loading: boolean
  result: { songs: MusicTrack[]; artists: MusicArtist[]; albums: MusicAlbum[] } | null
  searchQuery?: string
}>()

const emit = defineEmits<{
  (e: 'search', query: string): void
  (e: 'select-artist', artist: MusicArtist): void
  (e: 'select-album', album: MusicAlbum): void
}>()

const player = useMusicPlayerStore()
const hasSearched = ref(false)
const history = ref<string[]>(loadHistory())

function loadHistory(): string[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveHistory() {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.value))
}

watch(() => props.searchQuery, (val) => {
  if (val) {
    hasSearched.value = true
    addToHistory(val)
  }
}, { immediate: true })

function searchByKeyword(keyword: string) {
  hasSearched.value = true
  addToHistory(keyword)
  emit('search', keyword)
}

function addToHistory(q: string) {
  const h = history.value.filter(k => k !== q)
  history.value = [q, ...h].slice(0, MAX_HISTORY)
  saveHistory()
}

function clearHistory() {
  history.value = []
  saveHistory()
}

function formatScore(score: number): string {
  if (score >= 10000) return (score / 10000).toFixed(1) + '万'
  return String(score)
}

function formatDuration(seconds: number): string {
  if (!seconds) return '--:--'
  const minutes = Math.floor(seconds / 60)
  const remainSeconds = Math.floor(seconds % 60)
  return `${minutes}:${String(remainSeconds).padStart(2, '0')}`
}

function formatArtistMeta(artist: MusicArtist): string {
  const parts = []
  if (artist.song_count) parts.push(`${artist.song_count} 首歌`)
  if (artist.album_count) parts.push(`${artist.album_count} 张专辑`)
  return parts.join(' · ') || '歌手'
}

function handlePlaySong(track: MusicTrack) {
  player.playTrack(track)
}

function createArtistFromTrack(track: MusicTrack): MusicArtist {
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

function createAlbumFromTrack(track: MusicTrack): MusicAlbum {
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
</script>

<style scoped>
.music-search {
  padding: 1.5rem;
  max-width: 1280px;
  margin: 0 auto;
}

.music-search-home {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.music-search-section {
  margin-bottom: 1.5rem;
}

.music-search-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.music-search-section-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.music-search-clear-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  background: none;
  border: none;
  cursor: pointer;
}

.music-history-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.music-history-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem;
  background: hsl(var(--muted) / 0.4);
  border: none;
  border-radius: 9999px;
  font-size: 0.8125rem;
  color: hsl(var(--foreground));
  cursor: pointer;
  transition: all 0.15s ease;
}

.music-history-item:hover {
  background: hsl(var(--muted) / 0.6);
}

.music-hot-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.125rem;
}

.music-hot-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.5rem;
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease;
  border-radius: 0.375rem;
}

.music-hot-item:hover {
  background: hsl(var(--muted) / 0.3);
}

.music-hot-index {
  width: 1.5rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
  text-align: center;
}

.music-hot-index--top {
  color: hsl(var(--primary));
}

.music-hot-keyword {
  flex: 1;
  font-size: 0.875rem;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-hot-score {
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground));
}

.music-search-results {
  display: flex;
  flex-direction: column;
}

.music-search-all {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.music-search-summary {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  padding-bottom: 0.875rem;
  border-bottom: 1px solid hsl(var(--border) / 0.7);
}

.music-search-summary-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
}

.music-search-summary-title {
  margin-top: 0.25rem;
  font-size: 1.25rem;
  font-weight: 650;
  color: hsl(var(--foreground));
}

.music-search-summary-counts {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  white-space: nowrap;
}

.music-search-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 1.5rem;
  align-items: start;
}

.music-search-group {
  min-width: 0;
}

.music-search-group--songs {
  overflow: hidden;
}

.music-search-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.music-search-group-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.music-search-group-title span {
  font-size: 0.75rem;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
}

.music-search-table-head,
.music-search-song-row {
  display: grid;
  grid-template-columns: 2.25rem 3rem minmax(220px, 1.4fr) minmax(160px, 0.8fr) 4.5rem;
  align-items: center;
  gap: 0.75rem;
}

.music-search-table-head {
  height: 2rem;
  padding: 0 0.625rem;
  font-size: 0.6875rem;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
  border-bottom: 1px solid hsl(var(--border) / 0.6);
}

.music-search-song-row {
  min-height: 3.625rem;
  padding: 0.375rem 0.625rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background 0.15s ease;
}

.music-search-song-row:hover {
  background: hsl(var(--muted) / 0.3);
}

.music-search-col {
  min-width: 0;
}

.music-search-col--index,
.music-search-col--duration {
  text-align: right;
}

.music-search-col--duration {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.music-search-song-index {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.music-search-song-cover {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.375rem;
  overflow: hidden;
  background: hsl(var(--muted) / 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground));
}

.music-search-song-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-search-song-title {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-search-song-artist {
  display: block;
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  background: none;
  border: none;
  padding: 0;
  margin-top: 0.125rem;
  cursor: pointer;
  text-align: left;
}

.music-search-song-artist:hover:not(:disabled) {
  color: hsl(var(--primary));
}

.music-search-song-album {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
  font-size: 0.8125rem;
  color: hsl(var(--muted-foreground));
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
}

.music-search-song-album:hover:not(:disabled) {
  color: hsl(var(--primary));
}

.music-search-side {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.music-search-artists {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.music-search-artist-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.5rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background 0.15s ease;
}

.music-search-artist-item:hover {
  background: hsl(var(--muted) / 0.3);
}

.music-search-artist-avatar {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 9999px;
  overflow: hidden;
  background: hsl(var(--muted) / 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground));
}

.music-search-artist-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-search-artist-info {
  min-width: 0;
}

.music-search-artist-name {
  display: block;
  font-size: 0.8125rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-search-artist-meta {
  display: block;
  margin-top: 0.125rem;
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-search-albums {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.music-search-album-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.5rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background 0.15s ease;
}

.music-search-album-item:hover {
  background: hsl(var(--muted) / 0.3);
}

.music-search-album-cover {
  width: 2.5rem;
  height: 2.5rem;
  flex: 0 0 auto;
  border-radius: 0.375rem;
  object-fit: cover;
}

.music-search-album-cover--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  background: hsl(var(--muted) / 0.3);
  color: hsl(var(--muted-foreground));
}

.music-search-album-info {
  min-width: 0;
}

.music-search-album-name {
  display: block;
  font-size: 0.8125rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-search-album-artist {
  display: block;
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground));
  margin-top: 0.125rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .music-search {
    padding: 1rem;
  }

  .music-hot-list {
    grid-template-columns: 1fr;
  }

  .music-search-artists,
  .music-search-albums {
    flex-direction: column;
  }
}
</style>
