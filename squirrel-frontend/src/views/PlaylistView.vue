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
          :title="error ? '加载失败' : '开启你的视听之旅'"
          :copy="error ? '' : '创建一个播放列表，把心动的视频收集在一起'"
        >
          <template #actions>
            <Button v-if="!error" size="lg" class="rounded-full px-8" @click="openCreateModal">
              <Plus class="mr-2" />
              <span>新建播放列表</span>
            </Button>
            <Button v-else variant="outline" @click="reloadPlaylists">重试</Button>
          </template>
        </AppEmptyState>

        <div v-else class="playlist-layout">
          <!-- Sidebar: Library -->
          <aside class="playlist-sidebar">
            <div class="sidebar-header">
              <h2 class="sidebar-title">媒体库</h2>
              <Button variant="ghost" size="icon" class="sidebar-add-btn" @click="openCreateModal">
                <Plus />
              </Button>
            </div>

            <nav class="sidebar-nav scrollbar-hide">
              <button
                v-for="playlist in playlists"
                :key="playlist.id"
                class="sidebar-item"
                :class="{ 'is-active': String(activePlaylist?.id) === String(playlist.id) }"
                @click="selectPlaylist(playlist.id)"
              >
                <div class="sidebar-item__cover">
                  <template v-if="getPlaylistThumbnails(playlist).length">
                    <img
                      :src="getPlaylistThumbnails(playlist)[0]"
                      referrerpolicy="no-referrer"
                      class="sidebar-item__img"
                      @error="handleCoverImageError"
                    >
                  </template>
                  <div v-else class="sidebar-item__fallback">
                    <ListVideo />
                  </div>
                </div>
                <div class="sidebar-item__info">
                  <span class="sidebar-item__name">{{ playlist.name }}</span>
                  <span class="sidebar-item__meta">{{ playlist.video_count }} 个视频</span>
                </div>
              </button>
            </nav>
          </aside>

          <!-- Main Content: Detail -->
          <main class="playlist-main">
            <Transition name="fade-slide" mode="out-in">
              <div v-if="activePlaylist" :key="activePlaylist.id" class="playlist-detail-view">
                <!-- Header Section -->
                <header class="playlist-header">
                  <div class="playlist-header__bg">
                    <img
                      v-if="activePlaylistItems[0]?.video?.thumbnail"
                      :src="activePlaylistItems[0].video.thumbnail"
                      referrerpolicy="no-referrer"
                      class="playlist-header__bg-img"
                    >
                  </div>
                  
                  <div class="playlist-header__content">
                    <div class="playlist-header__cover">
                      <!-- 只有当缩略图 >= 4 时才显示拼贴，否则显示单张大图 -->
                      <div v-if="getPlaylistThumbnails(activePlaylist).length >= 4" class="playlist-mosaic">
                        <img
                          v-for="(thumb, i) in getPlaylistThumbnails(activePlaylist).slice(0, 4)"
                          :key="i"
                          :src="thumb"
                          referrerpolicy="no-referrer"
                          class="playlist-mosaic__img"
                        >
                      </div>
                      <div v-else-if="getPlaylistThumbnails(activePlaylist).length > 0" class="playlist-header__single">
                        <img
                          :src="getPlaylistThumbnails(activePlaylist)[0]"
                          referrerpolicy="no-referrer"
                          class="playlist-header__single-img"
                        >
                      </div>
                      <div v-else class="playlist-header__fallback">
                        <ListVideo :size="48" />
                      </div>
                    </div>

                    <div class="playlist-header__info">
                      <div class="playlist-header__type">播放列表</div>
                      <h1 class="playlist-header__title">{{ activePlaylist.name }}</h1>
                      <p v-if="activePlaylist.description" class="playlist-header__desc">
                        {{ activePlaylist.description }}
                      </p>
                      <div class="playlist-header__meta">
                        <span class="playlist-header__author">我的媒体库</span>
                        <span class="playlist-header__dot">•</span>
                        <span>{{ activePlaylistItems.length }} 个视频</span>
                        <span class="playlist-header__dot">•</span>
                        <span>{{ activePlaylistDurationLabel }}</span>
                      </div>

                      <div class="playlist-header__actions">
                        <Button size="lg" class="rounded-full px-8 shadow-lg shadow-primary/20" @click="playAll">
                          <Play class="mr-2 fill-current" />
                          <span>播放全部</span>
                        </Button>
                        
                        <DropdownMenu v-if="!activePlaylist.is_default">
                          <DropdownMenuTrigger as-child>
                            <Button variant="secondary" size="icon" class="rounded-full">
                              <MoreHorizontal />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="start" class="w-48">
                            <DropdownMenuItem @click="openEditModal">
                              <Pencil class="mr-2 h-4 w-4" />
                              编辑列表
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem class="text-destructive focus:text-destructive" @click="handleDelete(activePlaylist!.id)">
                              <Trash2 class="mr-2 h-4 w-4" />
                              删除列表
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>
                  </div>
                </header>

                <!-- List Section -->
                <div class="playlist-items-container">
                  <div v-if="loadingItems || isHydratingSelection" class="playlist-items-loading">
                    <LoadingIndicator :loading="true" />
                  </div>

                  <div v-else-if="!activePlaylistItems.length" class="playlist-items-empty">
                    <div class="empty-visual">
                      <ListVideo :size="64" />
                    </div>
                    <h3>这里空空如也</h3>
                    <p>快去添加一些精彩视频吧</p>
                  </div>

                  <div v-else class="playlist-items-list">
                    <div class="list-header">
                      <div class="list-header__index">#</div>
                      <div class="list-header__title">标题</div>
                      <div class="list-header__site">来源</div>
                      <div class="list-header__date">添加时间</div>
                      <div class="list-header__actions"></div>
                    </div>

                    <TransitionGroup name="list-stagger">
                      <article
                        v-for="(item, index) in activePlaylistItems"
                        :key="item.id"
                        class="video-row"
                        :class="{ 'is-playing': currentVideoId && String(item.video_id) === String(currentVideoId) }"
                        @click="playVideo(item)"
                      >
                        <div class="video-row__index">
                          <span class="index-num">{{ index + 1 }}</span>
                          <Play class="play-icon fill-current" />
                        </div>

                        <div class="video-row__main">
                          <div class="video-row__thumb">
                            <img
                              v-if="item.video?.thumbnail"
                              :src="item.video.thumbnail"
                              referrerpolicy="no-referrer"
                              @error="handlePlaylistItemImageError"
                            >
                            <div v-else class="thumb-fallback"><Film /></div>
                            <span v-if="item.video?.duration" class="video-row__duration">
                              {{ formatDuration(item.video.duration) }}
                            </span>
                          </div>
                          <div class="video-row__info">
                            <span class="video-row__title">{{ item.video?.title || '未知视频' }}</span>
                          </div>
                        </div>

                        <div class="video-row__site">
                          <Badge variant="outline" class="font-normal">{{ item.video?.site || '未知' }}</Badge>
                        </div>

                        <div class="video-row__date">
                          {{ formatDate(item.added_at) }}
                        </div>

                        <div class="video-row__actions">
                          <Button
                            variant="ghost"
                            size="icon"
                            class="h-8 w-8 rounded-full opacity-0"
                            @click.stop="handleRemoveVideo(item)"
                          >
                            <X class="h-4 w-4" />
                          </Button>
                        </div>
                      </article>
                    </TransitionGroup>
                  </div>
                </div>
              </div>

              <!-- Blank State -->
              <div v-else class="playlist-blank-state">
                <div class="blank-visual">
                  <div class="visual-circle"></div>
                  <PanelRightOpen :size="48" />
                </div>
                <h2>选择一个播放列表</h2>
                <p>查看并管理你收藏的视频内容</p>
              </div>
            </Transition>
          </main>
        </div>
      </div>
    </div>

    <!-- Modals & Dialogs (Keep existing logic but refine visuals if needed) -->
    <Dialog :open="showDeleteConfirm" @update:open="handleDeleteConfirmOpenChange">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>删除播放列表</DialogTitle>
          <DialogDescription>
            {{ deleteTargetPlaylist ? `确定要删除 "${deleteTargetPlaylist.name}" 吗？此操作将永久移除该列表，但不会删除视频本身。` : '确定要删除这个播放列表吗？' }}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="ghost" @click="closeDeleteConfirm">取消</Button>
          <Button variant="destructive" @click="confirmDelete">确认删除</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog :open="editorOpen" @update:open="handleEditorOpenChange">
      <DialogContent class="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{{ editingPlaylist ? '编辑列表信息' : '创建新列表' }}</DialogTitle>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid gap-2">
            <label for="name" class="text-sm font-medium">列表名称</label>
            <Input id="name" v-model="formName" placeholder="例如：我的最爱" @keyup.enter="handleSave" />
          </div>
          <div class="grid gap-2">
            <label for="description" class="text-sm font-medium">描述</label>
            <Textarea id="description" v-model="formDesc" placeholder="添加一些关于这个列表的说明..." rows="3" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" @click="closeModal">取消</Button>
          <Button :disabled="!formName.trim()" @click="handleSave">保存更改</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, ListVideo, Play, Trash2, MoreHorizontal, Pencil, Film, X, PanelRightOpen } from 'lucide-vue-next'
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
  DropdownMenuSeparator,
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

  // If this is the active playlist, we use the active items which are already loaded
  const items = activePlaylist.value && String(activePlaylist.value.id) === String(playlist.id)
    ? activePlaylistItems.value
    : []
  
  // If we have items, use them. Otherwise, try to find thumbnails from anywhere else? 
  // For now, just use what we have in active items or empty.
  const thumbs = items
    .map(item => item.video?.thumbnail)
    .filter((t): t is string => !!t)
    .slice(0, 4)
  
  if (thumbs.length > 0) {
    playlistThumbnails.value.set(playlist.id, thumbs)
  }
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
  if (activePlaylist.value && String(activePlaylist.value.id) === String(playlistId)) return
  
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

const playAll = () => {
  if (activePlaylistItems.value.length > 0) {
    playVideo(activePlaylistItems.value[0])
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
