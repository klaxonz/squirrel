<template>
  <div ref="rootRef" class="relative w-full max-w-[560px]" @focusin="handleFocusIn" @focusout="handleFocusOut">
    <!-- Search Input Field -->
    <div 
      class="flex items-center h-9 p-1 rounded-lg bg-accent/30 border border-border/20 transition-all duration-300 group focus-within:bg-background focus-within:border-primary/20 focus-within:ring-4 focus-within:ring-primary/5 shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]"
    >
      <!-- Scope Toggle (Local/Remote) -->
      <div v-if="searchModesList.length > 0" class="shrink-0">
        <button
          type="button"
          class="inline-flex h-7 items-center gap-1.5 rounded-md px-2.5 text-[12px] font-bold text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          @click="toggleMode"
        >
          <AppIcon :name="activeSearchMode === 'local' ? 'library' : 'siteFallback'" class="w-3.5 h-3.5" />
          {{ activeSearchModeLabel }}
        </button>
      </div>
      
      <div v-if="searchModesList.length > 0" class="w-px h-3 bg-border/40 mx-1.5 shrink-0" />
      <AppIcon v-else name="search" class="w-3.5 h-3.5 text-muted-foreground/40 group-focus-within:text-primary transition-colors ml-2 mr-1.5" :stroke-width="2.5" />
      
      <input
        ref="inputRef"
        v-model="inputValue"
        type="text"
        :placeholder="placeholder"
        class="flex-1 bg-transparent border-none px-1 text-[13px] font-medium outline-none placeholder:text-muted-foreground/30 min-w-0"
        @input="handleInput"
        @compositionstart="isComposing = true"
        @compositionend="handleCompositionEnd"
        @keydown.down.prevent="moveActiveSuggestion(1)"
        @keydown.up.prevent="moveActiveSuggestion(-1)"
        @keydown.enter.prevent="handleEnterKey"
        @keydown.esc.prevent="handleEscape"
      />

      <div class="flex items-center gap-1.5 pr-1">
        <!-- Loading Spinner -->
        <div v-if="isTyping" class="w-3 h-3 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
        
        <!-- Clear Button -->
        <button v-if="inputValue" @click="clearSearch" class="p-1 rounded-md hover:bg-muted text-muted-foreground/60 transition-colors">
          <AppIcon name="close" class="w-3.5 h-3.5" />
        </button>
        
        <button
          type="button"
          class="inline-flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground/60 transition-colors hover:bg-muted hover:text-foreground disabled:pointer-events-none disabled:opacity-30"
          :disabled="!trimmedInputValue"
          title="搜索"
          @mousedown.prevent
          @click="handleSearch"
        >
          <AppIcon name="search" class="h-3.5 w-3.5" />
        </button>
      </div>
    </div>

    <!-- Suggestions Dropdown -->
    <transition 
      enter-active-class="transition duration-200 ease-out" 
      enter-from-class="opacity-0 translate-y-1" 
      enter-to-class="opacity-100 translate-y-0" 
      leave-active-class="transition duration-150 ease-in" 
      leave-from-class="opacity-100 translate-y-0" 
      leave-to-class="opacity-0 translate-y-1"
    >
      <div v-if="showSuggestions" class="absolute top-full left-0 right-0 z-50 mt-2 flex flex-col gap-0.5 rounded-xl border border-border/60 bg-popover p-1.5 text-popover-foreground shadow-[0_18px_50px_-20px_rgba(0,0,0,0.35),0_8px_24px_-16px_rgba(0,0,0,0.25)]">
        <div class="flex items-center justify-between px-2 py-1.5 mb-1">
          <span class="text-[10px] font-bold tracking-widest uppercase text-muted-foreground/50">{{ suggestionTitle }}</span>
          <button v-if="recentSearches.length" @click="clearRecentSearches" class="text-[10px] font-bold text-muted-foreground/40 hover:text-destructive transition-colors uppercase">清空</button>
        </div>



        <div v-for="(item, index) in suggestionItems" :key="item.id" class="flex min-w-0 gap-1">
          <button
            class="flex min-w-0 flex-1 items-center gap-3 rounded-xl px-3 py-2 text-left transition-all"
            :class="index === activeSuggestionIndex ? 'bg-secondary text-foreground' : 'hover:bg-secondary/50 text-muted-foreground/80'"
            @mouseenter="activeSuggestionIndex = index"
            @click="selectSuggestion(item.value)"
          >
            <AppIcon :name="item.type === 'search' ? 'search' : 'history'" class="h-4 w-4 shrink-0 opacity-50" />
            <div class="flex min-w-0 flex-1 flex-col">
              <span class="block max-w-full truncate text-[13px] font-medium">{{ item.label }}</span>
              <span v-if="item.meta" class="block max-w-full truncate text-[10px] opacity-50">{{ item.meta }}</span>
            </div>
          </button>
          <button v-if="item.type === 'recent'" @click.stop="removeRecentSearch(item.value)" class="flex w-8 shrink-0 items-center justify-center rounded-xl text-muted-foreground/40 transition-colors hover:bg-destructive/10 hover:text-destructive">
            <AppIcon name="close" class="w-3.5 h-3.5" />
          </button>
        </div>
        
        <div v-if="!suggestionItems.length" class="p-8 text-center text-[12px] text-muted-foreground/40 font-medium">暂无搜索记录</div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { getSearchSuggestions } from '@/shared/api/search'
