<template>
  <div class="music-track-list">
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      leave-active-class="transition-all duration-150 ease-in"
      enter-from-class="opacity-0 -translate-y-2"
      leave-to-class="opacity-0 -translate-y-2"
    >
      <div v-if="selectionMode && selectedTracks.size > 0" class="music-track-batch-bar">
        <div class="music-batch-left">
          <button class="music-batch-btn" @click="toggleSelectAll">
            <AppIcon :name="isAllSelected ? 'check' : 'circle'" class="h-4 w-4" />
            {{ isAllSelected ? '取消全选' : '全选' }}
          </button>
          <span class="music-batch-count">已选 {{ selectedTracks.size }} 首</span>
        </div>
        <div class="music-batch-actions">
          <button class="music-batch-btn music-batch-btn--primary" @click="handlePlaySelected">
            <AppIcon name="play" class="h-4 w-4" />
            播放选中
          </button>
          <button class="music-batch-btn" @click="handleAddToPlaylist">
            <AppIcon name="addToPlaylist" class="h-4 w-4" />
            加入歌单
          </button>
          <button class="music-batch-btn music-batch-btn--close" @click="exitSelectionMode">
            <AppIcon name="close" class="h-4 w-4" />
          </button>
        </div>
      </div>
    </Transition>

    <header class="music-track-header">
      <span class="music-track-col music-track-col--checkbox"></span>
      <span class="music-track-col music-track-col--num">#</span>
      <span class="music-track-col music-track-col--cover"></span>
      <span class="music-track-col music-track-col--title">标题</span>
      <span class="music-track-col music-track-col--album">专辑</span>
      <span class="music-track-col music-track-col--duration">时长</span>
    </header>

    <article
      v-for="(track, index) in tracks"
      :key="track.hash || index"
      class="music-track-row"
      :class="{
        'music-track-row--playing': isPlaying(track),
        'music-track-row--selected': selectedTracks.has(track.hash)
      }"
      @click="handleRowClick(track, $event)"
      @contextmenu.prevent="handleContextMenu(track, $event)"
    >
      <div class="music-track-col music-track-col--checkbox">
        <button
          class="music-track-checkbox"
          :class="{ 'music-track-checkbox--checked': selectedTracks.has(track.hash) }"
          @click.stop="toggleSelect(track)"
        >
          <AppIcon v-if="selectedTracks.has(track.hash)" name="check" class="h-4 w-4" />
          <AppIcon v-else name="circle" class="h-4 w-4" />
        </button>
      </div>

      <div class="music-track-col music-track-col--num">
        <span v-if="isPlaying(track) && player.playing" class="music-track-playing">
          <i></i><i></i><i></i>
        </span>
        <span v-else class="music-track-num">{{ index + 1 }}</span>
      </div>

      <div class="music-track-col music-track-col--cover">
        <img v-if="track.cover" :src="track.cover" :alt="track.title" loading="lazy" />
        <div v-else class="music-track-cover-placeholder">
          <AppIcon name="playlistMusic" class="h-4 w-4" />
        </div>
      </div>

      <div class="music-track-col music-track-col--title">
        <div class="music-track-title-wrap">
          <span class="music-track-title">{{ track.title || '未知歌曲' }}</span>
          <span v-if="isPlaying(track)" class="music-track-playing-badge">正在播放</span>
        </div>
        <button
          class="music-track-artist"
          :disabled="!track.artist_id"
          @click.stop="$emit('select-artist', track)"
        >
          {{ track.artist || '未知歌手' }}
        </button>
      </div>

      <button
        class="music-track-col music-track-col--album"
        :disabled="!track.album_id"
        @click.stop="$emit('select-album', track)"
      >
        {{ track.album || '未知专辑' }}
      </button>

      <span class="music-track-col music-track-col--duration">
        {{ formatDuration(track.duration) }}
      </span>
    </article>

    <Transition
      enter-active-class="transition-opacity duration-150"
      leave-active-class="transition-opacity duration-100"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <div v-if="contextMenu.visible" class="music-context-menu" :style="contextMenuStyle">
        <button class="music-context-item" @click="handleContextPlay">
          <AppIcon name="play" class="h-4 w-4" />
          立即播放
        </button>
        <button class="music-context-item" @click="handleContextInsertNext">
          <AppIcon name="listEnd" class="h-4 w-4" />
          下一首播放
        </button>
        <div class="music-context-divider"></div>
        <button class="music-context-item" @click="handleContextAddToPlaylist">
          <AppIcon name="addToPlaylist" class="h-4 w-4" />
          添加到歌单
        </button>
        <div class="music-context-divider"></div>
        <button class="music-context-item" @click="handleContextSelectArtist">
          <AppIcon name="user" class="h-4 w-4" />
          查看歌手
        </button>
        <button class="music-context-item" @click="handleContextSelectAlbum">
          <AppIcon name="playlistMusic" class="h-4 w-4" />
          查看专辑
        </button>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import { useMusicPlayerStore } from '@/stores/musicPlayer'
