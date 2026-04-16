<template>
  <div class="playlist-page flex h-full flex-col bg-background text-foreground">
    <div class="playlist-toolbar-shell">
      <div class="toolbar-container">
        <PageHeader
          class="playlist-page__header"
          title="播放列表"
        >
          <template #meta>
            <span class="playlist-page__meta-inline">{{ playlists.length }} 个列表</span>
            <span v-if="playlists.length" class="playlist-page__meta-inline">{{ totalVideoCount }} 个视频</span>
          </template>
        </PageHeader>
      </div>
    </div>

    <div class="playlist-content scrollbar-hide">
      <div class="content-container playlist-content__inner">
        <div v-if="loading && !playlists.length" class="playlist-state playlist-state--loading">
          <div class="playlist-state__spinner" aria-hidden="true"></div>
          <span>正在加载播放列表</span>
        </div>

        <div v-else-if="!playlists.length" class="playlist-empty">
          <div class="playlist-empty__icon">
            <Icon icon="lucide:list-video" />
          </div>
          <h2 class="playlist-empty__title">{{ error ? '加载失败' : '暂无播放列表' }}</h2>

          <div class="playlist-empty__actions">
            <Button v-if="!error" @click="openCreateModal">
              <Icon icon="lucide:plus" />
              <span>新建播放列表</span>
            </Button>
            <Button v-else @click="reloadPlaylists">重试</Button>
          </div>
        </div>

        <div v-else class="playlist-workspace">
          <aside class="playlist-library">
            <div class="playlist-library__header">
              <div class="playlist-library__title-group">
                <h2 class="playlist-library__title">列表</h2>
                <span class="playlist-library__count">{{ playlists.length }}</span>
              </div>
              <div class="playlist-library__header-actions">
                <Button size="sm" class="playlist-library__create-btn" @click="openCreateModal">
                  <Icon icon="lucide:plus" />
                  <span>新建</span>
                </Button>
              </div>
            </div>

            <div class="playlist-library__list scrollbar-hide">
              <article
                v-for="playlist in playlists"
                :key="playlist.id"
                class="playlist-library-row"
                :class="{ 'is-active': String(activePlaylist?.id) === String(playlist.id) }"
              >
                <button
                  type="button"
                  class="playlist-library-row__primary"
                  :aria-pressed="String(activePlaylist?.id) === String(playlist.id)"
                  @click="selectPlaylist(playlist.id)"
                >
                  <span class="playlist-library-row__cover" aria-hidden="true">
                    <Icon icon="lucide:list-video" />
                  </span>

                  <div class="playlist-library-row__body">
                    <div class="playlist-library-row__topline">
                      <h3 class="playlist-library-row__name">{{ playlist.name }}</h3>
                      <Badge v-if="playlist.is_default" variant="secondary" class="playlist-library-row__badge">默认</Badge>
                    </div>

                    <p v-if="playlist.description" class="playlist-library-row__description">{{ playlist.description }}</p>

                    <div class="playlist-library-row__meta">
                      <span>{{ playlist.video_count }} 个视频</span>
                      <span class="playlist-library-row__meta-dot" aria-hidden="true"></span>
                      <span>{{ formatDate(playlist.updated_at) }}</span>
                    </div>
                  </div>
                </button>

                <button
                  v-if="!playlist.is_default"
                  type="button"
                  class="playlist-library-row__delete"
                  title="删除播放列表"
                  @click.stop="handleDelete(playlist.id)"
                >
                  <Icon icon="lucide:trash-2" />
                </button>
              </article>
            </div>
          </aside>

          <section class="playlist-detail">
            <div v-if="activePlaylist" class="playlist-detail__panel">
              <div class="playlist-detail__header">
                <div class="playlist-detail__summary">
                  <div class="playlist-detail__title-row">
                    <h2 class="playlist-detail__title">{{ activePlaylist.name }}</h2>
                    <Badge v-if="activePlaylist.is_default" variant="secondary" class="playlist-detail__badge">默认</Badge>
                  </div>
                  <div class="playlist-detail__meta">
                    <span>{{ activePlaylistItems.length }} 个视频</span>
                    <span class="playlist-detail__meta-dot" aria-hidden="true"></span>
                    <span>{{ activePlaylistDurationLabel }}</span>
                    <template v-if="activePlaylist.updated_at">
                      <span class="playlist-detail__meta-dot" aria-hidden="true"></span>
                      <span>{{ formatDate(activePlaylist.updated_at) }}</span>
                    </template>
                  </div>
                  <p v-if="activePlaylist.description" class="playlist-detail__description">{{ activePlaylist.description }}</p>
                </div>
                <div class="playlist-detail__actions">
                  <Button
                    v-if="!activePlaylist.is_default"
                    size="sm"
                    variant="secondary"
                    @click="openEditModal"
                  >
                    <Icon icon="lucide:pencil-line" />
                    <span>编辑列表</span>
                  </Button>
                </div>
              </div>

              <div class="playlist-detail__section-header">
                <h3 class="playlist-detail__section-title">视频</h3>
                <span class="playlist-detail__section-hint">{{ activePlaylistItems.length }}</span>
              </div>

              <div v-if="loadingItems || isHydratingSelection" class="playlist-detail__state">
                <div class="playlist-state__spinner" aria-hidden="true"></div>
                <span>正在加载列表内容</span>
              </div>

              <div v-else-if="!activePlaylistItems.length" class="playlist-detail__empty">
                <div class="playlist-detail__empty-icon">
                  <Icon icon="lucide:list-video" />
                </div>
                <h3 class="playlist-detail__empty-title">这个列表还是空的</h3>
              </div>

              <div v-else class="playlist-detail__items scrollbar-hide">
                <TransitionGroup name="playlist-item-list">
                  <article
                    v-for="(item, index) in activePlaylistItems"
                    :key="item.id"
                    class="playlist-item-row"
                    :class="{ 'is-playing': currentVideoId && String(item.video_id) === String(currentVideoId) }"
                  >
                    <button type="button" class="playlist-item-row__primary" @click="playVideo(item)">
                      <span class="playlist-item-row__index">{{ String(index + 1).padStart(2, '0') }}</span>

                      <div class="playlist-item-row__thumb">
                        <div class="playlist-item-row__thumb-fallback">
                          <Icon icon="lucide:film" />
                        </div>
                        <img
                          v-if="item.video?.thumbnail"
                          :src="item.video.thumbnail"
                          referrerpolicy="no-referrer"
                          :alt="item.video?.title || '播放列表视频'"
                          @error="handlePlaylistItemImageError"
                        >
                      </div>

                      <div class="playlist-item-row__body">
                        <span class="playlist-item-row__title">{{ item.video?.title || '未知视频' }}</span>
                        <span class="playlist-item-row__meta">
                          <span>{{ formatDuration(item.video?.duration) }}</span>
                          <template v-if="item.video?.site">
                            <span class="playlist-item-row__meta-dot" aria-hidden="true"></span>
                            <span>{{ item.video.site }}</span>
                          </template>
                          <span class="playlist-item-row__meta-dot" aria-hidden="true"></span>
                          <span>{{ formatDate(item.added_at) }}</span>
                        </span>
                      </div>
                    </button>

                    <button
                      type="button"
                      class="playlist-item-row__remove"
                      title="从列表移除"
                      @click="handleRemoveVideo(item)"
                    >
                      <Icon icon="lucide:x" />
                    </button>
                  </article>
                </TransitionGroup>
              </div>
            </div>

            <div v-else class="playlist-detail__blank">
              <div class="playlist-detail__blank-icon">
                <Icon icon="lucide:panel-right-open" />
              </div>
              <h3 class="playlist-detail__blank-title">选择一个播放列表</h3>
            </div>
          </section>
        </div>
      </div>
    </div>

    <Transition name="playlist-editor-fade">
      <div v-if="editorOpen" class="playlist-editor-layer" @click.self="handleEditorOpenChange(false)">
        <div class="playlist-editor">
          <div class="playlist-editor__header">
            <div class="playlist-editor__copy">
              <h3 class="playlist-editor__title">{{ editingPlaylist ? '编辑播放列表' : '新建播放列表' }}</h3>
            </div>

            <button type="button" class="playlist-editor__close" @click="closeModal">
              <Icon icon="lucide:x" />
            </button>
          </div>

          <div class="playlist-editor__form">
            <div class="playlist-editor__field">
              <label class="playlist-editor__label" for="playlist-name">名称</label>
              <Input
                id="playlist-name"
                v-model="formName"
                class="playlist-editor__input"
                placeholder="例如：今晚要看"
                @keyup.enter="handleSave"
              />
            </div>

            <div class="playlist-editor__field">
              <label class="playlist-editor__label" for="playlist-description">描述</label>
              <Textarea
                id="playlist-description"
                v-model="formDesc"
                class="playlist-editor__textarea"
                placeholder="可选"
              />
            </div>
          </div>

          <div class="playlist-editor__footer">
            <div class="playlist-editor__footer-actions">
              <Button variant="ghost" @click="closeModal">取消</Button>
              <Button :disabled="!formName.trim()" @click="handleSave">保存</Button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <Dialog :open="showDeleteConfirm" @update:open="handleDeleteConfirmOpenChange">
      <DialogContent class="playlist-delete-confirm">
        <DialogHeader class="playlist-editor__header">
          <DialogTitle>删除播放列表</DialogTitle>
          <DialogDescription>
            {{ deleteTargetPlaylist ? `确定删除“${deleteTargetPlaylist.name}”吗？此操作不可恢复。` : '确定删除这个播放列表吗？此操作不可恢复。' }}
          </DialogDescription>
        </DialogHeader>

        <DialogFooter class="playlist-editor__footer">
          <Button variant="ghost" @click="closeDeleteConfirm">取消</Button>
          <Button variant="destructive" @click="confirmDelete">确认删除</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import usePlaylist from '@/composables/usePlaylist'
