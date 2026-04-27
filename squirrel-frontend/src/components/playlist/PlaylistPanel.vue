<template>
  <div class="playlist-panel" :class="{ 'is-open': isOpen }">
    <div class="playlist-panel__header">
      <div class="header-content">
        <h3 class="playlist-panel__title">播放列表</h3>
        <span v-if="playlists.length" class="playlist-panel__count">{{ playlists.length }}</span>
      </div>
      <button class="playlist-panel__close-btn" @click="handleClose">
        <AppIcon name="close" class="h-5 w-5" />
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

    <div class="playlist-panel__content scrollbar-hide">
      <Transition name="fade-slide" mode="out-in">
        <!-- Playlists List -->
        <div v-if="activeTab === 'playlists'" key="playlists" class="playlist-panel__section">
          <div v-if="loading" class="playlist-panel__state">
            <div class="loading-spinner"></div>
          </div>
          <div v-else-if="!playlists.length" class="playlist-panel__state">
            <AppIcon name="playlistMusic" class="state-icon" />
            <span>暂无播放列表</span>
          </div>
          <div v-else class="playlist-panel__list">
            <div
              v-for="playlist in playlists"
              :key="playlist.id"
              class="playlist-card"
              :class="{ 'is-active': activePlaylist?.id === playlist.id }"
              @click="selectPlaylist(playlist.id)"
            >
              <div class="playlist-card__cover">
                <AppIcon v-if="!playlist.video_count" name="playlistMusic" class="h-4 w-4" />
                <AppIcon v-else name="play" class="h-4 w-4 fill-current" />
              </div>
              <div class="playlist-card__info">
                <span class="playlist-card__name">{{ playlist.name }}</span>
                <span class="playlist-card__meta">{{ playlist.video_count }} 个视频</span>
              </div>
              <button
                v-if="!playlist.is_default"
                class="playlist-card__delete"
                @click.stop="handleDeletePlaylist(playlist.id)"
              >
                <AppIcon name="trash" class="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
          <div class="playlist-panel__footer">
            <button class="playlist-panel__add-btn" @click="showCreateModal = true">
              <AppIcon name="plus" class="h-4 w-4" />
              <span>新建播放列表</span>
            </button>
          </div>
        </div>

        <!-- Playlist Items -->
        <div v-else-if="activeTab === 'items'" key="items" class="playlist-panel__section">
          <div v-if="!activePlaylist" class="playlist-panel__state">
            <AppIcon name="panelOpen" class="state-icon" />
            <span>请先选择一个列表</span>
          </div>
          <template v-else>
            <div class="playlist-panel__items-header">
              <div class="items-header__info">
                <h4 class="items-header__name">{{ activePlaylist.name }}</h4>
                <span class="items-header__meta">{{ activePlaylistItems.length }} 个视频</span>
              </div>
              <button
                v-if="videoId && !currentVideoAlreadyInActivePlaylist"
                class="playlist-panel__add-current"
                @click="addVideo(videoId, activePlaylist.id)"
              >
                添加当前视频
              </button>
            </div>

            <div v-if="loadingItems" class="playlist-panel__state">
              <div class="loading-spinner"></div>
            </div>
            <div v-else-if="!activePlaylistItems.length" class="playlist-panel__state">
              <AppIcon name="film" class="state-icon" />
              <span>列表还是空的</span>
            </div>
            <div v-else class="playlist-panel__items-list">
              <TransitionGroup name="list-stagger">
                <div
                  v-for="(item, index) in activePlaylistItems"
                  :key="item.id"
                  class="item-row"
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
                  <div class="item-row__drag">
                    <AppIcon name="gripVertical" class="h-3.5 w-3.5" />
                  </div>
                  <div class="item-row__thumb">
                    <img
                      v-if="item.video?.thumbnail"
                      :src="item.video.thumbnail"
                      referrerpolicy="no-referrer"
                      @error="(e) => (e.target as HTMLImageElement).style.display = 'none'"
                    >
                    <div v-else class="thumb-fallback"><AppIcon name="film" class="h-4 w-4" /></div>
                  </div>
                  <div class="item-row__info" @click="handlePlayItem(item)">
                    <span class="item-row__title">{{ item.video?.title || '未知视频' }}</span>
                    <span class="item-row__duration">{{ formatDuration(item.video?.duration) }}</span>
                  </div>
                  <button class="item-row__remove" @click="handleRemoveVideo(item)">
                    <AppIcon name="close" class="h-3.5 w-3.5" />
                  </button>
                </div>
              </TransitionGroup>
            </div>
          </template>
        </div>
      </Transition>
    </div>

    <!-- Create Modal -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showCreateModal" class="playlist-modal-overlay" @click.self="showCreateModal = false">
          <div class="playlist-modal">
            <h3 class="playlist-modal__title">新建播放列表</h3>
            <div class="playlist-modal__form">
              <div class="form-field">
                <label>名称</label>
                <input
                  v-model="newPlaylistName"
                  placeholder="输入名称..."
                  @keyup.enter="handleCreatePlaylist"
                >
              </div>
              <div class="form-field">
                <label>描述（可选）</label>
                <input v-model="newPlaylistDesc" placeholder="输入描述...">
              </div>
            </div>
            <div class="playlist-modal__actions">
              <button class="btn-cancel" @click="showCreateModal = false">取消</button>
              <button class="btn-confirm" :disabled="!newPlaylistName.trim()" @click="handleCreatePlaylist">创建</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
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
  width: 400px;
  max-width: 100vw;
  background: hsl(var(--background));
  border-left: 1px solid hsl(var(--border) / 0.4);
  transform: translateX(100%);
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 100;
  display: flex;
  flex-direction: column;
  box-shadow: -8px 0 32px rgba(0, 0, 0, 0.1);
}

