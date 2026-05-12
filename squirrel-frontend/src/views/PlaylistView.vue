<template>
  <AppPageShell variant="compact">
    <div class="flex h-full overflow-hidden bg-background text-foreground">
      <aside class="hidden w-72 shrink-0 flex-col border-r border-border/50 bg-background lg:flex">
        <div class="flex h-14 shrink-0 items-center justify-between border-b border-border/50 px-4">
          <div class="min-w-0">
            <h1 class="truncate text-sm font-semibold">播放列表</h1>
            <p class="mt-0.5 text-xs text-muted-foreground">{{ playlists.length }} 个列表</p>
          </div>
          <Button variant="ghost" size="icon" class="h-8 w-8 rounded-md" @click="openCreateModal">
            <AppIcon name="plus" class="h-4 w-4" />
          </Button>
        </div>

        <nav class="flex-1 space-y-1 overflow-y-auto p-2 custom-scrollbar">
          <button
            v-for="playlist in playlists"
            :key="playlist.id"
            class="group flex h-12 w-full items-center gap-2.5 rounded-md px-2 text-left transition-colors"
            :class="String(activePlaylist?.id) === String(playlist.id) ? 'bg-accent text-foreground' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'"
            @click="selectPlaylist(playlist.id)"
          >
            <div class="h-8 w-8 shrink-0 overflow-hidden rounded-md bg-muted">
              <img
                v-if="getPlaylistThumbnails(playlist).length"
                :src="getPlaylistThumbnails(playlist)[0]"
                referrerpolicy="no-referrer"
                class="h-full w-full object-cover"
              >
              <div v-else class="flex h-full w-full items-center justify-center text-muted-foreground">
                <AppIcon name="playlistVideo" class="h-4 w-4" />
              </div>
            </div>
            <div class="min-w-0 flex-1">
              <div class="truncate text-sm font-medium">{{ playlist.name }}</div>
              <div class="mt-0.5 text-xs text-muted-foreground">{{ playlist.video_count }} 个视频</div>
            </div>
          </button>
        </nav>
      </aside>

      <main class="flex min-w-0 flex-1 flex-col bg-background">
        <header class="flex h-14 shrink-0 items-center justify-between border-b border-border/50 px-4 lg:px-6">
          <div class="min-w-0">
            <h2 class="truncate text-base font-semibold">{{ activePlaylist?.name || '播放列表' }}</h2>
            <p class="mt-0.5 text-xs text-muted-foreground">
              {{ activePlaylist ? `${activePlaylistItems.length} 个视频 · ${activePlaylistDurationLabel}` : `${playlists.length} 个列表` }}
            </p>
          </div>

          <div class="flex shrink-0 items-center gap-1">
            <Button v-if="activePlaylistItems.length" size="sm" class="h-8 rounded-md px-3" @click="playAll">
              <AppIcon name="play" class="h-4 w-4 fill-current" />
              播放全部
            </Button>
            <Button variant="ghost" size="icon" class="h-9 w-9 rounded-md" @click="reloadPlaylists">
              <AppIcon name="refresh" class="h-4 w-4" :class="{ 'animate-spin': loading || isHydratingSelection }" />
            </Button>
            <DropdownMenu v-if="activePlaylist && !activePlaylist.is_default">
              <DropdownMenuTrigger as-child>
                <Button variant="ghost" size="icon" class="h-9 w-9 rounded-md">
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
            <Button variant="ghost" size="icon" class="h-9 w-9 rounded-md lg:hidden" @click="openCreateModal">
              <AppIcon name="plus" class="h-4 w-4" />
            </Button>
          </div>
        </header>

        <div v-if="playlists.length" class="border-b border-border/50 p-2 lg:hidden">
          <div class="flex gap-2 overflow-x-auto custom-scrollbar">
            <button
              v-for="playlist in playlists"
              :key="playlist.id"
              class="h-8 shrink-0 rounded-md px-3 text-sm font-medium transition-colors"
              :class="String(activePlaylist?.id) === String(playlist.id) ? 'bg-accent text-foreground' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'"
              @click="selectPlaylist(playlist.id)"
            >
              {{ playlist.name }}
            </button>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto custom-scrollbar">
          <div class="mx-auto w-full max-w-[1200px] p-4 lg:p-6">
            <div v-if="loading && !playlists.length" class="space-y-4">
              <div class="h-28 animate-pulse rounded-lg bg-accent/30" />
              <div class="space-y-2">
                <div v-for="i in 6" :key="i" class="h-16 animate-pulse rounded-lg bg-accent/25" />
              </div>
            </div>

            <div v-else-if="!playlists.length" class="flex min-h-[24rem] flex-col items-center justify-center text-center">
              <AppIcon name="playlistVideo" class="h-9 w-9 text-muted-foreground/30" />
              <h2 class="mt-4 text-sm font-semibold">{{ error ? '加载失败' : '暂无播放列表' }}</h2>
              <p v-if="!error" class="mt-1 text-sm text-muted-foreground">创建播放列表后会显示在这里。</p>
              <Button v-if="!error" class="mt-4 h-9 rounded-md px-3" @click="openCreateModal">
                <AppIcon name="plus" class="h-4 w-4" />
                新建播放列表
              </Button>
              <Button v-else variant="outline" class="mt-4 h-9 rounded-md px-3" @click="reloadPlaylists">重试</Button>
            </div>

            <div v-else-if="activePlaylist" class="space-y-6">
              <section class="flex flex-col gap-4 border-b border-border/50 pb-6 sm:flex-row sm:items-end">
                <div class="h-24 w-24 shrink-0 overflow-hidden rounded-lg bg-muted">
                  <div v-if="getPlaylistThumbnails(activePlaylist).length >= 4" class="grid h-full w-full grid-cols-2 grid-rows-2 gap-px">
                    <img
                      v-for="(thumb, i) in getPlaylistThumbnails(activePlaylist).slice(0, 4)"
                      :key="i"
                      :src="thumb"
                      referrerpolicy="no-referrer"
                      class="h-full w-full object-cover"
                    >
                  </div>
                  <img
                    v-else-if="getPlaylistThumbnails(activePlaylist).length > 0"
                    :src="getPlaylistThumbnails(activePlaylist)[0]"
                    referrerpolicy="no-referrer"
                    class="h-full w-full object-cover"
                  >
                  <div v-else class="flex h-full w-full items-center justify-center text-muted-foreground">
                    <AppIcon name="playlistVideo" class="h-8 w-8" />
                  </div>
                </div>

                <div class="min-w-0 flex-1">
                  <div class="text-xs font-medium text-muted-foreground">播放列表</div>
                  <h1 class="mt-1 truncate text-lg font-semibold">{{ activePlaylist.name }}</h1>
                  <p v-if="activePlaylist.description" class="mt-2 line-clamp-2 max-w-3xl text-sm leading-relaxed text-muted-foreground">
                    {{ activePlaylist.description }}
                  </p>
                  <div class="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span>我的媒体库</span>
                    <span class="h-1 w-1 rounded-full bg-border" />
                    <span>{{ activePlaylistItems.length }} 个视频</span>
                    <span class="h-1 w-1 rounded-full bg-border" />
                    <span>{{ activePlaylistDurationLabel }}</span>
                  </div>
                </div>
              </section>

              <div v-if="loadingItems || isHydratingSelection" class="space-y-2">
                <div v-for="i in 6" :key="i" class="h-16 animate-pulse rounded-lg bg-accent/25" />
              </div>

              <div v-else-if="!activePlaylistItems.length" class="flex min-h-[20rem] flex-col items-center justify-center text-center">
                <AppIcon name="playlistVideo" class="h-9 w-9 text-muted-foreground/30" />
                <h3 class="mt-4 text-sm font-semibold">暂无视频</h3>
                <p class="mt-1 text-sm text-muted-foreground">添加到列表的视频会显示在这里。</p>
              </div>

              <div v-else class="space-y-1">
                <div class="hidden h-8 grid-cols-[2rem_minmax(0,1fr)_8rem_8rem_3rem] items-center gap-3 border-b border-border/50 px-2 text-xs font-medium text-muted-foreground md:grid">
                  <div>#</div>
                  <div>标题</div>
                  <div>来源</div>
                  <div>添加时间</div>
                  <div />
                </div>

                <article
                  v-for="(item, index) in activePlaylistItems"
                  :key="item.id"
                  class="group grid cursor-pointer grid-cols-[2rem_minmax(0,1fr)_2rem] items-center gap-3 rounded-lg border border-transparent px-2 py-2 transition-colors hover:border-border/50 hover:bg-accent/40 md:grid-cols-[2rem_minmax(0,1fr)_8rem_8rem_3rem]"
                  :class="{ 'text-primary': currentVideoId && String(item.video_id) === String(currentVideoId) }"
                  @click="playVideo(item)"
                >
                  <div class="flex items-center justify-center text-sm text-muted-foreground">
                    <span class="group-hover:hidden">{{ index + 1 }}</span>
                    <AppIcon name="play" class="hidden h-4 w-4 fill-current text-foreground group-hover:block" />
                  </div>

                  <div class="flex min-w-0 items-center gap-3">
                    <div class="relative aspect-video w-20 shrink-0 overflow-hidden rounded-md bg-muted">
                      <img
                        v-if="item.video?.thumbnail"
                        :src="item.video.thumbnail"
                        referrerpolicy="no-referrer"
                        class="h-full w-full object-contain"
                      >
                      <div v-else class="flex h-full w-full items-center justify-center text-muted-foreground">
                        <AppIcon name="film" class="h-5 w-5" />
                      </div>
                      <span v-if="item.video?.duration" class="absolute bottom-1 right-1 inline-flex h-5 items-center rounded-md bg-black/65 px-1.5 text-[10px] font-medium text-white tabular-nums backdrop-blur-sm">
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
                    size="icon"
                    class="h-8 w-8 rounded-md opacity-0 transition-opacity group-hover:opacity-100"
                    @click.stop="handleRemoveVideo(item)"
                  >
                    <AppIcon name="close" class="h-4 w-4" />
                  </Button>
                </article>
              </div>
            </div>

            <div v-else class="flex min-h-[24rem] flex-col items-center justify-center text-center">
              <AppIcon name="panelOpen" class="h-9 w-9 text-muted-foreground/30" />
              <h2 class="mt-4 text-sm font-semibold">选择播放列表</h2>
              <p class="mt-1 text-sm text-muted-foreground">选择左侧列表后查看内容。</p>
            </div>
          </div>
        </div>
      </main>
    </div>

    <Dialog :open="showDeleteConfirm" @update:open="handleDeleteConfirmOpenChange">
      <DialogContent class="max-w-sm overflow-hidden rounded-lg p-0">
        <DialogHeader class="border-b border-border/50 p-5 text-left">
          <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-md bg-destructive/10 text-destructive">
            <AppIcon name="trash" class="h-5 w-5" />
          </div>
          <DialogTitle class="text-base font-semibold">删除播放列表？</DialogTitle>
          <DialogDescription class="text-sm leading-relaxed text-muted-foreground">
            {{ deleteTargetPlaylist ? `确定要删除 "${deleteTargetPlaylist.name}" 吗？此操作不会删除视频本身。` : '确定要删除这个播放列表吗？' }}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter class="gap-2 bg-muted/30 p-4">
          <Button variant="outline" class="h-9 rounded-md" @click="closeDeleteConfirm">取消</Button>
          <Button variant="destructive" class="h-9 rounded-md" @click="confirmDelete">确认删除</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog :open="editorOpen" @update:open="handleEditorOpenChange">
      <DialogContent class="max-w-sm overflow-hidden rounded-lg p-0">
        <DialogHeader class="border-b border-border/50 p-5 text-left">
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
          <Button variant="outline" class="h-9 rounded-md" @click="closeModal">取消</Button>
          <Button class="h-9 rounded-md" :disabled="!formName.trim()" @click="handleSave">
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
import AppIcon from '@/components/common/AppIcon.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import { Button } from '@/components/ui/button'
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

  const items = activePlaylist.value && String(activePlaylist.value.id) === String(playlist.id)
    ? activePlaylistItems.value
    : []

  const thumbs = items
    .map(item => item.video?.thumbnail)
    .filter((thumbnail): thumbnail is string => !!thumbnail)
    .slice(0, 4)

  if (thumbs.length > 0) {
    playlistThumbnails.value.set(playlist.id, thumbs)
  }
  return thumbs
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

onMounted(async () => {
  await reloadPlaylists()
})
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(var(--primary), 0.1); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(var(--primary), 0.2); }
</style>
