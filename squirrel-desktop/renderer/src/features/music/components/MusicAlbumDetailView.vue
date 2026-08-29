<template>
  <div class="music-album-detail">
    <MusicDetailHeader
      kicker="专辑"
      :title="album.name"
      :cover="album.cover"
      :description="album.intro || ''"
      fallback-icon="playlistMusic"
    >
      <template #meta>
        <Button
          v-if="album.artist_id"
          variant="link"
          size="sm"
          class="music-meta-link"
          @click="$emit('select-artist')"
        >
          {{ album.artist }}
        </Button>
        <span v-else>{{ album.artist }}</span>
        <span v-if="album.publish_date">{{ album.publish_date }}</span>
        <span v-if="total">{{ total }} 首歌</span>
      </template>
      <template #actions>
        <Button @click="playAll">
          <AppIcon name="play" class="h-4 w-4" />
          播放全部
        </Button>
        <Button
          variant="secondary"
          :class="shuffle && 'app-selection-active'"
          @click="shuffleAll"
        >
          <AppIcon name="shuffle" class="h-4 w-4" />
          随机
        </Button>
      </template>
    </MusicDetailHeader>

    <AppBlockLoader v-if="loading" text="加载歌曲中..." />

    <MusicTrackList
      v-else
      :tracks="tracks"
      :show-add-to-playlist="false"
      @select-artist="$emit('select-artist-track', $event)"
      @play-mv="$emit('play-mv', $event)"
    />

    <div v-if="hasMore" class="music-detail-load-more">
      <Button variant="outline" :loading="loadingMore" @click="$emit('load-more')">
        加载更多
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import AppBlockLoader from '@/shared/components/AppBlockLoader.vue'
import MusicDetailHeader from './shared/MusicDetailHeader.vue'
import MusicTrackList from './MusicTrackList.vue'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'
import type { MusicAlbum, MusicTrack } from '@/shared/api/music'

const props = defineProps<{
  album: MusicAlbum
  tracks: MusicTrack[]
  total: number
  loading: boolean
  loadingMore: boolean
  hasMore: boolean
}>()

defineEmits<{
  'play-all': [shuffle: boolean]
  'load-more': []
  'select-artist': []
  'select-artist-track': [track: MusicTrack]
  'play-mv': [track: MusicTrack]
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
.music-album-detail {
  width: 100%;
}

.music-meta-link {
  height: auto;
  padding: 0;
  font-size: inherit;
}

.music-detail-load-more {
  display: flex;
  justify-content: center;
  padding: var(--space-4) 0;
}
</style>
