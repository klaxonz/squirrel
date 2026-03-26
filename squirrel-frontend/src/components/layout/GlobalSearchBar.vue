<template>
  <div ref="rootRef" class="global-search-bar">
    <div class="global-search-bar__field">
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        class="global-search-bar__icon"
        aria-label="执行搜索"
        @click="handleSearch"
      >
        <MagnifyingGlassIcon class="h-4 w-4" />
      </Button>

      <Input
        v-model="inputValue"
        type="text"
        :placeholder="placeholder"
        class="global-search-bar__input"
        @keyup.enter="handleSearch"
        @keyup.esc="clearSearch"
        @input="handleInput"
      />

      <Button
        v-if="inputValue"
        type="button"
        variant="ghost"
        size="icon-sm"
        class="global-search-bar__clear"
        title="清除搜索 (ESC)"
        aria-label="清除搜索"
        @click="clearSearch"
      >
        <XMarkIcon class="h-4 w-4" />
      </Button>
    </div>
  </div>
</template>

<script setup>
import { onUnmounted, ref, watch } from 'vue'
import { MagnifyingGlassIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  placeholder: {
    type: String,
    default: '搜索...',
  },
  debounceMs: {
    type: Number,
    default: 300,
  },
})

const emit = defineEmits(['update:modelValue', 'search', 'clear'])

const inputValue = ref(props.modelValue)
const rootRef = ref(null)

watch(
  () => props.modelValue,
  (value) => {
    if (value !== inputValue.value) {
      inputValue.value = value || ''
    }
  },
)

let searchTimeout = null

const handleInput = () => {
  emit('update:modelValue', inputValue.value)
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    emit('search')
  }, props.debounceMs)
}

const handleSearch = () => {
  emit('search')
}

const clearSearch = () => {
  inputValue.value = ''
  emit('update:modelValue', '')
  emit('clear')
}

defineExpose({
  focus: () => {
    const input = rootRef.value?.querySelector?.('input')
    if (input) {
      input.focus()
    }
  },
  clear: clearSearch,
  setQuery: (query) => {
    inputValue.value = query || ''
    emit('update:modelValue', inputValue.value)
  },
})

onUnmounted(() => {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
})
</script>

<style scoped>
.global-search-bar {
  width: 100%;
}

.global-search-bar__field {
  position: relative;
  display: flex;
  width: 100%;
  align-items: center;
}

.global-search-bar__input {
  min-height: 2.5rem;
  padding-left: 2.5rem;
  padding-right: 2.5rem;
  border-color: hsl(var(--border) / 0.72);
}

.global-search-bar__icon,
.global-search-bar__clear {
  position: absolute;
  top: 50%;
  z-index: 1;
  transform: translateY(-50%);
}

.global-search-bar__icon {
  left: 0.25rem;
}

.global-search-bar__clear {
  right: 0.25rem;
}

@media (max-width: 640px) {
  .global-search-bar__input {
    min-height: 2.375rem;
  }
}
</style>
