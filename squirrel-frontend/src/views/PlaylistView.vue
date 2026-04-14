<template>
  <div class="playlist-view terminal-viewport scrollbar-hide">
    <div class="playlist-view__container">
      <div class="playlist-view__header">
        <h1 class="playlist-view__title">播放列表</h1>
        <button class="playlist-view__create-btn" @click="showCreateModal = true">
          <Icon icon="lucide:plus" />
          <span>新建播放列表</span>
        </button>
      </div>

      <div class="playlist-view__content">
        <div v-if="loading" class="playlist-view__loading">
          <div class="loading-spinner"></div>
          <span>加载中...</span>
        </div>

        <div v-else-if="!playlists.length" class="playlist-view__empty">
          <Icon icon="lucide:list-music" class="playlist-view__empty-icon" />
          <h2 class="playlist-view__empty-title">暂无播放列表</h2>
          <p class="playlist-view__empty-desc">创建一个播放列表来组织你喜欢的视频</p>
          <button class="playlist-view__create-btn playlist-view__create-btn--primary" @click="showCreateModal = true">
            <Icon icon="lucide:plus" />
            <span>新建播放列表</span>
          </button>
        </div>

        <div v-else class="playlist-view__grid">
          <div
            v-for="playlist in playlists"
            :key="playlist.id"
            class="playlist-card"
            @click="openPlaylist(playlist.id)"
          >
            <div class="playlist-card__cover">
              <Icon icon="lucide:list-music" class="playlist-card__cover-icon" />
            </div>
            <div class="playlist-card__body">
              <div class="playlist-card__badge" v-if="playlist.is_default">默认</div>
              <h3 class="playlist-card__name">{{ playlist.name }}</h3>
              <p class="playlist-card__desc" v-if="playlist.description">{{ playlist.description }}</p>
              <span class="playlist-card__count">{{ playlist.video_count }} 个视频</span>
            </div>
            <button
              v-if="!playlist.is_default"
              class="playlist-card__delete"
              @click.stop="handleDelete(playlist.id)"
            >
              <Icon icon="lucide:trash-2" />
            </button>
          </div>
        </div>
      </div>

      <!-- 播放列表详情抽屉 -->
      <div class="playlist-drawer" :class="{ 'is-open': isDrawerOpen }">
        <div v-if="activePlaylist" class="playlist-drawer__content">
          <div class="playlist-drawer__header">
            <button class="playlist-drawer__back" @click="closePlaylist">
              <Icon icon="lucide:arrow-left" />
            </button>
            <div class="playlist-drawer__info">
              <h2 class="playlist-drawer__title">{{ activePlaylist.name }}</h2>
              <span class="playlist-drawer__count">{{ activePlaylistItems.length }} 个视频</span>
            </div>
            <button
              v-if="!activePlaylist.is_default"
              class="playlist-drawer__edit"
              @click="startEditing"
            >
              <Icon icon="lucide:pencil" />
            </button>
          </div>

          <div v-if="loadingItems" class="playlist-drawer__loading">
            <div class="loading-spinner"></div>
          </div>
          <div v-else-if="!activePlaylistItems.length" class="playlist-drawer__empty">
            <Icon icon="lucide:film" class="playlist-drawer__empty-icon" />
            <span>播放列表为空</span>
          </div>
          <div v-else class="playlist-drawer__list">
            <TransitionGroup name="item-list">
              <div
                v-for="(item, index) in activePlaylistItems"
                :key="item.id"
                class="drawer-item"
                :class="{ 'is-playing': currentVideoId && String(item.video_id) === String(currentVideoId) }"
              >
                <span class="drawer-item__index">{{ index + 1 }}</span>
                <div class="drawer-item__thumb" @click="playVideo(item)">
                  <img
                    v-if="item.video?.thumbnail"
                    :src="item.video.thumbnail"
                    referrerpolicy="no-referrer"
                    :alt="item.video.title"
                    @error="(e) => (e.target as HTMLImageElement).style.display = 'none'"
                  >
                  <div v-else class="drawer-item__thumb-fallback">
                    <Icon icon="lucide:film" />
                  </div>
                </div>
                <div class="drawer-item__info" @click="playVideo(item)">
                  <span class="drawer-item__title">{{ item.video?.title || '未知视频' }}</span>
                  <span class="drawer-item__meta">
                    {{ formatDuration(item.video?.duration) }}
                  </span>
                </div>
                <button class="drawer-item__remove" @click="handleRemoveVideo(item)">
                  <Icon icon="lucide:x" />
                </button>
              </div>
            </TransitionGroup>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑弹窗 -->
    <Teleport to="body">
      <Transition name="modal-fade">
        <div v-if="showCreateModal || editingPlaylist" class="modal-overlay" @click.self="closeModal">
          <div class="modal-box">
            <h3 class="modal-box__title">
              {{ editingPlaylist ? '编辑播放列表' : '新建播放列表' }}
            </h3>
            <div class="modal-box__field">
              <label class="modal-box__label">名称</label>
              <input
                v-model="formName"
                class="modal-box__input"
                placeholder="输入播放列表名称"
                @keyup.enter="handleSave"
              >
            </div>
            <div class="modal-box__field">
              <label class="modal-box__label">描述（可选）</label>
              <input
                v-model="formDesc"
                class="modal-box__input"
                placeholder="输入描述"
              >
            </div>
            <div class="modal-box__actions">
              <button class="modal-box__btn modal-box__btn--cancel" @click="closeModal">取消</button>
              <button class="modal-box__btn modal-box__btn--confirm" @click="handleSave">保存</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import usePlaylist from '@/composables/usePlaylist'
