<template>
  <AppPageShell variant="compact" surface="organize" width="fluid" fill>
    <AppTwoColumnLayout
      ref="twoColumnRef"
      preset="playlist"
      responsive-mode="drawer"
      :default-sidebar-open="false"
    >
      <template #sidebar>
        <AppSidebarHeader title="播放列表" :subtitle="`${playlists.length} 个列表`">
          <template #actions>
            <Button
              size="sm" icon-only
              title="新建播放列表"
              aria-label="新建播放列表"
              @click="openCreateModal"
            >
              <AppIcon name="plus" class="h-4 w-4" />
            </Button>
          </template>
        </AppSidebarHeader>

        <nav class="app-workbench__nav custom-scrollbar" aria-label="播放列表">
          <AppListOption
            v-for="playlist in visiblePlaylists"
            :key="playlist.id"
            class="playlist-nav-item"
            :selected="String(activePlaylist?.id) === String(playlist.id)"
            @click="selectPlaylist(playlist.id)"
          >
            <div class="playlist-nav-thumb">
              <VideoThumbnail
                v-if="getPlaylistThumbnails(playlist).length"
                :src="getPlaylistThumbnails(playlist)[0]"
                fit="cover"
              />
              <div v-else class="flex h-full w-full items-center justify-center text-muted-foreground">
                <AppIcon name="playlistVideo" class="h-4 w-4" />
              </div>
            </div>
            <div class="playlist-nav-copy">
              <div class="playlist-nav-title-row">
                <span class="playlist-nav-title">{{ playlist.name }}</span>
                <span v-if="playlist.is_default" class="playlist-nav-badge">默认</span>
              </div>
              <div class="playlist-nav-meta">{{ playlist.video_count }} 个视频</div>
            </div>
          </AppListOption>
        </nav>
      </template>

      <template #header>
        <!-- Sidebar already carries the "播放列表 / N 个列表" title; the main
             pane header only appears once a playlist provides its own context. -->
        <AppPaneHeader
          v-if="activePlaylist"
          :title="activePlaylist.name"
          :subtitle="`${activePlaylistItems.length} 个视频 · ${activePlaylistDurationLabel}`"
        >
          <template #actions>
            <Button v-if="activePlaylistItems.length" size="sm" @click="playAll">
              <AppIcon name="play" class="h-4 w-4 fill-current" />
              播放全部
            </Button>
            <AppActionMenu
              v-if="activePlaylist && !activePlaylist.is_default"
              :items="playlistActionItems"
              trigger-label="更多操作"
            />
          </template>
        </AppPaneHeader>
      </template>

      <div class="app-workbench__content playlist-workbench-content">
        <NewContentBar
          class="playlist-workbench-content__new-content"
          :visible="newContentVisible"
          :count="newContentCount"
          @apply="applyNewContent"
        />

        <div v-if="loading && !playlists.length" class="app-content-stack app-content-stack--dense">
          <AppSkeleton height="7rem" rounded="var(--radius-lg)" shimmer />
          <div class="app-content-stack app-content-stack--dense">
            <AppSkeleton v-for="i in 6" :key="i" height="4rem" rounded="var(--radius-lg)" shimmer />
          </div>
        </div>

        <div v-else-if="!playlists.length" class="app-page-empty app-page-empty--compact">
          <AppEmptyState
            variant="plain"
            icon="playlistVideo"
            :title="error ? '加载失败' : '暂无播放列表'"
            :copy="error ? '' : '创建播放列表后会显示在这里。'"
          >
            <template #actions>
              <Button v-if="!error" @click="openCreateModal">
                <AppIcon name="plus" class="h-4 w-4" />
                新建播放列表
              </Button>
              <Button v-else severity="secondary" outlined @click="reloadPlaylists">重试</Button>
            </template>
          </AppEmptyState>
        </div>

        <div v-else-if="!visiblePlaylists.length" class="app-page-empty app-page-empty--compact">
          <AppEmptyState
            variant="plain"
            icon="playlistVideo"
            title="没有匹配的播放列表"
            copy="调整搜索词后再试。"
          />
        </div>

        <div v-else-if="activePlaylist" class="playlist-workspace">
          <section class="playlist-table">
            <header class="playlist-table-toolbar">
              <div>
                <h2 class="playlist-table-title">视频</h2>
                <p class="playlist-table-subtitle">点击行播放，使用右侧操作从列表移除。</p>
              </div>
              <span class="playlist-table-count">{{ activePlaylistItems.length }} 项</span>
            </header>

            <div v-if="loadingItems || isHydratingSelection" class="playlist-skeleton-list">
              <AppSkeleton v-for="i in 8" :key="i" height="4.75rem" rounded="var(--radius-md)" shimmer />
            </div>

            <div v-else-if="!activePlaylistItems.length" class="playlist-empty">
              <AppEmptyState variant="plain" icon="playlistVideo" title="暂无视频" copy="添加到列表的视频会显示在这里。" />
            </div>

            <div v-else class="playlist-queue-list">
              <div class="playlist-table-head" aria-hidden="true">
                <span>#</span>
                <span>标题</span>
                <span>来源</span>
                <span>添加时间</span>
                <span>时长</span>
                <span />
              </div>

              <article
                v-for="(item, index) in activePlaylistItems"
                :key="item.id"
                class="playlist-item-shell"
              >
                <AppContentRow
                  class="playlist-item group"
                  :class="{ 'is-current': currentVideoId && String(item.video_id) === String(currentVideoId) }"
                  :aria-label="`播放 ${item.video?.title || '视频'}`"
                  @activate="playVideo(item)"
                >
                  <div class="playlist-item-index">
                    <span>{{ index + 1 }}</span>
                    <AppIcon name="play" class="playlist-item-play h-4 w-4 fill-current" />
                  </div>

                  <div class="playlist-item-media">
                    <div class="playlist-row-thumb">
                      <VideoThumbnail v-if="item.video?.thumbnail" :src="item.video.thumbnail" fit="cover" />
                      <div v-else class="app-media-thumb-fallback">
                        <AppIcon name="film" class="h-5 w-5" />
                      </div>
                      <span v-if="item.video?.duration" class="app-media-duration-badge app-media-duration-badge--compact app-mono">
                        {{ formatDuration(item.video.duration) }}
                      </span>
                    </div>
                    <div class="playlist-item-copy">
                      <div class="playlist-item-title">{{ item.video?.title }}</div>
                      <div class="playlist-item-meta">
                        <span>{{ item.video?.site }}</span>
                        <span class="playlist-meta-dot" />
                        <span>{{ formatDate(item.added_at) }}</span>
                      </div>
                    </div>
                  </div>

                  <div class="playlist-item-site">{{ item.video?.site }}</div>
                  <div class="playlist-item-added">{{ formatDate(item.added_at) }}</div>
                  <div class="playlist-item-duration">
                    {{ item.video?.duration ? formatDuration(item.video.duration) : '—' }}
                  </div>

                  <template #actions>
                    <Button
                      text severity="secondary"
                      size="sm" icon-only
                      class="playlist-item-remove"
                      title="从播放列表移除"
                      aria-label="从播放列表移除"
                      @click="handleRemoveVideo(item)"
                    >
                      <AppIcon name="close" class="h-4 w-4" />
                    </Button>
                  </template>
                </AppContentRow>
              </article>
            </div>
          </section>
        </div>

        <div v-else class="app-page-empty app-page-empty--compact">
          <AppEmptyState variant="plain" icon="panelOpen" title="选择播放列表" copy="选择左侧列表后查看内容。" />
        </div>
      </div>
    </AppTwoColumnLayout>

    <ConfirmDialog
      :open="showDeleteConfirm"
      icon="trash"
      icon-bg-class="bg-destructive/10 text-destructive"
      title="删除播放列表？"
      cancel-label="取消"
      confirm-label="确认删除"
      confirm-variant="destructive"
      @update:open="handleDeleteConfirmOpenChange"
      @confirm="confirmDelete"
    >
      <template #description>
        {{ deleteTargetPlaylist ? `确定要删除 "${deleteTargetPlaylist.name}" 吗？此操作不会删除视频本身。` : '确定要删除这个播放列表吗？' }}
      </template>
    </ConfirmDialog>

    <Dialog :open="editorOpen" @update:open="handleEditorOpenChange">
      <DialogContent class="app-dialog-surface playlist-editor-dialog">
        <DialogHeader class="app-dialog-form-header">
          <DialogTitle class="app-dialog-form-title">{{ editingPlaylist ? '编辑列表' : '新建播放列表' }}</DialogTitle>
        </DialogHeader>
        <div class="app-dialog-form-body">
          <AppFormField v-slot="{ control }" id="playlist-editor-name" label="列表名称" required>
            <Input v-bind="control" v-model="formName" fluid placeholder="例如：我的最爱" @keyup.enter="handleSave" />
          </AppFormField>
          <AppFormField v-slot="{ control }" id="playlist-editor-description" label="描述">
            <Textarea v-bind="control" v-model="formDesc" fluid placeholder="添加一些关于这个列表的说明" rows="3" />
          </AppFormField>
        </div>
        <DialogFooter class="app-dialog-form-footer app-dialog-form-footer--end">
          <Button severity="secondary" outlined @click="closeModal">取消</Button>
          <Button :disabled="!formName.trim()" @click="handleSave">
            {{ editingPlaylist ? '保存' : '创建' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Skeleton as AppSkeleton } from '@/shared/ui/skeleton'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppActionMenu from '@/shared/components/AppActionMenu.vue'
import AppContentRow from '@/shared/components/layout/AppContentRow.vue'
import AppFormField from '@/shared/components/layout/AppFormField.vue'
import AppListOption from '@/shared/components/layout/AppListOption.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppPaneHeader from '@/shared/components/layout/AppPaneHeader.vue'
import AppSidebarHeader from '@/shared/components/layout/AppSidebarHeader.vue'
import AppTwoColumnLayout from '@/shared/components/layout/AppTwoColumnLayout.vue'
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
import ConfirmDialog from '@/shared/components/ConfirmDialog.vue'
import { Button } from '@/shared/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog'
import { Input } from '@/shared/ui/input'
import { Textarea } from '@/shared/ui/textarea'
import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import { prefetchDesktopPlaybackSource } from '@/features/video/composables/useVideoOperations'
import { usePlaylist } from '@/features/video/composables/usePlaylist'
import { getPlaylistItems } from '@/shared/api/playlist'
import NewContentBar from '@/shared/components/layout/NewContentBar.vue'
import { useNewContentDetector, prependPreservingScroll } from '@/shared/composables/useNewContentDetector'
import { usePlaylistEditor } from '@/features/video/composables/usePlaylistEditor'
import { usePlaylistDeleteConfirm } from '@/features/video/composables/usePlaylistDeleteConfirm'
import { usePlaylistThumbnails } from '@/features/video/composables/usePlaylistThumbnails'
import { formatDate, formatDuration } from '@/shared/lib/dateFormat'
import { useUIStore } from '@/shared/stores/ui'
import type { PlaylistItem } from '@/features/video/types/playlist'

defineOptions({ name: 'PlaylistView' })

const router = useRouter()
const twoColumnRef = ref<{ scrollEl: HTMLElement | null } | null>(null)

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

const isHydratingSelection = ref(false)

// Silent probe of the active playlist's items — no state mutation. Playlist
// order is positional (reorderable), so detection is set-based: any item id
// that is not currently displayed counts as new (see hasNew/countOf below).
const fetchItemsSilent = async (): Promise<PlaylistItem[]> => {
  if (!activePlaylist.value) return []
  try {
    const data = await getPlaylistItems(activePlaylist.value.id)
    return data || []
  } catch {
    return []
  }
}

// Reddit-style new-content detection; apply reloads the active playlist.
const {
  visible: newContentVisible,
  count: newContentCount,
  apply: applyNewContent,
  reset: resetNewContent,
} = useNewContentDetector<PlaylistItem>({
  getKnownId: () => activePlaylistItems.value[0]?.id ?? null,
  fetchNewest: fetchItemsSilent,
  idOf: (item) => item.id,
  hasNew: (items) => {
    const knownIds = new Set(activePlaylistItems.value.map((item) => item.id))
    return items.some((item) => !knownIds.has(item.id))
  },
  countOf: (items) => {
    const knownIds = new Set(activePlaylistItems.value.map((item) => item.id))
    return items.filter((item) => !knownIds.has(item.id)).length
  },
  onApply: async () => {
    const playlistId = activePlaylist.value?.id
    if (playlistId == null) return
    await prependPreservingScroll(
      () => twoColumnRef.value?.scrollEl ?? null,
      () => { void loadAndSetPlaylist(playlistId) },
    )
  },
  isEnabled: () => (
    !!activePlaylist.value
    && activePlaylistItems.value.length > 0
    && !loadingItems.value
    && !isHydratingSelection.value
  ),
  getScrollContainer: () => twoColumnRef.value?.scrollEl ?? null,
})

// Switching playlists rebuilds the list — pending detection is stale then.
watch(() => activePlaylist.value?.id, () => resetNewContent())

// Top-bar search filters the sidebar list by name (client-side; the playlist
// set is fully loaded, so no server round-trip is needed).
const uiStore = useUIStore()
const playlistSearchQuery = computed(() => uiStore.getSearchQuery('playlists'))
const searchTrigger = computed(() => uiStore.getSearchTrigger('playlists'))
const visiblePlaylists = computed(() => {
  const keyword = playlistSearchQuery.value.trim().toLowerCase()
  if (!keyword) return playlists.value
  return playlists.value.filter((playlist) => (playlist.name || '').toLowerCase().includes(keyword))
})
watch(searchTrigger, () => {
  const keyword = playlistSearchQuery.value.trim().toLowerCase()
  if (keyword && activePlaylist.value && !visiblePlaylists.value.some((p) => p.id === activePlaylist.value?.id)) {
    // Keep a valid selection when the active playlist is filtered out.
    const first = visiblePlaylists.value[0]
    if (first) selectPlaylist(first.id)
  }
})

const playlistActionItems = computed(() => [
  { label: '编辑列表', appIcon: 'pencil' as const, command: openEditModal },
  { separator: true },
  {
    label: '删除列表',
    appIcon: 'trash' as const,
    danger: true,
    command: () => {
      if (activePlaylist.value) handleDelete(activePlaylist.value.id)
    },
  },
])

const activePlaylistDurationSeconds = computed(() => (
  activePlaylistItems.value.reduce((sum, item) => sum + Number(item.video?.duration || 0), 0)
))
const activePlaylistDurationLabel = computed(() => (
  activePlaylistDurationSeconds.value ? formatDuration(activePlaylistDurationSeconds.value) : '暂无时长'
))
// ponytail: cached 4-up thumbnail projection lives in usePlaylistThumbnails.
// Only the active playlist has its items loaded in memory; others render a
// placeholder until opened.
const { getPlaylistThumbnails } = usePlaylistThumbnails({ activePlaylist, activePlaylistItems })

const selectPlaylist = async (playlistId: number | string) => {
  if (activePlaylist.value && String(activePlaylist.value.id) === String(playlistId)) return

  isHydratingSelection.value = true
  try {
    await loadAndSetPlaylist(playlistId)
  } finally {
    isHydratingSelection.value = false
  }
}

// Selection sync: pick the preferred id if still present, else the current
// active, else the first available. Used after create/update/delete to keep the
// list pointed at a valid playlist.
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

// ponytail: create/edit-playlist form state machine lives in usePlaylistEditor.
// onSaved re-syncs selection to the just-saved playlist; declared after
// syncSelectionWithList so the callback can reference it directly.
const {
  editingPlaylist,
  formName,
  formDesc,
  editorOpen,
  openCreateModal,
  openEditModal,
  closeModal,
  handleEditorOpenChange,
  handleSave,
} = usePlaylistEditor({
  activePlaylist,
  create,
  update,
  onSaved: (playlist) => syncSelectionWithList(playlist.id),
})

// ponytail: delete-playlist confirm-dialog flow (stash target → confirm →
// remove → re-sync when the active one was deleted) lives in
// usePlaylistDeleteConfirm.
const {
  showDeleteConfirm,
  deleteTargetPlaylist,
  handleDelete,
  confirmDelete,
  handleDeleteConfirmOpenChange,
} = usePlaylistDeleteConfirm({
  playlists,
  isActive: (playlist) => !!activePlaylist.value && String(activePlaylist.value.id) === String(playlist.id),
  remove,
  onDeleted: (wasActive) => { if (wasActive) syncSelectionWithList() },
})

const playVideo = (item: PlaylistItem) => {
  if (item.video?.id) {
    rememberVideoPlaybackSeed(item.video)
    void prefetchDesktopPlaybackSource(item.video)
    setCurrentVideo(item.video.id)
    router.push(`/video/${item.video.id}`)
  }
}

const playAll = () => {
  if (activePlaylistItems.value.length > 0) {
    playVideo(activePlaylistItems.value[0])
  }
}

const handleRemoveVideo = async (item: PlaylistItem) => {
  if (!activePlaylist.value) return
  await removeVideo(activePlaylist.value.id, item.video_id)
}

onMounted(async () => {
  await reloadPlaylists()
})
</script>

<style scoped>
.playlist-workbench-content {
  display: flex;
  flex-direction: column;
  max-width: none;
  min-height: 100%;
  padding: var(--space-4) var(--space-5) var(--app-content-padding-bottom);
}

/* Full-page empty states stretch with the pane so the copy centers vertically
   instead of anchoring to a fixed 28rem block at the top. */
.playlist-workbench-content > .app-page-empty {
  flex: 1;
}

.playlist-workbench-content__new-content {
  margin-bottom: var(--space-4);
}

.playlist-editor-dialog {
  width: min(100%, 24rem);
}

.playlist-nav-item {
  min-height: 2.75rem;
  align-items: stretch;
  padding: 0.375rem;
  border-radius: var(--radius-md);
}

.playlist-nav-thumb {
  display: flex;
  width: 2.5rem;
  height: 2.5rem;
  flex: none;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: var(--radius-sm);
  background: var(--app-media-thumb-placeholder);
  isolation: isolate;
}

.playlist-nav-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  justify-content: center;
  gap: 0.2rem;
}

