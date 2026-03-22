<template>
  <Tabs
    :model-value="modelValue"
    class="tab-bar"
    @update:model-value="(value) => emit('update:modelValue', String(value))"
  >
    <TabsList class="tab-bar__list">
      <TabsTrigger
        v-for="tab in tabs"
        :key="tab.value"
        :value="tab.value"
        class="tab-bar__trigger"
        @dblclick="emit('tab-dblclick', tab.value)"
      >
        <span class="tab-bar__label">{{ tab.label }}</span>
        <span v-if="tab.count !== undefined" class="tab-bar__count">
          {{ tab.count }}
        </span>
      </TabsTrigger>
    </TabsList>
  </Tabs>
</template>

<script setup>
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'

defineProps({
  modelValue: {
    type: String,
    default: 'all',
  },
  tabs: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['update:modelValue', 'tab-dblclick'])
</script>

<style scoped>
.tab-bar {
  width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;
  -webkit-overflow-scrolling: touch;
}

.tab-bar__list {
  display: inline-flex;
  min-width: max-content;
}

.tab-bar::-webkit-scrollbar {
  display: none;
}

.tab-bar__trigger {
  gap: 0.45rem;
  padding-inline: 0.95rem;
}

.tab-bar__label {
  white-space: nowrap;
}

.tab-bar__count {
  display: inline-flex;
  min-width: 1.35rem;
  justify-content: center;
  border-radius: 9999px;
  background: hsl(var(--background) / 0.72);
  padding: 0.08rem 0.35rem;
  font-size: var(--font-size-2xs);
  color: hsl(var(--muted-foreground));
}

:deep(.tab-bar__trigger[data-state="active"] .tab-bar__count) {
  background: hsl(var(--primary-foreground) / 0.16);
  color: hsl(var(--primary-foreground));
}
</style>
