<template>
  <div class="playlist-page flex h-full flex-col bg-background text-foreground">
    <div class="playlist-content scrollbar-hide">
      <div class="content-container playlist-content__inner">
        <div v-if="loading && !playlists.length" class="playlist-state playlist-state--loading">
          <LoadingIndicator :loading="true" text="正在加载播放列表" />
        </div>

        <div v-else-if="!playlists.length" class="playlist-empty-card">
          <p class="playlist-empty-card__eyebrow">播放列表</p>
          <h2 class="playlist-empty-card__title">{{ error ? '加载失败' : '还没有播放列表' }}</h2>
          <p v-if="!error" class="playlist-empty-card__copy">创建一个播放列表，把想看的视频收集到一起</p>
          <div class="playlist-empty-card__actions">
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
              <Button size="xs" class="playlist-library__create-btn" @click="openCreateModal">
                <Icon icon="lucide:plus" />
                <span>新建</span>
              </Button>
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
                  <span class="playlist-cover" aria-hidden="true">
                    <template v-if="getPlaylistThumbnails(playlist).length">
                      <img
                        v-for="(thumb, i) in getPlaylistThumbnails(playlist).slice(0, 3)"
                        :key="i"
                        :src="thumb"
                        referrerpolicy="no-referrer"
                        class="playlist-cover__img"
                        :class="[
                          `playlist-cover__img--${i}`,
                          { 'playlist-cover__img--single': getPlaylistThumbnails(playlist).length === 1 },
                          { 'playlist-cover__img--double': getPlaylistThumbnails(playlist).length === 2 },
                        ]"
                        @error="handleCoverImageError"
                      >
                    </template>
                    <span v-else class="playlist-cover__fallback">
                      <Icon icon="lucide:list-video" />
                    </span>
                    <span v-if="playlist.video_count" class="playlist-cover__count">
                      <Icon icon="lucide:play" class="playlist-cover__count-icon" />
                      {{ playlist.video_count }}
                    </span>
                  </span>

                  <div class="playlist-library-row__body">
                    <div class="playlist-library-row__topline">
                      <h3 class="playlist-library-row__name">{{ playlist.name }}</h3>
                      <Badge v-if="playlist.is_default" variant="secondary" class="playlist-library-row__badge">默认</Badge>
                    </div>
                    <p v-if="playlist.description" class="playlist-library-row__description">{{ playlist.description }}</p>
                    <span class="playlist-library-row__meta">{{ formatDate(playlist.updated_at) }}</span>
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
                    <Badge v-if="activePlaylist.is_default" variant="secondary">默认</Badge>
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
                <DropdownMenu v-if="!activePlaylist.is_default">
                  <DropdownMenuTrigger as-child>
                    <Button variant="ghost" size="icon-sm" class="playlist-detail__more-btn">
                      <Icon icon="lucide:more-horizontal" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem @click="openEditModal">
                      <Icon icon="lucide:pencil-line" class="playlist-dropdown-icon" />
                      编辑列表
                    </DropdownMenuItem>
                    <DropdownMenuItem class="text-destructive focus:text-destructive" @click="handleDelete(activePlaylist!.id)">
                      <Icon icon="lucide:trash-2" class="playlist-dropdown-icon" />
                      删除列表
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              <div v-if="loadingItems || isHydratingSelection" class="playlist-detail__state">
                <LoadingIndicator :loading="true" text="正在加载列表内容" />
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
                    v-for="item in activePlaylistItems"
                    :key="item.id"
                    class="playlist-item-row"
                    :class="{ 'is-playing': currentVideoId && String(item.video_id) === String(currentVideoId) }"
                  >
                    <button type="button" class="playlist-item-row__primary" @click="playVideo(item)">
                      <div class="playlist-item-row__thumb">
                        <div class="playlist-item-row__thumb-fallback">
                          <Icon icon="lucide:film" />
                        </div>
                        <img
                          v-if="item.video?.thumbnail"
                          :src="item.video.thumbnail"
                          referrerpolicy="no-referrer"
                          :alt="item.video?.title || '视频缩略图'"
                          @error="handlePlaylistItemImageError"
                        >
                        <span v-if="item.video?.duration" class="playlist-item-row__duration">
                          {{ formatDuration(item.video.duration) }}
                        </span>
                      </div>

                      <div class="playlist-item-row__body">
                        <span class="playlist-item-row__title">{{ item.video?.title || '未知视频' }}</span>
                        <span class="playlist-item-row__meta">
                          <template v-if="item.video?.site">
                            <span>{{ item.video.site }}</span>
                            <span class="playlist-item-row__meta-dot" aria-hidden="true"></span>
                          </template>
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

    <Dialog :open="showDeleteConfirm" @update:open="handleDeleteConfirmOpenChange">
      <DialogContent class="playlist-delete-confirm">
        <DialogHeader>
          <DialogTitle>删除播放列表</DialogTitle>
          <DialogDescription>
            {{ deleteTargetPlaylist ? `确定删除"${deleteTargetPlaylist.name}"吗？此操作不可恢复。` : '确定删除这个播放列表吗？此操作不可恢复。' }}
          </DialogDescription>
        </DialogHeader>

        <DialogFooter>
          <Button variant="ghost" @click="closeDeleteConfirm">取消</Button>
          <Button variant="destructive" @click="confirmDelete">确认删除</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Transition name="playlist-editor-fade">
      <div v-if="editorOpen" class="playlist-editor-layer" @click.self="handleEditorOpenChange(false)">
        <div class="playlist-editor">
          <div class="playlist-editor__header">
            <h3 class="playlist-editor__title">{{ editingPlaylist ? '编辑播放列表' : '新建播放列表' }}</h3>
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
                placeholder="例如：今晚要看"
                @keyup.enter="handleSave"
              />
            </div>

            <div class="playlist-editor__field">
              <label class="playlist-editor__label" for="playlist-description">描述</label>
              <Textarea
                id="playlist-description"
                v-model="formDesc"
                placeholder="可选"
              />
            </div>
          </div>

          <div class="playlist-editor__footer">
            <Button variant="ghost" @click="closeModal">取消</Button>
            <Button :disabled="!formName.trim()" @click="handleSave">保存</Button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import LoadingIndicator from '@/components/feed/LoadingIndicator.vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { rememberVideoPlaybackSeed } from '@/composables/videoPlaybackSeed'
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
const playlistThumbnails = ref<Map<string | number, string[]>>(new Map())

