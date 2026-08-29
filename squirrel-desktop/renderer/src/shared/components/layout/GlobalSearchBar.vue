<template>
  <div ref="rootRef" class="global-search" @focusin="handleFocusIn" @focusout="handleFocusOut">
    <div class="global-search__box" :class="{ 'is-open': showSuggestions }">
      <AppIcon name="search" class="global-search__leading-icon" :stroke-width="2.25" />

      <div v-if="searchModesList.length > 0" class="global-search__mode-wrap">
        <Button
          type="button"
          text severity="secondary"
          size="sm"
          class="global-search__mode"
          :class="{ 'is-remote': activeSearchMode === 'remote' }"
          :aria-pressed="activeSearchMode === 'remote'"
          :aria-label="`搜索范围：${activeSearchModeLabel}`"
          :title="`搜索范围：${activeSearchModeLabel}`"
          @click="toggleMode"
        >
          <AppIcon :name="activeSearchMode === 'local' ? 'library' : 'siteFallback'" class="global-search__mode-icon" />
          <span class="global-search__mode-label">{{ activeSearchModeLabel }}</span>
        </Button>
      </div>

      <input
        :id="inputId"
        ref="inputRef"
        v-model="inputValue"
        type="text"
        :placeholder="placeholder"
        class="global-search__input"
        role="combobox"
        :aria-label="placeholder || '搜索'"
        aria-autocomplete="list"
        aria-haspopup="listbox"
        :aria-controls="listboxId"
        :aria-expanded="showSuggestions"
        :aria-activedescendant="activeDescendantId"
        :aria-busy="isLoadingSuggestions || undefined"
        @input="handleInput"
        @compositionstart="isComposing = true"
        @compositionend="handleCompositionEnd"
        @keydown.down.prevent="moveActiveSuggestion(1)"
        @keydown.up.prevent="moveActiveSuggestion(-1)"
        @keydown.enter.prevent="handleEnterKey"
        @keydown.esc.prevent="handleEscape"
      />

      <div class="global-search__actions">
        <div
          v-if="isTyping || isLoadingSuggestions"
          class="global-search__loading"
          role="status"
          aria-live="polite"
        >
          <AppSpinner size="sm" aria-hidden="true" />
          <span class="sr-only">正在加载搜索建议</span>
        </div>

        <Button
          v-if="inputValue"
          text
          severity="secondary"
          size="sm"
          icon-only
          class="global-search__clear"
          title="清除"
          aria-label="清除"
          @click="clearSearch"
        >
          <AppIcon name="close" class="w-3.5 h-3.5" />
        </Button>
      </div>
    </div>

    <!-- Suggestions Dropdown -->
    <transition
      enter-active-class="transition duration-base ease-out"
      enter-from-class="opacity-0 translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-fast ease-default"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 translate-y-1"
    >
      <div
        v-if="showSuggestions"
        class="global-search__suggestions"
      >
        <div class="global-search__suggestions-header">
          <span>{{ suggestionTitle }}</span>
          <Button
            v-if="recentSearches.length"
            link size="sm"
            class="global-search__clear-recent"
            @mousedown.prevent
            @click="clearRecentSearches"
          >清空</Button>
        </div>

        <div
          :id="listboxId"
          class="global-search__suggestions-list"
          role="listbox"
          :aria-label="suggestionTitle"
          :aria-busy="isLoadingSuggestions || undefined"
        >
          <div v-for="(item, index) in suggestionItems" :key="item.id" class="global-search__suggestion-row" role="presentation">
            <Button
              :id="getOptionId(index)"
              text severity="secondary"
              class="global-search__suggestion"
              :class="{ 'is-active': index === activeSuggestionIndex }"
              role="option"
              :aria-selected="index === activeSuggestionIndex"
              tabindex="-1"
              @mouseenter="activeSuggestionIndex = index"
              @mousedown.prevent
              @click="selectSuggestion(item.value)"
            >
              <AppIcon :name="item.type === 'search' ? 'search' : 'history'" class="h-4 w-4 shrink-0 opacity-50" />
              <div class="global-search__suggestion-copy">
                <span class="global-search__suggestion-label">{{ item.label }}</span>
                <span v-if="item.meta" class="global-search__suggestion-meta">{{ item.meta }}</span>
              </div>
            </Button>
            <Button
              v-if="item.type === 'recent'"
              text severity="secondary" size="sm" icon-only
              class="global-search__remove"
              :aria-label="`从最近搜索中移除 ${item.label}`"
              :title="`从最近搜索中移除 ${item.label}`"
              @mousedown.prevent
              @click.stop="removeRecentSearchItem(item.value, index)"
            >
              <AppIcon name="close" class="w-3.5 h-3.5" />
            </Button>
          </div>

          <div v-if="!suggestionItems.length" class="global-search__empty">暂无搜索记录</div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Spinner as AppSpinner } from '@/shared/ui/skeleton'
