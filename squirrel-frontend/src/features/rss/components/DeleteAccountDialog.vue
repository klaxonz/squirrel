<template>
  <Dialog :open="open" @update:open="$emit('update:open', $event)">
    <DialogContent class="delete-account-dialog app-dialog-surface">
      <DialogHeader class="app-dialog-form-header">
        <div class="delete-account-dialog__icon">
          <AppIcon name="trash" class="h-5 w-5" />
        </div>
        <DialogTitle class="app-dialog-form-title">确认删除账号？</DialogTitle>
        <DialogDescription class="delete-account-dialog__description app-dialog-form-description">
          此操作将永久移除该 RSS 账号「{{ accountName }}」及其同步的所有订阅源和文章记录。该操作不可撤销。
        </DialogDescription>
      </DialogHeader>
      <DialogFooter class="app-dialog-form-footer app-dialog-form-footer--end">
        <Button variant="outline" size="sm" @click="$emit('update:open', false)">取消</Button>
        <Button variant="destructive" size="sm" @click="$emit('confirm')">确认删除</Button>
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

<style scoped>
.delete-account-dialog {
  max-width: 24rem;
}

.delete-account-dialog__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  margin-bottom: 0.75rem;
  border: 1px solid hsl(var(--destructive) / 0.18);
  border-radius: 0.5rem;
  background: hsl(var(--destructive) / 0.08);
  color: hsl(var(--destructive));
}

.delete-account-dialog__description {
  font-size: 0.875rem;
  line-height: 1.55;
}

.delete-account-dialog__button--danger {
  background: hsl(var(--destructive));
  color: hsl(var(--destructive-foreground));
}

.delete-account-dialog__button--danger:hover {
  background: hsl(var(--destructive) / 0.9);
}
</style>
