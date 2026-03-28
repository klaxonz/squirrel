<template>
  <div ref="rootRef" class="search-minimal">
    <span class="search-index">00</span>
    <input
      v-model="inputValue"
      type="text"
      :placeholder="placeholder"
      class="search-input"
      @keyup.enter="handleSearch"
      @keyup.esc="clearSearch"
      @input="handleInput"
    />
    <div class="search-line"></div>
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
    default: 'SEARCH /',
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
.search-minimal {
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
}

.search-index {
  position: absolute;
  left: -1.5rem;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.6rem;
  color: rgba(255, 255, 255, 0.2);
}

.search-input {
  width: 100%;
  background: transparent;
  border: none;
  padding: 0.5rem 0;
  color: #fff;
  font-size: 0.8rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  outline: none;
}

.search-input::placeholder {
  color: rgba(255, 255, 255, 0.1);
}

.search-line {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 1px;
  background: rgba(255, 255, 255, 0.05);
  transition: all 0.5s ease;
}

.search-input:focus ~ .search-line {
  background: rgba(255, 255, 255, 0.3);
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.1);
}
</style>
