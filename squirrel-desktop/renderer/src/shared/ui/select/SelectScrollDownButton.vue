<script setup lang="ts">
import type { SelectScrollDownButtonProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { SelectScrollDownButton, useForwardProps } from "reka-ui"
import AppIcon from '@/shared/icons/AppIcon.vue'
import { cn } from '@/shared/lib/utils'

const props = defineProps<SelectScrollDownButtonProps & { class?: HTMLAttributes["class"] }>()

const delegatedProps = reactiveOmit(props, "class")

const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <SelectScrollDownButton v-bind="forwardedProps" :class="cn('flex cursor-default items-center justify-center py-1', props.class)">
    <slot>
      <AppIcon name="chevronDown" />
    </slot>
  </SelectScrollDownButton>
</template>
