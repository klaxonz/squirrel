<template>
  <Button variant="secondary" size="sm" @click="openDialog">
    <AppIcon name="plus" class="h-3.5 w-3.5" />
    创建歌单
  </Button>

  <Dialog :open="open" @update:open="handleOpenChange">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>创建歌单</DialogTitle>
        <DialogDescription>
          输入歌单名称，创建后即可添加歌曲。
        </DialogDescription>
      </DialogHeader>

      <div class="flex flex-col gap-2 py-4">
        <Input
          v-model="playlistName"
          placeholder="歌单名称"
          maxlength="20"
          :disabled="creating"
          @keyup.enter.prevent="handleCreate"
        />
        <p v-if="error" role="alert" class="text-xs text-destructive">
          {{ error }}
        </p>
      </div>

      <DialogFooter>
        <Button variant="secondary" outlined :disabled="creating" @click="closeDialog">
          取消
        </Button>
        <Button
          :loading="creating"
          :disabled="!playlistName.trim()"
          @click="handleCreate"
        >
          创建
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'

const props = defineProps<{
  onCreate: (name: string) => Promise<boolean>
}>()

const open = ref(false)
const playlistName = ref('')
const creating = ref(false)
const error = ref('')

function openDialog() {
  error.value = ''
  open.value = true
}

function closeDialog() {
  if (creating.value) return
  open.value = false
  playlistName.value = ''
  error.value = ''
}

function handleOpenChange(nextOpen: boolean) {
  if (nextOpen) {
    openDialog()
    return
  }
  closeDialog()
}

async function handleCreate() {
  const name = playlistName.value.trim()
  if (!name || creating.value) return

  creating.value = true
  error.value = ''
  let created = false

  try {
    created = await props.onCreate(name)
  } catch {
    created = false
  } finally {
    creating.value = false
  }

  if (created) {
    closeDialog()
    return
  }

  error.value = '创建失败，请稍后重试'
}
</script>
