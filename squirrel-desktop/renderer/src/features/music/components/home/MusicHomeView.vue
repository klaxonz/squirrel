<template>
  <div class="music-home">
    <MusicHomeControlBar
      :fm-mode="fmMode"
      :fm-pool-id="fmPoolId"
      :fm-loading="fmLoading"
      :fm-active="fmActive"
      :fm-playing="fmPlaying"
      @fm-play="$emit('fm-play')"
      @everyday="$emit('navigate', 'everyday')"
      @new-songs="$emit('navigate', 'new-songs')"
      @switch-fm-mode="$emit('switch-fm-mode', $event)"
      @switch-fm-pool="$emit('switch-fm-pool', $event)"
    />

    <MusicRecentSection
      v-if="recentTracks.length"
      :tracks="recentTracks"
      @view-all="$emit('navigate', 'profile')"
      @play-track="handlePlayTrack"
    />

    <div class="music-home-board">
      <MusicSection
        class="music-home-recommendations"
        title="推荐歌单"
        description="按当前曲库与收听记录整理"
        :more-action="true"
        @more="$emit('navigate', 'playlists')"
      >
        <AppBlockLoader v-if="playlistsLoading" size="sm" text="加载推荐歌单..." />
        <AppEmptyState
          v-else-if="recommendedPlaylists.length === 0"
          variant="plain"
          icon="playlistMusic"
          title="暂无推荐歌单"
          copy="登录音乐账号后可同步收藏与每日推荐。"
        />
        <div v-else class="music-home-recommendation-layout">
          <MusicCard
            v-if="featuredPlaylist"
            :cover="playlistCover(featuredPlaylist)"
            :title="playlistTitle(featuredPlaylist)"
            :subtitle="playlistOwner(featuredPlaylist)"
            :meta="playlistMeta(featuredPlaylist)"
            size="lg"
            variant="playlist"
            layout="feature"
            playable
            @select="$emit('select-playlist', featuredPlaylist)"
            @play="$emit('play-playlist', featuredPlaylist)"
          />

          <div class="music-home-playlist-list">
            <MusicCard
              v-for="(item, index) in supportingPlaylists"
              :key="playlistKey(item, index)"
              :cover="playlistCover(item)"
              :title="playlistTitle(item)"
              :subtitle="playlistOwner(item)"
              :meta="playlistMeta(item)"
              size="sm"
              variant="playlist"
              layout="row"
              playable
              @select="$emit('select-playlist', item)"
              @play="$emit('play-playlist', item)"
            />
          </div>
        </div>
      </MusicSection>

      <MusicSection
        class="music-home-ranks"
        title="热门榜单"
        description="正在快速上升的音乐"
        :more-action="true"
        @more="$emit('navigate', 'ranks')"
      >
        <AppBlockLoader v-if="ranksLoading" size="sm" text="加载排行榜..." />
        <AppEmptyState
          v-else-if="ranks.length === 0"
          variant="plain"
          icon="list"
          title="暂无榜单"
          copy="稍后刷新，或登录后查看实时榜单。"
        />
        <MusicRankRow v-else :ranks="ranks.slice(0, 6)" @select="$emit('select-rank', $event)" />
      </MusicSection>
    </div>

    <MusicSection
      title="新碟上架"
      description="最近发行的专辑与单曲"
      :more-action="true"
      @more="$emit('navigate', 'new_albums')"
    >
      <AppBlockLoader v-if="albumsLoading" size="sm" text="加载新专辑..." />
      <AppEmptyState
        v-else-if="albums.length === 0"
        variant="plain"
        icon="disc"
        title="暂无新专辑"
        copy="新碟上架后会自动出现在这里。"
      />
      <div v-else class="music-home-album-list">
        <MusicCard
          v-for="album in visibleAlbums"
          :key="album.id"
          :cover="album.cover"
          :title="album.name"
          :subtitle="album.artist"
          :meta="album.publish_date || album.type"
          size="sm"
          variant="album"
          layout="row"
          playable
          @select="$emit('select-album', album)"
          @play="$emit('play-album', album)"
        />
      </div>
    </MusicSection>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MusicHomeControlBar from './MusicHomeControlBar.vue'
