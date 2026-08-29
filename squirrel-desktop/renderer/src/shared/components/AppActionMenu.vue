<script setup lang="ts">
import {
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuPortal,
  DropdownMenuRoot,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from 'reka-ui'
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { AppIconName } from '@/shared/icons/app-icons'
import { Spinner as AppSpinner } from '@/shared/ui/skeleton'
import { Button } from '@/shared/ui/button'

export interface AppActionMenuItem {
  label?: string
  appIcon?: AppIconName
  separator?: boolean
  disabled?: boolean
  visible?: boolean
  loading?: boolean
  danger?: boolean
  command?: () => void | Promise<void>
}

withDefaults(defineProps<{
  items: AppActionMenuItem[]
  triggerLabel: string
  buttonClass?: string
  disabled?: boolean
  icon?: AppIconName
}>(), {
  buttonClass: '',
  disabled: false,
  icon: 'more',
})
</script>

<template>
  <DropdownMenuRoot>
    <DropdownMenuTrigger as-child>
      <Button
        type="button"
        text variant="secondary"
        size="sm" icon-only
        :class="buttonClass"
        :disabled="disabled"
        :aria-label="triggerLabel"
        :title="triggerLabel"
      >
        <slot name="trigger"><AppIcon :name="icon" class="h-4 w-4" /></slot>
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuPortal>
      <DropdownMenuContent class="sq-menu" :side-offset="6" align="end">
        <template v-for="(item, index) in items" :key="`${item.label || 'separator'}-${index}`">
          <DropdownMenuSeparator v-if="item.separator" class="sq-menu__separator" />
          <DropdownMenuItem
            v-else-if="item.visible !== false"
            :disabled="item.disabled || item.loading"
            :class="['sq-menu__item', { 'sq-menu__item--danger': item.danger }]"
            @select="item.command?.()"
          >
            <AppSpinner v-if="item.loading" size="sm" />
            <AppIcon v-else-if="item.appIcon" :name="item.appIcon" class="h-4 w-4 shrink-0" />
            <span>{{ item.label }}</span>
          </DropdownMenuItem>
        </template>
      </DropdownMenuContent>
    </DropdownMenuPortal>
  </DropdownMenuRoot>
</template>
