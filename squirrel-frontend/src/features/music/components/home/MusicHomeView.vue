<template>
  <div class="music-home">
    <MusicGreetingSection
      :user="user"
      :recent-track="lastPlayedTrack"
      :has-current-track="Boolean(player.currentTrack)"
      :featured-playlist="featuredPlaylist"
      :fm-mode="fmMode"
      :fm-pool-id="fmPoolId"
      :fm-loading="fmLoading"
      :fm-active="fmActive"
      :fm-playing="fmPlaying"
      @continue-play="$emit('continue-play', $event)"
      @fm-play="$emit('fm-play')"
      @everyday="$emit('navigate', 'everyday')"
      @new-songs="$emit('navigate', 'new-songs')"
      @open-featured="$emit('select-playlist', $event)"
      @play-featured="$emit('play-playlist', $event)"
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
        title="为你推荐"
        description="从你的收听偏好中挑选"
        :more-action="true"
        @more="$emit('navigate', 'playlists')"
      >
        <AppBlockLoader v-if="playlistsLoading" size="sm" text="加载推荐歌单..." />
        <AppEmptyState
          v-else-if="recommendedPlaylists.length === 0"
          variant="plain"
          icon="playlistMusic"
          title="暂无推荐歌单"
        />
        <MusicCardGrid v-else layout="grid-5">
          <MusicCard
            v-for="item in recommendedPlaylists"
            :key="item.specialid"
            :cover="item.imgurl"
            :title="item.specialname || item.name || '未命名歌单'"
            :meta="item.play_count ? formatCount(item.play_count) + ' 次播放' : item.nickname"
            size="md"
            variant="playlist"
            playable
            @select="$emit('select-playlist', item)"
            @play="$emit('play-playlist', item)"
          />
        </MusicCardGrid>
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
      />
      <MusicCardGrid v-else layout="grid-auto">
        <MusicCard
          v-for="album in albums"
          :key="album.id"
          :cover="album.cover"
          :title="album.name"
          :subtitle="album.artist"
          size="md"
          variant="album"
          @select="$emit('select-album', album)"
        />
      </MusicCardGrid>
    </MusicSection>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MusicGreetingSection from './MusicGreetingSection.vue'
import MusicRecentSection from './MusicRecentSection.vue'
import MusicSection from '../shared/MusicSection.vue'
import MusicCard from '../shared/MusicCard.vue'
import MusicCardGrid from '../shared/MusicCardGrid.vue'
import MusicRankRow from '../shared/MusicRankRow.vue'
import AppBlockLoader from '@/shared/components/AppBlockLoader.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import { formatCount } from '@/shared/lib/dateFormat'
import type { MusicPlaylist, MusicRank, MusicAlbum, MusicTrack, MusicUserProfile } from '@/shared/api/music'
import { useMusicPlayerStore } from '@/features/music/stores/musicPlayer'

type FmMode = 'normal' | 'small' | 'peak'

const props = defineProps<{
  playlists: MusicPlaylist[]
  ranks: MusicRank[]
  albums: MusicAlbum[]
  playlistsLoading: boolean
  ranksLoading: boolean
  albumsLoading: boolean
  user?: MusicUserProfile | null
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
  'fm-play': []
  'continue-play': [track: MusicTrack]
  'switch-fm-mode': [mode: FmMode]
  'switch-fm-pool': [poolId: string]
}>()

const player = useMusicPlayerStore()

const recentTracks = computed(() => props.historyTracks?.slice(0, 5) || [])
const lastPlayedTrack = computed(() => player.lastSessionTrack)
const featuredPlaylist = computed(() => props.playlists[0] || null)
const recommendedPlaylists = computed(() => props.playlists.slice(1, 11))

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

.music-home-board {
  display: grid;
  grid-template-columns: minmax(0, 2.25fr) minmax(17rem, 0.75fr);
  align-items: start;
  gap: var(--space-5);
  margin-bottom: var(--space-6);
}

.music-home-board > .music-section {
  margin-bottom: 0;
}

@media (max-width: 1180px) {
  .music-home-board {
    grid-template-columns: 1fr;
  }
}
</style>
