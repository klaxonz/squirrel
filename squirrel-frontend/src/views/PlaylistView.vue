<template>
  <AppPageShell class="playlist-page">
    <div class="playlist-content scrollbar-hide">
      <div class="content-container playlist-content__inner">
        <div v-if="loading && !playlists.length" class="playlist-state playlist-state--loading">
          <LoadingIndicator :loading="true" text="正在加载播放列表" />
        </div>

        <AppEmptyState
          v-else-if="!playlists.length"
          class="playlist-empty-card"
          eyebrow="播放列表"
          :title="error ? '加载失败' : '还没有播放列表'"
          :copy="error ? '' : '创建一个播放列表，把想看的视频收集到一起'"
        >
          <template #actions>
            <Button v-if="!error" @click="openCreateModal">
              <Icon icon="lucide:plus" />
              <span>新建播放列表</span>
            </Button>
            <Button v-else @click="reloadPlaylists">重试</Button>
          </template>
        </AppEmptyState>

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
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import AppEmptyState from '@/components/layout/AppEmptyState.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
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

<style scoped src="../styles/views/PlaylistView.css"></style>
