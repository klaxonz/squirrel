<template>
  <div class="music-user-playlists">
    <TransitionGroup
      name="playlist-list"
      tag="div"
      class="music-user-playlists-list"
    >
      <button
        v-for="playlist in visiblePlaylists"
        :key="playlist.id"
        class="music-user-playlist-item"
        :class="{ 'music-user-playlist-item--active': selectedId === playlist.id }"
        @click="$emit('select', playlist)"
      >
        <AppIcon name="playlistMusic" class="h-3.5 w-3.5" />
        <span class="truncate">{{ playlist.name }}</span>
        <span class="music-user-playlist-count">{{ playlist.song_count }}</span>
      </button>
    </TransitionGroup>

    <button
      v-if="playlists.length > maxVisible"
      class="music-user-playlists-more"
      @click="toggleExpand"
    >
      {{ isExpanded ? '收起' : `展开全部 (${playlists.length - maxVisible}个)` }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { MusicUserPlaylist } from '@/shared/api/music'

const props = withDefaults(defineProps<{
  playlists: MusicUserPlaylist[]
  selectedId?: string
  maxVisible?: number
}>(), {
  maxVisible: 5,
})

defineEmits<{
  select: [playlist: MusicUserPlaylist]
}>()

const isExpanded = ref(false)

const visiblePlaylists = computed(() => {
  if (isExpanded.value) {
    return props.playlists.slice(0, 15)
  }
  return props.playlists.slice(0, props.maxVisible)
})

function toggleExpand() {
  isExpanded.value = !isExpanded.value
}
</script>

<style scoped>
.music-user-playlists {
  margin-top: 0.25rem;
}

.music-user-playlists-list {
  display: flex;
  flex-direction: column;
}

.music-user-playlist-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 1.25rem;
  margin: 0.0625rem 0.5rem;
  width: calc(100% - 1rem);
  border: none;
  background: none;
  color: hsl(var(--foreground) / 0.6);
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
  border-radius: 0.375rem;
}

.music-user-playlist-item:hover {
  color: hsl(var(--foreground));
  background: hsl(var(--muted) / 0.3);
}

.music-user-playlist-item--active {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.08);
}

.music-user-playlist-count {
  font-size: 0.5625rem;
  color: hsl(var(--muted-foreground) / 0.5);
  margin-left: auto;
  font-variant-numeric: tabular-nums;
}

.music-user-playlists-more {
  display: block;
  width: calc(100% - 1rem);
  margin: 0.25rem 0.5rem;
  padding: 0.375rem 1.25rem;
  font-size: 0.6875rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  border-radius: 0.375rem;
  transition: all 0.15s ease;
}

.music-user-playlists-more:hover {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.05);
}

.playlist-list-move,
.playlist-list-enter-active,
.playlist-list-leave-active {
  transition: all 0.2s ease;
}

.playlist-list-enter-from,
.playlist-list-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}
</style>