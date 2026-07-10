<template>
  <div ref="rootRef" class="global-search" @focusin="handleFocusIn" @focusout="handleFocusOut">
    <div class="global-search__box" :class="{ 'is-open': showSuggestions }">
      <div v-if="searchModesList.length > 0" class="global-search__mode-wrap">
        <Button
          type="button"
          variant="ghost"
          size="xs"
          class="global-search__mode"
          :aria-pressed="activeSearchMode === 'remote'"
          :aria-label="`搜索范围：${activeSearchModeLabel}`"
          @click="toggleMode"
        >
          <AppIcon :name="activeSearchMode === 'local' ? 'library' : 'siteFallback'" class="w-3.5 h-3.5" />
          {{ activeSearchModeLabel }}
        </Button>
      </div>
      
      <div v-if="searchModesList.length > 0" class="global-search__divider" />
      <AppIcon v-else name="search" class="global-search__leading-icon" :stroke-width="2.5" />
      
      <input
        ref="inputRef"
        v-model="inputValue"
        type="text"
        :placeholder="placeholder"
        class="global-search__input"
        @input="handleInput"
        @compositionstart="isComposing = true"
        @compositionend="handleCompositionEnd"
        @keydown.down.prevent="moveActiveSuggestion(1)"
        @keydown.up.prevent="moveActiveSuggestion(-1)"
        @keydown.enter.prevent="handleEnterKey"
        @keydown.esc.prevent="handleEscape"
      />

      <div class="global-search__actions">
        <AppSpinner v-if="isTyping" size="sm" />
        
        <Button v-if="inputValue" variant="ghost" size="mini-icon" class="global-search__icon-button" @click="clearSearch">
          <AppIcon name="close" class="w-3.5 h-3.5" />
        </Button>
        
        <Button
          type="button"
          variant="ghost"
          size="mini-icon"
          class="global-search__icon-button"
          :disabled="!trimmedInputValue"
          title="搜索"
          @mousedown.prevent
          @click="handleSearch"
        >
          <AppIcon name="search" class="h-3.5 w-3.5" />
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
        role="listbox"
        :aria-label="suggestionTitle"
      >
        <div class="global-search__suggestions-header">
          <span>{{ suggestionTitle }}</span>
          <Button v-if="recentSearches.length" variant="link" size="xs" class="global-search__clear-recent" @click="clearRecentSearches">清空</Button>
        </div>



        <div v-for="(item, index) in suggestionItems" :key="item.id" class="global-search__suggestion-row">
          <Button
            variant="ghost"
            size="default"
            class="global-search__suggestion"
            :class="{ 'is-active': index === activeSuggestionIndex }"
            @mouseenter="activeSuggestionIndex = index"
            @click="selectSuggestion(item.value)"
          >
            <AppIcon :name="item.type === 'search' ? 'search' : 'history'" class="h-4 w-4 shrink-0 opacity-50" />
            <div class="global-search__suggestion-copy">
              <span class="global-search__suggestion-label">{{ item.label }}</span>
              <span v-if="item.meta" class="global-search__suggestion-meta">{{ item.meta }}</span>
            </div>
          </Button>
          <Button v-if="item.type === 'recent'" variant="ghost" size="icon-sm" class="global-search__remove" @click.stop="removeRecentSearch(item.value)">
            <AppIcon name="close" class="w-3.5 h-3.5" />
          </Button>
        </div>
        
        <div v-if="!suggestionItems.length" class="global-search__empty">暂无搜索记录</div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
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
const isComposing = ref(false)
const isPanelOpen = ref(false)
const activeSuggestionIndex = ref(-1)
const remoteSuggestions = ref<SearchSuggestionItem[]>([])
const rootRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)

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

const trimmedInputValue = computed(() => inputValue.value.trim())
const showSuggestions = computed(() => props.suggestionsEnabled && isPanelOpen.value && isFocused.value)
const searchModesList = computed(() => props.searchModes ?? [])
const activeSearchModeLabel = computed(() => {
  return searchModesList.value.find((mode) => mode.value === props.activeSearchMode)?.label || ''
})
const selectableItems = computed<SuggestionItem[]>(() => [...suggestionItems.value])

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
  if (!props.suggestionsEnabled || !trimmedInputValue.value) {
    remoteSuggestions.value = []
    return
  }
  try {
    const data = await getSearchSuggestions({ query: trimmedInputValue.value, scope: props.suggestionScope })
    remoteSuggestions.value = data?.items || []
  } catch {
    remoteSuggestions.value = []
  }
}

