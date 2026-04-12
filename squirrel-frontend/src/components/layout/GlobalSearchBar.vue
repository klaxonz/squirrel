<template>
  <div ref="rootRef" class="search-command-bar" :class="{ 'search-command-bar--focused': isFocused }">
    <div class="search-inner">
      <div class="search-icon-group">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <circle cx="11" cy="11" r="7" stroke-width="1.8" />
          <path d="m16.5 16.5 4.5 4.5" stroke-width="1.8" stroke-linecap="round" />
        </svg>
        <div class="search-divider"></div>
      </div>

      <input
        v-model="inputValue"
        type="text"
        :placeholder="placeholder"
        class="search-field"
        @focus="isFocused = true"
        @blur="isFocused = false"
        @keyup.enter="handleSearch"
        @keyup.esc="clearSearch"
        @input="handleInput"
      />

      <div class="search-actions">
        <span v-if="isTyping" class="search-status-dot"></span>
        <button
          v-if="inputValue"
          type="button"
          class="search-clear-btn"
          aria-label="清除搜索"
          @click="clearSearch"
        >
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor">
            <path d="M4 4l8 8M12 4l-8 8" stroke-width="1.5" stroke-linecap="round" />
          </svg>
        </button>
        <kbd v-else class="search-hint-key">⏎</kbd>
      </div>
    </div>
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
    default: '搜索',
  },
  debounceMs: {
    type: Number,
    default: 300,
  },
})

const emit = defineEmits(['update:modelValue', 'search', 'clear'])

const inputValue = ref(props.modelValue)
const rootRef = ref(null)
const isFocused = ref(false)
const isTyping = ref(false)

let typingTimeout = null
let searchTimeout = null

watch(
  () => props.modelValue,
  (value) => {
    if (value !== inputValue.value) {
      inputValue.value = value || ''
    }
  },
)

const handleInput = () => {
  emit('update:modelValue', inputValue.value)

  isTyping.value = true
  if (typingTimeout) clearTimeout(typingTimeout)
  typingTimeout = setTimeout(() => {
    isTyping.value = false
  }, 400)

  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    emit('search')
  }, props.debounceMs)
}

const handleSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  isTyping.value = false
  emit('search')
}

const clearSearch = () => {
  inputValue.value = ''
  emit('update:modelValue', '')
  emit('clear')
  rootRef.value?.querySelector('input')?.focus()
}

defineExpose({
  focus: () => {
    const input = rootRef.value?.querySelector?.('input')
    if (input) input.focus()
  },
  clear: clearSearch,
  setQuery: (query) => {
    inputValue.value = query || ''
    emit('update:modelValue', inputValue.value)
  },
})

onUnmounted(() => {
  if (searchTimeout) clearTimeout(searchTimeout)
  if (typingTimeout) clearTimeout(typingTimeout)
})
</script>

<style scoped>
.search-command-bar {
  position: relative;
  display: flex;
  align-items: center;
  background: hsl(var(--secondary) / 0.5);
  border: 1px solid hsl(var(--border) / 0.6);
  border-radius: var(--radius-lg);
  padding: 0.5rem 0.75rem;
  transition: all 0.2s ease;
}

.search-command-bar--focused {
  background: hsl(var(--secondary) / 0.8);
  border-color: hsl(var(--primary) / 0.5);
  box-shadow: 0 0 0 3px hsl(var(--primary) / 0.1);
}

.search-inner {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
}

.search-icon-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.search-icon {
  width: 1rem;
  height: 1rem;
  color: hsl(var(--muted-foreground) / 0.7);
  transition: color 0.2s ease;
}

.search-command-bar--focused .search-icon {
  color: hsl(var(--primary));
}

.search-divider {
  width: 1px;
  height: 1rem;
  background: linear-gradient(
    to bottom,
    transparent,
    hsl(var(--border) / 0.5) 30%,
    hsl(var(--border) / 0.5) 70%,
    transparent
  );
}

.search-field {
  flex: 1;
  background: transparent;
  border: none;
  color: hsl(var(--foreground));
  font-size: 0.8125rem;
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  letter-spacing: 0.03em;
  outline: none;
  padding: 0.125rem 0;
  width: 100%;
  min-width: 0;
}

.search-field::placeholder {
  color: hsl(var(--muted-foreground) / 0.45);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.6875rem;
}

.search-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.search-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: hsl(var(--primary));
  animation: typing-pulse 0.8s ease-in-out infinite;
}

@keyframes typing-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.7); }
}

.search-clear-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  border-radius: var(--radius-sm);
  background: hsl(var(--muted) / 0.5);
  border: 1px solid hsl(var(--border) / 0.3);
  color: hsl(var(--muted-foreground) / 0.7);
  cursor: pointer;
  transition: all 0.15s ease;
}

.search-clear-btn svg {
  width: 10px;
  height: 10px;
}

.search-clear-btn:hover {
  background: hsl(var(--destructive) / 0.15);
  border-color: hsl(var(--destructive) / 0.3);
  color: hsl(var(--destructive));
}

.search-clear-btn:active {
  transform: scale(0.92);
}

.search-hint-key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.5rem;
  height: 1.25rem;
  padding: 0 0.25rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.5rem;
  font-weight: 600;
  color: hsl(var(--muted-foreground) / 0.4);
  background: hsl(var(--background) / 0.4);
  border: 1px solid hsl(var(--border) / 0.25);
  border-radius: 3px;
  letter-spacing: 0.02em;
  transition: all 0.2s ease;
}

.search-command-bar--focused .search-hint-key {
  color: hsl(var(--primary) / 0.7);
  border-color: hsl(var(--primary) / 0.3);
  background: hsl(var(--primary) / 0.05);
}
</style>