import { Button } from '@/shared/ui/button'
import { getSearchSuggestions } from '@/shared/api/search'
import type { SearchSuggestionItem } from '@/shared/api/search'
import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import {
  findDesktopPlaybackProvider,
  resolveDesktopPlayback,
  isDesktopPlaybackClient,
} from '@/features/video/composables/useVideoOperations'
import { useUIStore } from '@/shared/stores/ui'
import { useSearchHistory } from '@/shared/composables/useSearchHistory'

type SearchModeOption = {
  value: string
  label: string
}

// ponytail: dropdown row union — 'search' for remote suggestions, 'recent' for
// local history; collapsed into one shape so the template list stays flat.
type SuggestionItem = {
  id: string
  type: 'search' | 'recent'
  value: string
  label: string
  meta?: string
}

type SeedSubscription = {
  name: string
  url: string
  avatar: string
}

let globalSearchInstanceCount = 0

const props = defineProps<{
  searchScope: string
  placeholder?: string
  suggestionScope: string
  suggestionsEnabled: boolean
  searchModes?: readonly SearchModeOption[]
  activeSearchMode?: string
  searchRedirectName?: string
}>()

const emit = defineEmits(['search', 'clear', 'search-mode-change'])
const uiStore = useUIStore()
const route = useRoute()
const router = useRouter()

const inputValue = ref(uiStore.getSearchQuery(props.searchScope))
const isFocused = ref(false)
const isTyping = ref(false)
const isLoadingSuggestions = ref(false)
const isComposing = ref(false)
const isPanelOpen = ref(false)
const activeSuggestionIndex = ref(-1)
const remoteSuggestions = ref<SearchSuggestionItem[]>([])
const rootRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
const instanceId = `global-search-${++globalSearchInstanceCount}`
const inputId = `${instanceId}-input`
const listboxId = `${instanceId}-listbox`

// ponytail: recent-search history (add/remove/clear + localStorage persistence,
// capped at 10, most-recent-first, de-duped) lives in useSearchHistory.
const {
  recentSearches,
  addRecentSearch,
  removeRecentSearch,
  clearRecentSearches,
} = useSearchHistory(props.searchScope)

let typingTimeout: ReturnType<typeof setTimeout> | undefined
let suggestionTimeout: ReturnType<typeof setTimeout> | undefined
let suggestionRequestId = 0

const trimmedInputValue = computed(() => inputValue.value.trim())
const showSuggestions = computed(() => props.suggestionsEnabled && isPanelOpen.value && isFocused.value)
const searchModesList = computed(() => props.searchModes ?? [])
const activeSearchModeLabel = computed(() => {
  return searchModesList.value.find((mode) => mode.value === props.activeSearchMode)?.label || ''
})
const selectableItems = computed<SuggestionItem[]>(() => [...suggestionItems.value])
const getOptionId = (index: number) => `${instanceId}-option-${index}`
const activeDescendantId = computed(() => {
  if (!showSuggestions.value || activeSuggestionIndex.value < 0 || !selectableItems.value[activeSuggestionIndex.value]) {
    return undefined
  }
  return getOptionId(activeSuggestionIndex.value)
})

watch(() => uiStore.getSearchQuery(props.searchScope), (newVal) => {
  if (newVal !== inputValue.value) inputValue.value = newVal
})

const suggestionItems = computed<SuggestionItem[]>(() => {
  const items: SuggestionItem[] = []
  const seen = new Set<string>()

  remoteSuggestions.value.forEach(s => {
    if (!seen.has(s.value.toLowerCase())) {
      seen.add(s.value.toLowerCase())
      items.push({ id: `r-${s.value}`, type: 'search', value: s.value, label: s.label || s.value, meta: s.meta })
    }
  })

  recentSearches.value.forEach(s => {
    if (!seen.has(s.toLowerCase())) {
      seen.add(s.toLowerCase())
      items.push({ id: `h-${s}`, type: 'recent', value: s, label: s })
    }
  })

  return items.slice(0, 8)
})

