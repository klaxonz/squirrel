<template>
  <div
    class="app-segmented-control"
    :class="[`app-segmented-control--${size}`]"
    role="tablist"
    :aria-label="ariaLabel"
  >
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="app-segmented-control__item"
      :class="{ 'is-active': modelValue === option.value }"
      role="tab"
      :aria-selected="modelValue === option.value"
      @click="selectOption(option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: {
    type: [String, Number],
    required: true,
  },
  options: {
    type: Array,
    required: true,
  },
  ariaLabel: {
    type: String,
    default: '切换选项',
  },
  size: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'sm'].includes(value),
  },
})

const emit = defineEmits(['update:modelValue', 'change'])

const selectOption = (value) => {
  if (value === props.modelValue) return
  emit('update:modelValue', value)
  emit('change', value)
}
</script>

<style scoped>
.app-segmented-control {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  background: hsl(var(--secondary));
  border-radius: var(--radius-md);
  padding: 2px;
}

.app-segmented-control__item {
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-sm);
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 500;
  transition: all var(--duration-fast) var(--ease-default);
}

.app-segmented-control__item:hover {
  color: hsl(var(--foreground));
}

.app-segmented-control__item.is-active {
  color: hsl(var(--foreground));
  background: hsl(var(--card));
  box-shadow: var(--shadow-xs);
}

.app-segmented-control--sm .app-segmented-control__item {
  padding: 0.125rem 0.5rem;
  font-size: 0.75rem;
}
</style>
