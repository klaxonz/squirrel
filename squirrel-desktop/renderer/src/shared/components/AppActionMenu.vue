<script setup lang="ts">
import { ref } from 'vue'
import PrimeMenu from 'primevue/menu'
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { AppIconName } from '@/shared/icons/app-icons'
import AppSpinner from '@/shared/components/AppSpinner.vue'
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

const menu = ref<{ toggle: (event: Event) => void } | null>(null)

const toggle = (event: Event) => {
  menu.value?.toggle(event)
}
</script>

<template>
  <Button
    type="button"
    variant="ghost"
    size="icon-sm"
    :class="buttonClass"
    :disabled="disabled"
    :aria-label="triggerLabel"
    :title="triggerLabel"
    aria-haspopup="menu"
    @click="toggle"
  >
    <slot name="trigger">
      <AppIcon :name="icon" class="h-4 w-4" />
    </slot>
  </Button>

  <PrimeMenu ref="menu" popup :model="items" class="app-action-menu">
    <template #item="{ item, props: itemProps }">
      <a
        v-bind="itemProps.action"
        :class="['app-action-menu__item', { 'app-action-menu__item--danger': item.danger }]"
      >
        <AppSpinner v-if="item.loading" size="sm" />
        <AppIcon v-else-if="item.appIcon" :name="item.appIcon" class="app-action-menu__icon" />
        <span>{{ item.label }}</span>
      </a>
    </template>
  </PrimeMenu>
</template>
