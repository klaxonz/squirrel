<template>
  <div class="playlist-panel" :class="{ 'is-open': isOpen }">
    <div class="playlist-panel__header">
      <h3 class="playlist-panel__title">播放列表</h3>
      <button class="playlist-panel__close-btn" @click="handleClose">
        <X />
      </button>
    </div>

    <div class="playlist-panel__tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="playlist-panel__tab"
        :class="{ 'is-active': activeTab === tab.key }"
        @click="switchTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="playlist-panel__content">
      <template v-if="activeTab === 'playlists'">
        <div class="playlist-panel__section">
          <div v-if="loading" class="playlist-panel__loading">
            <div class="loading-spinner"></div>
          </div>
          <div v-else-if="!playlists.length" class="playlist-panel__empty">
            <ListMusic class="playlist-panel__empty-icon" />
            <span>暂无播放列表</span>
          </div>
          <div v-else class="playlist-panel__scroll scrollbar-hide">
            <div class="playlist-panel__list">
              <div
                v-for="playlist in playlists"
                :key="playlist.id"
                class="playlist-card"
                :class="{ 'is-active': activePlaylist?.id === playlist.id }"
                @click="selectPlaylist(playlist.id)"
              >
                <div class="playlist-card__info">
                  <span class="playlist-card__name">{{ playlist.name }}</span>
                  <span class="playlist-card__count">{{ playlist.video_count }} 个视频</span>
                </div>
                <button
                  v-if="!playlist.is_default"
                  class="playlist-card__delete"
                  @click.stop="handleDeletePlaylist(playlist.id)"
                >
                  <Trash2 />
                </button>
              </div>
            </div>
          </div>
          <div class="playlist-panel__actions">
            <button class="playlist-panel__add-btn" @click="showCreateModal = true">
              <Plus />
              <span>新建播放列表</span>
            </button>
          </div>
        </div>
      </template>

      <template v-else-if="activeTab === 'items'">
        <div class="playlist-panel__section">
          <div v-if="!activePlaylist" class="playlist-panel__empty">
            <span>请先选择一个播放列表</span>
          </div>
          <template v-else>
            <div class="playlist-panel__items-header">
              <div class="playlist-panel__items-summary">
                <span class="playlist-panel__items-name">{{ activePlaylist.name }}</span>
                <span class="playlist-panel__items-count">{{ activePlaylistItems.length }} 个视频</span>
              </div>
              <button
                v-if="videoId && !currentVideoAlreadyInActivePlaylist"
                class="playlist-panel__items-add-current"
                @click="addVideo(videoId, activePlaylist.id)"
              >
                添加当前视频
              </button>
            </div>
            <div v-if="loadingItems" class="playlist-panel__loading">
              <div class="loading-spinner"></div>
            </div>
            <div v-else-if="!activePlaylistItems.length" class="playlist-panel__empty">
              <Film class="playlist-panel__empty-icon" />
              <span>播放列表为空</span>
            </div>
            <div v-else class="playlist-panel__items-list playlist-panel__scroll scrollbar-hide">
              <TransitionGroup name="playlist-item">
                <div
                  v-for="(item, index) in activePlaylistItems"
                  :key="item.id"
                  class="playlist-item-card"
                  :class="{
                    'is-playing': currentVideoId && String(item.video_id) === String(currentVideoId),
                    'is-dragging': draggingIndex === index
                  }"
                  draggable="true"
                  @dragstart="handleDragStart($event, index)"
                  @dragover.prevent="handleDragOver($event, index)"
                  @drop="handleDrop($event, index)"
                  @dragend="handleDragEnd"
                >
                  <div class="playlist-item-card__drag-handle">
                    <GripVertical />
                  </div>
                  <div class="playlist-item-card__thumb">
                    <img
                      v-if="item.video?.thumbnail"
                      :src="item.video.thumbnail"
                      referrerpolicy="no-referrer"
                      :alt="item.video.title"
                      @error="(e) => (e.target as HTMLImageElement).style.display = 'none'"
                    >
                    <div v-else class="playlist-item-card__thumb-fallback">
                      <Film />
                    </div>
                  </div>
                  <div class="playlist-item-card__info" @click="handlePlayItem(item)">
                    <span class="playlist-item-card__title">{{ item.video?.title || '未知视频' }}</span>
                    <span class="playlist-item-card__duration">
                      {{ formatDuration(item.video?.duration) }}
                    </span>
                  </div>
                  <button class="playlist-item-card__remove" @click="handleRemoveVideo(item)">
                    <X />
                  </button>
                </div>
              </TransitionGroup>
            </div>
          </template>
        </div>
      </template>
    </div>

    <Teleport to="body">
      <Transition name="modal-fade">
        <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
          <div class="modal-box">
            <h3 class="modal-box__title">新建播放列表</h3>
            <div class="modal-box__field">
              <label class="modal-box__label">名称</label>
              <input
                v-model="newPlaylistName"
                class="modal-box__input"
                placeholder="输入播放列表名称"
                @keyup.enter="handleCreatePlaylist"
              >
            </div>
            <div class="modal-box__field">
              <label class="modal-box__label">描述（可选）</label>
              <input
                v-model="newPlaylistDesc"
                class="modal-box__input"
                placeholder="输入描述"
              >
            </div>
            <div class="modal-box__actions">
              <button class="modal-box__btn modal-box__btn--cancel" @click="showCreateModal = false">取消</button>
              <button class="modal-box__btn modal-box__btn--confirm" @click="handleCreatePlaylist">创建</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import { X, ListMusic, Trash2, Plus, Film, GripVertical } from 'lucide-vue-next'