import type { SearchSuggestionItem } from '@/shared/api/search'
import { rememberVideoPlaybackSeed } from '@/features/video/composables/videoPlaybackSeed'
import {
  findDesktopPlaybackProvider,
  resolveDesktopPlayback,
  isDesktopPlaybackClient,
} from '@/features/video/composables/useVideoOperations'
import { useUIStore } from '@/shared/stores/ui'

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
  modelValue?: string
  placeholder?: string
  suggestionScope?: string
  searchModes?: readonly SearchModeOption[]
  activeSearchMode?: string
}>()

const emit = defineEmits(['update:modelValue', 'search', 'clear', 'search-mode-change'])
const uiStore = useUIStore()
const router = useRouter()

const inputValue = ref(uiStore.searchQuery)
const isFocused = ref(false)
const isTyping = ref(false)
const isComposing = ref(false)
const isPanelOpen = ref(false)
const activeSuggestionIndex = ref(-1)
const recentSearches = ref<string[]>([])
const remoteSuggestions = ref<SearchSuggestionItem[]>([])
const rootRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)

let typingTimeout: ReturnType<typeof setTimeout> | undefined
let suggestionTimeout: ReturnType<typeof setTimeout> | undefined

const trimmedInputValue = computed(() => inputValue.value.trim())
const showSuggestions = computed(() => isPanelOpen.value && isFocused.value)
const searchModesList = computed(() => props.searchModes ?? [])
const activeSearchModeLabel = computed(() => {
  return searchModesList.value.find((mode) => mode.value === props.activeSearchMode)?.label || ''
})
const selectableItems = computed<SuggestionItem[]>(() => [...suggestionItems.value])

watch(() => uiStore.searchQuery, (newVal) => {
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
  uiStore.searchQuery = inputValue.value
  emit('update:modelValue', inputValue.value)
  activeSuggestionIndex.value = -1
  isPanelOpen.value = true
  isTyping.value = true
  clearTimeout(typingTimeout)
  typingTimeout = setTimeout(() => isTyping.value = false, 400)
  
  clearTimeout(suggestionTimeout)
  suggestionTimeout = setTimeout(loadRemoteSuggestions, 300)
}

async function loadRemoteSuggestions() {
  if (!trimmedInputValue.value) {
    remoteSuggestions.value = []
    return
  }
  try {
    const { data } = await getSearchSuggestions({ query: trimmedInputValue.value, scope: props.suggestionScope })
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
  uiStore.searchQuery = val
  emit('update:modelValue', val)
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
    const next = [trimmedInputValue.value, ...recentSearches.value.filter(s => s !== trimmedInputValue.value)].slice(0, 10)
    recentSearches.value = next
    localStorage.setItem('search-history', JSON.stringify(next))
  }
  uiStore.triggerSearch(inputValue.value)
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
  uiStore.searchQuery = ''
  emit('update:modelValue', '')
  emit('clear')
  uiStore.triggerSearch('')
  inputRef.value?.focus()
}

function handleCompositionEnd() {
  isComposing.value = false
  handleInput()
}

function clearRecentSearches() {
  recentSearches.value = []
  localStorage.removeItem('search-history')
}

function removeRecentSearch(val: string) {
  recentSearches.value = recentSearches.value.filter(s => s !== val)
  localStorage.setItem('search-history', JSON.stringify(recentSearches.value))
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
  const saved = localStorage.getItem('search-history')
  if (saved) recentSearches.value = JSON.parse(saved)
  window.addEventListener('keydown', handleGlobalKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
})
</script>
