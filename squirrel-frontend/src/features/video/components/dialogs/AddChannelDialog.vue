<template>
  <Dialog :open="show" @update:open="handleOpenChange">
    <DialogContent class="max-w-xl gap-0 overflow-hidden p-0">
      <div class="add-channel-dialog__hero">
        <DialogHeader class="space-y-2 px-6 pb-4 pt-6">
          <DialogTitle class="text-xl font-semibold tracking-[-0.03em]">添加订阅</DialogTitle>
          <DialogDescription class="leading-6">
            输入频道、空间、播放列表或收藏夹地址，系统会自动识别并建立订阅。
          </DialogDescription>
        </DialogHeader>
      </div>

      <div class="space-y-5 px-6 py-5">
        <div class="space-y-2">
          <label class="text-sm font-medium text-foreground" for="add-channel-url">订阅地址</label>
          <Input
            id="add-channel-url"
            v-model="channelUrl"
            type="url"
            placeholder="支持频道地址或播放列表地址"
            :disabled="loading"
          />
          <p class="text-xs leading-5 text-muted-foreground">
            支持：视频网站频道/播放列表、哔哩哔哩用户空间/合集/收藏夹。
          </p>
        </div>

        <Alert v-if="error" variant="destructive">
          <AlertDescription>{{ error }}</AlertDescription>
        </Alert>
      </div>

      <DialogFooter class="border-t border-border/70 bg-secondary/28 px-6 py-4 sm:justify-end">
        <Button size="sm" variant="ghost" :disabled="loading" @click="emit('close')">取消</Button>
        <Button size="sm" :loading="loading" :disabled="!channelUrl" @click="handleSubmit">
          确认添加
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { subscribe } from '@/shared/api'
import { Alert, AlertDescription } from '@/shared/ui/alert'
import { Button } from '@/shared/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog'
import { Input } from '@/shared/ui/input'

const props = defineProps<{
  show?: boolean
}>()

const emit = defineEmits(['close', 'added'])

const channelUrl = ref('')
const loading = ref(false)
const error = ref('')

watch(() => props.show, (visible) => {
  if (!visible) {
    channelUrl.value = ''
    error.value = ''
  }
})

const handleOpenChange = (open: boolean) => {
  if (!open) {
    emit('close')
  }
}

const handleSubmit = async () => {
  if (!channelUrl.value) return

  loading.value = true
  error.value = ''

  try {
    await subscribe(channelUrl.value)
    emit('added')
    emit('close')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '添加频道失败，请检查地址是否正确'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.add-channel-dialog__hero {
  background:
    radial-gradient(circle at top right, hsl(var(--primary) / 0.12), transparent 36%),
    linear-gradient(180deg, hsl(var(--card) / 0.98), hsl(var(--background) / 0.92));
}
</style>
