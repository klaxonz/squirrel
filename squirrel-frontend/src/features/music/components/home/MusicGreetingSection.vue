<template>
  <section class="music-greeting">
    <header class="music-greeting-header">
      <div class="music-greeting-identity">
        <div class="music-greeting-avatar">
          <img v-if="user?.avatar" :src="user.avatar" :alt="user?.nickname ? `${user.nickname}的头像` : '用户头像'" />
          <AppIcon v-else name="user" class="h-5 w-5" />
        </div>
        <div class="music-greeting-copy">
          <h1 class="music-greeting-title">{{ greetingText }}</h1>
          <p class="music-greeting-subtitle">{{ subtitleText }}</p>
        </div>
      </div>

      <Button
        v-if="recentTrack && !hasCurrentTrack"
        variant="secondary"
        class="music-continue-button"
        @click="$emit('continue-play', recentTrack)"
      >
        <AppIcon name="play" class="h-3.5 w-3.5" />
        <span>继续播放</span>
        <strong>{{ recentTrack.title }}</strong>
      </Button>
    </header>

    <div class="music-hero-grid" :class="{ 'music-hero-grid--fm-only': !featuredPlaylist }">
      <article v-if="featuredPlaylist" class="music-featured">
        <Button
          unstyled
          class="music-featured-cover"
          :aria-label="`打开歌单 ${featuredTitle}`"
          @click="$emit('open-featured', featuredPlaylist)"
        >
          <img
            v-if="featuredPlaylist.imgurl"
            :src="featuredPlaylist.imgurl"
            :alt="featuredTitle"
          />
          <span v-else class="music-featured-cover-placeholder">
            <AppIcon name="playlistMusic" class="h-10 w-10" />
          </span>
        </Button>

        <div class="music-featured-content">
          <div class="music-featured-copy">
            <span class="music-featured-kicker">今日精选</span>
            <h2 class="music-featured-title">{{ featuredTitle }}</h2>
            <p v-if="featuredPlaylist.intro" class="music-featured-description">
              {{ featuredPlaylist.intro }}
            </p>
            <div
              v-if="featuredPlaylist.nickname || featuredPlaylist.play_count"
              class="music-featured-meta"
            >
              <span v-if="featuredPlaylist.nickname">
                <AppIcon name="user" class="h-3.5 w-3.5" />
                {{ featuredPlaylist.nickname }}
              </span>
              <span v-if="featuredPlaylist.play_count">
                <AppIcon name="play" class="h-3.5 w-3.5" />
                {{ formatCount(featuredPlaylist.play_count) }} 次播放
              </span>
            </div>
            <div v-if="featuredPlaylist.tags?.length" class="music-featured-tags" aria-label="歌单标签">
              <span v-for="tag in featuredPlaylist.tags.slice(0, 3)" :key="tag.tag_name">
                {{ tag.tag_name }}
              </span>
            </div>
            <div class="music-featured-actions">
              <Button
                variant="secondary"
                size="sm"
                @click="$emit('play-featured', featuredPlaylist)"
              >
                <AppIcon name="play" class="h-3.5 w-3.5" />
                播放
              </Button>
              <Button
                variant="ghost"
                size="sm"
                class="music-featured-details"
                @click="$emit('open-featured', featuredPlaylist)"
              >
                查看歌单
                <AppIcon name="chevronRight" class="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </div>
      </article>

      <div class="music-hero-utility">
        <section class="music-fm-panel" :class="{ 'music-fm-panel--active': fmActive }">
          <header class="music-fm-header">
            <div class="music-fm-heading">
              <span class="music-fm-icon">
                <AppIcon v-if="fmPlaying" name="playlistMusic" class="h-5 w-5" />
                <AppIcon v-else name="star" class="h-5 w-5" />
              </span>
              <div>
                <span class="music-fm-label">私人 FM</span>
                <span class="music-fm-meta">{{ fmStateText }}</span>
              </div>
            </div>

            <Button
              unstyled
              class="music-fm-play"
              :title="fmButtonTitle"
              :loading="fmLoading"
              @click="$emit('fm-play')"
            >
              <AppIcon v-if="!fmLoading && fmPlaying" name="pause" class="h-4 w-4" />
              <AppIcon v-else-if="!fmLoading" name="play" class="h-4 w-4" />
            </Button>
          </header>

          <div class="music-fm-options">
            <div class="music-fm-option-row">
              <span class="music-fm-option-label">模式</span>
              <div class="music-fm-segment">
                <Button
                  v-for="modeOption in fmModes"
                  :key="modeOption.value"
                  variant="ghost"
                  size="xs"
                  :class="{ 'is-active': fmMode === modeOption.value }"
                  :aria-pressed="fmMode === modeOption.value"
                  @click="$emit('switch-fm-mode', modeOption.value)"
                >
                  {{ modeOption.label }}
                </Button>
              </div>
            </div>
            <div class="music-fm-option-row">
              <span class="music-fm-option-label">曲库</span>
              <div class="music-fm-segment">
                <Button
                  v-for="poolOption in fmPools"
                  :key="poolOption.value"
                  variant="ghost"
                  size="xs"
                  :class="{ 'is-active': fmPoolId === poolOption.value }"
                  :aria-pressed="fmPoolId === poolOption.value"
                  @click="$emit('switch-fm-pool', poolOption.value)"
                >
                  {{ poolOption.label }}
                </Button>
              </div>
            </div>
          </div>
        </section>

        <div class="music-quick-actions">
          <MusicActionButton
            icon="time"
            label="每日推荐"
            description="按今天的口味生成"
            @click="$emit('everyday')"
          />
          <MusicActionButton
            icon="playlists"
            label="新歌速递"
            description="浏览最近发布"
            @click="$emit('new-songs')"
          />
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import MusicActionButton from './MusicActionButton.vue'
import { formatCount } from '@/shared/lib/dateFormat'
import type { MusicPlaylist, MusicUserProfile, MusicTrack } from '@/shared/api/music'

