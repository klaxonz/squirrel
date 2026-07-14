<template>
  <Dialog v-model:open="open">
    <DialogContent class="max-w-sm overflow-hidden rounded-lg p-0">
      <DialogHeader class="app-divider-bottom p-5 text-left">
        <div
          class="mb-3 flex h-10 w-10 items-center justify-center rounded-md"
          :class="iconBgClass"
        >
          <AppIcon :name="icon" class="h-5 w-5" :class="iconClass" />
        </div>
        <DialogTitle class="text-base font-semibold">{{ title }}</DialogTitle>
        <DialogDescription class="text-sm leading-relaxed text-muted-foreground">
          <slot name="description">{{ description }}</slot>
        </DialogDescription>
      </DialogHeader>
      <DialogFooter class="app-dialog-form-footer app-dialog-form-footer--end">
        <Button variant="outline" size="sm" @click="open = false">{{ cancelLabel }}</Button>
        <Button size="sm" :variant="confirmVariant" @click="$emit('confirm')">{{ confirmLabel }}</Button>
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
}>()

const open = defineModel<boolean>('open', { required: true })

defineEmits<{ confirm: [] }>()
</script>
