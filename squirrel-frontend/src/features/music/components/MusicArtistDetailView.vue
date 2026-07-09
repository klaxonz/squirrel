<template>
  <div class="music-artist-detail">
    <MusicDetailHeader
      kicker="歌手"
      :title="artist.name"
      :cover="artist.avatar"
      cover-shape="circle"
      fallback-icon="user"
    >
      <template #meta>
        <span>{{ artist.song_count || 0 }} 首歌曲</span>
        <span>{{ artist.album_count || 0 }} 张专辑</span>
        <span v-if="artist.fan_count">{{ formatCount(artist.fan_count) }} 粉丝</span>
      </template>
      <template #actions>
        <Button @click="playAll">
          <AppIcon name="play" class="h-4 w-4" />
          播放热门
        </Button>
        <Button
          variant="secondary"
          :loading="followLoading"
          :class="followed && 'border-primary/50 bg-primary/10 text-primary hover:bg-primary/15 hover:text-primary'"
          @click="handleFollow"
        >
          <AppIcon v-if="!followLoading" name="heart" class="h-4 w-4" :class="{ 'fill-current': followed }" />
          {{ followed ? '已关注' : '关注' }}
        </Button>
      </template>
    </MusicDetailHeader>

    <section v-if="albums.length" class="music-detail-section">
      <h2 class="music-detail-section-title">专辑</h2>
      <div class="music-detail-grid music-detail-grid--albums">
        <button
          v-for="album in albums"
          :key="album.id"
          type="button"
          class="music-detail-tile"
          @click="$emit('select-album', album)"
        >
          <img :src="album.cover" :alt="album.name" loading="lazy" />
          <span class="music-detail-tile__title">{{ album.name }}</span>
        </button>
      </div>
    </section>

    <section v-if="videos.length" class="music-detail-section">
      <h2 class="music-detail-section-title">MV</h2>
      <div class="music-detail-grid music-detail-grid--videos">
        <button
          v-for="video in videos"
          :key="video.id"
          type="button"
          class="music-detail-tile music-detail-tile--video"
          @click="$emit('play-video', video)"
        >
          <img :src="video.cover" :alt="video.name" loading="lazy" />
          <span class="music-detail-tile__title">{{ video.name }}</span>
        </button>
      </div>
    </section>

    <section class="music-detail-section">
      <h2 class="music-detail-section-title">热门歌曲</h2>
      <AppBlockLoader v-if="tracksLoading" size="sm" />
      <MusicTrackList
        v-else
        :tracks="tracks"
        :show-add-to-playlist="false"
        @select-artist="$emit('select-artist', $event)"
        @play-mv="$emit('play-mv', $event)"
      />
      <div v-if="hasMore" class="music-detail-load-more">
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
import MusicDetailHeader from './shared/MusicDetailHeader.vue'
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
  if (props.followed) emit('unfollow')
  else emit('follow')
}
</script>

<style scoped>
.music-artist-detail {
  width: 100%;
}

.music-detail-section {
  margin-bottom: var(--space-6);
}

.music-detail-section-title {
  margin: 0 0 var(--space-3);
  color: hsl(var(--foreground));
  font-family: var(--app-heading-font);
  font-size: var(--app-h3-size);
  font-weight: var(--app-h3-weight);
  letter-spacing: var(--app-h3-tracking);
  line-height: var(--app-h3-leading);
}

.music-detail-grid {
  display: grid;
  gap: var(--space-3);
}

.music-detail-grid--albums {
  grid-template-columns: repeat(auto-fill, minmax(7.5rem, 1fr));
}

.music-detail-grid--videos {
  grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
}

.music-detail-tile {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.music-detail-tile:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.5);
  border-radius: var(--radius-md);
}

.music-detail-tile img {
  display: block;
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.4);
}

.music-detail-tile--video img {
  aspect-ratio: 16 / 9;
}

.music-detail-tile__title {
  overflow: hidden;
  color: hsl(var(--foreground));
  font-size: 0.8125rem;
  font-weight: 600;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-detail-load-more {
  display: flex;
  justify-content: center;
  padding: var(--space-4) 0;
}
</style>
