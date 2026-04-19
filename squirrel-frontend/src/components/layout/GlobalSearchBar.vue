<template>
  <div
    ref="rootRef"
    class="search-command-bar"
    :class="{
      'search-command-bar--focused': isFocused,
      'search-command-bar--open': showSuggestions,
    }"
    @focusin="handleFocusIn"
    @focusout="handleFocusOut"
  >
    <div class="search-inner">
      <div class="search-icon-group">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <circle cx="11" cy="11" r="7" stroke-width="1.8" />
          <path d="m16.5 16.5 4.5 4.5" stroke-width="1.8" stroke-linecap="round" />
        </svg>
        <div class="search-divider"></div>
      </div>

      <input
        ref="inputRef"
        v-model="inputValue"
        type="text"
        :placeholder="placeholder"
        class="search-field"
        @input="handleInput"
        @keydown.down.prevent="moveActiveSuggestion(1)"
        @keydown.up.prevent="moveActiveSuggestion(-1)"
        @keydown.enter.prevent="handleEnterKey"
        @keydown.esc.prevent="handleEscape"
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

    <transition name="search-suggestions-fade">
      <div
        v-if="showSuggestions"
        class="search-suggestions"
        role="listbox"
        aria-label="搜索提示"
      >
        <div class="search-suggestions__header">
          <span class="search-suggestions__title">{{ suggestionTitle }}</span>
          <button
            v-if="recentSearches.length"
            type="button"
            class="search-suggestions__clear-all"
            @mousedown.prevent
            @click="clearRecentSearches"
          >
            清空
          </button>
        </div>

        <div
          v-for="(item, index) in suggestionItems"
          :key="item.id"
          class="search-suggestion-row"
          :class="{ 'search-suggestion-row--active': index === activeSuggestionIndex }"
        >
          <button
            type="button"
            class="search-suggestion-item"
            :class="{ 'search-suggestion-item--active': index === activeSuggestionIndex }"
            :aria-selected="index === activeSuggestionIndex"
            @mousedown.prevent
            @mouseenter="activeSuggestionIndex = index"
            @click="selectSuggestion(item.value)"
          >
            <span class="search-suggestion-item__icon" aria-hidden="true">
              <svg v-if="item.type === 'search'" viewBox="0 0 20 20" fill="none" stroke="currentColor">
                <circle cx="9" cy="9" r="5.5" stroke-width="1.6" />
                <path d="m13.5 13.5 4 4" stroke-width="1.6" stroke-linecap="round" />
              </svg>
              <svg v-else viewBox="0 0 20 20" fill="none" stroke="currentColor">
                <path d="M10 4.25v5.5l3.5 2.25" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
                <circle cx="10" cy="10" r="6.5" stroke-width="1.6" />
              </svg>
            </span>
            <span class="search-suggestion-item__content">
              <span class="search-suggestion-item__label">{{ item.label }}</span>
              <span v-if="item.meta" class="search-suggestion-item__meta">{{ item.meta }}</span>
            </span>
          </button>

          <button
            v-if="item.type === 'recent'"
            type="button"
            class="search-suggestion-remove"
            aria-label="删除这条搜索历史"
            @mousedown.prevent
            @click.stop="removeRecentSearch(item.value)"
          >
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor">
              <path d="M4 4l8 8M12 4l-8 8" stroke-width="1.5" stroke-linecap="round" />
            </svg>
          </button>
        </div>

        <p v-if="showSearchFallback" class="search-suggestions__empty">
          回车搜索“{{ trimmedInputValue }}”
        </p>

        <p v-else-if="!suggestionItems.length" class="search-suggestions__empty">
          暂无历史
        </p>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { getSearchSuggestions } from '@/api/search'

const SEARCH_HISTORY_STORAGE_KEY = 'global-search-history'
const MAX_RECENT_SEARCHES = 8
const MAX_REMOTE_SUGGESTIONS = 6

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
    default: 500,
  },
  historyScopeKey: {
    type: String,
    default: 'GLOBAL',
  },
  historyScopeLabel: {
    type: String,
    default: '当前页',
  },
  suggestionScope: {
    type: String,
    default: 'home',
  },
})

const emit = defineEmits(['update:modelValue', 'search', 'clear'])

