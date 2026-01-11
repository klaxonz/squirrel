<template>
  <div ref="rootRef" class="select-wrapper relative">
    <button
      :id="selectId"
      type="button"
      :disabled="disabled"
      :aria-expanded="isOpen ? 'true' : 'false'"
      :aria-controls="menuId"
      :class="[
        'select-trigger w-full text-left bg-bg-secondary border text-text-primary transition-colors duration-150 focus:outline-none focus:ring-1 disabled:opacity-50 disabled:cursor-not-allowed relative',
        sizeClasses.trigger,
        error ? 'border-color-error ring-1 ring-color-error focus:border-color-error focus:ring-color-error' : 'border-border-primary focus:border-border-hover focus:ring-border-hover'
      ]"
      @click="toggleOpen"
      @keydown="onKeydown"
    >
      <span
        :class="[
          'block truncate',
          hasValue ? 'text-text-primary' : 'text-text-muted'
        ]"
      >
        {{ displayLabel }}
      </span>
      <span
        :class="[
          'absolute right-3 pointer-events-none text-text-muted transition-transform duration-150',
          sizeClasses.icon,
          isOpen ? 'rotate-180' : ''
        ]"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </span>
    </button>

    <transition name="select-fade">
      <div
        v-if="isOpen"
        :id="menuId"
        class="select-menu absolute z-20 mt-2 w-full rounded-xl border border-border-secondary bg-bg-secondary shadow-2xl overflow-hidden"
      >
        <ul class="select-scroll max-h-64 overflow-y-auto py-2">
          <li v-for="option in normalizedOptions" :key="option.value" class="px-2">
            <button
              type="button"
              class="w-full text-left px-3 py-2 text-sm rounded-md transition-colors"
              :class="[
                option.disabled ? 'text-text-tertiary cursor-not-allowed' : 'text-text-primary hover:bg-bg-hover',
                isSelected(option) ? 'bg-bg-elevated font-medium' : ''
              ]"
              :disabled="option.disabled"
              @click="selectOption(option)"
            >
              <div class="flex items-center justify-between">
                <span class="truncate">{{ option.label }}</span>
                <span v-if="isSelected(option)" class="text-text-tertiary text-xs">✓</span>
              </div>
            </button>
          </li>
        </ul>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number, Boolean],
    default: ''
  },
  options: {
    type: Array,
    required: true,
    validator: (options) => {
      return options.every(opt => {
        if (typeof opt === 'string' || typeof opt === 'number') return true
        return opt && typeof opt.value !== 'undefined' && typeof opt.label !== 'undefined'
      })
    }
  },
  placeholder: {
    type: String,
    default: ''
  },
  disabled: {
    type: Boolean,
    default: false
  },
  error: {
    type: Boolean,
    default: false
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value)
  },
  selectId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

const rootRef = ref(null)
const isOpen = ref(false)

const menuId = computed(() => (props.selectId ? `${props.selectId}-menu` : 'select-menu'))

const normalizedOptions = computed(() => {
  return props.options.map(opt => {
    if (typeof opt === 'string' || typeof opt === 'number') {
      return { value: opt, label: String(opt), disabled: false }
    }
    return { ...opt, disabled: !!opt.disabled }
  })
})

const selectedOption = computed(() => {
  return normalizedOptions.value.find(opt => String(opt.value) === String(props.modelValue))
})

const hasValue = computed(() => {
  return selectedOption.value || !(props.modelValue === '' || props.modelValue === null || props.modelValue === undefined)
})

const displayLabel = computed(() => {
  if (selectedOption.value) return selectedOption.value.label
  return props.placeholder || '请选择'
})

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return { trigger: 'px-2.5 py-1.5 pr-8 text-xs rounded-md', icon: 'top-1.5' }
    case 'lg':
      return { trigger: 'px-4 py-3 pr-10 text-base rounded-lg', icon: 'top-3.5' }
    default:
      return { trigger: 'px-3 py-2 pr-9 text-sm rounded-lg', icon: 'top-2.5' }
  }
})

const isSelected = (option) => {
  return String(option.value) === String(props.modelValue)
}

const selectOption = (option) => {
  if (option.disabled) return
  emit('update:modelValue', option.value)
  isOpen.value = false
}

const toggleOpen = () => {
  if (props.disabled) return
  isOpen.value = !isOpen.value
}

const onKeydown = (event) => {
  if (props.disabled) return
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    toggleOpen()
  }
  if (event.key === 'Escape') {
    isOpen.value = false
  }
}

const handleClickOutside = (event) => {
  if (!rootRef.value) return
  if (!rootRef.value.contains(event.target)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
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

.select-scroll::-webkit-scrollbar {
  width: 8px;
}

.select-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.select-scroll::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: 9999px;
}

.select-scroll::-webkit-scrollbar-thumb:hover {
  background: var(--scrollbar-thumb-hover);
}
</style>