const editorOpen = computed(() => showCreateModal.value || !!editingPlaylist.value)
const activePlaylistDurationSeconds = computed(() => (
  activePlaylistItems.value.reduce((sum, item) => sum + Number(item.video?.duration || 0), 0)
))
const activePlaylistDurationLabel = computed(() => (
  activePlaylistDurationSeconds.value ? formatDuration(activePlaylistDurationSeconds.value) : '暂无时长'
))

const getPlaylistThumbnails = (playlist: Playlist): string[] => {
  const cached = playlistThumbnails.value.get(playlist.id)
  if (cached) return cached

  const items = activePlaylist.value && String(activePlaylist.value.id) === String(playlist.id)
    ? activePlaylistItems.value
    : []
  const thumbs = items
    .map(item => item.video?.thumbnail)
    .filter((t): t is string => !!t)
    .slice(0, 3)
  playlistThumbnails.value.set(playlist.id, thumbs)
  return thumbs
}

const handleCoverImageError = (event: Event) => {
  const target = event.target as HTMLImageElement | null
  if (target) target.style.display = 'none'
}

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
  if (!open) closeModal()
}

const closeDeleteConfirm = () => {
  showDeleteConfirm.value = false
  deleteTargetPlaylist.value = null
}

const handleDeleteConfirmOpenChange = (open: boolean) => {
  if (!open) closeDeleteConfirm()
}

const syncSelectionWithList = async (preferredPlaylistId: number | string | null = null) => {
  const availablePlaylists = playlists.value
  const availableIds = new Set(availablePlaylists.map(p => String(p.id)))
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
    if (updated) await syncSelectionWithList(updated.id)
    return
  }

  const created = await create(playlistName, playlistDescription)
  closeModal()
  if (created) await syncSelectionWithList(created.id)
}

const handleDelete = (playlistId: number | string) => {
  const target = playlists.value.find(p => String(p.id) === String(playlistId)) || null
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
    rememberVideoPlaybackSeed(item.video)
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
  if (target) target.style.display = 'none'
}

onMounted(async () => {
  await reloadPlaylists()
})
</script>

<style scoped>
.playlist-page {
  min-height: 100%;
}

.content-container {
  width: 100%;
  margin: 0 auto;
  padding: 0 1rem;
}

@media (min-width: 640px) {
  .content-container {
    padding: 0 1.5rem;
  }
}

@media (min-width: 1024px) {
  .content-container {
    padding: 0 2rem;
  }
}