const inputValue = ref(props.modelValue)
const inputRef = ref(null)
const rootRef = ref(null)
const isFocused = ref(false)
const isTyping = ref(false)
const isPanelOpen = ref(false)
const activeSuggestionIndex = ref(-1)
const recentSearches = ref([])
const remoteSuggestions = ref([])

let typingTimeout = null
let suggestionTimeout = null
let latestSuggestionRequestId = 0

const normalizedScopeKey = computed(() => String(props.historyScopeKey || 'GLOBAL'))
const normalizedScopeLabel = computed(() => String(props.historyScopeLabel || props.placeholder || '当前页'))
const normalizedSuggestionScope = computed(() => String(props.suggestionScope || 'home'))
const trimmedInputValue = computed(() => inputValue.value.trim())

const normalizeRecentSearches = (items) => {
  const result = []
  const seen = new Set()

  for (const item of Array.isArray(items) ? items : []) {
    const normalized = String(item || '').trim()
    const normalizedKey = normalized.toLowerCase()
    if (!normalized || seen.has(normalizedKey)) {
      continue
    }
    seen.add(normalizedKey)
    result.push(normalized)
    if (result.length >= MAX_RECENT_SEARCHES) {
      break
    }
  }

  return result
}

const readStoredHistory = () => {
  if (typeof window === 'undefined') {
    return {}
  }

  try {
    const raw = window.localStorage.getItem(SEARCH_HISTORY_STORAGE_KEY)
    if (!raw) {
      return {}
    }

    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch (_) {
    return {}
  }
}

const writeStoredHistory = (nextItems) => {
  recentSearches.value = nextItems

  if (typeof window === 'undefined') {
    return
  }

  const nextHistory = readStoredHistory()
  if (nextItems.length) {
    nextHistory[normalizedScopeKey.value] = nextItems
  } else {
    delete nextHistory[normalizedScopeKey.value]
  }

  if (Object.keys(nextHistory).length) {
    window.localStorage.setItem(SEARCH_HISTORY_STORAGE_KEY, JSON.stringify(nextHistory))
    return
  }

  window.localStorage.removeItem(SEARCH_HISTORY_STORAGE_KEY)
}

const loadRecentSearches = () => {
  const history = readStoredHistory()
  recentSearches.value = normalizeRecentSearches(history[normalizedScopeKey.value])
}

const persistRecentSearch = (value) => {
  const normalized = String(value || '').trim()
  if (!normalized) {
    return
  }

  const normalizedKey = normalized.toLowerCase()
  const nextItems = [
    normalized,
    ...recentSearches.value.filter((item) => item.toLowerCase() !== normalizedKey),
  ].slice(0, MAX_RECENT_SEARCHES)

  writeStoredHistory(nextItems)
}

const filteredRecentSearches = computed(() => {
  const keyword = trimmedInputValue.value.toLowerCase()
  const exactMatch = trimmedInputValue.value.toLowerCase()

  if (!keyword) {
    return recentSearches.value.slice(0, MAX_RECENT_SEARCHES)
  }

  return recentSearches.value
    .filter((item) => {
      const itemKey = item.toLowerCase()
      return itemKey.includes(keyword) && itemKey !== exactMatch
    })
    .slice(0, MAX_RECENT_SEARCHES - 1)
})

const suggestionItems = computed(() => {
  const items = []
  const seen = new Set()

  remoteSuggestions.value.forEach((item) => {
    const value = String(item?.value || '').trim()
    const dedupeKey = value.toLowerCase()
    if (!value || seen.has(dedupeKey)) {
      return
    }

    seen.add(dedupeKey)
    items.push({
      id: `remote-${item.type}-${value}`,
      type: item.type || 'search',
      value,
      label: String(item.label || value),
      meta: String(item.meta || `在${normalizedScopeLabel.value}中搜索`),
    })
  })

  filteredRecentSearches.value.forEach((item, index) => {
    const dedupeKey = item.toLowerCase()
    if (!seen.has(dedupeKey)) {
      seen.add(dedupeKey)
      items.push({
        id: `recent-${index}-${item}`,
        type: 'recent',
        value: item,
        label: item,
        meta: '',
      })
    }
  })

  return items.slice(0, MAX_RECENT_SEARCHES)
})

const hasRemoteSuggestions = computed(() => remoteSuggestions.value.length > 0)

const suggestionTitle = computed(() => {
  if (trimmedInputValue.value && hasRemoteSuggestions.value) {
    return '猜你想搜'
  }
  if (trimmedInputValue.value) {
    return filteredRecentSearches.value.length ? '相关历史' : '直接搜索'
  }
  return '最近搜索'
})

const showSuggestions = computed(() => {
  return isPanelOpen.value && isFocused.value
})

const showSearchFallback = computed(() => {
  return !!trimmedInputValue.value && !hasRemoteSuggestions.value && !filteredRecentSearches.value.length
})

watch(
  () => props.modelValue,
  (value) => {
    if (value !== inputValue.value) {
      inputValue.value = value || ''
    }
  },
)

watch(
  normalizedScopeKey,
  () => {
    loadRecentSearches()
    activeSuggestionIndex.value = -1
  },
  { immediate: true },
)

watch(suggestionItems, (items) => {
  if (!items.length) {
    activeSuggestionIndex.value = -1
    return
  }

  if (activeSuggestionIndex.value >= items.length) {
    activeSuggestionIndex.value = items.length - 1
  }
})

const focusInput = () => {
  inputRef.value?.focus?.()
}

const openSuggestionPanel = () => {
  isPanelOpen.value = true
}

const closeSuggestionPanel = () => {
  isPanelOpen.value = false
  activeSuggestionIndex.value = -1
}

const handleFocusIn = () => {
  isFocused.value = true
  openSuggestionPanel()
}

const handleFocusOut = (event) => {
  if (rootRef.value?.contains(event.relatedTarget)) {
    return
  }

  isFocused.value = false
  closeSuggestionPanel()
}

const handleInput = () => {
  emit('update:modelValue', inputValue.value)
  openSuggestionPanel()
  activeSuggestionIndex.value = -1

  isTyping.value = true
  if (typingTimeout) clearTimeout(typingTimeout)
  typingTimeout = setTimeout(() => {
    isTyping.value = false
  }, 400)

  if (suggestionTimeout) clearTimeout(suggestionTimeout)
  suggestionTimeout = setTimeout(() => {
    void loadRemoteSuggestions()
  }, props.debounceMs)
}

const handleSearch = ({ persist = false } = {}) => {
  isTyping.value = false
  if (persist) {
    persistRecentSearch(inputValue.value)
  }
  emit('search')
  closeSuggestionPanel()
}

const clearSearch = () => {
  inputValue.value = ''
  emit('update:modelValue', '')
  emit('clear')
  remoteSuggestions.value = []
  openSuggestionPanel()
  focusInput()
}

const selectSuggestion = (value) => {
  inputValue.value = value || ''
  emit('update:modelValue', inputValue.value)
  handleSearch({ persist: true })
  focusInput()
}

const removeRecentSearch = (value) => {
  const normalizedValue = String(value || '').trim().toLowerCase()
  const nextItems = recentSearches.value.filter((item) => item.toLowerCase() !== normalizedValue)
  writeStoredHistory(nextItems)
}

const clearRecentSearches = () => {
  writeStoredHistory([])
  activeSuggestionIndex.value = -1
}

const moveActiveSuggestion = (direction) => {
  if (!suggestionItems.value.length) {
    return
  }

  openSuggestionPanel()

  if (activeSuggestionIndex.value < 0) {
    activeSuggestionIndex.value = direction > 0 ? 0 : suggestionItems.value.length - 1
    return
  }

  activeSuggestionIndex.value =
    (activeSuggestionIndex.value + direction + suggestionItems.value.length) % suggestionItems.value.length
}

const handleEnterKey = () => {
  const activeItem = suggestionItems.value[activeSuggestionIndex.value]
  if (activeItem) {
    selectSuggestion(activeItem.value)
    return
  }

  handleSearch({ persist: true })
}

const handleEscape = () => {
  if (showSuggestions.value) {
    closeSuggestionPanel()
    return
  }

  clearSearch()
}

const handleDocumentPointerDown = (event) => {
  if (rootRef.value?.contains(event.target)) {
    return
  }

  isFocused.value = false
  closeSuggestionPanel()
}

const loadRemoteSuggestions = async () => {
  const query = trimmedInputValue.value
  const requestId = ++latestSuggestionRequestId

  if (!query) {
    remoteSuggestions.value = []
    isTyping.value = false
    return
  }

  const { data, error } = await getSearchSuggestions({
    query,
    scope: normalizedSuggestionScope.value,
    limit: MAX_REMOTE_SUGGESTIONS,
  })

  if (requestId !== latestSuggestionRequestId || query !== trimmedInputValue.value) {
    return
  }

  if (error) {
    remoteSuggestions.value = []
    isTyping.value = false
    return
  }

  remoteSuggestions.value = Array.isArray(data?.items) ? data.items : []
  isTyping.value = false
}

defineExpose({
  focus: () => {
    focusInput()
  },
  clear: clearSearch,
  setQuery: (query) => {
    inputValue.value = query || ''
    emit('update:modelValue', inputValue.value)
  },
})

onMounted(() => {
  document.addEventListener('pointerdown', handleDocumentPointerDown)
})

onUnmounted(() => {
  if (typingTimeout) clearTimeout(typingTimeout)
  if (suggestionTimeout) clearTimeout(suggestionTimeout)
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
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

.search-command-bar--open {
  z-index: 30;
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

.search-suggestions-fade-enter-active,
.search-suggestions-fade-leave-active {
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.search-suggestions-fade-enter-from,
.search-suggestions-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.search-suggestions {
  position: absolute;
  top: calc(100% + 0.55rem);
  left: 0;
  right: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.45rem;
  border-radius: calc(var(--radius-lg) + 0.05rem);
  border: 1px solid hsl(var(--border) / 0.7);
  background:
    linear-gradient(180deg, hsl(var(--background) / 0.98) 0%, hsl(var(--background) / 0.95) 100%);
  backdrop-filter: blur(18px);
  box-shadow:
    0 24px 60px -28px hsl(var(--foreground) / 0.45),
    0 10px 24px -18px hsl(var(--foreground) / 0.22);
}

.search-suggestions__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0.1rem 0.15rem;
}

.search-suggestions__title {
  color: hsl(var(--muted-foreground) / 0.78);
  font-size: 0.62rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.search-suggestions__clear-all {
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground) / 0.78);
  font-size: 0.68rem;
  cursor: pointer;
  transition: color 0.15s ease;
}

.search-suggestions__clear-all:hover {
  color: hsl(var(--destructive));
}

.search-suggestion-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.25rem;
  align-items: stretch;
}

.search-suggestion-item,
.search-suggestion-remove {
  border: 1px solid transparent;
  transition: all 0.15s ease;
}

.search-suggestion-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  width: 100%;
  padding: 0.56rem 0.65rem;
  border-radius: calc(var(--radius) - 0.05rem);
  background: hsl(var(--secondary) / 0.42);
  color: hsl(var(--foreground));
  cursor: pointer;
  text-align: left;
}

.search-suggestion-item--active,
.search-suggestion-item:hover {
  background: hsl(var(--accent));
  border-color: hsl(var(--primary) / 0.18);
  transform: translateY(-1px);
}

.search-suggestion-item__icon {
  display: inline-flex;
  width: 1rem;
  height: 1rem;
  flex: 0 0 auto;
  color: hsl(var(--primary));
}

.search-suggestion-item__icon svg {
  width: 100%;
  height: 100%;
}

.search-suggestion-item__content {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 0.08rem;
}

.search-suggestion-item__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.2;
}

.search-suggestion-item__meta {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: hsl(var(--muted-foreground) / 0.8);
  font-size: 0.66rem;
  line-height: 1.15;
}

.search-suggestion-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.8rem;
  border-radius: calc(var(--radius) - 0.05rem);
  background: hsl(var(--secondary) / 0.36);
  color: hsl(var(--muted-foreground) / 0.82);
  cursor: pointer;
}

.search-suggestion-remove svg {
  width: 0.7rem;
  height: 0.7rem;
}

.search-suggestion-remove:hover {
  background: hsl(var(--destructive) / 0.12);
  color: hsl(var(--destructive));
}

.search-suggestions__empty {
  margin: 0;
  padding: 0.55rem 0.45rem 0.35rem;
  color: hsl(var(--muted-foreground) / 0.8);
  font-size: 0.72rem;
  text-align: center;
}

@media (max-width: 767px) {
  .search-suggestions {
    top: calc(100% + 0.45rem);
    padding: 0.38rem;
  }

  .search-suggestion-item {
    padding: 0.5rem 0.58rem;
  }

  .search-suggestion-item__meta {
    display: none;
  }
}
</style>
