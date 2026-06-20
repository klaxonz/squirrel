<template>
  <Dialog :open="open" @update:open="$emit('update:open', $event)">
    <DialogContent class="max-w-sm overflow-hidden rounded-xl p-0 border border-border/50 bg-background/95 backdrop-blur-xl">
      <DialogHeader class="border-b border-border/10 p-5 text-left">
        <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
          <AppIcon name="trash" class="h-5 w-5" />
        </div>
        <DialogTitle class="text-base font-semibold text-foreground">确认删除账号？</DialogTitle>
        <DialogDescription class="text-sm leading-relaxed text-muted-foreground/90 mt-1">
          此操作将永久移除该 RSS 账号「{{ accountName }}」及其同步的所有订阅源和文章记录。该操作不可撤销。
        </DialogDescription>
      </DialogHeader>
      <DialogFooter class="gap-2 bg-muted/30 p-4">
        <Button variant="outline" class="h-9 rounded-xl text-xs font-semibold" @click="$emit('update:open', false)">取消</Button>
        <Button class="h-9 rounded-xl bg-destructive text-destructive-foreground hover:bg-destructive/90 text-xs font-semibold" @click="$emit('confirm')">确认删除</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
/**
 * Delete-RSS-account confirmation dialog. Extracted from RssSources.vue (was an
 * inline ~18-line Dialog block). Controlled via v-model:open; emits `confirm`
 * when the user confirms deletion.
 */
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/shared/ui/dialog'

defineProps<{
  open: boolean
  accountName: string
}>()

defineEmits<{
  'update:open': [value: boolean]
  confirm: []
}>()
</script>