const suggestionTitle = computed(() => trimmedInputValue.value ? '搜索建议' : '最近搜索')
const matchedPlaybackProvider = computed(() => findDesktopPlaybackProvider(trimmedInputValue.value))

const handleInput = () => {
  uiStore.setSearchQuery(props.searchScope, inputValue.value)
  activeSuggestionIndex.value = -1
  suggestionRequestId += 1
  isLoadingSuggestions.value = false
  if (isComposing.value) return
  if (!props.suggestionsEnabled) {
    isPanelOpen.value = false
    isTyping.value = false
    remoteSuggestions.value = []
    return
  }
  isPanelOpen.value = true
  isTyping.value = true
  clearTimeout(typingTimeout)
  typingTimeout = setTimeout(() => isTyping.value = false, 400)

  clearTimeout(suggestionTimeout)
  suggestionTimeout = setTimeout(loadRemoteSuggestions, 300)
}

async function loadRemoteSuggestions() {
  const requestId = ++suggestionRequestId
  if (!props.suggestionsEnabled || !trimmedInputValue.value) {
    remoteSuggestions.value = []
    isLoadingSuggestions.value = false
    return
  }
  isLoadingSuggestions.value = true
  try {
    const data = await getSearchSuggestions({ query: trimmedInputValue.value, scope: props.suggestionScope })
    if (requestId === suggestionRequestId) remoteSuggestions.value = data?.items || []
  } catch {
    if (requestId === suggestionRequestId) remoteSuggestions.value = []
  } finally {
    if (requestId === suggestionRequestId) isLoadingSuggestions.value = false
  }
}

function handleEnterKey() {
  if (isComposing.value) return
  if (activeSuggestionIndex.value >= 0) {
    const item = selectableItems.value[activeSuggestionIndex.value]
    if (item) selectSuggestion(item.value)
  } else {
    handleSearch()
  }
}

function selectSuggestion(val: string) {
  inputValue.value = val
  uiStore.setSearchQuery(props.searchScope, val)
  handleSearch()
}

async function handleSearch() {
  const provider = matchedPlaybackProvider.value
  if (provider) {
    const url = trimmedInputValue.value
    const fakeId = `_sandbox_${Date.now()}`
    const site = provider.site
    const isDesktop = isDesktopPlaybackClient()

    let title = url
    let thumbnail: string | undefined
    let uploader = ''
    let uploaderUrl = ''
    let uploaderAvatar = ''
    let subscriptions: SeedSubscription[] = []

    if (isDesktop) {
      try {
        const info = await resolveDesktopPlayback(provider, url, { forceRefresh: true })
        if (info?.title) title = info.title
        if (info?.thumbnail) thumbnail = info.thumbnail
        const uname = info?.uploader_name
        const uurl = info?.uploader_url
        const uavatar = info?.uploader_avatar
        if (uname) {
          uploader = String(uname)
          uploaderUrl = String(uurl || '')
          uploaderAvatar = String(uavatar || '')
          subscriptions = [{ name: uploader, url: uploaderUrl, avatar: uploaderAvatar }]
        }
      } catch { /* keep title as url if resolve fails */ }
    }

    rememberVideoPlaybackSeed({
      id: fakeId,
      url,
      title,
      thumbnail,
      site,
      source: 'remote',
      uploader,
      uploader_url: uploaderUrl,
      uploader_avatar: uploaderAvatar,
      subscriptions,
    })
    isPanelOpen.value = false
    inputRef.value?.blur()
    router.push({ name: 'VideoPlay', params: { videoId: fakeId } })
    return
  }
  if (trimmedInputValue.value) {
    addRecentSearch(trimmedInputValue.value)
  }
  if (props.searchRedirectName) {
    const query: LocationQueryRaw = { ...route.query, q: trimmedInputValue.value }
    if (props.activeSearchMode === 'remote') query.mode = 'remote'
    else {
      delete query.mode
      delete query.site
    }
    await router.push({ name: props.searchRedirectName, query })
  }
  uiStore.triggerSearch(props.searchScope, inputValue.value)
  emit('search')
  isPanelOpen.value = false
  inputRef.value?.blur()
}

