<template>
  <Dialog v-model:open="open">
    <DialogContent class="app-dialog-surface confirm-dialog">
      <DialogHeader class="app-dialog-form-header confirm-dialog__header">
        <div
          class="confirm-dialog__icon"
          :class="iconBgClass"
        >
          <AppIcon :name="icon" class="h-5 w-5" :class="iconClass" />
        </div>
        <DialogTitle class="app-dialog-form-title">{{ title }}</DialogTitle>
        <DialogDescription class="app-dialog-form-description">
          <slot name="description">{{ description }}</slot>
        </DialogDescription>
      </DialogHeader>
      <DialogFooter class="app-dialog-form-footer app-dialog-form-footer--end">
        <Button severity="secondary" outlined size="sm" :disabled="confirming" @click="open = false">{{ cancelLabel }}</Button>
        <Button size="sm" :variant="confirmVariant" :loading="confirming" :disabled="confirming" @click="$emit('confirm')">{{ confirmLabel }}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog'
import type { AppIconName } from '@/shared/icons/app-icons'

// ponytail: a generic confirm modal parameterizing the two identical delete /
// execute confirmations in ScheduledTasks. The description can be a plain prop
// or a #description slot (for inline-styled task names).
defineProps<{
  icon: AppIconName
  iconBgClass: string
  iconClass?: string
  title: string
  description?: string
  cancelLabel?: string
  confirmLabel: string
  confirmVariant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost'
  confirming?: boolean
}>()

const open = defineModel<boolean>('open', { required: true })

defineEmits<{ confirm: [] }>()
</script>

<style scoped>
.confirm-dialog {
  width: min(100%, 24rem);
}

.confirm-dialog__header {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.confirm-dialog__icon {
  display: inline-flex;
  width: 2.5rem;
  height: 2.5rem;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-3);
  border-radius: var(--radius-md);
}
</style>
