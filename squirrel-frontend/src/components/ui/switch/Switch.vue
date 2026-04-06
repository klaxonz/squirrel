<script setup lang="ts">
import type { SwitchRootProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { computed } from 'vue'
import { reactiveOmit } from '@vueuse/core'
import {
  SwitchRoot,
  SwitchThumb,
} from 'reka-ui'
import { cn } from '@/lib/utils'

type SwitchProps = Omit<SwitchRootProps<boolean>, 'modelValue'> & {
  class?: HTMLAttributes['class']
  checked?: boolean | null
  modelValue?: boolean | null
}

const props = defineProps<SwitchProps>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'update:checked': [value: boolean]
}>()

const delegatedProps = reactiveOmit(props, 'class', 'checked', 'modelValue')

const resolvedModelValue = computed(() => {
  if (props.modelValue !== undefined) {
    return props.modelValue
  }
  if (props.checked !== undefined) {
    return props.checked
  }
  return undefined
})

const handleUpdate = (value: boolean) => {
  emit('update:modelValue', value)
  emit('update:checked', value)
}
</script>

<template>
  <SwitchRoot
    v-bind="delegatedProps"
    :model-value="resolvedModelValue"
    :class="cn(
      'peer inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border border-border/70 bg-input/75 shadow-[0_10px_24px_hsl(var(--surface-shadow))] transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:border-primary/30 data-[state=checked]:bg-primary data-[state=unchecked]:bg-input/75',
      props.class,
    )"
    @update:model-value="handleUpdate"
  >
    <SwitchThumb
      :class="cn('pointer-events-none block h-5 w-5 rounded-full bg-background shadow-[0_8px_18px_hsl(var(--surface-shadow))] ring-0 transition-transform duration-200 data-[state=checked]:translate-x-5 data-[state=unchecked]:translate-x-0')"
    >
      <slot name="thumb" />
    </SwitchThumb>
  </SwitchRoot>
</template>