import usePlaylist from '@/composables/usePlaylist'
import { formatDuration } from '@/utils/dateFormat'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
  videoId: {
    type: [Number, String],
    default: null,
  },
})

const emit = defineEmits(['close', 'play-video'])

const {
  playlists,
  activePlaylist,
  activePlaylistItems,
  loading,
  loadingItems,
  currentVideoId,
  fetchPlaylists,
  loadAndSetPlaylist,
  create,
  addVideo,
  remove: deletePlaylist,
  removeVideo,
  reorder,
} = usePlaylist()

const activeTab = ref('playlists')
const showCreateModal = ref(false)
const newPlaylistName = ref('')
const newPlaylistDesc = ref('')
const draggingIndex = ref(-1)

const tabs: { key: string; label: string }[] = [
  { key: 'playlists', label: '列表' },
  { key: 'items', label: '视频' },
]

const currentVideoAlreadyInActivePlaylist = computed(() => {
  if (!props.videoId || !activePlaylist.value) return false
  return activePlaylistItems.value.some((item) => String(item.video_id) === String(props.videoId))
})

const switchTab = (key: string) => {
  activeTab.value = key
}

const openPlaylist = async (playlistId: number | string) => {
  activeTab.value = 'items'
  await loadAndSetPlaylist(playlistId)
}

const selectPlaylist = async (playlistId: number | string) => {
  if (props.videoId) {
    await addVideo(props.videoId, playlistId)
  }
  await openPlaylist(playlistId)
}

const handleClose = () => {
  emit('close')
}

const handleCreatePlaylist = async () => {
  if (!newPlaylistName.value.trim()) return
  const result = await create(newPlaylistName.value.trim(), newPlaylistDesc.value.trim() || null)
  if (result) {
    newPlaylistName.value = ''
    newPlaylistDesc.value = ''
    showCreateModal.value = false
    if (props.videoId) {
      await addVideo(props.videoId, result.id)
    }
    await openPlaylist(result.id)
  }
}

const handleDeletePlaylist = async (playlistId: number | string) => {
  await deletePlaylist(playlistId)
}

const handlePlayItem = (item: { video?: { id: number | string } | null }) => {
  if (item.video) {
    emit('play-video', item.video)
  }
}

const handleRemoveVideo = async (item: { video_id: number | string }) => {
  if (!activePlaylist.value) return
  await removeVideo(activePlaylist.value.id, item.video_id)
}

const handleDragStart = (e: DragEvent, index: number) => {
  draggingIndex.value = index
  e.dataTransfer!.effectAllowed = 'move'
}

const handleDragOver = (e: DragEvent, index: number) => {
  if (draggingIndex.value === index) return
}

const handleDrop = async (e: DragEvent, targetIndex: number) => {
  e.preventDefault()
  if (draggingIndex.value === targetIndex) return
  if (!activePlaylist.value) return

  const previousItems = [...activePlaylistItems.value]
  const items = [...activePlaylistItems.value]
  const [moved] = items.splice(draggingIndex.value, 1)
  items.splice(targetIndex, 0, moved)

  activePlaylistItems.value = items.map((item, index) => ({
    ...item,
    position: index + 1,
  }))
  draggingIndex.value = -1

  const ok = await reorder(activePlaylist.value.id, moved.video_id, targetIndex + 1)
  if (!ok) {
    activePlaylistItems.value = previousItems
  }
}

