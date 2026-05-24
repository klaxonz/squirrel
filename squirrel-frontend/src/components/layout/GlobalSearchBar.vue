<template>
  <div ref="rootRef" class="relative w-full max-w-[560px]" @focusin="handleFocusIn" @focusout="handleFocusOut">
    <!-- Search Input Field -->
    <div 
      class="flex items-center h-9 px-3 rounded-lg bg-accent/30 border border-border/20 transition-all duration-300 group focus-within:bg-background focus-within:border-primary/20 focus-within:ring-4 focus-within:ring-primary/5 shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]"
    >
      <AppIcon name="search" class="w-3.5 h-3.5 text-muted-foreground/40 group-focus-within:text-primary transition-colors mr-2.5" :stroke-width="2.5" />
      
      <input
        ref="inputRef"
        v-model="inputValue"
        type="text"
        :placeholder="placeholder"
        class="flex-1 bg-transparent border-none text-[13px] font-medium outline-none placeholder:text-muted-foreground/30"
        @input="handleInput"
        @compositionstart="isComposing = true"
        @compositionend="handleCompositionEnd"
        @keydown.down.prevent="moveActiveSuggestion(1)"
        @keydown.up.prevent="moveActiveSuggestion(-1)"
        @keydown.enter.prevent="handleEnterKey"
        @keydown.esc.prevent="handleEscape"
      />

      <div class="flex items-center gap-2 ml-2">
        <!-- Loading Spinner -->
        <div v-if="isTyping" class="w-3 h-3 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
        
        <!-- Clear Button -->
        <button v-if="inputValue" @click="clearSearch" class="p-1 rounded-md hover:bg-muted text-muted-foreground/60 transition-colors">
          <AppIcon name="close" class="w-3 h-3" />
        </button>
        
        <!-- Kbd Hint (Linear Style) -->
        <button
          v-if="activeSearchModeLabel"
          type="button"
          class="h-6 shrink-0 rounded-md border border-border/50 bg-muted/40 px-2 text-[11px] font-semibold text-muted-foreground/70 transition-colors hover:bg-background hover:text-foreground"
          @click.stop="cycleSearchMode"
        >
          {{ activeSearchModeLabel }}
        </button>

        <div v-else class="hidden md:flex items-center gap-1 px-1.5 py-0.5 rounded border border-border/60 bg-muted/50 text-[10px] font-bold text-muted-foreground/40 tracking-tighter">
          <span class="text-[11px] leading-none">⌘</span>K
        </div>
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

        <div v-if="searchActionItems.length" class="grid grid-cols-2 gap-1 px-1 pb-1">
          <button
            v-for="(item, index) in searchActionItems"
            :key="item.id"
            type="button"
            class="flex min-w-0 items-center gap-2 rounded-lg px-3 py-2 text-left transition-colors"
            :class="index === activeSuggestionIndex ? 'bg-secondary text-foreground' : 'text-muted-foreground/80 hover:bg-secondary/50 hover:text-foreground'"
            @mouseenter="activeSuggestionIndex = index"
            @click="searchWithMode(item.mode)"
          >
            <AppIcon name="search" class="h-3.5 w-3.5 shrink-0 opacity-60" />
            <div class="min-w-0">
              <span class="block truncate text-[12px] font-semibold">{{ item.label }}</span>
              <span class="block truncate text-[10px] opacity-50">{{ item.meta }}</span>
            </div>
          </button>
        </div>

        <div v-for="(item, index) in suggestionItems" :key="item.id" class="flex min-w-0 gap-1">
          <button
            class="flex min-w-0 flex-1 items-center gap-3 rounded-xl px-3 py-2 text-left transition-all"
            :class="index + searchActionItems.length === activeSuggestionIndex ? 'bg-secondary text-foreground' : 'hover:bg-secondary/50 text-muted-foreground/80'"
            @mouseenter="activeSuggestionIndex = index + searchActionItems.length"
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
        
        <div v-if="!searchActionItems.length && !suggestionItems.length" class="p-8 text-center text-[12px] text-muted-foreground/40 font-medium">暂无搜索记录</div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch, type PropType } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import { getSearchSuggestions } from '@/api/search'
import { useUIStore } from '@/stores/ui'

type SearchModeOption = {
  value: string
  label: string
}

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '搜索或输入命令...' },
  suggestionScope: { type: String, default: 'home' },
  searchModes: { type: Array as PropType<readonly SearchModeOption[]>, default: () => [] },
  activeSearchMode: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'search', 'clear', 'search-mode-change'])
const uiStore = useUIStore()

const inputValue = ref(uiStore.searchQuery)
const isFocused = ref(false)
const isTyping = ref(false)
const isComposing = ref(false)
const isPanelOpen = ref(false)
const activeSuggestionIndex = ref(-1)
const recentSearches = ref<string[]>([])
const remoteSuggestions = ref<any[]>([])
const rootRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)

let typingTimeout: any = null
let suggestionTimeout: any = null

const trimmedInputValue = computed(() => inputValue.value.trim())
const showSuggestions = computed(() => isPanelOpen.value && isFocused.value)
const activeSearchModeLabel = computed(() => {
  return props.searchModes.find((mode) => mode.value === props.activeSearchMode)?.label || ''
})
const searchActionItems = computed(() => {
  if (!trimmedInputValue.value) return []
  return props.searchModes.map((mode) => ({
    id: `mode-${mode.value}`,
    type: 'mode',
    mode: mode.value,
    label: `${mode.label}搜索`,
    meta: trimmedInputValue.value,
  }))
})
const selectableItems = computed(() => [...searchActionItems.value, ...suggestionItems.value])

watch(() => uiStore.searchQuery, (newVal) => {
  if (newVal !== inputValue.value) inputValue.value = newVal
})

const suggestionItems = computed(() => {
  const items: any[] = []
  const seen = new Set()
  
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
  } catch (_) {
    remoteSuggestions.value = []
  }
}

function handleEnterKey() {
  if (isComposing.value) return
  if (activeSuggestionIndex.value >= 0) {
    const item = selectableItems.value[activeSuggestionIndex.value]
    if (item?.type === 'mode') {
      searchWithMode(item.mode)
    } else if (item?.value) {
      selectSuggestion(item.value)
    }
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

function handleSearch() {
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

function searchWithMode(mode: string) {
  emit('search-mode-change', mode)
  handleSearch()
}

function cycleSearchMode() {
  if (props.searchModes.length < 2) return
  const currentIndex = props.searchModes.findIndex((mode) => mode.value === props.activeSearchMode)
  const nextMode = props.searchModes[(currentIndex + 1) % props.searchModes.length]
  emit('search-mode-change', nextMode.value)
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
