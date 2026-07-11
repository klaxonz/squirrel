<script setup lang="ts">
import type { SwitchRootEmits, SwitchRootProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { SwitchRoot, SwitchThumb, useForwardPropsEmits } from 'reka-ui'
import { cn } from '@/shared/lib/utils'

const props = defineProps<SwitchRootProps<boolean> & { class?: HTMLAttributes['class'] }>()
const emits = defineEmits<SwitchRootEmits>()

const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <SwitchRoot
    v-bind="forwarded"
    :class="cn(
      'peer inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border border-border/70 bg-input/65 transition-colors duration-fast ease-default focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/45 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-40 data-[state=checked]:border-primary/45 data-[state=checked]:bg-primary data-[state=unchecked]:bg-input/65 motion-reduce:transition-none',
      props.class,
    )"
  >
    <SwitchThumb
      :class="cn('pointer-events-none block h-4 w-4 rounded-full border border-border/60 bg-background shadow-sm ring-0 transition-transform duration-fast ease-default data-[state=checked]:translate-x-4 data-[state=checked]:border-primary/20 data-[state=unchecked]:translate-x-0 motion-reduce:transition-none')"
    >
      <slot name="thumb" />
    </SwitchThumb>
  </SwitchRoot>
</template>
