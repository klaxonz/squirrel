<template>
  <Dialog v-model:open="open">
    <DialogContent class="max-w-sm overflow-hidden rounded-lg p-0">
      <DialogHeader class="border-b border-border/50 p-5 text-left">
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
      <DialogFooter class="gap-2 bg-muted/30 p-4">
        <Button variant="outline" class="h-9 rounded-md" @click="open = false">{{ cancelLabel }}</Button>
        <Button :variant="confirmVariant" class="h-9 rounded-md" @click="$emit('confirm')">{{ confirmLabel }}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import AppIcon from '@/components/common/AppIcon.vue'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { AppIconName } from '@/icons/app-icons'

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