import { formatDate, formatDuration } from '@/utils/dateFormat'
import type { Playlist, PlaylistItem } from '@/types/playlist'

const router = useRouter()

const {
  playlists,
  loading,
  loadingItems,
  error,
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
const isHydratingSelection = ref(false)
const showDeleteConfirm = ref(false)
const deleteTargetPlaylist = ref<Playlist | null>(null)

const editorOpen = computed(() => showCreateModal.value || !!editingPlaylist.value)
const defaultPlaylist = computed(() => playlists.value.find((playlist) => playlist.is_default) || null)
const totalVideoCount = computed(() => playlists.value.reduce((sum, playlist) => sum + Number(playlist.video_count || 0), 0))
const activePlaylistDurationSeconds = computed(() => (
  activePlaylistItems.value.reduce((sum, item) => sum + Number(item.video?.duration || 0), 0)
))
const activePlaylistDurationLabel = computed(() => (
  activePlaylistDurationSeconds.value ? formatDuration(activePlaylistDurationSeconds.value) : '暂无时长'
))

const closeModal = () => {
  showCreateModal.value = false
  editingPlaylist.value = null
  formName.value = ''
  formDesc.value = ''
}

const openCreateModal = () => {
  editingPlaylist.value = null
  formName.value = ''
  formDesc.value = ''
  showCreateModal.value = true
}

const openEditModal = () => {
  if (!activePlaylist.value) return

  showCreateModal.value = false
  editingPlaylist.value = activePlaylist.value
  formName.value = activePlaylist.value.name
  formDesc.value = activePlaylist.value.description || ''
}

const handleEditorOpenChange = (open: boolean) => {
  if (!open) {
    closeModal()
  }
}

const closeDeleteConfirm = () => {
  showDeleteConfirm.value = false
  deleteTargetPlaylist.value = null
}

const handleDeleteConfirmOpenChange = (open: boolean) => {
  if (!open) {
    closeDeleteConfirm()
  }
}

const syncSelectionWithList = async (preferredPlaylistId: number | string | null = null) => {
  const availablePlaylists = playlists.value
  const availableIds = new Set(availablePlaylists.map((playlist) => String(playlist.id)))
  const nextPlaylistId = preferredPlaylistId && availableIds.has(String(preferredPlaylistId))
    ? preferredPlaylistId
    : activePlaylist.value && availableIds.has(String(activePlaylist.value.id))
      ? activePlaylist.value.id
      : availablePlaylists[0]?.id

  if (!nextPlaylistId) {
    activePlaylist.value = null
    activePlaylistItems.value = []
    return
  }

  isHydratingSelection.value = true

  try {
    await loadAndSetPlaylist(nextPlaylistId)
  } finally {
    isHydratingSelection.value = false
  }
}

const reloadPlaylists = async () => {
  await fetchPlaylists()

  if (!playlists.value.length) {
    activePlaylist.value = null
    activePlaylistItems.value = []
    return
  }

  await syncSelectionWithList()
}

const selectPlaylist = async (playlistId: number | string) => {
  isHydratingSelection.value = true

  try {
    await loadAndSetPlaylist(playlistId)
  } finally {
    isHydratingSelection.value = false
  }
}

const handleSave = async () => {
  const playlistName = formName.value.trim()
  const playlistDescription = formDesc.value.trim() || null

  if (!playlistName) return

  if (editingPlaylist.value) {
    const updated = await update(editingPlaylist.value.id, playlistName, playlistDescription)
    closeModal()

    if (updated) {
      await syncSelectionWithList(updated.id)
    }

    return
  }

  const created = await create(playlistName, playlistDescription)
  closeModal()

  if (created) {
    await syncSelectionWithList(created.id)
  }
}

const handleDelete = (playlistId: number | string) => {
  const target = playlists.value.find((playlist) => String(playlist.id) === String(playlistId)) || null
  if (!target) return

  deleteTargetPlaylist.value = target
  showDeleteConfirm.value = true
}

const confirmDelete = async () => {
  const target = deleteTargetPlaylist.value
  if (!target) return

  const wasActivePlaylist = !!activePlaylist.value && String(activePlaylist.value.id) === String(target.id)
  const removed = await remove(target.id)

  closeDeleteConfirm()

  if (!removed) return

  if (wasActivePlaylist) {
    await syncSelectionWithList()
  }
}

const playVideo = (item: PlaylistItem) => {
  if (item.video?.id) {
    setCurrentVideo(item.video.id)
    router.push(`/video/${item.video.id}`)
  }
}

const handleRemoveVideo = async (item: PlaylistItem) => {
  if (!activePlaylist.value) return

  await removeVideo(activePlaylist.value.id, item.video_id)
}

const handlePlaylistItemImageError = (event: Event) => {
  const target = event.target as HTMLImageElement | null

  if (target) {
    target.style.display = 'none'
  }
}

onMounted(async () => {
  await reloadPlaylists()
})
</script>

<style scoped>
.playlist-page {
  min-height: 100%;
}

.playlist-toolbar-shell {
  border-bottom: 1px solid hsl(var(--border) / 0.55);
  background:
    linear-gradient(180deg, hsl(var(--primary) / 0.06), transparent 72%),
    hsl(var(--background));
}

.toolbar-container,
.content-container {
  width: 100%;
  margin: 0 auto;
  padding: 0 1rem;
}

@media (min-width: 640px) {
  .toolbar-container,
  .content-container {
    padding: 0 1.5rem;
  }
}

@media (min-width: 1024px) {
  .toolbar-container,
  .content-container {
    padding: 0 2rem;
  }
}

.playlist-page__header {
  padding: 0.85rem 0 1rem;
}

.playlist-page__meta-badge {
  border-radius: 999px;
}

.playlist-page__meta-inline {
  font-size: 0.72rem;
  color: hsl(var(--muted-foreground));
  letter-spacing: 0.04em;
}

.playlist-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.playlist-content__inner {
  position: relative;
  padding-top: 1rem;
  padding-bottom: 1.25rem;
}

.playlist-editor-layer {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem 0;
  background: hsl(var(--background) / 0.58);
  backdrop-filter: blur(4px);
}

.playlist-state,
.playlist-empty,
.playlist-detail__blank,
.playlist-detail__empty,
.playlist-detail__state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.playlist-state {
  min-height: 18rem;
  gap: 0.75rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.85rem;
}

.playlist-state__spinner {
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 999px;
  border: 2px solid hsl(var(--border));
  border-top-color: hsl(var(--primary));
  animation: playlist-spin 0.8s linear infinite;
}

@keyframes playlist-spin {
  to {
    transform: rotate(360deg);
  }
}

.playlist-empty {
  align-items: center;
  justify-content: center;
  min-height: min(58dvh, 28rem);
  gap: 0.9rem;
  padding: 2rem;
  border: none;
  border-radius: 0;
  background: transparent;
  text-align: center;
}

.playlist-empty__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: calc(var(--radius-lg) + 2px);
  background: hsl(var(--secondary) / 0.7);
  color: hsl(var(--primary));
  font-size: 1rem;
}

