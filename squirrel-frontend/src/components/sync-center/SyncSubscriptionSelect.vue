<template>
  <div ref="rootRef" class="relative">
    <button
      type="button"
      class="flex w-full items-center justify-between rounded-md border border-input bg-background px-3 pr-8 text-left text-xs text-foreground shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      :class="props.size === 'sm' ? 'h-8' : 'h-9'"
      :aria-expanded="isOpen ? 'true' : 'false'"
      @click="toggle"
      @keydown="handleTriggerKeydown"
    >
      <div class="flex min-w-0 items-center gap-2">
        <img
          v-if="selectedOption?.avatar"
          :src="getAvatarSrc(selectedOption.avatar, `subscription-trigger-${selectedOption.value}`)"
          :alt="selectedOption.label"
          class="h-4 w-4 shrink-0 rounded-full object-cover ring-1 ring-border"
          referrerpolicy="no-referrer"
          @error="(event) => handleAvatarError(event, `subscription-trigger-${selectedOption?.value || 'unknown'}`)"
        >
        <span class="truncate" :class="selectedOption ? 'text-foreground' : 'text-muted-foreground'">
          {{ selectedOption?.label || placeholder }}
        </span>
      </div>
      <span
        class="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-transform duration-150"
        :class="isOpen ? 'rotate-180' : ''"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </span>
    </button>

    <transition name="select-fade">
      <div
        v-if="isOpen"
        class="absolute z-20 mt-2 w-full overflow-hidden rounded-xl border border-border bg-card shadow-2xl"
      >
        <div class="border-b border-border p-2">
          <input
            ref="searchInputRef"
            v-model="searchQuery"
            type="text"
            placeholder="搜索频道"
            class="w-full rounded-md border border-border bg-background px-3 py-2 text-xs text-foreground outline-none transition-colors focus:border-border focus:ring-1 focus:ring-border"
            @keydown.escape.stop="close"
          >
        </div>

        <div class="max-h-72 overflow-y-auto py-2">
          <button
            type="button"
            class="mx-2 flex w-[calc(100%-1rem)] items-center justify-between rounded-md px-3 py-2 text-left text-sm transition-colors"
            :class="isSelected(allOption) ? 'bg-muted font-medium text-foreground' : 'text-foreground hover:bg-accent'"
            @click="selectOption(allOption)"
          >
            <span class="truncate">{{ allOption.label }}</span>
            <span v-if="isSelected(allOption)" class="text-xs text-muted-foreground/70">✓</span>
          </button>

          <button
            v-for="option in filteredOptions"
            :key="option.value"
            type="button"
            class="mx-2 mt-1 flex w-[calc(100%-1rem)] items-center justify-between rounded-md px-3 py-2 text-left text-sm transition-colors"
            :class="isSelected(option) ? 'bg-muted font-medium text-foreground' : 'text-foreground hover:bg-accent'"
            @click="selectOption(option)"
          >
            <div class="flex min-w-0 items-center gap-2">
              <img
                :src="getAvatarSrc(option.avatar, `subscription-option-${option.value}`)"
                :alt="option.label"
                class="h-6 w-6 shrink-0 rounded-full object-cover ring-1 ring-border"
                referrerpolicy="no-referrer"
                @error="(event) => handleAvatarError(event, `subscription-option-${option.value}`)"
              >
              <span class="truncate">{{ option.label }}</span>
            </div>
            <span v-if="isSelected(option)" class="text-xs text-muted-foreground/70">✓</span>
          </button>

          <div v-if="!filteredOptions.length" class="px-3 py-3 text-xs text-muted-foreground">
            没有匹配的频道
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useDropdown } from '@/composables/useDropdown'
import { useImageFallback } from '@/composables/useImageFallback'

interface SubscriptionOption {
  value: string
  label: string
  avatar: string | null
}

const props = withDefaults(defineProps<{
  modelValue: string
  options: SubscriptionOption[]
  placeholder?: string
  size?: 'sm' | 'md'
}>(), {
  placeholder: '全部频道',
  size: 'md',
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const { close, isOpen, rootRef, toggle } = useDropdown({ closeOnEscape: true })
const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback()
const searchInputRef = ref<HTMLInputElement | null>(null)
const searchQuery = ref('')

const allOption = computed<SubscriptionOption>(() => {
  return props.options.find((option) => option.value === '') || { value: '', label: props.placeholder, avatar: null }
})

const selectedOption = computed(() => {
  return props.options.find((option) => String(option.value) === String(props.modelValue)) || null
})

const filteredOptions = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase()
  return props.options
    .filter((option) => option.value !== '')
    .filter((option) => !keyword || option.label.toLowerCase().includes(keyword))
})

const isSelected = (option: SubscriptionOption) => String(option.value) === String(props.modelValue)

const selectOption = (option: SubscriptionOption) => {
  emit('update:modelValue', option.value)
  searchQuery.value = ''
  close()
}

const handleTriggerKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    toggle()
    return
  }
  if (event.key === 'Escape') {
    close()
  }
}

watch(isOpen, async (open) => {
  if (!open) {
    searchQuery.value = ''
    return
  }
  await nextTick()
  searchInputRef.value?.focus()
})
</script>

<style scoped>
.select-fade-enter-active,
.select-fade-leave-active {
  transition: opacity 150ms ease, transform 150ms ease;
}

.select-fade-enter-from,
.select-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
