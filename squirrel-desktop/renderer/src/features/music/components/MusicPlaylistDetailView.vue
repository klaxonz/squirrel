<template>
  <div class="music-playlist-detail">
    <div class="music-playlist-topbar">
      <div class="music-playlist-topbar-left">
        <h1 class="music-playlist-topbar-title">{{ playlist.specialname || playlist.name }}</h1>
        <span class="music-playlist-topbar-meta">{{ total }} 首</span>
      </div>
      <div class="music-playlist-topbar-actions">
        <Button
          variant="ghost"
          size="icon-sm"
          :class="shuffle && 'app-selection-active'"
          title="随机播放"
          @click="shuffleAll"
        >
          <AppIcon name="shuffle" class="h-4 w-4" />
        </Button>
        <Button
          v-if="showCollect"
          variant="ghost"
          size="icon-sm"
          :class="collected && 'app-selection-active'"
          title="收藏"
          @click="$emit('collect')"
        >
          <AppIcon name="heart" class="h-4 w-4" :class="{ 'fill-current': collected }" />
        </Button>
        <Button size="player-sm" title="播放全部" @click="playAll">
          <AppIcon name="play" class="h-4 w-4" />
        </Button>
      </div>
    </div>

    <AppBlockLoader v-if="loading" text="加载中..." />

    <div v-else class="music-playlist-tracks">
      <MusicTrackList
        :tracks="tracks"
        :show-mv="false"
        :show-related="false"
        @select-artist="$emit('select-artist', $event)"
        @select-album="$emit('select-album', $event)"
        @add-to-playlist="$emit('add-to-playlist', $event)"
      />
    </div>

    <div v-if="hasMore" class="music-playlist-load-more">
      <Button variant="outline" :loading="loadingMore" @click="$emit('load-more')">
        加载更多
      </Button>
    </div>

    <section v-if="similar.length" class="music-playlist-similar">
      <h2 class="music-playlist-similar-title">相似歌单</h2>
      <div class="music-playlist-similar-grid">
        <article
          v-for="item in similar"
          :key="item.specialid"
          class="music-playlist-similar-card"
          @click="$emit('change', item)"
        >
          <img :src="item.imgurl" :alt="item.specialname" loading="lazy" />
          <h3>{{ item.specialname }}</h3>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import AppBlockLoader from '@/shared/components/AppBlockLoader.vue'
import MusicTrackList from './MusicTrackList.vue'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import type { MusicPlaylist, MusicTrack } from '@/shared/api/music'

const props = defineProps<{
  playlist: MusicPlaylist
  tracks: MusicTrack[]
  total: number
  loading: boolean
  loadingMore: boolean
  hasMore: boolean
  similar: MusicPlaylist[]
  showCollect: boolean
  collected: boolean
}>()

defineEmits<{
  'play-all': [shuffle: boolean]
  'collect': []
  'load-more': []
  'select-artist': [track: MusicTrack]
  'select-album': [track: MusicTrack]
  'play-mv': [track: MusicTrack]
  'select-related': [track: MusicTrack]
  'add-to-playlist': [track: MusicTrack]
  'change': [playlist: MusicPlaylist]
}>()

const player = useMusicPlayerStore()
const shuffle = computed(() => player.shuffle)

function playAll() {
  player.shuffle = false
  player.playQueue(props.tracks, 0)
}

function shuffleAll() {
  player.shuffle = true
  player.playQueue(props.tracks, 0)
}
</script>

<style scoped>
.music-playlist-detail {
  width: 100%;
}

.music-playlist-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--app-hairline);
}

.music-playlist-topbar-left {
  display: flex;
  min-width: 0;
  align-items: baseline;
  gap: 0.75rem;
}

.music-playlist-topbar-title {
  margin: 0;
  overflow: hidden;
  color: var(--app-heading-color);
  font-family: var(--app-heading-font);
  font-size: var(--app-h2-size);
  font-weight: var(--app-h2-weight);
  letter-spacing: var(--app-h2-tracking);
  line-height: var(--app-h2-leading);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-playlist-topbar-meta {
  flex-shrink: 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.music-playlist-topbar-actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 0.375rem;
}

.music-playlist-tracks {
  margin: 0;
}

.music-playlist-load-more {
  display: flex;
  justify-content: center;
  padding: var(--space-5) 0;
}

.music-playlist-similar {
  margin-top: var(--space-7);
  padding-top: var(--space-6);
  border-top: 1px solid var(--app-hairline);
}

.music-playlist-similar-title {
  margin: 0 0 var(--space-4);
  color: hsl(var(--foreground));
  font-family: var(--app-heading-font);
  font-size: var(--app-h3-size);
  font-weight: var(--app-h3-weight);
  letter-spacing: var(--app-h3-tracking);
}

.music-playlist-similar-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(8rem, 1fr));
  gap: 1rem;
}

.music-playlist-similar-card {
  cursor: pointer;
  transition: transform 0.2s ease;
}

.music-playlist-similar-card:hover {
  transform: translateY(-4px);
}

.music-playlist-similar-card img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: 0.625rem;
  box-shadow: 0 4px 12px hsl(var(--foreground) / 0.08);
}

.music-playlist-similar-card h3 {
  font-size: 0.8125rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  margin-top: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
