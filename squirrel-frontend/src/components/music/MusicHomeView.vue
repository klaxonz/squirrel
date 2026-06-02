<template>
  <div class="music-home">
    <section v-if="banners.length" class="music-hero">
      <div class="music-hero-slider">
        <div
          v-for="(banner, index) in banners.slice(0, 5)"
          :key="banner.id"
          class="music-hero-slide"
          :class="{ 'music-hero-slide--active': index === currentBanner }"
        >
          <img :src="banner.cover" :alt="banner.title" class="music-hero-img" />
          <div class="music-hero-overlay">
            <h2 class="music-hero-title">{{ banner.title }}</h2>
          </div>
        </div>
      </div>
      <div class="music-hero-dots">
        <button
          v-for="(_, index) in banners.slice(0, 5)"
          :key="index"
          class="music-hero-dot"
          :class="{ 'music-hero-dot--active': index === currentBanner }"
          @click="currentBanner = index"
        />
      </div>
    </section>

    <section class="music-section">
      <div class="music-section-header">
        <h2 class="music-section-title">推荐歌单</h2>
        <button class="music-section-more" @click="$emit('navigate', 'playlists')">
          更多 <AppIcon name="chevronRight" class="h-4 w-4" />
        </button>
      </div>
      <div v-if="loading" class="music-grid-skeleton">
        <div v-for="i in 6" :key="i" class="skeleton-card" />
      </div>
      <div v-else class="music-card-grid">
        <article
          v-for="item in playlists.slice(0, 6)"
          :key="item.id"
          class="music-card"
          @click="$emit('select-playlist', item)"
        >
          <div class="music-card-image">
            <img :src="item.cover" :alt="item.name" loading="lazy" />
            <div class="music-card-play">
              <AppIcon name="play" class="h-5 w-5" />
            </div>
          </div>
          <h3 class="music-card-name">{{ item.name }}</h3>
          <p class="music-card-meta">{{ item.play_count ? formatCount(item.play_count) + '次播放' : item.creator }}</p>
        </article>
      </div>
    </section>

    <section class="music-section">
      <div class="music-section-header">
        <h2 class="music-section-title">排行榜</h2>
        <button class="music-section-more" @click="$emit('navigate', 'ranks')">
          更多 <AppIcon name="chevronRight" class="h-4 w-4" />
        </button>
      </div>
      <div v-if="ranksLoading" class="music-grid-skeleton">
        <div v-for="i in 4" :key="i" class="skeleton-card" />
      </div>
      <div v-else class="music-card-grid music-card-grid--4">
        <article
          v-for="rank in ranks.slice(0, 4)"
          :key="rank.id"
          class="music-card music-card--rank"
          @click="$emit('select-rank', rank)"
        >
          <div class="music-card-image">
            <img :src="rank.cover" :alt="rank.name" loading="lazy" />
            <div class="music-card-play">
              <AppIcon name="play" class="h-5 w-5" />
            </div>
          </div>
          <h3 class="music-card-name">{{ rank.name }}</h3>
          <p class="music-card-meta">{{ rank.update_frequency || '实时更新' }}</p>
        </article>
      </div>
    </section>

    <section class="music-section">
      <div class="music-section-header">
        <h2 class="music-section-title">新碟上架</h2>
        <button class="music-section-more" @click="$emit('navigate', 'new_albums')">
          更多 <AppIcon name="chevronRight" class="h-4 w-4" />
        </button>
      </div>
      <div v-if="albumsLoading" class="music-grid-skeleton">
        <div v-for="i in 6" :key="i" class="skeleton-card" />
      </div>
      <div v-else class="music-card-grid">
        <article
          v-for="album in albums.slice(0, 6)"
          :key="album.id"
          class="music-card music-card--album"
          @click="$emit('select-album', album)"
        >
          <div class="music-card-image">
            <img :src="album.cover" :alt="album.name" loading="lazy" />
            <div class="music-card-play">
              <AppIcon name="play" class="h-5 w-5" />
            </div>
          </div>
          <h3 class="music-card-name">{{ album.name }}</h3>
          <p class="music-card-meta">{{ album.artist }}</p>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import type { MusicPlaylist, MusicRank, MusicAlbum } from '@/api/music'

defineProps<{
  banners: Array<{ id: string; title: string; cover: string }>
  playlists: MusicPlaylist[]
  ranks: MusicRank[]
  albums: MusicAlbum[]
  loading: boolean
  ranksLoading: boolean
  albumsLoading: boolean
}>()

defineEmits<{
  'navigate': [section: string]
  'select-playlist': [playlist: MusicPlaylist]
  'select-rank': [rank: MusicRank]
  'select-album': [album: MusicAlbum]
}>()

const currentBanner = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  timer = setInterval(() => {
    currentBanner.value = (currentBanner.value + 1) % 5
  }, 5000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

function formatCount(count: number): string {
  if (count >= 100000000) return (count / 100000000).toFixed(1) + '亿'
  if (count >= 10000) return (count / 10000).toFixed(1) + '万'
  return String(count)
}
</script>

<style scoped>
.music-home {
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

.music-hero {
  position: relative;
  border-radius: 1rem;
  overflow: hidden;
  margin-bottom: 2rem;
}

.music-hero-slider {
  position: relative;
  aspect-ratio: 21/9;
}

.music-hero-slide {
  position: absolute;
  inset: 0;
  opacity: 0;
  transition: opacity 0.5s ease;
}

.music-hero-slide--active {
  opacity: 1;
}

.music-hero-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0,0,0,0.7) 0%, transparent 50%);
  display: flex;
  align-items: flex-end;
  padding: 1.5rem;
}

.music-hero-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: white;
  max-width: 50%;
}

.music-hero-dots {
  position: absolute;
  bottom: 0.75rem;
  right: 1.5rem;
  display: flex;
  gap: 0.5rem;
}

.music-hero-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 9999px;
  border: none;
  background: hsl(var(--muted-foreground) / 0.4);
  cursor: pointer;
  transition: all 0.2s ease;
}

.music-hero-dot--active {
  width: 1.25rem;
  background: hsl(var(--primary));
}

.music-section {
  margin-bottom: 2rem;
}

.music-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.music-section-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: hsl(var(--foreground));
}

.music-section-more {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.8125rem;
  color: hsl(var(--muted-foreground));
  background: none;
  border: none;
  cursor: pointer;
}

.music-section-more:hover {
  color: hsl(var(--foreground));
}

.music-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 1.25rem;
}

.music-card-grid--4 {
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
}

.music-card {
  cursor: pointer;
  transition: transform 0.2s ease;
}

.music-card:hover {
  transform: translateY(-4px);
}

.music-card-image {
  position: relative;
  aspect-ratio: 1;
  border-radius: 0.75rem;
  overflow: hidden;
  background: hsl(var(--muted) / 0.3);
}

.music-card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-card-play {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  opacity: 0;
  transition: opacity 0.2s ease;
}

.music-card:hover .music-card-play {
  opacity: 1;
}

.music-card-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: hsl(var(--foreground));
  margin-top: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-card-meta {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  margin-top: 0.125rem;
}

.music-grid-skeleton {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 1.25rem;
}

.skeleton-card {
  aspect-ratio: 1;
  border-radius: 0.75rem;
  background: hsl(var(--muted) / 0.3);
  animation: skeleton-pulse 1.5s infinite;
}

@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@media (max-width: 768px) {
  .music-home {
    padding: 1rem;
  }

  .music-hero-title {
    font-size: 1rem;
    max-width: 100%;
  }

  .music-card-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
  }

  .music-card-grid--4 {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>