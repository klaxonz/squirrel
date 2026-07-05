<template>
  <Button
    variant="outline"
    size="sm"
    class="music-create-playlist-btn"
    :class="{ 'music-create-playlist-btn--compact': compact }"
    @click="showDialog = true"
  >
    <AppIcon name="plus" class="h-3.5 w-3.5" />
    <span>创建歌单</span>
  </Button>

  <Dialog v-model:open="showDialog">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>创建歌单</DialogTitle>
        <DialogDescription>
          输入歌单名称，创建一个新的歌单
        </DialogDescription>
      </DialogHeader>
      <div class="flex flex-col gap-4 py-4">
        <Input
          v-model="playlistName"
          placeholder="歌单名称"
          maxlength="20"
          @keyup.enter="handleCreate"
        />
      </div>
      <DialogFooter>
        <Button variant="outline" @click="showDialog = false">取消</Button>
        <Button :disabled="!playlistName.trim() || creating" @click="handleCreate">
          {{ creating ? '创建中...' : '创建' }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/shared/ui/dialog'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'

withDefaults(defineProps<{
  compact?: boolean
}>(), {
  compact: false,
})

const emit = defineEmits<{
  create: [name: string]
}>()

const showDialog = ref(false)
const playlistName = ref('')
const creating = ref(false)

async function handleCreate() {
  const name = playlistName.value.trim()
  if (!name) return

  creating.value = true
  emit('create', name)
  creating.value = false
  playlistName.value = ''
  showDialog.value = false
}
</script>

<style scoped>
.music-create-playlist-btn {
  justify-content: center;
  gap: 0.375rem;
  margin: 0.25rem 0.5rem;
  width: calc(100% - 1rem);
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground));
  border: 1px dashed hsl(var(--border) / 0.6);
}

.music-create-playlist-btn:hover {
  color: hsl(var(--primary));
  border-color: hsl(var(--primary) / 0.4);
}

.music-create-playlist-btn--compact {
  width: auto;
  margin: 0;
  flex: 0 0 auto;
  white-space: nowrap;
}
</style>
