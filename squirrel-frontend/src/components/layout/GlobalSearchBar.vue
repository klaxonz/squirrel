<template>
  <div ref="rootRef" class="relative w-full max-w-[560px]" @focusin="isFocused = true" @focusout="handleFocusOut">
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
      <div v-if="showSuggestions" class="absolute top-full left-0 right-0 mt-2 p-1.5 bg-popover border border-border/60 rounded-2xl shadow-2xl z-50 flex flex-col gap-0.5">
        <div class="flex items-center justify-between px-2 py-1.5 mb-1">
          <span class="text-[10px] font-bold tracking-widest uppercase text-muted-foreground/50">{{ suggestionTitle }}</span>
          <button v-if="recentSearches.length" @click="clearRecentSearches" class="text-[10px] font-bold text-muted-foreground/40 hover:text-destructive transition-colors uppercase">Clear</button>
        </div>

        <div v-for="(item, index) in suggestionItems" :key="item.id" class="flex gap-1">
          <button
            class="flex-1 flex items-center gap-3 px-3 py-2 rounded-xl text-left transition-all"
            :class="index === activeSuggestionIndex ? 'bg-secondary text-foreground' : 'hover:bg-secondary/50 text-muted-foreground/80'"
            @mouseenter="activeSuggestionIndex = index"
            @click="selectSuggestion(item.value)"
          >
            <AppIcon :name="item.type === 'search' ? 'search' : 'history'" class="w-4 h-4 opacity-50" />
            <div class="flex flex-col min-w-0">
              <span class="text-[13px] font-medium truncate">{{ item.label }}</span>
              <span v-if="item.meta" class="text-[10px] opacity-50 truncate">{{ item.meta }}</span>
            </div>
          </button>
          <button v-if="item.type === 'recent'" @click.stop="removeRecentSearch(item.value)" class="w-8 flex items-center justify-center rounded-xl hover:bg-destructive/10 hover:text-destructive text-muted-foreground/40 transition-colors">
            <AppIcon name="close" class="w-3.5 h-3.5" />
          </button>
        </div>
        
        <div v-if="!suggestionItems.length" class="p-8 text-center text-[12px] text-muted-foreground/40 font-medium">No recent searches</div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import { getSearchSuggestions } from '@/api/search'
import { useUIStore } from '@/stores/ui'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: 'Search or type a command...' },
  suggestionScope: { type: String, default: 'home' }
})

const emit = defineEmits(['update:modelValue', 'search', 'clear'])
const uiStore = useUIStore()

const inputValue = ref(uiStore.searchQuery)
const isFocused = ref(false)
const isTyping = ref(false)
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

const suggestionTitle = computed(() => trimmedInputValue.value ? 'Suggestions' : 'Recent')

const handleInput = () => {
  uiStore.searchQuery = inputValue.value
  emit('update:modelValue', inputValue.value)
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
  const { data } = await getSearchSuggestions({ query: trimmedInputValue.value, scope: props.suggestionScope })
  remoteSuggestions.value = data?.items || []
}

function handleEnterKey() {
  if (activeSuggestionIndex.value >= 0) {
    selectSuggestion(suggestionItems.value[activeSuggestionIndex.value].value)
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

function clearSearch() {
  inputValue.value = ''
  uiStore.searchQuery = ''
  emit('update:modelValue', '')
  emit('clear')
  inputRef.value?.focus()
}

function clearRecentSearches() {
  recentSearches.value = []
  localStorage.removeItem('search-history')
}

function removeRecentSearch(val: string) {
  recentSearches.value = recentSearches.value.filter(s => s !== val)
  localStorage.setItem('search-history', JSON.stringify(recentSearches.value))
}

function handleFocusOut(e: FocusEvent) {
  if (!rootRef.value?.contains(e.relatedTarget as Node)) {
    isFocused.value = false
    isPanelOpen.value = false
  }
}

function moveActiveSuggestion(dir: number) {
  isPanelOpen.value = true
  const len = suggestionItems.value.length
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
