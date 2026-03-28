<template>
  <div ref="rootRef" class="search-terminal-box">
    <div class="search-prefix">
      <span class="prefix-symbol">></span>
      <span class="prefix-index">00</span>
    </div>
    <input
      v-model="inputValue"
      type="text"
      :placeholder="placeholder"
      class="search-input-minimal"
      @keyup.enter="handleSearch"
      @keyup.esc="clearSearch"
      @input="handleInput"
    />
    <div class="search-suffix">
      <span v-if="inputValue" class="char-count">{{ inputValue.length }}CH</span>
      <span class="cmd-hint">/</span>
    </div>
    <div class="search-border"></div>
  </div>
</template>

<script setup>
import { onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  placeholder: {
    type: String,
    default: 'EXECUTE_QUERY',
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
.search-terminal-box {
  position: relative;
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.02);
  padding: 0.4rem 0.75rem;
  border: 1px solid rgba(255, 255, 255, 0.05);
  transition: all 0.3s ease;
}

.search-terminal-box:focus-within {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 77, 0, 0.3);
  box-shadow: 0 0 20px rgba(255, 77, 0, 0.05);
}

.search-prefix {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-right: 0.75rem;
  pointer-events: none;
}

.prefix-symbol {
  color: #ff4d00;
  font-family: 'Courier New', Courier, monospace;
  font-weight: 800;
  font-size: 0.8rem;
}

.prefix-index {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.55rem;
  color: rgba(255, 255, 255, 0.2);
}

.search-input-minimal {
  flex: 1;
  background: transparent;
  border: none;
  color: #fff;
  font-size: 0.75rem;
  font-family: 'Courier New', Courier, monospace;
  letter-spacing: 0.05em;
  outline: none;
  padding: 0;
  width: 100%;
}

.search-input-minimal::placeholder {
  color: rgba(255, 255, 255, 0.1);
  text-transform: uppercase;
}

.search-suffix {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-left: 0.75rem;
  pointer-events: none;
}

.char-count {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.5rem;
  color: #ff4d00;
  opacity: 0.6;
}

.cmd-hint {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.6rem;
  color: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.05);
  padding: 1px 4px;
  border-radius: 2px;
}

.search-terminal-box:focus-within .cmd-hint {
  color: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.15);
}
</style>