function selectMode(mode: string) {
  if (mode === props.activeSearchMode) return
  isPanelOpen.value = false
  emit('search-mode-change', mode)
  inputRef.value?.focus()
}

function toggleMode() {
  if (!props.searchModes) return
  const currentIndex = props.searchModes.findIndex((mode) => mode.value === props.activeSearchMode)
  const nextMode = props.searchModes[(currentIndex + 1) % props.searchModes.length]
  if (nextMode) selectMode(nextMode.value)
}

function clearSearch() {
  suggestionRequestId += 1
  inputValue.value = ''
  remoteSuggestions.value = []
  isLoadingSuggestions.value = false
  activeSuggestionIndex.value = -1
  uiStore.setSearchQuery(props.searchScope, '')
  emit('clear')
  if (route.query.q) {
    const query = { ...route.query }
    delete query.q
    delete query.mode
    delete query.site
    router.replace({ query })
  }
  uiStore.triggerSearch(props.searchScope, '')
  inputRef.value?.focus()
}

function handleCompositionEnd() {
  isComposing.value = false
  handleInput()
}

function removeRecentSearchItem(value: string, index: number) {
  removeRecentSearch(value)
  if (activeSuggestionIndex.value === index) activeSuggestionIndex.value = -1
  else if (activeSuggestionIndex.value > index) activeSuggestionIndex.value -= 1
}

function handleFocusIn(e: FocusEvent) {
  if (rootRef.value?.contains(e.relatedTarget as Node)) return
  isFocused.value = true
  isPanelOpen.value = true
  activeSuggestionIndex.value = -1
  if (trimmedInputValue.value) loadRemoteSuggestions()
}

function handleFocusOut(e: FocusEvent) {
  if (!rootRef.value?.contains(e.relatedTarget as Node)) {
    isFocused.value = false
    isPanelOpen.value = false
  }
}

function moveActiveSuggestion(dir: number) {
  isPanelOpen.value = true
  const len = selectableItems.value.length
  if (len === 0) return
  activeSuggestionIndex.value = (activeSuggestionIndex.value + dir + len) % len
}

function handleEscape() {
  isPanelOpen.value = false
  activeSuggestionIndex.value = -1
}

const handleGlobalKeydown = (e: KeyboardEvent) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    inputRef.value?.focus()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleGlobalKeydown)
})

onUnmounted(() => {
  clearTimeout(typingTimeout)
  clearTimeout(suggestionTimeout)
  suggestionRequestId += 1
  window.removeEventListener('keydown', handleGlobalKeydown)
})
</script>

<style scoped>
.global-search {
  position: relative;
  width: 100%;
  max-width: 40rem;
}

.global-search__box {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  height: 2.25rem;
  padding: 0 0.5rem 0 0.75rem;
  border: 1px solid transparent;
  border-radius: 999px;
  background: hsl(var(--muted) / 0.72);
  transition:
    background-color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default),
    box-shadow var(--duration-fast) var(--ease-default);
}

/* Single outer focus affordance for the composite control.
   Nested input/button focus rings are suppressed below so they do not
   stack with this ring (global :focus-visible + Button ring utilities). */
.global-search__box:focus-within {
  border-color: hsl(var(--foreground) / 0.1);
  background: hsl(var(--card));
  box-shadow: 0 0 0 1px hsl(var(--foreground) / 0.04);
}

/* is-open only while the panel is visible; never override focus chrome. */
.global-search__box.is-open:not(:focus-within) {
  border-color: hsl(var(--border) / 0.35);
  background: hsl(var(--muted) / 0.55);
}

.global-search__leading-icon {
  flex: 0 0 auto;
  width: 0.875rem;
  height: 0.875rem;
  color: hsl(var(--muted-foreground) / 0.55);
  transition: color var(--duration-fast) var(--ease-default);
}

.global-search__box:focus-within .global-search__leading-icon {
  color: hsl(var(--muted-foreground) / 0.78);
}

.global-search__mode-wrap {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
}

.global-search__mode {
  gap: 0.25rem;
  height: 1.375rem;
  min-width: 0;
  padding: 0 0.375rem 0 0.25rem;
  border-radius: 999px;
  border-color: transparent;
  background: transparent;
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: var(--app-text-xs);
  font-weight: 500;
  letter-spacing: 0.01em;
}