.playlist-empty__title {
  margin: 0;
  font-size: clamp(1.05rem, 1rem + 0.25vw, 1.2rem);
  font-weight: 650;
  letter-spacing: -0.03em;
}

.playlist-empty__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.playlist-workspace {
  display: grid;
  grid-template-columns: minmax(16rem, 18.5rem) minmax(0, 1fr);
  gap: 0;
  min-height: calc(100dvh - 11rem);
}

.playlist-library,
.playlist-detail__panel,
.playlist-detail__blank {
  min-height: 0;
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.playlist-library {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-right: 1.2rem;
}

.playlist-library__header,
.playlist-detail__section-header,
.playlist-detail__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.playlist-library__header {
  padding: 0.25rem 0 0.85rem;
  border-bottom: 1px solid hsl(var(--border) / 0.45);
}

.playlist-library__title-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.playlist-library__header-actions {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.playlist-library__title,
.playlist-detail__section-title,
.playlist-detail__title {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: hsl(var(--foreground));
}

.playlist-library__count,
.playlist-detail__section-hint {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.5rem;
  height: 1.5rem;
  padding: 0 0.45rem;
  border-radius: 999px;
  background: hsl(var(--secondary) / 0.85);
  color: hsl(var(--muted-foreground));
  font-size: 0.68rem;
  font-weight: 600;
}

.playlist-library__create-btn {
  border-radius: 999px;
  padding-inline: 0.7rem;
}

.playlist-library__list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0.15rem 0 0;
}

.playlist-library-row {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.4rem;
  align-items: flex-start;
  padding: 0;
  border-bottom: 1px solid hsl(var(--border) / 0.42);
  transition: border-color 0.15s ease;
}

.playlist-library-row:hover {
  border-color: hsl(var(--border) / 0.72);
}

.playlist-library-row.is-active {
  border-color: hsl(var(--primary) / 0.38);
}

.playlist-library-row__primary {
  width: 100%;
  display: grid;
  grid-template-columns: 2.4rem minmax(0, 1fr);
  gap: 0.75rem;
  align-items: center;
  padding: 0.75rem 0;
  border: none;
  border-radius: 0;
  background: transparent;
  text-align: left;
  transition: opacity 0.15s ease;
}

.playlist-library-row:hover .playlist-library-row__primary {
  opacity: 1;
}

.playlist-library-row.is-active .playlist-library-row__primary {
  opacity: 1;
}

.playlist-library-row__body {
  min-width: 0;
  display: grid;
  gap: 0.3rem;
}

.playlist-library-row__cover {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.4rem;
  height: 2.4rem;
  border-radius: calc(var(--radius-sm) + 1px);
  background: hsl(var(--secondary) / 0.75);
  color: hsl(var(--primary));
  font-size: 0.95rem;
}

.playlist-library-row.is-active .playlist-library-row__cover {
  background: hsl(var(--primary) / 0.12);
}

.playlist-library-row__topline {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.playlist-library-row__name {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.85rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.playlist-library-row__badge,
.playlist-detail__badge {
  flex-shrink: 0;
  border-radius: 999px;
}

.playlist-library-row__description {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.72rem;
  line-height: 1.45;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

.playlist-library-row__meta,
.playlist-detail__meta,
.playlist-item-row__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.4rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.68rem;
}

.playlist-library-row__meta-dot,
.playlist-detail__meta-dot,
.playlist-item-row__meta-dot {
  width: 0.2rem;
  height: 0.2rem;
  border-radius: 999px;
  background: hsl(var(--border));
}

.playlist-library-row__delete {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.85rem;
  height: 1.85rem;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s ease, background 0.15s ease, color 0.15s ease;
  margin-top: 0.62rem;
}

.playlist-library-row:hover .playlist-library-row__delete,
.playlist-library-row__delete:focus-visible {
  opacity: 1;
}

.playlist-library-row__delete:hover {
  background: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}

.playlist-detail {
  min-width: 0;
  border-left: 1px solid hsl(var(--border) / 0.45);
  padding-left: 1.2rem;
}

.playlist-detail__panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.playlist-detail__header {
  align-items: flex-start;
  padding: 0.25rem 0 0.85rem;
  border-bottom: 1px solid hsl(var(--border) / 0.45);
}

.playlist-detail__summary {
  min-width: 0;
  display: grid;
  gap: 0.35rem;
}

.playlist-detail__title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.playlist-detail__actions {
  flex-shrink: 0;
}

.playlist-detail__section-header {
  padding: 0.8rem 0 0.7rem;
  border-bottom: 1px solid hsl(var(--border) / 0.35);
}

.playlist-detail__state,
.playlist-detail__empty,
.playlist-detail__blank {
  flex: 1;
  min-height: 0;
  gap: 0.75rem;
  padding: 2rem;
}

.playlist-detail__items {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0.15rem 0 0;
}

.playlist-detail__empty-icon,
.playlist-detail__blank-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3.2rem;
  height: 3.2rem;
  border-radius: 999px;
  background: hsl(var(--secondary) / 0.6);
  color: hsl(var(--primary));
  font-size: 1.2rem;
}

.playlist-detail__empty-title,
.playlist-detail__blank-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.playlist-item-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.55rem;
  align-items: center;
  padding: 0;
  border: none;
  border-bottom: 1px solid hsl(var(--border) / 0.42);
  border-radius: 0;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.playlist-item-row:hover {
  border-color: hsl(var(--border) / 0.72);
}

.playlist-item-row.is-playing {
  background: linear-gradient(90deg, hsl(var(--primary) / 0.08), transparent 72%);
  border-color: hsl(var(--primary) / 0.34);
}

.playlist-item-row__primary {
  width: 100%;
  display: grid;
  grid-template-columns: auto 7rem minmax(0, 1fr);
  gap: 0.7rem;
  align-items: center;
  border: none;
  background: transparent;
  text-align: left;
  padding: 0.8rem 0;
}

.playlist-item-row__index {
  min-width: 2rem;
  color: hsl(var(--muted-foreground));
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
}

.playlist-item-row__thumb {
  position: relative;
  width: 6.5rem;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: calc(var(--radius-sm) + 1px);
  background: hsl(var(--secondary) / 0.75);
}

.playlist-item-row__thumb img,
.playlist-item-row__thumb-fallback {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.playlist-item-row__thumb img {
  object-fit: cover;
}

.playlist-item-row__thumb-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground));
  font-size: 1rem;
}

