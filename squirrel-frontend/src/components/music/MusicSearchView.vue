<template>
  <div class="music-search">
    <div class="music-search-header">
      <div class="music-search-input-wrap">
        <AppIcon name="search" class="h-5 w-5 text-muted-foreground" />
        <input
          v-model="query"
          type="text"
          class="music-search-input"
          placeholder="搜索歌曲、歌手、专辑、歌词"
          @keyup.enter="handleSearch"
        />
        <button v-if="query" class="music-search-clear" @click="clearQuery">
          <AppIcon name="close" class="h-4 w-4" />
        </button>
      </div>
    </div>

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
            <AppIcon name="history" class="h-4 w-4 text-muted-foreground" />
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
      <div v-if="loading" class="music-search-loading">
        <AppIcon name="loadingSpinner" class="h-8 w-8 animate-spin text-primary" />
        <span>搜索中...</span>
      </div>

      <template v-else-if="result">
        <section v-if="result.songs.length" class="music-result-section">
          <div class="music-result-header">
            <h3 class="music-result-title">歌曲</h3>
            <span class="music-result-count">{{ result.songs.length }} 首</span>
          </div>
          <MusicTrackList
            :tracks="result.songs.slice(0, 10)"
            :show-mv="false"
            :show-related="false"
            :show-add-to-playlist="false"
          />
          <button
            v-if="result.songs.length > 10"
            class="music-result-more"
            @click="$emit('more-songs', query)"
          >
            查看更多歌曲
          </button>
        </section>

        <section v-if="result.artists.length" class="music-result-section">
          <div class="music-result-header">
            <h3 class="music-result-title">歌手</h3>
          </div>
          <div class="music-artist-list">
            <article
              v-for="artist in result.artists"
              :key="artist.id"
              class="music-artist-item"
              @click="$emit('select-artist', artist)"
            >
              <div class="music-artist-avatar">
                <img v-if="artist.avatar" :src="artist.avatar" :alt="artist.name" />
                <AppIcon v-else name="user" class="h-6 w-6 text-muted-foreground" />
              </div>
              <div class="music-artist-info">
                <h4 class="music-artist-name">{{ artist.name }}</h4>
                <p class="music-artist-meta">{{ artist.song_count || 0 }} 首歌曲</p>
              </div>
            </article>
          </div>
        </section>

        <section v-if="result.albums.length" class="music-result-section">
          <div class="music-result-header">
            <h3 class="music-result-title">专辑</h3>
          </div>
          <div class="music-album-list">
            <article
              v-for="album in result.albums"
              :key="album.id"
              class="music-album-item"
              @click="$emit('select-album', album)"
            >
              <div class="music-album-cover">
                <img v-if="album.cover" :src="album.cover" :alt="album.name" />
                <AppIcon v-else name="playlistMusic" class="h-6 w-6 text-muted-foreground" />
              </div>
              <div class="music-album-info">
                <h4 class="music-album-name">{{ album.name }}</h4>
                <p class="music-album-meta">{{ album.artist }}</p>
              </div>
            </article>
          </div>
        </section>

        <div v-if="isEmpty" class="music-search-empty">
          <AppIcon name="search" class="h-12 w-12 text-muted-foreground/30" />
          <p>未找到「{{ query }}」相关结果</p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import MusicTrackList from './MusicTrackList.vue'
import type { MusicTrack, MusicArtist, MusicAlbum, MusicHotSearch } from '@/api/music'

const props = defineProps<{
  hotSearches: MusicHotSearch[]
  loading: boolean
  result: { songs: MusicTrack[]; artists: MusicArtist[]; albums: MusicAlbum[] } | null
}>()

const emit = defineEmits<{
  'search': [query: string]
  'select-artist': [artist: MusicArtist]
  'select-album': [album: MusicAlbum]
  'more-songs': [query: string]
}>()

const query = ref('')
const hasSearched = ref(false)
const history = ref<string[]>([])

const isEmpty = computed(() => {
  if (!props.result) return false
  return !props.result.songs.length && !props.result.artists.length && !props.result.albums.length
})

watch(query, (val) => {
  if (!val) hasSearched.value = false
})

function handleSearch() {
  const q = query.value.trim()
  if (!q) return
  hasSearched.value = true
  addToHistory(q)
  emit('search', q)
}

function searchByKeyword(keyword: string) {
  query.value = keyword
  handleSearch()
}

function clearQuery() {
  query.value = ''
  hasSearched.value = false
}

function addToHistory(q: string) {
  const h = history.value.filter(k => k !== q)
  history.value = [q, ...h].slice(0, 10)
}

function clearHistory() {
  history.value = []
}

function formatScore(score: number): string {
  if (score >= 10000) return (score / 10000).toFixed(1) + '万'
  return String(score)
}
</script>

<style scoped>
.music-search {
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.music-search-header {
  margin-bottom: 1.5rem;
}

.music-search-input-wrap {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: 9999px;
  transition: border-color 0.2s ease;
}

.music-search-input-wrap:focus-within {
  border-color: hsl(var(--primary));
}

.music-search-input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  font-size: 0.9375rem;
  color: hsl(var(--foreground));
}

.music-search-input::placeholder {
  color: hsl(var(--muted-foreground));
}

.music-search-clear {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border: none;
  border-radius: 9999px;
  background: hsl(var(--muted));
  color: hsl(var(--muted-foreground));
  cursor: pointer;
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
}

.music-history-item:hover {
  background: hsl(var(--muted) / 0.6);
}

.music-hot-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.25rem;
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
}

.music-hot-item:hover {
  background: hsl(var(--muted) / 0.3);
}

.music-hot-index {
  width: 1.5rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
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

.music-search-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: hsl(var(--muted-foreground));
}

.music-search-results {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.music-result-section {
  margin-bottom: 1.5rem;
}

.music-result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid hsl(var(--border));
}

.music-result-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.music-result-count {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.music-result-more {
  display: block;
  margin: 1rem auto 0;
  padding: 0.5rem 1rem;
  font-size: 0.8125rem;
  color: hsl(var(--primary));
  background: none;
  border: 1px solid hsl(var(--primary) / 0.3);
  border-radius: 9999px;
  cursor: pointer;
}

.music-artist-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
}

.music-artist-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: 0.75rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.music-artist-item:hover {
  border-color: hsl(var(--primary) / 0.5);
  transform: translateY(-2px);
}

.music-artist-avatar {
  width: 3rem;
  height: 3rem;
  border-radius: 9999px;
  overflow: hidden;
  background: hsl(var(--muted) / 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}

.music-artist-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-artist-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: hsl(var(--foreground));
}

.music-artist-meta {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  margin-top: 0.125rem;
}

.music-album-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
}

.music-album-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: 0.75rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.music-album-item:hover {
  border-color: hsl(var(--primary) / 0.5);
  transform: translateY(-2px);
}

.music-album-cover {
  width: 3rem;
  height: 3rem;
  border-radius: 0.5rem;
  overflow: hidden;
  background: hsl(var(--muted) / 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}

.music-album-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-album-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: hsl(var(--foreground));
}

.music-album-meta {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  margin-top: 0.125rem;
}

.music-search-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.9375rem;
}

@media (max-width: 768px) {
  .music-search {
    padding: 1rem;
  }

  .music-hot-list {
    grid-template-columns: 1fr;
  }

  .music-artist-list,
  .music-album-list {
    grid-template-columns: 1fr;
  }
}
</style>