import { formatDuration } from '@/utils/dateFormat'
import type { Playlist } from '@/types/playlist'

const router = useRouter()

const {
  playlists,
  loading,
  loadingItems,
  activePlaylist,
  activePlaylistItems,
  currentVideoId,
  setCurrentVideo,
  fetchPlaylists,
  loadAndSetPlaylist,
  create,
  update,
  remove,
  removeVideo,
} = usePlaylist()

const showCreateModal = ref(false)
const editingPlaylist = ref<Playlist | null>(null)
const formName = ref('')
const formDesc = ref('')

const isDrawerOpen = ref(false)

const closeModal = () => {
  showCreateModal.value = false
  editingPlaylist.value = null
  formName.value = ''
  formDesc.value = ''
}

const startEditing = () => {
  if (!activePlaylist.value) return
  editingPlaylist.value = activePlaylist.value
  formName.value = activePlaylist.value.name
  formDesc.value = activePlaylist.value.description || ''
}

const handleSave = async () => {
  if (!formName.value.trim()) return

  if (editingPlaylist.value) {
    await update(editingPlaylist.value.id, formName.value.trim(), formDesc.value.trim() || null)
  } else {
    const created = await create(formName.value.trim(), formDesc.value.trim() || null)
    if (created) {
      await openPlaylist(created.id)
    }
  }
  closeModal()
}

const handleDelete = async (playlistId: number | string) => {
  await remove(playlistId)
}

const openPlaylist = async (playlistId: number | string) => {
  await loadAndSetPlaylist(playlistId)
  isDrawerOpen.value = true
}

const closePlaylist = () => {
  isDrawerOpen.value = false
}

const playVideo = (item: { video?: { id: number | string } | null }) => {
  if (item.video?.id) {
    setCurrentVideo(item.video.id)
    router.push(`/video/${item.video.id}`)
  }
}

const handleRemoveVideo = async (item: { video_id: number | string }) => {
  if (!activePlaylist.value) return
  await removeVideo(activePlaylist.value.id, item.video_id)
}

onMounted(() => {
  fetchPlaylists()
})
</script>

<style scoped>
.playlist-view {
  background-color: hsl(var(--background));
  background-image:
    linear-gradient(hsl(var(--foreground) / 0.02) 1px, transparent 1px),
    linear-gradient(90deg, hsl(var(--foreground) / 0.02) 1px, transparent 1px);
  background-size: 40px 40px;
  min-height: 100vh;
}

.playlist-view__container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.playlist-view__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2rem;
}

.playlist-view__title {
  font-size: 1.5rem;
  font-weight: 700;
  color: hsl(var(--foreground));
  margin: 0;
}

.playlist-view__create-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  background: hsl(var(--accent) / 0.1);
  color: hsl(var(--foreground));
  font-size: 0.85rem;
  font-weight: 500;
  border: 1px solid hsl(var(--border));
  cursor: pointer;
  transition: all 0.2s;
}

.playlist-view__create-btn:hover {
  background: hsl(var(--accent) / 0.2);
  border-color: hsl(var(--primary) / 0.5);
}

.playlist-view__create-btn--primary {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  border-color: transparent;
}

.playlist-view__create-btn--primary:hover {
  background: hsl(var(--primary) / 0.9);
}

.playlist-view__loading,
.playlist-view__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 4rem 2rem;
  text-align: center;
}

.playlist-view__empty-icon {
  width: 3rem;
  height: 3rem;
  color: hsl(var(--muted-foreground));
  opacity: 0.4;
}

.playlist-view__empty-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  margin: 0;
}

.playlist-view__empty-desc {
  font-size: 0.85rem;
  color: hsl(var(--muted-foreground));
  margin: 0;
}