type FmMode = 'normal' | 'small' | 'peak'

const props = defineProps<{
  user?: MusicUserProfile | null
  recentTrack?: MusicTrack | null
  hasCurrentTrack?: boolean
  featuredPlaylist?: MusicPlaylist | null
  fmMode: FmMode
  fmPoolId: string
  fmLoading?: boolean
  fmActive?: boolean
  fmPlaying?: boolean
}>()

defineEmits<{
  'continue-play': [track: MusicTrack]
  'open-featured': [playlist: MusicPlaylist]
  'play-featured': [playlist: MusicPlaylist]
  'fm-play': []
  'everyday': []
  'new-songs': []
  'switch-fm-mode': [mode: FmMode]
  'switch-fm-pool': [poolId: string]
}>()

const fmModes = [
  { value: 'normal' as const, label: '发现' },
  { value: 'small' as const, label: '小众' },
  { value: 'peak' as const, label: '30s' },
]

const fmPools = [
  { value: '0', label: '口味' },
  { value: '1', label: '风格' },
  { value: '2', label: 'Gamma' },
]

const currentModeLabel = computed(() => fmModes.find(item => item.value === props.fmMode)!.label)
const currentPoolLabel = computed(() => fmPools.find(item => item.value === props.fmPoolId)!.label)
const featuredTitle = computed(() => props.featuredPlaylist?.specialname || props.featuredPlaylist?.name || '精选歌单')
const fmStateText = computed(() => {
  const base = `${currentModeLabel.value} · ${currentPoolLabel.value}`
  if (props.fmLoading) return `加载中 · ${base}`
  if (props.fmPlaying) return `正在播放 · ${base}`
  if (props.fmActive) return `已暂停 · ${base}`
  return base
})
const fmButtonTitle = computed(() => {
  if (props.fmLoading) return '正在加载私人 FM'
  if (props.fmPlaying) return '暂停私人 FM'
  if (props.fmActive) return '继续私人 FM'
  return '播放私人 FM'
})

const greetingText = computed(() => {
  const hour = new Date().getHours()
  const name = props.user?.nickname || ''
  if (hour < 6) return name ? `${name}，夜深了` : '夜深了，还在听歌吗'
  if (hour < 12) return name ? `${name}，早上好` : '早上好'
  if (hour < 14) return name ? `${name}，中午好` : '中午好'
  if (hour < 18) return name ? `${name}，下午好` : '下午好'
  if (hour < 22) return name ? `${name}，晚上好` : '晚上好'
  return name ? `${name}，夜深了` : '夜深了'
})

const subtitleText = computed(() => {
  if (props.recentTrack && !props.hasCurrentTrack) {
    return `上次播放：${props.recentTrack.title}`
  }
  return '从熟悉的声音开始，或发现一些新的。'
})
</script>

<style scoped>
.music-greeting {
  width: 100%;
  padding: var(--space-2) 0 var(--space-6);
}

.music-greeting-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  margin-bottom: var(--space-4);
}

.music-greeting-identity {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-3);
}

.music-greeting-avatar {
  display: flex;
  width: 2.75rem;
  height: 2.75rem;
  flex: none;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--radius-lg);
  background: hsl(var(--muted) / 0.45);
  color: hsl(var(--muted-foreground));
}

.music-greeting-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-greeting-copy {
  min-width: 0;
}

.music-greeting-title {
  margin: 0;
  color: var(--app-heading-color);
  font-family: var(--app-heading-font);
  font-size: var(--app-h1-size);
  font-weight: var(--app-h1-weight);
  letter-spacing: 0;
  line-height: var(--app-h1-leading);
}

.music-greeting-subtitle {
  margin: 0.25rem 0 0;
  overflow: hidden;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-continue-button {
  max-width: 24rem;
  min-width: 0;
  justify-content: flex-start;
}

.music-continue-button span {
  flex: none;
  font-size: 0.75rem;
  font-weight: 650;
}

.music-continue-button strong {
  min-width: 0;
  overflow: hidden;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.48fr) minmax(22rem, 1.02fr);
  gap: var(--space-3);
  align-items: stretch;
}