.playlist-panel.is-open {
  transform: translateX(0);
}

.playlist-panel__header {
  padding: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid hsl(var(--border) / 0.4);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.playlist-panel__title {
  font-size: 1.125rem;
  font-weight: 700;
  margin: 0;
}

.playlist-panel__count {
  font-size: 0.75rem;
  font-weight: 600;
  background: hsl(var(--secondary));
  padding: 0.125rem 0.5rem;
  border-radius: 99px;
  color: hsl(var(--muted-foreground));
}

.playlist-panel__close-btn {
  color: hsl(var(--muted-foreground));
  transition: color 0.2s;
  padding: 0.5rem;
  margin: -0.5rem;
  border-radius: 50%;
}

.playlist-panel__close-btn:hover {
  background: hsl(var(--accent) / 0.1);
  color: hsl(var(--foreground));
}

.playlist-panel__tabs {
  display: flex;
  padding: 0.5rem 1.5rem 0;
  gap: 1.5rem;
  border-bottom: 1px solid hsl(var(--border) / 0.4);
}

.playlist-panel__tab {
  padding: 0.75rem 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
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
  overflow-y: auto;
  padding: 1rem 1.5rem;
}

.playlist-panel__section {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.playlist-panel__state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
  padding: 4rem 0;
}

.state-icon {
  width: 32px;
  height: 32px;
  opacity: 0.2;
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid hsl(var(--border));
  border-top-color: hsl(var(--primary));
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.playlist-panel__list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.playlist-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
}

.playlist-card:hover {
  background: hsl(var(--accent) / 0.08);
}

.playlist-card.is-active {
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
}

.playlist-card__cover {
  width: 40px;
  height: 40px;
  border-radius: 6px;
  background: hsl(var(--secondary));
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground));
}

.playlist-card.is-active .playlist-card__cover {
  background: hsl(var(--primary) / 0.2);
  color: hsl(var(--primary));
}

