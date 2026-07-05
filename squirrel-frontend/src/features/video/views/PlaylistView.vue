<template>
  <AppPageShell variant="compact">
    <div class="app-workbench">
      <aside class="app-workbench__sidebar">
        <div class="app-workbench__sidebar-header">
          <div class="min-w-0">
            <h1 class="app-h3 truncate">播放列表</h1>
            <p class="mt-0.5 text-xs text-muted-foreground">{{ playlists.length }} 个列表</p>
          </div>
          <Button
            size="icon-sm"
            title="新建播放列表"
            aria-label="新建播放列表"
            @click="openCreateModal"
          >
            <AppIcon name="plus" class="h-4 w-4" />
          </Button>
        </div>

        <nav class="playlist-nav custom-scrollbar">
          <Button
            v-for="playlist in playlists"
            :key="playlist.id"
            variant="ghost"
            size="sm"
            class="playlist-nav-item group"
            :class="{ 'playlist-nav-item--active': String(activePlaylist?.id) === String(playlist.id) }"
            :aria-current="String(activePlaylist?.id) === String(playlist.id) ? 'true' : undefined"
            @click="selectPlaylist(playlist.id)"
          >
            <div class="app-compact-thumb">
              <VideoThumbnail
                v-if="getPlaylistThumbnails(playlist).length"
                :src="getPlaylistThumbnails(playlist)[0]"
                fit="cover"
              />
              <div v-else class="flex h-full w-full items-center justify-center text-muted-foreground">
                <AppIcon name="playlistVideo" class="h-4 w-4" />
              </div>
            </div>
            <div class="min-w-0 flex-1">
              <div class="truncate text-sm font-medium">{{ playlist.name }}</div>
              <div class="mt-0.5 text-xs text-muted-foreground">{{ playlist.video_count }} 个视频</div>
            </div>
          </Button>
        </nav>
      </aside>

      <main class="app-workbench__main">
        <header class="app-workbench__header">
          <div class="min-w-0">
            <h2 class="app-h2 truncate">{{ activePlaylist?.name || '播放列表' }}</h2>
            <p class="mt-0.5 text-xs text-muted-foreground">
              {{ activePlaylist ? `${activePlaylistItems.length} 个视频 · ${activePlaylistDurationLabel}` : `${playlists.length} 个列表` }}
            </p>
          </div>

          <div class="flex shrink-0 items-center gap-1.5">
            <Button v-if="activePlaylistItems.length" size="sm" @click="playAll">
              <AppIcon name="play" class="h-4 w-4 fill-current" />
              播放全部
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              :disabled="loading || isHydratingSelection"
              title="刷新"
              aria-label="刷新"
              @click="reloadPlaylists"
            >
              <AppSpinner v-if="loading || isHydratingSelection" size="sm" />
              <AppIcon v-else name="refresh" class="h-4 w-4" />
            </Button>
            <DropdownMenu v-if="activePlaylist && !activePlaylist.is_default">
              <DropdownMenuTrigger as-child>
                <Button variant="ghost" size="icon-sm" aria-label="更多操作">
                  <AppIcon name="more" class="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" class="w-40">
                <DropdownMenuItem @click="openEditModal">
                  <AppIcon name="pencil" class="mr-2 h-4 w-4" />
                  编辑列表
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem class="text-destructive focus:text-destructive" @click="handleDelete(activePlaylist.id)">
                  <AppIcon name="trash" class="mr-2 h-4 w-4" />
                  删除列表
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <div class="app-workbench__scroll custom-scrollbar">
          <div class="app-workbench__content playlist-content">
            <div v-if="loading && !playlists.length" class="space-y-4">
              <AppSkeleton height="7rem" rounded="var(--radius-lg)" shimmer />
              <div class="space-y-2">
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
                  <Button v-else variant="outline" @click="reloadPlaylists">重试</Button>
                </template>
              </AppEmptyState>
            </div>

            <div v-else-if="activePlaylist" class="space-y-6">
              <section class="app-divider-bottom flex flex-col gap-4 pb-6 sm:flex-row sm:items-end">
                <div class="h-24 w-24 shrink-0 overflow-hidden rounded-lg bg-muted">
                  <div v-if="getPlaylistThumbnails(activePlaylist).length >= 4" class="grid h-full w-full grid-cols-2 grid-rows-2 gap-px">
                    <VideoThumbnail
                      v-for="(thumb, i) in getPlaylistThumbnails(activePlaylist).slice(0, 4)"
                      :key="i"
                      :src="thumb"
                      fit="cover"
                    />
                  </div>
                  <VideoThumbnail
                    v-else-if="getPlaylistThumbnails(activePlaylist).length > 0"
                    :src="getPlaylistThumbnails(activePlaylist)[0]"
                    fit="cover"
                  />
                  <div v-else class="flex h-full w-full items-center justify-center text-muted-foreground">
                    <AppIcon name="playlistVideo" class="h-6 w-6" />
                  </div>
                </div>

                <div class="min-w-0 flex-1">
                  <div class="text-xs font-medium text-muted-foreground">播放列表</div>
                  <h1 class="app-h2 mt-1 truncate">{{ activePlaylist.name }}</h1>
                  <p v-if="activePlaylist.description" class="mt-2 line-clamp-2 max-w-3xl text-sm leading-relaxed text-muted-foreground">
                    {{ activePlaylist.description }}
                  </p>
                  <div class="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span>我的媒体库</span>
                    <span class="h-3 w-px bg-border" />
                    <span>{{ activePlaylistItems.length }} 个视频</span>
                    <span class="h-3 w-px bg-border" />
                    <span>{{ activePlaylistDurationLabel }}</span>
                  </div>
                </div>
              </section>

              <div v-if="loadingItems || isHydratingSelection" class="space-y-2">
                <AppSkeleton v-for="i in 6" :key="i" height="4rem" rounded="var(--radius-lg)" shimmer />
              </div>

              <div v-else-if="!activePlaylistItems.length" class="app-page-empty app-page-empty--compact">
                <AppEmptyState variant="plain" icon="playlistVideo" title="暂无视频" copy="添加到列表的视频会显示在这里。" />
              </div>

              <div v-else class="space-y-1">
                <div class="playlist-table-head app-divider-bottom hidden grid-cols-[2rem_minmax(0,1fr)_8rem_8rem_3rem] items-center gap-3 px-2 text-xs font-medium text-muted-foreground md:grid">
                  <div>#</div>
                  <div>标题</div>
                  <div>来源</div>
                  <div>添加时间</div>
                  <div />
                </div>

                <article
                  v-for="(item, index) in activePlaylistItems"
                  :key="item.id"
                  class="group grid cursor-pointer grid-cols-[2rem_minmax(0,1fr)_2rem] items-center gap-3 rounded-lg border border-transparent px-2 py-2 outline-none transition-colors hover:border-border/50 hover:bg-accent/40 focus-visible:border-border/50 focus-visible:bg-accent/40 focus-visible:ring-2 focus-visible:ring-ring/40 md:grid-cols-[2rem_minmax(0,1fr)_8rem_8rem_3rem]"
                  :class="{ 'text-primary': currentVideoId && String(item.video_id) === String(currentVideoId) }"
                  role="button"
                  tabindex="0"
                  @click="playVideo(item)"
                  @keydown.enter.prevent="playVideo(item)"
                  @keydown.space.prevent="playVideo(item)"
                >
                  <div class="flex items-center justify-center text-sm text-muted-foreground">
                    <span class="group-hover:hidden">{{ index + 1 }}</span>
                    <AppIcon name="play" class="hidden h-4 w-4 fill-current text-foreground group-hover:block" />
                  </div>

                  <div class="flex min-w-0 items-center gap-3">
                    <div class="relative aspect-video w-20 shrink-0 overflow-hidden rounded-md bg-muted">
                      <VideoThumbnail
                        v-if="item.video?.thumbnail"
                        :src="item.video.thumbnail"
                        fit="contain"
                      />
                      <div v-else class="flex h-full w-full items-center justify-center text-muted-foreground">
                        <AppIcon name="film" class="h-5 w-5" />
                      </div>
                      <span v-if="item.video?.duration" class="playlist-duration-badge">
                        {{ formatDuration(item.video.duration) }}
                      </span>
                    </div>
                    <div class="min-w-0">
                      <div class="truncate text-sm font-medium text-foreground">{{ item.video?.title || '未知视频' }}</div>
                      <div class="mt-1 text-xs text-muted-foreground md:hidden">
                        {{ item.video?.site || '未知' }} · {{ formatDate(item.added_at) }}
                      </div>
                    </div>
                  </div>

                  <div class="hidden truncate text-sm text-muted-foreground md:block">{{ item.video?.site || '未知' }}</div>
                  <div class="hidden text-sm text-muted-foreground md:block">{{ formatDate(item.added_at) }}</div>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    class="opacity-0 transition-opacity group-hover:opacity-100"
                    @click.stop="handleRemoveVideo(item)"
                  >
                    <AppIcon name="close" class="h-4 w-4" />
                  </Button>
                </article>
              </div>
            </div>

            <div v-else class="app-page-empty app-page-empty--compact">
              <AppEmptyState variant="plain" icon="panelOpen" title="选择播放列表" copy="选择左侧列表后查看内容。" />
            </div>
          </div>
        </div>
      </main>
    </div>

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
      <DialogContent class="max-w-sm overflow-hidden rounded-lg p-0">
        <DialogHeader class="app-divider-bottom p-5 text-left">
          <DialogTitle class="text-base font-semibold">{{ editingPlaylist ? '编辑列表' : '新建播放列表' }}</DialogTitle>
        </DialogHeader>
        <div class="space-y-4 p-5">
          <div class="space-y-2">
            <label for="name" class="text-sm font-medium">列表名称</label>
            <Input id="name" v-model="formName" placeholder="例如：我的最爱" @keyup.enter="handleSave" />
          </div>
          <div class="space-y-2">
            <label for="description" class="text-sm font-medium">描述</label>
            <Textarea id="description" v-model="formDesc" placeholder="添加一些关于这个列表的说明" rows="3" />
          </div>
        </div>
        <DialogFooter class="gap-2 bg-muted/30 p-4">
          <Button variant="outline" @click="closeModal">取消</Button>
          <Button :disabled="!formName.trim()" @click="handleSave">
            {{ editingPlaylist ? '保存' : '创建' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/shared/ui/dropdown-menu'
import { Input } from '@/shared/ui/input'
import { Textarea } from '@/shared/ui/textarea'
import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import { usePlaylist } from '@/features/video/composables/usePlaylist'
import { usePlaylistEditor } from '@/features/video/composables/usePlaylistEditor'
import { usePlaylistDeleteConfirm } from '@/features/video/composables/usePlaylistDeleteConfirm'
import { usePlaylistThumbnails } from '@/features/video/composables/usePlaylistThumbnails'
import { formatDate, formatDuration } from '@/shared/lib/dateFormat'
import type { PlaylistItem } from '@/features/video/types/playlist'

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

const isHydratingSelection = ref(false)

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
.playlist-table-head {
  min-height: 2rem;
}

.playlist-nav {
  flex: 1;
  overflow-y: auto;
  padding: 0.625rem;
}

.playlist-nav-item {
  display: flex;
  width: 100%;
  min-height: 3rem;
  align-items: center;
  gap: 0.625rem;
  border: 0;
  border-radius: 0.5rem;
  background: transparent;
  padding: 0.375rem 0.5rem;
  color: hsl(var(--muted-foreground));
  text-align: left;
  outline: none;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.playlist-nav-item:hover,
.playlist-nav-item--active {
  background: hsl(var(--accent) / 0.58);
  color: hsl(var(--foreground));
}

.playlist-content {
  --app-workbench-content-width: 1200px;
}

.playlist-duration-badge {
  position: absolute;
  right: 0.25rem;
  bottom: 0.25rem;
  display: inline-flex;
  height: 1.25rem;
  align-items: center;
  border-radius: 0.375rem;
  background: hsl(0 0% 0% / 0.72);
  padding: 0 0.375rem;
  color: white;
  font-size: 0.625rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

@media (prefers-reduced-motion: reduce) {
  .playlist-nav-item {
    transition: none;
  }
}
</style>
