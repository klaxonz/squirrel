<template>
  <div class="mb-4 flex items-center justify-between gap-4">
    <div class="app-section-title !mb-0">
      <h2 class="app-section-title__text">{{ title }}</h2>
    </div>

    <div class="flex items-center gap-3">
      <button
        v-if="viewMoreLabel"
        type="button"
        class="group/more flex h-8 items-center gap-1 rounded-md px-1 text-xs font-medium text-muted-foreground transition-colors hover:text-primary"
        @click="$emit('viewMore')"
      >
        {{ viewMoreLabel }}
        <AppIcon name="chevronRight" class="size-3.5 transition-transform group-hover/more:translate-x-0.5" />
      </button>

      <div
        class="flex gap-1 opacity-0 transition-opacity duration-200 group-hover/container:opacity-100"
        :class="{ '!opacity-100': canScrollLeft || canScrollRight }"
      >
        <button
          class="flex size-8 items-center justify-center rounded-md border border-border/60 bg-transparent text-muted-foreground transition-colors hover:bg-accent/40 hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30"
          :disabled="!canScrollLeft"
          :title="'向左滚动'"
          @click="$emit('scroll', 'left')"
        >
          <AppIcon name="chevronLeft" class="size-4" />
        </button>
        <button
          class="flex size-8 items-center justify-center rounded-md border border-border/60 bg-transparent text-muted-foreground transition-colors hover:bg-accent/40 hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30"
          :disabled="!canScrollRight"
          :title="'向右滚动'"
          @click="$emit('scroll', 'right')"
        >
          <AppIcon name="chevronRight" class="size-4" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'

defineProps<{
  title: string
  viewMoreLabel?: string
  canScrollLeft: boolean
  canScrollRight: boolean
}>()

defineEmits<{
  viewMore: []
  scroll: [direction: 'left' | 'right']
}>()
</script>
