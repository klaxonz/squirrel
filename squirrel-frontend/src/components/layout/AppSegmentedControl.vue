<template>
  <div
    class="app-segmented-control"
    :class="[`app-segmented-control--${variant}`]"
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
  variant: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'dense', 'tactical'].includes(value),
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
  display: flex;
  align-items: center;
  gap: 0.125rem;
  background: var(--app-control-bg);
  border-radius: var(--app-control-radius);
  padding: 2px;
}

.app-segmented-control__item {
  padding: 0.2rem 0.6rem;
  border-radius: var(--app-control-item-radius);
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground) / 0.7);
  cursor: pointer;
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0;
  transition: all 0.15s ease;
}

.app-segmented-control__item:hover {
  color: hsl(var(--foreground));
  background: var(--app-control-hover-bg);
}

.app-segmented-control__item.is-active {
  color: hsl(var(--foreground));
  background: var(--app-control-active-bg);
  box-shadow: var(--app-control-shadow);
}

.app-segmented-control--dense {
  gap: var(--app-dense-toolbar-gap);
}

.app-segmented-control--tactical {
  background: hsl(var(--secondary) / 0.5);
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: var(--app-tactical-control-radius);
  padding: 0.2rem;
}

.app-segmented-control--tactical .app-segmented-control__item {
  min-width: 8rem;
  height: 1.8rem;
  border-radius: var(--app-tactical-control-radius);
  font-family: var(--app-label-font);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0;
  color: hsl(var(--muted-foreground) / 0.4);
}

.app-segmented-control--tactical .app-segmented-control__item.is-active {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  box-shadow: none;
}
</style>