.playlist-item-row__body {
  min-width: 0;
  display: grid;
  gap: 0.35rem;
}

.playlist-item-row__title {
  color: hsl(var(--foreground));
  font-size: 0.84rem;
  font-weight: 600;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.playlist-item-row__remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  opacity: 0.4;
  transition: opacity 0.15s ease, background 0.15s ease, color 0.15s ease;
  margin-right: 0.1rem;
}

.playlist-item-row:hover .playlist-item-row__remove,
.playlist-item-row__remove:focus-visible {
  opacity: 1;
}

.playlist-item-row__remove:hover {
  background: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}

.playlist-editor {
  width: min(100%, 30rem);
  border: 1px solid hsl(var(--border) / 0.85);
  border-radius: var(--radius-lg);
  background: hsl(var(--card));
  box-shadow: var(--shadow-popup);
  overflow: hidden;
}

.playlist-editor__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1rem 0.8rem;
  border-bottom: 1px solid hsl(var(--border) / 0.5);
}

.playlist-editor__copy {
  min-width: 0;
  display: grid;
}

.playlist-editor__title {
  margin: 0;
  font-size: 0.98rem;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.playlist-editor__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.playlist-editor__close:hover {
  background: hsl(var(--secondary) / 0.8);
  color: hsl(var(--foreground));
}

.playlist-editor__form {
  display: grid;
  gap: 0.8rem;
  padding: 1rem;
}

.playlist-editor__field {
  display: grid;
  gap: 0.45rem;
}

.playlist-editor__label {
  color: hsl(var(--muted-foreground));
  font-size: 0.72rem;
  font-weight: 500;
}

.playlist-editor__input,
.playlist-editor__textarea {
  background: hsl(var(--background));
  border-color: hsl(var(--border));
}

.playlist-editor__textarea {
  min-height: 6rem;
  resize: vertical;
}

.playlist-editor__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.8rem;
  padding: 0.85rem 1rem 1rem;
  border-top: 1px solid hsl(var(--border) / 0.5);
}