import MusicRecentSection from './MusicRecentSection.vue'
import MusicSection from '../shared/MusicSection.vue'
import MusicCard from '../shared/MusicCard.vue'
import MusicRankRow from '../shared/MusicRankRow.vue'
import AppBlockLoader from '@/shared/components/AppBlockLoader.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import { formatCount } from '@/shared/lib/dateFormat'
import type { MusicPlaylist, MusicRank, MusicAlbum, MusicTrack } from '@/shared/api/music'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'

type FmMode = 'normal' | 'small' | 'peak'

const props = defineProps<{
  playlists: MusicPlaylist[]
  ranks: MusicRank[]
  albums: MusicAlbum[]
  playlistsLoading: boolean
  ranksLoading: boolean
  albumsLoading: boolean
  historyTracks?: MusicTrack[]
  fmMode: FmMode
  fmPoolId: string
  fmLoading?: boolean
  fmActive?: boolean
  fmPlaying?: boolean
}>()

defineEmits<{
  navigate: [section: string]
  'select-playlist': [playlist: MusicPlaylist]
  'select-rank': [rank: MusicRank]
  'select-album': [album: MusicAlbum]
  'play-playlist': [playlist: MusicPlaylist]
  'play-album': [album: MusicAlbum]
  'fm-play': []
  'switch-fm-mode': [mode: FmMode]
  'switch-fm-pool': [poolId: string]
}>()

const player = useMusicPlayerStore()

const recentTracks = computed(() => props.historyTracks?.slice(0, 5) || [])
const recommendedPlaylists = computed(() => props.playlists.slice(0, 8))
const featuredPlaylist = computed(() => recommendedPlaylists.value[0] || null)
const supportingPlaylists = computed(() => recommendedPlaylists.value.slice(1))
const visibleAlbums = computed(() => props.albums.slice(0, 8))

function playlistKey(playlist: MusicPlaylist, index: number): string {
  return playlist.specialid
    || playlist.global_collection_id
    || playlist.id
    || `${playlistTitle(playlist)}-${index}`
}

function playlistCover(playlist: MusicPlaylist): string {
  return playlist.imgurl || playlist.cover || ''
}

function playlistTitle(playlist: MusicPlaylist): string {
  return playlist.specialname || playlist.name || '未命名歌单'
}

function playlistOwner(playlist: MusicPlaylist): string {
  return playlist.nickname || playlist.creator || '精选歌单'
}

function playlistMeta(playlist: MusicPlaylist): string {
  return playlist.play_count ? `${formatCount(playlist.play_count)} 次播放` : ''
}

function handlePlayTrack(track: MusicTrack) {
  player.playTrack(track)
}
</script>

<style scoped>
.music-home {
  display: flex;
  width: 100%;
  flex-direction: column;
  padding-bottom: var(--space-7);
}

/* Two equal boards — the rank column reads as a peer of recommendations,
   not a narrow sidebar. */
.music-home-board {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
  gap: clamp(var(--space-5), 2.5vw, var(--space-7));
  margin-bottom: var(--space-6);
}

.music-home-board > .music-section {
  margin-bottom: 0;
}

/* Each board is a half column now — stack the feature card above the list
   instead of squeezing them side by side. */
.music-home-recommendation-layout {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: clamp(var(--space-3), 1.4vw, var(--space-5));
}

.music-home-recommendation-layout > :deep(.music-card--feature) {
  width: min(100%, 18rem);
}

.music-home-playlist-list,
.music-home-album-list {
  display: grid;
  min-width: 0;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: clamp(var(--space-4), 2vw, var(--space-7));
}

.music-home-ranks :deep(.music-rank-list) {
  border-top: 0;
}

@media (max-width: 1180px) {
  .music-home-board {
    grid-template-columns: 1fr;
  }

  .music-home-ranks {
    max-width: none;
  }
}

@media (max-width: 780px) {
  .music-home-playlist-list,
  .music-home-album-list {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