.loading-spinner {
  width: 2rem;
  height: 2rem;
  border: 2px solid hsl(var(--border));
  border-top-color: hsl(var(--primary));
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.playlist-view__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.playlist-card {
  position: relative;
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.playlist-card:hover {
  border-color: hsl(var(--primary) / 0.5);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px hsl(var(--foreground) / 0.08);
}

.playlist-card__cover {
  width: 4rem;
  height: 4rem;
  background: hsl(var(--accent) / 0.1);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.playlist-card__cover-icon {
  width: 1.5rem;
  height: 1.5rem;
  color: hsl(var(--primary));
}

.playlist-card__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.playlist-card__badge {
  display: inline-block;
  width: fit-content;
  padding: 0.1rem 0.4rem;
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
  font-size: 0.65rem;
  font-weight: 600;
  border-radius: 4px;
}

.playlist-card__name {
  font-size: 0.9rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.playlist-card__desc {
  font-size: 0.75rem;
  color: hsl(var(--muted-foreground));
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.playlist-card__count {
  font-size: 0.7rem;
  color: hsl(var(--muted-foreground));
  margin-top: auto;
}

.playlist-card__delete {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  width: 1.75rem;
  height: 1.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  border-radius: 4px;
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

/* Drawer */
.playlist-drawer {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: 480px;
  max-width: 100vw;
  background: hsl(var(--background));
  border-right: 1px solid hsl(var(--border) / 0.5);
  transform: translateX(-100%);
  transition: transform 0.3s cubic-bezier(0.2, 0, 0.1, 1);
  z-index: 90;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.playlist-drawer.is-open {
  transform: translateX(0);
}

.playlist-drawer__header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-bottom: 1px solid hsl(var(--border) / 0.5);
}

.playlist-drawer__back {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  background: transparent;
  border: none;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.playlist-drawer__back:hover {
  background: hsl(var(--accent) / 0.1);
  color: hsl(var(--foreground));
}

.playlist-drawer__info {
  flex: 1;
  min-width: 0;
}

.playlist-drawer__title {
  font-size: 1rem;
  font-weight: 700;
  color: hsl(var(--foreground));
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.playlist-drawer__count {
  font-size: 0.7rem;
  color: hsl(var(--muted-foreground));
}

.playlist-drawer__edit {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  background: transparent;
  border: none;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.playlist-drawer__edit:hover {
  background: hsl(var(--accent) / 0.1);
  color: hsl(var(--foreground));
}

.playlist-drawer__loading,
.playlist-drawer__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 2rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.85rem;
}

.playlist-drawer__empty-icon {
  width: 2rem;
  height: 2rem;
  opacity: 0.4;
}

.playlist-drawer__list {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
}

.drawer-item {
  display: grid;
  grid-template-columns: 2rem 5rem 1fr 2rem;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.drawer-item:hover {
  background: hsl(var(--accent) / 0.08);
}

.drawer-item.is-playing {
  background: hsl(var(--primary) / 0.1);
  border-color: hsl(var(--primary) / 0.3);
}

.drawer-item__index {
  font-size: 0.7rem;
  color: hsl(var(--muted-foreground));
  font-family: 'JetBrains Mono', monospace;
  text-align: center;
}

.drawer-item__thumb {
  width: 5rem;
  aspect-ratio: 16 / 9;
  border-radius: 4px;
  overflow: hidden;
  background: hsl(var(--muted));
  cursor: pointer;
}

.drawer-item__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.drawer-item__thumb-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground));
}

.drawer-item__info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
  cursor: pointer;
}

.drawer-item__title {
  font-size: 0.82rem;
  font-weight: 500;
  color: hsl(var(--foreground));
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.drawer-item__meta {
  font-size: 0.65rem;
  color: hsl(var(--muted-foreground));
  font-family: 'JetBrains Mono', monospace;
}

.drawer-item__remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  background: transparent;
  border: none;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  border-radius: 4px;
  opacity: 0;
  transition: all 0.2s;
}

.drawer-item:hover .drawer-item__remove {
  opacity: 1;
}

.drawer-item__remove:hover {
  background: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}

.item-list-enter-active,
.item-list-leave-active {
  transition: all 0.3s ease;
}

.item-list-enter-from,
.item-list-leave-to {
  opacity: 0;
  transform: translateX(-10px);
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
  max-width: 400px;
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
  transition: border-color 0.2s;
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
  transition: all 0.2s;
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
  transition: opacity 0.2s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .playlist-view__container {
    padding: 1rem;
  }

  .playlist-drawer {
    width: 100vw;
  }
}
</style>