.playlist-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.playlist-content__inner {
  position: relative;
  padding-top: 0.75rem;
  padding-bottom: 1.25rem;
}

/* ─── States ─── */
.playlist-state,
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
}

/* ─── Empty Card (unified with Subscribed style) ─── */
.playlist-empty-card {
  min-height: 40vh;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  text-align: center;
  gap: 1.25rem;
  padding: 2rem;
  border: 1px dashed hsl(var(--border) / 0.6);
  border-radius: var(--radius-lg);
}

.playlist-empty-card__eyebrow {
  margin: 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: hsl(var(--primary));
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.playlist-empty-card__title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.playlist-empty-card__copy {
  margin: 0;
  max-width: 22rem;
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground));
  line-height: 1.6;
}

.playlist-empty-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

/* ─── Workspace (two-column grid) ─── */
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

/* ─── Library (left column) ─── */
.playlist-library {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-right: 1.2rem;
}

.playlist-library__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.15rem 0 0.75rem;
  border-bottom: 1px solid hsl(var(--border) / 0.4);
}

.playlist-library__title-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.playlist-library__title {
  margin: 0;
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.playlist-library__count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.4rem;
  height: 1.4rem;
  padding: 0 0.4rem;
  border-radius: 999px;
  background: hsl(var(--secondary) / 0.85);
  color: hsl(var(--muted-foreground));
  font-size: 0.65rem;
  font-weight: 600;
}

.playlist-library__create-btn {
  border-radius: calc(var(--radius-sm) + 1px);
  gap: 0.3rem;
}

.playlist-library__list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0.35rem 0 0;
}

/* ─── Library Row ─── */
.playlist-library-row {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.2rem;
  align-items: flex-start;
  padding: 0;
  border-radius: var(--radius-md);
  transition: background 0.15s ease;
}

.playlist-library-row:hover {
  background: hsl(var(--secondary) / 0.12);
}

.playlist-library-row.is-active {
  background: hsl(var(--primary) / 0.06);
  box-shadow: inset 2px 0 0 hsl(var(--primary));
}

.playlist-library-row__primary {
  width: 100%;
  display: grid;
  grid-template-columns: 3.6rem minmax(0, 1fr);
  gap: 0.65rem;
  align-items: center;
  padding: 0.55rem 0.4rem;
  border: none;
  border-radius: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.playlist-library-row__body {
  min-width: 0;
  display: grid;
  gap: 0.2rem;
}

.playlist-library-row__topline {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  min-width: 0;
}

.playlist-library-row__name {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.82rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.playlist-library-row__badge {
  flex-shrink: 0;
  border-radius: 999px;
}

.playlist-library-row__description {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.7rem;
  line-height: 1.4;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

.playlist-library-row__meta {
  color: hsl(var(--muted-foreground));
  font-size: 0.66rem;
}

/* ─── Mosaic Cover ─── */
.playlist-cover {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  width: 3.6rem;
  aspect-ratio: 16 / 12;
  overflow: hidden;
  border-radius: calc(var(--radius-sm) - 1px);
  background: hsl(var(--secondary) / 0.75);
  gap: 1px;
}

.playlist-cover__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.playlist-cover__img--0 {
  grid-row: 1 / 3;
}

.playlist-cover__img--single {
  grid-column: 1 / 3;
  grid-row: 1 / 3;
}

.playlist-cover__img--double.playlist-cover__img--0 {
  grid-row: 1 / 3;
}

.playlist-cover__fallback {
  grid-column: 1 / 3;
  grid-row: 1 / 3;
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--primary));
  font-size: 0.85rem;
}

.playlist-cover__count {
  position: absolute;
  bottom: 2px;
  right: 2px;
  display: flex;
  align-items: center;
  gap: 0.15rem;
  padding: 0.05rem 0.25rem;
  border-radius: calc(var(--radius-sm) - 2px);
  background: hsl(var(--background) / 0.88);
  backdrop-filter: blur(4px);
  color: hsl(var(--foreground));
  font-size: 0.52rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}

.playlist-cover__count-icon {
  width: 0.45rem;
  height: 0.45rem;
}

.playlist-library-row__delete {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.7rem;
  height: 1.7rem;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s ease, background 0.15s ease, color 0.15s ease;
  margin-top: 0.4rem;
  margin-right: 0.1rem;
}

.playlist-library-row:hover .playlist-library-row__delete,
.playlist-library-row__delete:focus-visible {
  opacity: 1;
}

.playlist-library-row__delete:hover {
  background: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}

/* ─── Detail (right column) ─── */
.playlist-detail {
  min-width: 0;
  border-left: 1px solid hsl(var(--border) / 0.4);
  padding-left: 1.2rem;
}

.playlist-detail__panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.playlist-detail__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.15rem 0 0.75rem;
  border-bottom: 1px solid hsl(var(--border) / 0.4);
}

