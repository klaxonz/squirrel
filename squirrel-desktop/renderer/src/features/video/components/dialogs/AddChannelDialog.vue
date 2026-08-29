<template>
  <Dialog :open="show" @update:open="handleOpenChange">
    <DialogContent class="app-dialog-surface max-w-xl">
      <DialogHeader class="app-dialog-form-header">
        <DialogTitle class="app-dialog-form-title">添加订阅</DialogTitle>
        <DialogDescription class="app-dialog-form-description">
          输入频道、空间、播放列表或收藏夹地址，系统会自动识别并建立订阅。
        </DialogDescription>
      </DialogHeader>

      <div class="app-dialog-form-body">
        <div class="app-dialog-form-field">
          <label class="app-dialog-form-label" for="add-channel-url">订阅地址</label>
          <Input fluid
            id="add-channel-url"
            v-model="channelUrl"
            type="url"
            placeholder="支持频道地址或播放列表地址"
            :disabled="loading"
            class="app-form-input"
          />
          <p class="add-channel-dialog__help">
            支持：视频网站频道/播放列表、哔哩哔哩用户空间/合集/收藏夹。
          </p>
        </div>

        <Alert v-if="error" variant="destructive">
          <p class="text-sm [&_p]:leading-relaxed">{{ error }}</p>
        </Alert>
      </div>

      <DialogFooter class="app-dialog-form-footer app-dialog-form-footer--end">
        <Button size="sm" text variant="secondary" :disabled="loading" @click="emit('close')">取消</Button>
        <Button size="sm" :loading="loading" :disabled="!channelUrl" @click="handleSubmit">
          确认添加
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import { subscribe } from '@/shared/api'
import { Alert } from '@/shared/ui/alert'
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
    error.value = errorMessage(err, '添加频道失败，请检查地址是否正确')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.add-channel-dialog__help {
  margin: 0;
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-sm);
  line-height: 1.5;
}
</style>