.playlist-editor__footer-actions {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.playlist-item-list-enter-active,
.playlist-item-list-leave-active {
  transition: all 0.2s ease;
}

.playlist-item-list-enter-from,
.playlist-item-list-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

.playlist-editor-fade-enter-active,
.playlist-editor-fade-leave-active {
  transition: opacity 0.18s ease;
}

.playlist-editor-fade-enter-from,
.playlist-editor-fade-leave-to {
  opacity: 0;
}

@media (max-width: 1023px) {
  .playlist-workspace {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .playlist-library {
    padding-right: 0;
    padding-bottom: 1rem;
    border-bottom: 1px solid hsl(var(--border) / 0.45);
  }

  .playlist-detail {
    border-left: none;
    padding-left: 0;
    padding-top: 1rem;
  }
}

@media (max-width: 767px) {
  .playlist-content__inner {
    padding-top: 0.75rem;
  }

  .playlist-empty {
    padding: 1.5rem 0;
  }

  .playlist-editor-layer {
    padding: 1rem 0;
    align-items: flex-start;
  }

  .playlist-editor {
    width: 100%;
  }

  .playlist-editor__footer {
    justify-content: flex-end;
  }

  .playlist-editor__footer-actions {
    justify-content: flex-end;
  }

  .playlist-library__header,
  .playlist-detail__header,
  .playlist-detail__section-header {
    padding-left: 0;
    padding-right: 0;
  }

  .playlist-detail__actions {
    width: 100%;
  }

  .playlist-detail__actions :deep(button) {
    width: 100%;
  }

  .playlist-library__create-btn {
    padding-inline: 0.55rem;
  }

  .playlist-item-row__primary {
    grid-template-columns: 2rem minmax(0, 1fr);
  }

  .playlist-item-row__thumb {
    grid-column: 2;
    width: 100%;
    max-width: 12rem;
  }

  .playlist-item-row__body {
    grid-column: 2;
  }

  .playlist-item-row__remove {
    align-self: flex-start;
    opacity: 1;
  }
}

@media (hover: none) {
  .playlist-library-row__delete,
  .playlist-item-row__remove {
    opacity: 1;
  }
}
</style>