.playlist-nav-title-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.375rem;
}

.playlist-nav-title {
  min-width: 0;
  overflow: hidden;
  color: hsl(var(--foreground));
  font-size: var(--app-text-md);
  font-weight: 700;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.playlist-nav-badge {
  display: inline-flex;
  flex: none;
  align-items: center;
  border-radius: 999px;
  background: var(--app-selection-count-bg);
  padding: 0.125rem 0.35rem;
  color: var(--app-selection-count-fg);
  font-size: var(--app-text-badge-size);
  font-weight: 700;
  line-height: 1;
}

.playlist-nav-meta {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  font-weight: 500;
  line-height: 1.2;
}

.playlist-workspace {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  width: 100%;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-md);
  background: hsl(var(--card));
  padding: var(--space-4);
}

.playlist-table {
  min-width: 0;
}

.playlist-table-toolbar {
  display: none;
}

.playlist-queue-list {
  display: flex;
  flex-direction: column;
}

.playlist-table-head,
.playlist-item {
  display: grid;
  grid-template-columns: 2.5rem minmax(20rem, 1fr) minmax(7rem, 10rem) minmax(7rem, 9rem) minmax(4rem, 5.5rem) 2rem;
  align-items: center;
  column-gap: var(--space-4);
}

.playlist-table-head {
  min-height: 2rem;
  border-bottom: 1px solid hsl(var(--border));
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-xs);
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.playlist-item {
  min-height: 4.5rem;
  border: 1px solid transparent;
  border-bottom-color: hsl(var(--border));
  border-radius: 0;
  padding: 0.5rem 0;
  cursor: pointer;
  outline: none;
  transition:
    background-color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.playlist-item :deep(.app-content-row__content) {
  display: grid;
  grid-column: 1 / 6;
  grid-template-columns: 2.5rem minmax(20rem, 1fr) minmax(7rem, 10rem) minmax(7rem, 9rem) minmax(4rem, 5.5rem);
  align-items: center;
  column-gap: var(--space-4);
}

.playlist-item :deep(.app-content-row__actions) {
  grid-column: 6;
}

.playlist-item:hover,
.playlist-item:has(.app-content-row__primary:focus-visible) {
  border-color: transparent;
  border-bottom-color: hsl(var(--border));
  background: var(--app-row-hover-bg);
}

.playlist-item:has(.app-content-row__primary:focus-visible) {
  border-radius: var(--radius-md);
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.42);
}

