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
          severity="secondary"
          :loading="followLoading"
          :class="followed && 'app-selection-active'"
          @click="handleFollow"
        >
          <AppIcon v-if="!followLoading" name="heart" class="h-4 w-4" :class="{ 'fill-current': followed }" />
          {{ followed ? '已关注' : '关注' }}
        </Button>
      </template>
    </MusicDetailHeader>

    <section v-if="albums.length" class="music-detail-section">
      <h2 class="music-detail-section-title">专辑</h2>
      <div class="app-music-grid">
        <MusicCard
          v-for="album in albums"
          :key="album.id"
          :cover="album.cover"
          :title="album.name"
          :subtitle="album.artist"
          variant="album"
          @select="$emit('select-album', album)"
        />
      </div>
    </section>

    <section v-if="videos.length" class="music-detail-section">
      <h2 class="music-detail-section-title">MV</h2>
      <div class="app-video-grid">
        <article
          v-for="video in videos"
          :key="video.id"
          class="music-artist-video-card"
          role="button"
          tabindex="0"
          :aria-label="`播放 MV：${video.name}`"
          @click="playVideo(video)"
          @keydown.enter.prevent="playVideo(video)"
          @keydown.space.prevent="playVideo(video)"
        >
          <div class="music-artist-video-card__thumb">
            <img :src="video.cover" :alt="video.name" loading="lazy" />
          </div>
          <div class="music-artist-video-card__body">
            <h3 class="music-artist-video-card__title" :title="video.name">{{ video.name }}</h3>
            <p class="music-artist-video-card__meta">{{ video.artist }}</p>
          </div>
        </article>
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
        <Button severity="secondary" outlined :loading="loadingMore" @click="$emit('load-more')">
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
import MusicCard from './shared/MusicCard.vue'
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

function playVideo(video: MusicVideo) {
  emit('play-video', video)
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

.music-artist-video-card {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.625rem;
  cursor: pointer;
  outline: none;
}

.music-artist-video-card__thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: var(--app-card-radius);
  background: var(--app-media-thumb-placeholder);
  transition: box-shadow var(--duration-base) var(--ease-default);
}

.music-artist-video-card:hover .music-artist-video-card__thumb,
.music-artist-video-card:focus-visible .music-artist-video-card__thumb {
  box-shadow: inset 0 0 0 1px hsl(var(--foreground) / 0.16);
}

.music-artist-video-card:focus-visible .music-artist-video-card__thumb {
  outline: 2px solid hsl(var(--ring) / 0.55);
  outline-offset: 2px;
}

.music-artist-video-card__thumb img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-artist-video-card__body {
  min-width: 0;
  padding-inline: 0.125rem;
}

.music-artist-video-card__title {
  display: -webkit-box;
  overflow: hidden;
  margin: 0;
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.3;
  text-overflow: ellipsis;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.music-artist-video-card__meta {
  overflow: hidden;
  margin: 0.25rem 0 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (prefers-reduced-motion: reduce) {
  .music-artist-video-card__thumb {
    transition: none;
  }
}

.music-detail-load-more {
  display: flex;
  justify-content: center;
  padding: var(--space-4) 0;
}
</style>
