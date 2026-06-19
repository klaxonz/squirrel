<template>
  <nav v-if="breadcrumbs.length" class="flex items-center gap-1.5 px-2 overflow-hidden whitespace-nowrap select-none" aria-label="路径导航">
    <template v-for="(item, index) in breadcrumbs" :key="`${item.label}-${index}`">
      <router-link
        v-if="item.to"
        :to="item.to"
        class="text-[12px] font-medium text-muted-foreground/60 hover:text-foreground transition-colors"
      >
        {{ item.label }}
      </router-link>
      <span v-else class="text-[12px] font-semibold text-foreground/80">
        {{ item.label }}
      </span>
      <AppIcon
        v-if="index < breadcrumbs.length - 1"
        name="breadcrumb"
        class="w-3 h-3 text-muted-foreground/30 shrink-0"
        aria-hidden="true"
      />
    </template>
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
