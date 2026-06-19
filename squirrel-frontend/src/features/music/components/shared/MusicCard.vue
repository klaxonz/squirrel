<template>
  <article
    class="music-card"
    :class="[sizeClass, variantClass]"
    @click="$emit('select')"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    <div class="music-card-cover" :style="coverStyle">
      <img
        v-if="cover"
        :src="cover"
        :alt="title"
        loading="lazy"
        @error="handleCoverError"
      />
      <div v-else class="music-card-placeholder">
        <AppIcon :name="placeholderIcon" class="h-8 w-8" />
      </div>

      <Transition
        enter-active-class="transition-opacity duration-200"
        leave-active-class="transition-opacity duration-150"
        enter-from-class="opacity-0"
        leave-to-class="opacity-0"
      >
        <div v-if="isHovered || isPlaying" class="music-card-overlay">
          <button class="music-card-play-btn" @click.stop="$emit('play')">
            <AppIcon name="play" class="h-5 w-5" />
          </button>
        </div>
      </Transition>

      <span v-if="isPlaying" class="music-card-playing-badge">
        <AppIcon name="volumeHigh" class="h-3 w-3" />
      </span>

      <span v-if="badge" class="music-card-badge">{{ badge }}</span>
    </div>

    <div class="music-card-info">
      <h3 class="music-card-title" :title="title">{{ title }}</h3>
      <p v-if="subtitle" class="music-card-subtitle" :title="subtitle">{{ subtitle }}</p>
      <p v-if="meta" class="music-card-meta">{{ meta }}</p>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
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
}>(), {
  size: 'md',
  variant: 'playlist',
  isPlaying: false,
})

defineEmits<{
  select: []
  play: []
}>()

const isHovered = ref(false)
const coverError = ref(false)

const sizeClass = computed(() => musicCardVariants({ size: props.size }))
const variantClass = computed(() => musicCardVariants({ variant: props.variant }))

const coverStyle = computed(() => {
  const radii: Record<MusicCardSize, string> = {
    xs: '6px',
    sm: '8px',
    md: '12px',
    lg: '14px',
    xl: '16px',
  }
  return { '--card-radius': radii[props.size] }
})

const placeholderIcon = computed(() => {
  const icons: Record<MusicCardVariant, AppIconName> = {
    playlist: 'playlistMusic',
    album: 'disc',
    artist: 'user',
    rank: 'list',
  }
  return icons[props.variant]
})

function handleCoverError() {
  coverError.value = true
}
</script>

<style scoped>
.music-card {
  cursor: pointer;
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.music-card:hover {
  transform: translateY(-4px);
}

.music-card--xs .music-card-info { padding: 0.375rem 0; }
.music-card--sm .music-card-info { padding: 0.5rem 0; }
.music-card--md .music-card-info { padding: 0.625rem 0; }
.music-card--lg .music-card-info { padding: 0.75rem 0; }
.music-card--xl .music-card-info { padding: 0.875rem 0; }

.music-card-cover {
  position: relative;
  aspect-ratio: 1;
  border-radius: var(--card-radius, 12px);
  overflow: hidden;
  background: hsl(var(--muted) / 0.3);
  box-shadow: 0 4px 16px hsl(var(--foreground) / 0.08), 0 2px 4px hsl(var(--foreground) / 0.04);
  transition: box-shadow 0.25s ease;
}

.music-card:hover .music-card-cover {
  box-shadow: 0 8px 28px hsl(var(--foreground) / 0.14), 0 4px 8px hsl(var(--foreground) / 0.06);
}

.music-card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.music-card:hover .music-card-cover img {
  transform: scale(1.06);
}

.music-card-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground) / 0.4);
}

.music-card-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, transparent 0%, hsl(var(--foreground) / 0.55) 100%);
}

.music-card-play-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 9999px;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 16px hsl(var(--foreground) / 0.15);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.music-card-play-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 20px hsl(var(--foreground) / 0.2);
}

.music-card-playing-badge {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 9999px;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
}

.music-card-badge {
  position: absolute;
  bottom: 0.5rem;
  left: 0.5rem;
  padding: 0.125rem 0.5rem;
  font-size: 0.625rem;
  font-weight: 600;
  background: hsl(var(--background) / 0.85);
  color: hsl(var(--foreground));
  border-radius: 0.25rem;
  backdrop-filter: blur(4px);
}

.music-card-info {
  min-width: 0;
}

.music-card-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-card--xs .music-card-title { font-size: 0.75rem; }
.music-card--lg .music-card-title { font-size: 0.9375rem; }
.music-card--xl .music-card-title { font-size: 1rem; }

.music-card-subtitle {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  margin-top: 0.125rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-card-meta {
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground) / 0.7);
  margin-top: 0.25rem;
}
</style>