.global-search__mode:hover {
  border-color: transparent;
  background: hsl(var(--foreground) / 0.05);
  color: hsl(var(--foreground) / 0.82);
}

/* Neutral ink-wash active — never brand primary */
.global-search__mode[aria-pressed='true'],
.global-search__mode.is-remote {
  background: hsl(var(--foreground) / 0.06);
  color: hsl(var(--foreground) / 0.88);
}

.global-search__mode:active {
  transform: none;
}

.global-search__mode-icon {
  width: 0.8125rem;
  height: 0.8125rem;
  opacity: 0.85;
}

.global-search__mode-label {
  line-height: 1;
}

.global-search__input {
  min-width: 0;
  flex: 1 1 auto;
  height: 100%;
  padding: 0 0.25rem;
  border: 0;
  background: transparent;
  color: hsl(var(--foreground));
  font-size: var(--app-text-base);
  font-weight: 400;
  outline: none;
  box-shadow: none;
}

/* Kill global input :focus-visible ring — parent owns focus chrome. */
.global-search__input:focus,
.global-search__input:focus-visible {
  outline: none;
  box-shadow: none;
}

.global-search__input::placeholder {
  /* Full muted, not /0.5: the half-alpha blend measured ~2:1 on dark and
     read as invisible against the input surface. */
  color: hsl(var(--muted-foreground));
  font-weight: 400;
}

.global-search__actions {
  display: flex;
  align-items: center;
  gap: 0.125rem;
  min-width: 1.5rem;
  justify-content: flex-end;
}

.global-search__loading {
  display: flex;
  align-items: center;
}

.global-search__clear {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 999px;
  color: hsl(var(--muted-foreground) / 0.62);
}

.global-search__clear:hover:not(:disabled) {
  color: hsl(var(--foreground));
  background: hsl(var(--foreground) / 0.06);
}

/* Composite control: internal buttons never paint their own focus ring. */
.global-search__box :deep(button:focus-visible) {
  --tw-ring-shadow: 0 0 #0000;
  --tw-ring-offset-shadow: 0 0 #0000;
  outline: none;
  box-shadow: none;
}

.global-search__suggestions {
  position: absolute;
  top: 100%;
  right: 0;
  left: 0;
  z-index: var(--z-popover);
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  margin-top: 0.5rem;
  padding: 0.375rem;
  border: 1px solid hsl(var(--border) / 0.8);
  border-radius: var(--radius-lg);
  background: hsl(var(--popover));
  color: hsl(var(--popover-foreground));
  box-shadow: var(--app-floating-shadow);
}

.global-search__suggestions-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.25rem;
  padding: 0.375rem 0.5rem;
  color: hsl(var(--muted-foreground) / 0.68);
  font-size: var(--app-text-xs);
  font-weight: 650;
}

.global-search__clear-recent {
  height: auto;
  padding: 0;
  font-size: var(--app-text-xs);
  font-weight: 650;
  color: hsl(var(--destructive));
}

.global-search__suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.global-search__suggestion-row {
  display: flex;
  min-width: 0;
  gap: 0.25rem;
}

.global-search__suggestion {
  min-width: 0;
  flex: 1 1 auto;
  justify-content: flex-start;
  gap: 0.75rem;
  height: auto;
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-md);
  text-align: left;
}

.global-search__suggestion.is-active {
  background: var(--app-selection-bg);
  color: var(--app-selection-fg);
}

.global-search__suggestion-copy {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  flex-direction: column;
}

.global-search__suggestion-label,
.global-search__suggestion-meta {
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.global-search__suggestion-label {
  font-size: var(--app-text-base);
  font-weight: 500;
}

.global-search__suggestion-meta {
  color: hsl(var(--muted-foreground) / 0.6);
  font-size: var(--app-text-xs);
}

.global-search__remove {
  flex: 0 0 auto;
  width: 2rem;
  height: auto;
  border-radius: var(--radius-md);
  color: hsl(var(--muted-foreground) / 0.48);
}

.global-search__remove:hover {
  background: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}

.global-search__empty {
  padding: 2rem;
  color: hsl(var(--muted-foreground) / 0.52);
  font-size: var(--app-text-sm);
  font-weight: 500;
  text-align: center;
}

@media (prefers-reduced-motion: reduce) {
  .global-search__box,
  .global-search__leading-icon,
  .global-search__clear-recent {
    transition: none;
  }
}
</style>