.playlist-detail__summary {
  min-width: 0;
  display: grid;
  gap: 0.3rem;
}

.playlist-detail__title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.playlist-detail__title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 650;
  letter-spacing: -0.02em;
}

.playlist-detail__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.4rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.7rem;
}

.playlist-detail__meta-dot {
  width: 0.2rem;
  height: 0.2rem;
  border-radius: 999px;
  background: hsl(var(--border));
}

.playlist-detail__description {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.78rem;
  line-height: 1.5;
}

.playlist-detail__more-btn {
  flex-shrink: 0;
}

.playlist-dropdown-icon {
  width: 1rem;
  height: 1rem;
  margin-right: 0.4rem;
  opacity: 0.6;
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
  padding: 0.35rem 0 0;
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

/* ─── Video Item Row ─── */
.playlist-item-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.4rem;
  align-items: center;
  padding: 0;
  border: none;
  border-radius: var(--radius-md);
  transition: background 0.15s ease;
}

.playlist-item-row:hover {
  background: hsl(var(--secondary) / 0.15);
}

.playlist-item-row.is-playing {
  background: hsl(var(--primary) / 0.06);
  box-shadow: inset 2px 0 0 hsl(var(--primary));
}

.playlist-item-row__primary {
  width: 100%;
  display: grid;
  grid-template-columns: 7.5rem minmax(0, 1fr);
  gap: 0.7rem;
  align-items: center;
  border: none;
  background: transparent;
  text-align: left;
  padding: 0.5rem 0.4rem;
  cursor: pointer;
}

.playlist-item-row__thumb {
  position: relative;
  width: 7.5rem;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: calc(var(--radius-sm));
  background: hsl(var(--secondary) / 0.75);
  flex-shrink: 0;
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
  font-size: 1.1rem;
}

.playlist-item-row__duration {
  position: absolute;
  bottom: 4px;
  right: 4px;
  padding: 0.1rem 0.35rem;
  border-radius: calc(var(--radius-sm) - 2px);
  background: rgb(0 0 0 / 0.75);
  color: #fff;
  font-size: 0.62rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  line-height: 1.3;
}

.playlist-item-row__body {
  min-width: 0;
  display: grid;
  gap: 0.25rem;
  align-content: center;
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

.playlist-item-row__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.66rem;
}

.playlist-item-row__meta-dot {
  width: 0.2rem;
  height: 0.2rem;
  border-radius: 999px;
  background: hsl(var(--border));
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
  opacity: 0;
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

/* ─── Editor Modal ─── */
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
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1rem 0.8rem;
  border-bottom: 1px solid hsl(var(--border) / 0.5);
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

.playlist-editor__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.6rem;
  padding: 0.85rem 1rem 1rem;
  border-top: 1px solid hsl(var(--border) / 0.5);
}

/* ─── Transitions ─── */
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

/* ─── Responsive ─── */
@media (max-width: 1023px) {
  .playlist-workspace {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .playlist-library {
    padding-right: 0;
    padding-bottom: 1rem;
    border-bottom: 1px solid hsl(var(--border) / 0.4);
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

  .playlist-empty-card {
    padding: 1.5rem 0;
  }

  .playlist-editor-layer {
    padding: 1rem 0;
    align-items: flex-start;
  }

  .playlist-editor {
    width: 100%;
  }

  .playlist-library__header {
    padding-left: 0;
    padding-right: 0;
  }

  .playlist-detail__header {
    padding-left: 0;
    padding-right: 0;
  }

  .playlist-item-row__primary {
    grid-template-columns: 5.5rem minmax(0, 1fr);
    gap: 0.5rem;
  }

  .playlist-item-row__thumb {
    width: 5.5rem;
  }

  .playlist-item-row__remove {
    opacity: 1;
  }

  .playlist-library-row__primary {
    grid-template-columns: 2.8rem minmax(0, 1fr);
  }

  .playlist-cover {
    width: 2.8rem;
  }
}

@media (hover: none) {
  .playlist-library-row__delete,
  .playlist-item-row__remove {
    opacity: 1;
  }
}
</style>