function handleEnterKey() {
  if (isComposing.value) return
  if (activeSuggestionIndex.value >= 0) {
    const item = selectableItems.value[activeSuggestionIndex.value]
      selectSuggestion(item.value)
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
  inputValue.value = ''
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
  inputRef.value?.blur()
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
  window.removeEventListener('keydown', handleGlobalKeydown)
})
</script>

<style scoped>
.global-search {
  position: relative;
  width: 100%;
  max-width: 35rem;
}

.global-search__box {
  display: flex;
  align-items: center;
  gap: 0.125rem;
  height: 2.25rem;
  padding: 0.1875rem 0.25rem 0.1875rem 0.1875rem;
  border: 1px solid hsl(var(--border) / 0.45);
  border-radius: var(--radius-md);
  background: hsl(var(--card) / 0.55);
  transition:
    background-color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default),
    box-shadow var(--duration-fast) var(--ease-default);
}

/* Single outer focus affordance for the composite control.
   Nested input/button focus rings are suppressed below so they do not
   stack with this ring (global :focus-visible + Button ring utilities). */
.global-search__box:focus-within {
  border-color: hsl(var(--ring));
  background: hsl(var(--card) / 0.78);
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.22);
}

/* is-open only while the panel is visible; never override focus chrome. */
.global-search__box.is-open:not(:focus-within) {
  border-color: hsl(var(--border) / 0.65);
}

.global-search__mode-wrap {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
}

.global-search__mode {
  gap: 0.3125rem;
  height: 1.875rem;
  padding: 0 0.5rem;
  border-radius: calc(var(--radius-md) - 1px);
  border-color: transparent;
  background: hsl(var(--secondary) / 0.72);
  color: hsl(var(--foreground) / 0.88);
  font-size: 0.75rem;
  font-weight: 650;
  letter-spacing: 0.01em;
}

.global-search__mode:hover {
  border-color: transparent;
  background: hsl(var(--secondary));
  color: hsl(var(--foreground));
}

.global-search__mode:active {
  transform: none;
}

.global-search__divider {
  flex: 0 0 auto;
  width: 1px;
  height: 1rem;
  margin: 0 0.25rem 0 0.125rem;
  background: hsl(var(--border) / 0.72);
  border-radius: 1px;
}

.global-search__leading-icon {
  width: 0.875rem;
  height: 0.875rem;
  margin: 0 0.375rem 0 0.5rem;
  color: hsl(var(--muted-foreground) / 0.48);
  transition: color var(--duration-fast) var(--ease-default);
}

.global-search__box:focus-within .global-search__leading-icon {
  color: hsl(var(--primary));
}

.global-search__input {
  min-width: 0;
  flex: 1 1 auto;
  height: 100%;
  padding: 0 0.375rem;
  border: 0;
  background: transparent;
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  font-weight: 500;
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
  color: hsl(var(--muted-foreground) / 0.52);
}

.global-search__actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding-right: 0.125rem;
}

.global-search__icon-button {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 0.375rem;
  color: hsl(var(--muted-foreground) / 0.72);
}

.global-search__icon-button:hover:not(:disabled) {
  color: hsl(var(--foreground));
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
  font-size: 0.6875rem;
  font-weight: 650;
}

.global-search__clear-recent {
  height: auto;
  padding: 0;
  font-size: 0.6875rem;
  font-weight: 650;
  color: hsl(var(--destructive));
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
  border-radius: 0.5rem;
  text-align: left;
}

.global-search__suggestion.is-active {
  background: hsl(var(--secondary));
  color: hsl(var(--foreground));
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
  font-size: 0.875rem;
  font-weight: 500;
}

.global-search__suggestion-meta {
  color: hsl(var(--muted-foreground) / 0.6);
  font-size: 0.6875rem;
}

.global-search__remove {
  flex: 0 0 auto;
  width: 2rem;
  height: auto;
  border-radius: 0.5rem;
  color: hsl(var(--muted-foreground) / 0.48);
}

.global-search__remove:hover {
  background: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}

.global-search__empty {
  padding: 2rem;
  color: hsl(var(--muted-foreground) / 0.52);
  font-size: 0.75rem;
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