.playlist-card__info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.playlist-card__name {
  font-size: 0.875rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.playlist-card__meta {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.playlist-card__delete {
  padding: 0.5rem;
  border-radius: 0.25rem;
  color: hsl(var(--muted-foreground));
  opacity: 0;
  transition: all 0.2s;
}

.playlist-card:hover .playlist-card__delete {
  opacity: 1;
}

.playlist-card__delete:hover {
  background: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}

.playlist-panel__footer {
  margin-top: auto;
  padding-top: 1.5rem;
}

.playlist-panel__add-btn {
  width: 100%;
  padding: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border: 1px dashed hsl(var(--border));
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
  transition: all 0.2s;
}

.playlist-panel__add-btn:hover {
  border-color: hsl(var(--primary));
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.05);
}

/* Items List */
.playlist-panel__items-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.items-header__name {
  font-size: 1rem;
  font-weight: 700;
  margin: 0;
}

.items-header__meta {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
}

.playlist-panel__add-current {
  font-size: 0.75rem;
  font-weight: 700;
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.1);
  padding: 0.375rem 0.75rem;
  border-radius: 99px;
  transition: all 0.2s;
}

.playlist-panel__add-current:hover {
  background: hsl(var(--primary) / 0.2);
}

.playlist-panel__items-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.item-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  border-radius: 0.5rem;
  transition: all 0.2s;
  cursor: pointer;
}

.item-row:hover {
  background: hsl(var(--accent) / 0.08);
}

.item-row.is-playing {
  background: hsl(var(--primary) / 0.05);
  color: hsl(var(--primary));
}

.item-row__drag {
  color: hsl(var(--muted-foreground));
  opacity: 0;
  cursor: grab;
}

.item-row:hover .item-row__drag {
  opacity: 1;
}

.item-row__thumb {
  width: 80px;
  aspect-ratio: 16 / 9;
  border-radius: 4px;
  overflow: hidden;
  background: hsl(var(--secondary));
  flex-shrink: 0;
}

.item-row__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.item-row__info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.item-row__title {
  font-size: 0.8125rem;
  font-weight: 600;
  line-height: 1.2;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.item-row__duration {
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground));
}

.item-row__remove {
  padding: 0.5rem;
  color: hsl(var(--muted-foreground));
  opacity: 0;
}

.item-row:hover .item-row__remove {
  opacity: 1;
}

.item-row__remove:hover {
  color: hsl(var(--destructive));
}

/* Modal */
.playlist-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.playlist-modal {
  background: hsl(var(--background));
  border: 1px solid hsl(var(--border) / 0.4);
  border-radius: 1rem;
  padding: 2rem;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
}

.playlist-modal__title {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0 0 1.5rem;
}

.playlist-modal__form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-field label {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  color: hsl(var(--muted-foreground));
}

.form-field input {
  background: hsl(var(--secondary) / 0.5);
  border: 1px solid transparent;
  padding: 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.form-field input:focus {
  background: hsl(var(--background));
  border-color: hsl(var(--primary));
  outline: none;
}

.playlist-modal__actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  margin-top: 2rem;
}

.playlist-modal__actions button {
  padding: 0.625rem 1.25rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-cancel {
  background: transparent;
  color: hsl(var(--muted-foreground));
}

.btn-cancel:hover {
  background: hsl(var(--accent) / 0.1);
}

.btn-confirm {
  background: hsl(var(--primary));
  color: white;
}

.btn-confirm:hover {
  background: hsl(var(--primary) / 0.9);
}

.btn-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Transitions */
.fade-slide-enter-active, .fade-slide-leave-active { transition: all 0.3s ease; }
.fade-slide-enter-from { opacity: 0; transform: translateY(10px); }
.fade-slide-leave-to { opacity: 0; transform: translateY(-10px); }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@media (max-width: 640px) {
  .playlist-panel { width: 100vw; }
}
</style>

@media (max-width: 640px) {
  .playlist-panel {
    width: 100vw;
  }
}
</style>
