<template>
  <nav class="flex min-w-0 items-center gap-1.5 overflow-hidden whitespace-nowrap select-none" aria-label="路径导航">
    <template v-for="(item, index) in breadcrumbs" :key="`${item.label}-${index}`">
      <router-link
        v-if="item.to"
        :to="item.to"
        class="truncate text-xs font-medium text-muted-foreground/65 transition-colors hover:text-foreground"
      >
        {{ item.label }}
      </router-link>
      <span v-else class="truncate text-xs font-semibold text-foreground/80">
        {{ item.label }}
      </span>
      <AppIcon
        v-if="index < breadcrumbs.length - 1"
        name="breadcrumb"
        class="size-3 shrink-0 text-muted-foreground/30"
        aria-hidden="true"
      />
    </template>
    <span v-if="!breadcrumbs.length" class="truncate text-xs font-semibold text-foreground/80">
      {{ pageTitle || sectionLabel }}
    </span>
  </nav>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { BreadcrumbItem } from '@/shared/constants/sidebar'

defineProps<{
  sectionLabel?: string
  pageTitle: string
  breadcrumbs: BreadcrumbItem[]
}>()
</script>