import type { MusicTrack } from '@/api/music'

const props = withDefaults(defineProps<{
  tracks: MusicTrack[]
  showMv?: boolean
  showRelated?: boolean
  showAddToPlaylist?: boolean
}>(), {
  showMv: true,
  showRelated: true,
  showAddToPlaylist: true,
})

const emit = defineEmits<{
  (e: 'select-artist', track: MusicTrack): void
  (e: 'select-album', track: MusicTrack): void
  (e: 'play-mv', track: MusicTrack): void
  (e: 'select-related', track: MusicTrack): void
  (e: 'add-to-playlist', track: MusicTrack): void
  (e: 'add-tracks-to-playlist', tracks: MusicTrack[]): void
}>()

const player = useMusicPlayerStore()

const selectionMode = ref(false)
const selectedTracks = ref<Set<string>>(new Set())

const contextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  track: null as MusicTrack | null,
})

const contextMenuStyle = computed(() => ({
  left: `${contextMenu.x}px`,
  top: `${contextMenu.y}px`,
}))

const isAllSelected = computed(() => {
  if (props.tracks.length === 0) return false
  return props.tracks.every(t => selectedTracks.value.has(t.hash))
})

function isPlaying(track: MusicTrack): boolean {
  return player.currentTrack?.hash === track.hash
}

function handleRowClick(track: MusicTrack, _event: MouseEvent) {
  if (selectionMode.value) {
    toggleSelect(track)
  } else {
    player.playTrack(track)
  }
}

function toggleSelect(track: MusicTrack) {
  if (selectedTracks.value.has(track.hash)) {
    selectedTracks.value.delete(track.hash)
    if (selectedTracks.value.size === 0) {
      selectionMode.value = false
    }
  } else {
    selectedTracks.value.add(track.hash)
    selectionMode.value = true
  }
}

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedTracks.value.clear()
    selectionMode.value = false
  } else {
    props.tracks.forEach(t => selectedTracks.value.add(t.hash))
    selectionMode.value = true
  }
}

function exitSelectionMode() {
  selectedTracks.value.clear()
  selectionMode.value = false
}

function handlePlaySelected() {
  const tracks = props.tracks.filter(t => selectedTracks.value.has(t.hash))
  if (tracks.length > 0) {
    player.playQueue(tracks, 0)
    exitSelectionMode()
  }
}

function handleAddToPlaylist() {
  const tracks = props.tracks.filter(t => selectedTracks.value.has(t.hash))
  if (tracks.length > 0) {
    emit('add-tracks-to-playlist', tracks)
    exitSelectionMode()
  }
}

function handleContextMenu(track: MusicTrack, event: MouseEvent) {
  contextMenu.visible = true
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY
  contextMenu.track = track
}

