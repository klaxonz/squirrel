<template>
  <div class="music-artist-detail">
    <header class="music-artist-header">
      <div class="music-artist-cover">
        <img v-if="artist.avatar" :src="artist.avatar" :alt="artist.name" loading="lazy" />
        <div v-else class="music-artist-cover-placeholder">
          <AppIcon name="user" class="h-16 w-16" />
        </div>
      </div>
      <div class="music-artist-info">
        <span class="music-artist-type">歌手</span>
        <h1 class="music-artist-name">{{ artist.name }}</h1>
        <div class="music-artist-meta">
          <span>{{ artist.song_count || 0 }} 首歌曲</span>
          <span>{{ artist.album_count || 0 }} 张专辑</span>
          <span v-if="artist.fan_count">{{ formatCount(artist.fan_count) }} 粉丝</span>
        </div>
        <div class="music-artist-actions">
          <button class="music-action-btn music-action-btn--primary" @click="playAll">
            <AppIcon name="play" class="h-5 w-5" />
            播放热门
          </button>
          <button class="music-action-btn" :class="{ 'music-action-btn--active': followed }" @click="handleFollow">
            <AppIcon name="heart" class="h-5 w-5" :class="{ 'fill-current': followed }" />
            {{ followed ? '已关注' : '关注' }}
          </button>
        </div>
      </div>
    </header>

    <section v-if="albums.length" class="music-artist-section">
      <h2 class="music-section-title">专辑</h2>
      <div class="music-album-grid">
        <article
          v-for="album in albums"
          :key="album.id"
          class="music-album-card"
          @click="$emit('select-album', album)"
        >
          <img :src="album.cover" :alt="album.name" loading="lazy" />
          <h3 class="music-album-name">{{ album.name }}</h3>
        </article>
      </div>
    </section>

    <section v-if="videos.length" class="music-artist-section">
      <h2 class="music-section-title">MV</h2>
      <div class="music-video-grid">
        <article
          v-for="video in videos"
          :key="video.id"
          class="music-video-card"
          @click="$emit('play-video', video)"
        >
          <img :src="video.cover" :alt="video.name" loading="lazy" />
          <h3 class="music-video-name">{{ video.name }}</h3>
        </article>
      </div>
    </section>

    <section class="music-artist-section">
      <h2 class="music-section-title">热门歌曲</h2>
      <AppBlockLoader v-if="tracksLoading" size="sm" />
      <MusicTrackList
        v-else
        :tracks="tracks"
        :show-add-to-playlist="false"
        @select-artist="$emit('select-artist', $event)"
        @play-mv="$emit('play-mv', $event)"
      />
      <div v-if="hasMore" class="music-load-more">
        <Button variant="outline" :loading="loadingMore" @click="$emit('load-more')">
          加载更多
        </Button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import AppBlockLoader from '@/shared/components/AppBlockLoader.vue'
import MusicTrackList from './MusicTrackList.vue'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import { formatCount } from '@/shared/lib/dateFormat'
import type { MusicArtist, MusicTrack, MusicAlbum, MusicVideo } from '@/shared/api/music'

const props = defineProps<{
  artist: MusicArtist
  tracks: MusicTrack[]
  albums: MusicAlbum[]
  videos: MusicVideo[]
  followed: boolean
  followLoading?: boolean
  tracksLoading: boolean
  loadingMore: boolean
  hasMore: boolean
}>()

const emit = defineEmits<{
  'play-all': []
  'follow': []
  'unfollow': []
  'load-more': []
  'select-album': [album: MusicAlbum]
  'play-video': [video: MusicVideo]
  'select-artist': [track: MusicTrack]
  'play-mv': [track: MusicTrack]
}>()

const player = useMusicPlayerStore()

function playAll() {
  player.playQueue(props.tracks, 0)
}

function handleFollow() {
  if (props.followed) {
    emit('unfollow')
  } else {
    emit('follow')
  }
}
</script>

<style scoped>
.music-artist-detail {
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.music-artist-header {
  display: flex;
  gap: 2rem;
  margin-bottom: 2rem;
}

.music-artist-cover {
  width: 200px;
  height: 200px;
  border-radius: 9999px;
  overflow: hidden;
  background: hsl(var(--muted) / 0.3);
}

.music-artist-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-artist-cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground));
}

.music-artist-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.music-artist-type {
  font-size: 0.6875rem;
  font-weight: 600;
  color: hsl(var(--primary));
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.music-artist-name {
  font-size: 1.5rem;
  font-weight: 700;
  color: hsl(var(--foreground));
  margin-top: 0.5rem;
}

.music-artist-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground));
  margin-top: 0.5rem;
}

.music-artist-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1rem;
}

.music-action-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: hsl(var(--foreground));
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: 9999px;
  cursor: pointer;
}

.music-action-btn:hover {
  background: hsl(var(--muted));
}

.music-action-btn--primary {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  border-color: hsl(var(--primary));
}

.music-action-btn--active {
  color: hsl(var(--primary));
  border-color: hsl(var(--primary));
}

.music-artist-section {
  margin-bottom: 2rem;
}

.music-section-title {
  font-size: 1rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  margin-bottom: 1rem;
}

.music-album-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 1rem;
}

.music-album-card {
  cursor: pointer;
}

.music-album-card img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: 0.5rem;
}

.music-album-name {
  font-size: 0.8125rem;
  font-weight: 500;
  color: hsl(var(--foreground));
  margin-top: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.music-video-card {
  cursor: pointer;
}

.music-video-card img {
  width: 100%;
  aspect-ratio: 16/9;
  object-fit: cover;
  border-radius: 0.5rem;
}

.music-video-name {
  font-size: 0.8125rem;
  font-weight: 500;
  color: hsl(var(--foreground));
  margin-top: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-load-more {
  display: flex;
  justify-content: center;
  padding: 1rem 0;
}

.music-load-more-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground));
  background: none;
  border: 1px solid hsl(var(--border));
  border-radius: 9999px;
  cursor: pointer;
}

.music-load-more-btn:hover:not(:disabled) {
  color: hsl(var(--foreground));
  border-color: hsl(var(--primary));
}

@media (max-width: 768px) {
  .music-artist-detail {
    padding: 1rem;
  }

  .music-artist-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .music-artist-cover {
    width: 160px;
    height: 160px;
  }

  .music-artist-actions {
    justify-content: center;
  }
}
</style>