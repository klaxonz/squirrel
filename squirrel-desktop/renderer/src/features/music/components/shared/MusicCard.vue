<template>
  <article
    class="music-card"
    :class="[sizeClass, variantClass, { 'music-card--playing': isPlaying }]"
  >
    <div class="music-card-cover">
      <Button
        unstyled
        class="music-card-cover-button"
        :aria-label="`打开 ${title}`"
        @click="$emit('select')"
      >
        <img
          v-if="cover && !coverError"
          :src="cover"
          :alt="title"
          loading="lazy"
          @error="handleCoverError"
        />
        <span v-else class="music-card-placeholder">
          <AppIcon :name="placeholderIcon" class="h-7 w-7" />
        </span>
      </Button>

      <Button
        v-if="playable"
        unstyled
        class="music-card-play"
        :aria-label="`播放 ${title}`"
        @click.stop="$emit('play')"
      >
        <AppIcon name="play" class="music-card-play-icon" />
      </Button>

      <span v-if="isPlaying" class="music-card-playing-badge">
        <AppIcon name="volumeHigh" class="h-3 w-3" />
      </span>

      <span v-if="badge" class="music-card-badge">{{ badge }}</span>
    </div>

    <Button unstyled class="music-card-info" @click="$emit('select')">
      <span class="music-card-title" :title="title">{{ title }}</span>
      <span v-if="subtitle" class="music-card-subtitle" :title="subtitle">{{ subtitle }}</span>
      <span v-if="meta" class="music-card-meta">{{ meta }}</span>
    </Button>
  </article>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import type { AppIconName } from '@/shared/icons/app-icons'
import { musicCardVariants, type MusicCardSize, type MusicCardVariant } from './music-card.variants'

const props = withDefaults(defineProps<{
  cover?: string
  title: string
  subtitle?: string
  meta?: string
  badge?: string
  size?: MusicCardSize
  variant?: MusicCardVariant
  isPlaying?: boolean
  playable?: boolean
}>(), {
  size: 'md',
  variant: 'playlist',
  isPlaying: false,
  playable: false,
})

defineEmits<{
  select: []
  play: []
}>()

const coverError = ref(false)

const sizeClass = computed(() => musicCardVariants({ size: props.size }))
const variantClass = computed(() => musicCardVariants({ variant: props.variant }))

const placeholderIcon = computed(() => {
  const icons: Record<MusicCardVariant, AppIconName> = {
    playlist: 'playlistMusic',
    album: 'disc',
    artist: 'user',
    rank: 'list',
  }
  return icons[props.variant]
})

watch(() => props.cover, () => {
  coverError.value = false
})

function handleCoverError() {
  coverError.value = true
}
</script>

<style scoped>
.music-card {
  min-width: 0;
}

.music-card--xs { --music-card-radius: var(--radius-sm); }
.music-card--sm { --music-card-radius: var(--radius-md); }
.music-card--md,
.music-card--lg,
.music-card--xl { --music-card-radius: var(--radius-lg); }

.music-card-cover {
  position: relative;
  aspect-ratio: 1;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.45);
  border-radius: var(--music-card-radius, var(--radius-lg));
  background: hsl(var(--muted) / 0.3);
  transition: border-color var(--duration-fast) var(--ease-default);
}

.music-card-cover::after {
  position: absolute;
  inset: 0;
  z-index: 1;
  background: var(--app-media-scrim-soft);
  content: '';
  opacity: 0;
  pointer-events: none;
  transition: opacity var(--duration-fast) var(--ease-out);
}

.music-card-cover-button {
  display: block;
  width: 100%;
  height: 100%;
  cursor: pointer;
}

.music-card-cover-button img,
.music-card-placeholder {
  width: 100%;
  height: 100%;
}

.music-card-cover-button img {
  display: block;
  object-fit: cover;
  transition: transform var(--duration-slow) var(--ease-out);
}

.music-card:hover .music-card-cover {
  border-color: hsl(var(--border));
}

.music-card:hover .music-card-cover-button img {
  transform: scale(1.025);
}

.music-card-cover-button:focus-visible,
.music-card-info:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: 2px;
}

.music-card-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground) / 0.42);
}

.music-card-play {
  position: absolute;
  top: 50%;
  left: 50%;
  z-index: 2;
  display: flex;
  width: 2.75rem;
  height: 2.75rem;
  align-items: center;
  justify-content: center;
  border: 0;
  background: transparent;
  color: hsl(var(--app-media-on-image));
  opacity: 0;
  transform: translate(-50%, -50%) scale(0.88);
  cursor: pointer;
  transition:
    opacity var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out),
    color var(--duration-fast) var(--ease-default);
}

.music-card-play-icon {
  width: 1.5rem;
  height: 1.5rem;
  fill: currentColor;
  filter: drop-shadow(0 2px 5px hsl(var(--overlay) / 0.42));
  transform: translateX(0.075rem);
}

.music-card:hover .music-card-cover::after,
.music-card:focus-within .music-card-cover::after,
.music-card--playing .music-card-cover::after,
.music-card:hover .music-card-play,
.music-card:focus-within .music-card-play,
.music-card--playing .music-card-play {
  opacity: 1;
}

.music-card:hover .music-card-play,
.music-card:focus-within .music-card-play,
.music-card--playing .music-card-play {
  transform: translate(-50%, -50%) scale(1);
}

.music-card-play:hover {
  color: hsl(var(--app-media-on-image) / 0.84);
  transform: translate(-50%, -50%) scale(1.08);
}

.music-card-play:active {
  transform: translate(-50%, -50%) scale(0.92);
}

.music-card-play:focus-visible {
  border-radius: var(--radius-md);
  outline: 2px solid hsl(var(--app-media-on-image) / 0.9);
  outline-offset: 0;
}

.music-card-playing-badge {
  position: absolute;
  top: var(--space-2);
  left: var(--space-2);
  z-index: 2;
  display: flex;
  width: 1.5rem;
  height: 1.5rem;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
}

.music-card-badge {
  position: absolute;
  bottom: var(--space-2);
  left: var(--space-2);
  z-index: 2;
  border: 1px solid hsl(var(--app-media-on-image) / 0.16);
  border-radius: var(--radius-sm);
  padding: 0.2rem 0.45rem;
  background: var(--app-media-badge-bg);
  color: hsl(var(--app-media-on-image) / 0.92);
  font-size: 0.625rem;
  font-weight: 650;
}

.music-card-info {
  display: block;
  width: 100%;
  min-width: 0;
  padding: 0.625rem 0 0;
  color: hsl(var(--foreground));
  text-align: left;
  cursor: pointer;
}

.music-card-title,
.music-card-subtitle,
.music-card-meta {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-card-title {
  font-size: 0.8125rem;
  font-weight: 650;
  line-height: 1.3;
}

.music-card--xs .music-card-title { font-size: 0.75rem; }
.music-card--lg .music-card-title { font-size: 0.875rem; }
.music-card--xl .music-card-title { font-size: 0.9375rem; }

.music-card-subtitle {
  margin-top: 0.2rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.music-card-meta {
  margin-top: 0.25rem;
  color: hsl(var(--muted-foreground) / 0.76);
  font-size: 0.6875rem;
}

@media (prefers-reduced-motion: reduce) {
  .music-card-cover,
  .music-card-cover::after,
  .music-card-cover-button img,
  .music-card-play {
    transition: none;
  }
}
</style>
