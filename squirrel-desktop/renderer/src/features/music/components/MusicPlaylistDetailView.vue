<template>
  <div class="music-playlist-detail">
    <MusicDetailHeader
      kicker="歌单"
      :title="playlist.specialname || playlist.name || '未命名歌单'"
      :cover="playlist.imgurl || playlist.cover"
      :description="playlist.intro || ''"
    >
      <template #meta>
        <span v-if="playlist.nickname || playlist.creator">
          {{ playlist.nickname || playlist.creator }}
        </span>
        <span>{{ total }} 首歌</span>
        <span v-if="playlist.play_count">{{ formatCount(playlist.play_count) }} 次播放</span>
        <span v-if="collectCount">{{ formatCount(collectCount) }} 次收藏</span>
      </template>
      <template #actions>
        <Button @click="playAll">
          <AppIcon name="play" class="h-4 w-4" />
          播放全部
        </Button>
        <Button
          severity="secondary"
          :class="shuffle && 'app-selection-active'"
          @click="shuffleAll"
        >
          <AppIcon name="shuffle" class="h-4 w-4" />
          随机
        </Button>
        <Button
          v-if="showCollect"
          severity="secondary"
          :class="collected && 'app-selection-active'"
          @click="$emit('collect')"
        >
          <AppIcon name="heart" class="h-4 w-4" :class="{ 'fill-current': collected }" />
          {{ collected ? '已收藏' : '收藏' }}
        </Button>
      </template>
    </MusicDetailHeader>

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
      <Button severity="secondary" outlined :loading="loadingMore" @click="$emit('load-more')">
        加载更多
      </Button>
    </div>

    <section v-if="similar.length" class="music-playlist-similar">
      <h2 class="music-playlist-similar-title">相似歌单</h2>
      <div class="app-music-grid">
        <MusicCard
          v-for="item in similar"
          :key="item.specialid"
          :cover="item.imgurl"
          :title="item.specialname || item.name || '未命名歌单'"
          :subtitle="item.nickname || item.creator || '歌单'"
          variant="playlist"
          @select="$emit('change', item)"
        />
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
import MusicCard from './shared/MusicCard.vue'
import MusicDetailHeader from './shared/MusicDetailHeader.vue'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import { formatCount } from '@/shared/lib/dateFormat'
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
const collectCount = computed(() => props.playlist.collectcount || props.playlist.collect_count || 0)

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

</style>