function closeContextMenu() {
  contextMenu.visible = false
  contextMenu.track = null
}

function handleContextPlay() {
  if (contextMenu.track) {
    player.playTrack(contextMenu.track)
  }
  closeContextMenu()
}

function handleContextInsertNext() {
  if (contextMenu.track) {
    player.insertNext(contextMenu.track)
  }
  closeContextMenu()
}

function handleContextAddToPlaylist() {
  if (contextMenu.track) {
    emit('add-to-playlist', contextMenu.track)
  }
  closeContextMenu()
}

function handleContextSelectArtist() {
  if (contextMenu.track && contextMenu.track.artist_id) {
    emit('select-artist', contextMenu.track)
  }
  closeContextMenu()
}

function handleContextSelectAlbum() {
  if (contextMenu.track && contextMenu.track.album_id) {
    emit('select-album', contextMenu.track)
  }
  closeContextMenu()
}

function handleClickOutside(event: MouseEvent) {
  if (contextMenu.visible) {
    const target = event.target as HTMLElement
    if (!target.closest('.music-context-menu')) {
      closeContextMenu()
    }
  }
}

function formatDuration(seconds: number): string {
  if (!seconds || isNaN(seconds)) return '--:--'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.music-track-list {
  display: flex;
  flex-direction: column;
  padding: 0 1.5rem;
}

.music-track-batch-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.875rem 1rem;
  background: linear-gradient(135deg, hsl(var(--primary) / 0.1) 0%, hsl(var(--primary) / 0.05) 100%);
  border: 1px solid hsl(var(--primary) / 0.2);
  border-radius: 0.75rem;
  margin-bottom: 1rem;
}

.music-batch-left {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.music-batch-count {
  font-size: 0.8125rem;
  color: hsl(var(--muted-foreground));
  font-weight: 500;
}

.music-batch-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.music-batch-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  background: hsl(var(--background));
  border: 1px solid hsl(var(--border) / 0.6);
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.music-batch-btn:hover {
  background: hsl(var(--muted) / 0.5);
  border-color: hsl(var(--border));
}

.music-batch-btn--primary {
  background: linear-gradient(135deg, hsl(var(--primary)) 0%, hsl(var(--primary) / 0.9) 100%);
  color: hsl(var(--primary-foreground));
  border-color: hsl(var(--primary));
  box-shadow: 0 2px 8px hsl(var(--primary) / 0.2);
}

.music-batch-btn--primary:hover {
  box-shadow: 0 4px 12px hsl(var(--primary) / 0.3);
  transform: translateY(-1px);
}

.music-batch-btn--close {
  padding: 0.5rem;
}

.music-track-header {
  display: grid;
  grid-template-columns: 2.5rem 2.5rem 3.25rem 1fr minmax(0, 1fr) 4.5rem;
  gap: 1rem;
  align-items: center;
  padding: 0.625rem 1rem;
  border-bottom: 1px solid hsl(var(--border) / 0.3);
  font-size: 0.6875rem;
  font-weight: 700;
  color: hsl(var(--muted-foreground) / 0.7);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.music-track-row {
  display: grid;
  grid-template-columns: 2.5rem 2.5rem 3.25rem 1fr minmax(0, 1fr) 4.5rem;
  gap: 1rem;
  align-items: center;
  padding: 0.625rem 1rem;
  margin: 0.125rem 0;
  border-radius: 0.625rem;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.music-track-row:hover {
  background: hsl(var(--muted) / 0.35);
}

.music-track-row--playing {
  background: linear-gradient(90deg, hsl(var(--primary) / 0.1) 0%, hsl(var(--primary) / 0.05) 100%);
}

.music-track-row--selected {
  background: hsl(var(--primary) / 0.12);
}

.music-track-col--checkbox {
  display: flex;
  align-items: center;
  justify-content: center;
}

.music-track-checkbox {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.375rem;
  height: 1.375rem;
  border: none;
  background: none;
  color: hsl(var(--muted-foreground) / 0.4);
  cursor: pointer;
  border-radius: 0.375rem;
  transition: all 0.15s ease;
  opacity: 0;
}

.music-track-row:hover .music-track-checkbox,
.music-track-checkbox--checked {
  opacity: 1;
}

.music-track-checkbox:hover {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.1);
}

.music-track-checkbox--checked {
  color: hsl(var(--primary));
}

.music-track-col--num {
  text-align: center;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  font-weight: 500;
}

.music-track-num {
  opacity: 0.5;
}

.music-track-row:hover .music-track-num {
  opacity: 0.25;
}

.music-track-playing {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 2px;
  height: 1.125rem;
}

.music-track-playing i {
  width: 3px;
  height: 100%;
  background: linear-gradient(180deg, hsl(var(--primary)) 0%, hsl(var(--primary) / 0.7) 100%);
  border-radius: 1px;
  animation: track-playing 0.6s ease-in-out infinite;
}

.music-track-playing i:nth-child(2) { animation-delay: 0.15s; }
.music-track-playing i:nth-child(3) { animation-delay: 0.3s; }

@keyframes track-playing {
  0%, 100% { transform: scaleY(0.4); }
  50% { transform: scaleY(1); }
}

.music-track-col--cover {
  width: 3rem;
  height: 3rem;
  border-radius: 0.5rem;
  overflow: hidden;
  background: hsl(var(--muted) / 0.3);
  box-shadow: 0 2px 6px hsl(var(--foreground) / 0.05);
}

.music-track-col--cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.music-track-cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground));
}