.music-hero-grid--fm-only {
  grid-template-columns: 1fr;
}

.music-featured {
  display: grid;
  grid-template-columns: 15rem minmax(0, 1fr);
  min-height: 13rem;
  overflow: hidden;
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--radius-xl);
  background: hsl(var(--card) / 0.56);
}

.music-featured-cover {
  position: relative;
  display: block;
  min-width: 0;
  overflow: hidden;
  border-right: 1px solid var(--app-surface-border-subtle);
  background: hsl(var(--muted) / 0.35);
  cursor: pointer;
}

.music-featured-cover img,
.music-featured-cover-placeholder {
  width: 100%;
  height: 100%;
  min-height: 13rem;
}

.music-featured-cover img {
  display: block;
  object-fit: cover;
  transition: transform var(--duration-slow) var(--ease-out);
}

.music-featured-cover:hover img {
  transform: scale(1.025);
}

.music-featured-cover-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground) / 0.45);
}

.music-featured-cover:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: -2px;
}

.music-featured-content {
  display: flex;
  min-width: 0;
  align-items: center;
  padding: var(--space-5);
}

.music-featured-copy {
  min-width: 0;
  width: 100%;
  max-width: 36rem;
}

.music-featured-kicker {
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 750;
}

.music-featured-title {
  display: -webkit-box;
  margin: var(--space-2) 0 0;
  overflow: hidden;
  color: hsl(var(--foreground));
  font-family: var(--app-heading-font);
  font-size: 1.375rem;
  font-weight: 650;
  letter-spacing: 0;
  line-height: 1.15;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.music-featured-description {
  display: -webkit-box;
  margin: var(--space-2) 0 0;
  overflow: hidden;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.music-featured-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-3);
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
}

.music-featured-meta span {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.music-featured-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-3);
}

.music-featured-tags span {
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: var(--radius-sm);
  padding: 0.2rem 0.45rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  line-height: 1.2;
}

.music-featured-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-4);
}

.music-featured-details {
  color: hsl(var(--muted-foreground));
}

.music-featured-details:hover {
  background: transparent;
  color: hsl(var(--foreground));
}

.music-hero-utility {
  display: grid;
  min-width: 0;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: var(--space-2);
}

.music-fm-panel {
  display: flex;
  min-height: 8.5rem;
  flex-direction: column;
  justify-content: space-between;
  gap: var(--space-4);
  border: 1px solid var(--app-surface-border-subtle);
  border-radius: var(--radius-xl);
  padding: var(--space-4);
  background: hsl(var(--card) / 0.56);
}

.music-fm-panel--active {
  border-color: hsl(var(--foreground) / 0.18);
}

.music-fm-header,
.music-fm-heading,
.music-fm-option-row {
  display: flex;
  align-items: center;
}

.music-fm-header {
  justify-content: space-between;
  gap: var(--space-3);
}

.music-fm-heading {
  min-width: 0;
  gap: var(--space-3);
}

.music-fm-icon {
  display: flex;
  width: 2.5rem;
  height: 2.5rem;
  flex: none;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-lg);
  background: hsl(var(--muted) / 0.52);
  color: hsl(var(--foreground) / 0.72);
}

.music-fm-play {
  display: flex;
  width: 2rem;
  height: 2rem;
  flex: none;
  align-items: center;
  justify-content: center;
  border: 1px solid hsl(var(--border) / 0.62);
  border-radius: 999px;
  background: hsl(var(--muted) / 0.48);
  color: hsl(var(--foreground));
  cursor: pointer;
  transition:
    background-color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default),
    transform var(--duration-fast) var(--ease-default);
}

.music-fm-play:hover {
  border-color: hsl(var(--foreground) / 0.24);
  background: hsl(var(--foreground));
  color: hsl(var(--background));
}

.music-fm-play:active {
  transform: scale(0.94);
}

.music-fm-play:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: 2px;
}

.music-fm-label,
.music-fm-meta {
  display: block;
}

.music-fm-label {
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  font-weight: 700;
}

.music-fm-meta {
  margin-top: 0.125rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.music-fm-options {
  display: grid;
  gap: var(--space-2);
}

.music-fm-option-row {
  min-width: 0;
  justify-content: space-between;
  gap: var(--space-3);
}

.music-fm-option-label {
  flex: none;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 650;
}

.music-fm-segment {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 0.125rem;
  padding: 0.125rem;
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.34);
}

.music-fm-segment :deep(.is-active) {
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  box-shadow: 0 0 0 1px hsl(var(--border) / 0.58);
}

.music-quick-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

@media (max-width: 1180px) {
  .music-hero-grid {
    grid-template-columns: 1fr;
  }

  .music-hero-utility {
    grid-template-columns: minmax(20rem, 1fr) minmax(20rem, 1fr);
    grid-template-rows: auto;
  }

  .music-quick-actions {
    align-content: stretch;
  }
}

@media (prefers-reduced-motion: reduce) {
  .music-featured-cover img {
    transition: none;
  }
}
</style>
