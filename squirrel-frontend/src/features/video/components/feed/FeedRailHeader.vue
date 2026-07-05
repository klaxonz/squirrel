<template>
  <div class="mb-4 flex items-center justify-between gap-4">
    <div class="app-section-title !mb-0">
      <h2 class="app-section-title__text">{{ title }}</h2>
    </div>

    <div class="flex items-center gap-3">
      <Button
        v-if="viewMoreLabel"
        type="button"
        variant="ghost"
        size="sm"
        class="group/more"
        @click="$emit('viewMore')"
      >
        {{ viewMoreLabel }}
        <AppIcon name="chevronRight" class="size-3.5 transition-transform group-hover/more:translate-x-0.5" />
      </Button>

      <div
        class="flex gap-1 opacity-0 transition-opacity duration-200 group-hover/container:opacity-100"
        :class="{ '!opacity-100': canScrollLeft || canScrollRight }"
      >
        <Button
          variant="ghost"
          size="icon-sm"
          :disabled="!canScrollLeft"
          :title="'向左滚动'"
          @click="$emit('scroll', 'left')"
        >
          <AppIcon name="chevronLeft" class="size-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          :disabled="!canScrollRight"
          :title="'向右滚动'"
          @click="$emit('scroll', 'right')"
        >
          <AppIcon name="chevronRight" class="size-4" />
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'

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