.playlist-item.is-current {
  background: hsl(var(--foreground) / 0.08);
}

.playlist-item-index {
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-md);
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}

.playlist-item-play {
  display: none;
  color: hsl(var(--foreground));
}

.playlist-item:hover .playlist-item-index span,
.playlist-item:has(.app-content-row__primary:focus-visible) .playlist-item-index span,
.playlist-item.is-current .playlist-item-index span {
  display: none;
}

.playlist-item:hover .playlist-item-play,
.playlist-item:has(.app-content-row__primary:focus-visible) .playlist-item-play,
.playlist-item.is-current .playlist-item-play {
  display: block;
}

.playlist-item-media {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-3);
}

.playlist-row-thumb {
  position: relative;
  width: 6.25rem;
  aspect-ratio: 16 / 9;
  flex: none;
  overflow: hidden;
  border-radius: var(--radius-md);
  border: 0;
  background: var(--app-media-thumb-placeholder);
  isolation: isolate;
}

.playlist-item-copy {
  min-width: 0;
}

.playlist-item-title {
  overflow: hidden;
  color: hsl(var(--foreground));
  font-size: var(--app-text-base);
  font-weight: 650;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.playlist-item-meta {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.45rem;
  margin-top: 0.375rem;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  font-weight: 500;
  line-height: 1.3;
}

.playlist-item-site,
.playlist-item-added,
.playlist-item-duration {
  overflow: hidden;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-md);
  font-weight: 500;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.playlist-item-added,
.playlist-item-duration {
  justify-self: start;
}

.playlist-meta-dot {
  width: 0.1875rem;
  height: 0.1875rem;
  flex: none;
  border-radius: 999px;
  background: hsl(var(--muted-foreground) / 0.55);
}

.playlist-item-remove {
  opacity: 0;
  transition:
    opacity var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.playlist-item:hover .playlist-item-remove,
.playlist-item:focus-within .playlist-item-remove {
  opacity: 1;
}

.playlist-item-remove:hover,
.playlist-item-remove:focus-visible {
  color: hsl(var(--destructive));
}

@media (hover: none), (prefers-reduced-motion: reduce) {
  .playlist-item-remove {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .playlist-item-remove {
    transition: none;
  }
}

.playlist-skeleton-list {
  display: grid;
  gap: var(--space-2);
}

@media (max-width: 1280px) {
  .playlist-table-head,
  .playlist-item {
    grid-template-columns: 2.75rem minmax(0, 1fr) 2rem;
  }

  .playlist-item :deep(.app-content-row__content) {
    grid-column: 1 / 3;
    grid-template-columns: 2.75rem minmax(0, 1fr);
  }

  .playlist-item :deep(.app-content-row__actions) {
    grid-column: 3;
  }

  .playlist-item-site,
  .playlist-item-added,
  .playlist-item-duration,
  .playlist-table-head span:nth-child(3),
  .playlist-table-head span:nth-child(4),
  .playlist-table-head span:nth-child(5) {
    display: none;
  }
}
</style>