const handleDragEnd = () => {
  draggingIndex.value = -1
}

onMounted(() => {
  fetchPlaylists()
})

watch(() => props.isOpen, async (open) => {
  if (!open) return
  await fetchPlaylists()
  if (activePlaylist.value) {
    await loadAndSetPlaylist(activePlaylist.value.id)
  }
})
</script>

<style scoped>
.playlist-panel {
  position: fixed;
  right: 0;
  top: 0;
  bottom: 0;
  width: 360px;
  max-width: 100vw;
  background: hsl(var(--background));
  border-left: 1px solid hsl(var(--border) / 0.5);
  transform: translateX(100%);
  transition: transform var(--duration-normal) var(--ease-default);
  z-index: 100;
  display: flex;
  flex-direction: column;
}

.playlist-panel.is-open {
  transform: translateX(0);
}

.playlist-panel__header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  border-bottom: 1px solid hsl(var(--border) / 0.5);
}

.playlist-panel__title {
  font-size: 1rem;
  font-weight: 700;
  color: hsl(var(--foreground));
  margin: 0;
}

.playlist-panel__close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  border-radius: 4px;
  transition: all var(--duration-normal) var(--ease-default);
}

.playlist-panel__close-btn:hover {
  background: hsl(var(--accent) / 0.1);
  color: hsl(var(--foreground));
}

.playlist-panel__tabs {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  background: hsl(var(--background));
  border-bottom: 1px solid hsl(var(--border) / 0.5);
  flex-shrink: 0;
}

.playlist-panel__tab {
  flex: 1;
  padding: 0.625rem;
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all var(--duration-normal) var(--ease-default);
}

.playlist-panel__tab:hover {
  color: hsl(var(--foreground));
}

.playlist-panel__tab.is-active {
  color: hsl(var(--primary));
  border-bottom-color: hsl(var(--primary));
}

.playlist-panel__content {
  flex: 1;
  min-height: 0;
  padding: 0.75rem;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.playlist-panel__section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.playlist-panel__scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.playlist-panel__scroll::-webkit-scrollbar {
  display: none;
}

.playlist-panel__loading,
.playlist-panel__empty {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 2rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.8rem;
}

.playlist-panel__empty-icon {
  width: 2rem;
  height: 2rem;
  opacity: 0.5;
}

.loading-spinner {
  width: 1.5rem;
  height: 1.5rem;
  border: 2px solid hsl(var(--border));
  border-top-color: hsl(var(--primary));
  border-radius: 50%;
  animation: spin var(--duration-slow) linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.playlist-panel__list {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding-bottom: 0.5rem;
}

.playlist-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.625rem 0.75rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-default);
  border: 1px solid transparent;
}

.playlist-card:hover {
  background: hsl(var(--accent) / 0.08);
}

.playlist-card.is-active {
  background: hsl(var(--primary) / 0.1);
  border-color: hsl(var(--primary) / 0.3);
}

.playlist-card__info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
}

.playlist-card__name {
  font-size: 0.85rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.playlist-card__count {
  font-size: 0.7rem;
  color: hsl(var(--muted-foreground));
}

.playlist-card__delete {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  border-radius: 4px;
  opacity: 0;
  transition: all var(--duration-normal) var(--ease-default);
  flex-shrink: 0;
}

.playlist-card:hover .playlist-card__delete {
  opacity: 1;
}

.playlist-card__delete:hover {
  background: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}

.playlist-panel__actions {
  flex-shrink: 0;
  padding: 0.75rem 0;
  border-top: 1px solid hsl(var(--border) / 0.3);
  margin-top: 0.5rem;
  background: linear-gradient(180deg, hsl(var(--background) / 0.65), hsl(var(--background)));
  backdrop-filter: blur(10px);
}

.playlist-panel__add-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  width: 100%;
  padding: 0.5rem;
  border: 1px dashed hsl(var(--border));
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  border-radius: 6px;
  transition: all var(--duration-normal) var(--ease-default);
}

.playlist-panel__add-btn:hover {
  border-color: hsl(var(--primary) / 0.5);
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.05);
}