.music-track-col--title {
  min-width: 0;
}

.music-track-title-wrap {
  display: flex;
  align-items: center;
  gap: 0.625rem;
}

.music-track-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-track-playing-badge {
  font-size: 0.5625rem;
  padding: 0.1875rem 0.5rem;
  background: linear-gradient(135deg, hsl(var(--primary)) 0%, hsl(var(--primary) / 0.85) 100%);
  color: hsl(var(--primary-foreground));
  border-radius: 0.25rem;
  flex-shrink: 0;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.music-track-artist {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
  transition: color 0.15s ease;
}

.music-track-artist:hover:not(:disabled) {
  color: hsl(var(--primary));
}

.music-track-artist:disabled {
  cursor: default;
}

.music-track-col--album {
  font-size: 0.8125rem;
  color: hsl(var(--muted-foreground));
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
  transition: color 0.15s ease;
}

.music-track-col--album:hover:not(:disabled) {
  color: hsl(var(--primary));
}

.music-track-col--duration {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground) / 0.7);
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-weight: 500;
}

.music-context-menu {
  position: fixed;
  z-index: 200;
  min-width: 180px;
  background: linear-gradient(180deg, hsl(var(--card)) 0%, hsl(var(--card) / 0.95) 100%);
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 0.75rem;
  box-shadow: 0 12px 32px hsl(var(--foreground) / 0.15);
  padding: 0.5rem;
  backdrop-filter: blur(12px);
}

.music-context-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.625rem 0.75rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: hsl(var(--foreground));
  background: none;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s ease;
}

.music-context-item:hover {
  background: hsl(var(--muted) / 0.5);
}

.music-context-divider {
  height: 1px;
  background: hsl(var(--border) / 0.5);
  margin: 0.375rem 0;
}

@media (max-width: 768px) {
  .music-track-list {
    padding: 0 1rem;
  }

  .music-track-header,
  .music-track-row {
    grid-template-columns: 2.5rem 2.5rem 3.25rem 1fr 4.5rem;
  }

  .music-track-col--album {
    display: none;
  }

  .music-track-batch-bar {
    flex-direction: column;
    gap: 0.875rem;
    align-items: stretch;
  }

  .music-batch-left,
  .music-batch-actions {
    justify-content: center;
  }
}
</style>