.playlist-panel__items-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.5rem 0;
  margin-bottom: 0.5rem;
  border-bottom: 1px solid hsl(var(--border) / 0.3);
}

.playlist-panel__items-summary {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
}

.playlist-panel__items-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.playlist-panel__items-count {
  font-size: 0.7rem;
  color: hsl(var(--muted-foreground));
}

.playlist-panel__items-add-current {
  flex-shrink: 0;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  border: 1px solid hsl(var(--primary) / 0.35);
  background: hsl(var(--primary) / 0.08);
  color: hsl(var(--primary));
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-default);
}

.playlist-panel__items-add-current:hover {
  background: hsl(var(--primary) / 0.15);
  border-color: hsl(var(--primary) / 0.5);
}

.playlist-panel__items-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding-bottom: 0.5rem;
}

.playlist-item-card {
  display: grid;
  grid-template-columns: 1.5rem 5rem 1fr 1.5rem;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.5rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-default);
  border: 1px solid transparent;
}

.playlist-item-card:hover {
  background: hsl(var(--accent) / 0.08);
}

.playlist-item-card.is-playing {
  background: hsl(var(--primary) / 0.1);
  border-color: hsl(var(--primary) / 0.3);
}

.playlist-item-card.is-dragging {
  opacity: 0.5;
  background: hsl(var(--accent) / 0.15);
}

.playlist-item-card__drag-handle {
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground));
  cursor: grab;
  opacity: 0;
  transition: opacity var(--duration-normal) var(--ease-default);
}

.playlist-item-card:hover .playlist-item-card__drag-handle {
  opacity: 1;
}

.playlist-item-card__thumb {
  width: 5rem;
  aspect-ratio: 16 / 9;
  border-radius: 4px;
  overflow: hidden;
  background: hsl(var(--muted));
  flex-shrink: 0;
}

.playlist-item-card__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.playlist-item-card__thumb-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground));
}

.playlist-item-card__info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
}

.playlist-item-card__title {
  font-size: 0.78rem;
  font-weight: 500;
  color: hsl(var(--foreground));
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.playlist-item-card__duration {
  font-size: 0.65rem;
  color: hsl(var(--muted-foreground));
  font-family: 'JetBrains Mono', monospace;
}

.playlist-item-card__remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  border-radius: 4px;
  opacity: 0;
  transition: all var(--duration-normal) var(--ease-default);
  flex-shrink: 0;
}

.playlist-item-card:hover .playlist-item-card__remove {
  opacity: 1;
}

.playlist-item-card__remove:hover {
  background: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}

.playlist-item-enter-active,
.playlist-item-leave-active {
  transition: all var(--duration-slow) var(--ease-out);
}

.playlist-item-enter-from,
.playlist-item-leave-to {
  opacity: 0;
  transform: translateX(10px);
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 1rem;
}

.modal-box {
  background: hsl(var(--background));
  border: 1px solid hsl(var(--border));
  border-radius: 8px;
  padding: 1.5rem;
  width: 100%;
  max-width: 360px;
}

.modal-box__title {
  font-size: 1rem;
  font-weight: 700;
  color: hsl(var(--foreground));
  margin: 0 0 1rem;
}

.modal-box__field {
  margin-bottom: 1rem;
}

.modal-box__label {
  display: block;
  font-size: 0.75rem;
  font-weight: 500;
  color: hsl(var(--muted-foreground));
  margin-bottom: 0.375rem;
}

.modal-box__input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid hsl(var(--border));
  border-radius: 6px;
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  font-size: 0.85rem;
  outline: none;
  transition: border-color var(--duration-normal) var(--ease-default);
  box-sizing: border-box;
}

.modal-box__input:focus {
  border-color: hsl(var(--primary));
}

.modal-box__actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
  margin-top: 1.25rem;
}

.modal-box__btn {
  padding: 0.4rem 1rem;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-default);
  border: 1px solid transparent;
}

.modal-box__btn--cancel {
  background: transparent;
  color: hsl(var(--muted-foreground));
  border-color: hsl(var(--border));
}

.modal-box__btn--cancel:hover {
  background: hsl(var(--accent) / 0.1);
}

.modal-box__btn--confirm {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
}

.modal-box__btn--confirm:hover {
  background: hsl(var(--primary) / 0.9);
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity var(--duration-normal) var(--ease-default);
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .playlist-panel {
    width: 100vw;
  }
}
</style>
