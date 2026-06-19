<script setup lang="ts">
import type { PrimitiveProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import type { ButtonVariants } from "."
import { computed } from "vue"
import { Primitive } from "reka-ui"
import { cn } from '@/shared/lib/utils'
import { buttonVariants } from "."
import AppSpinner from '@/shared/components/AppSpinner.vue'

interface Props extends PrimitiveProps {
  variant?: ButtonVariants["variant"]
  size?: ButtonVariants["size"]
  class?: HTMLAttributes["class"]
  /**
   * Show a spinner before the slot content and disable interaction. Replaces
   * the 27 hand-rolled `<AppIcon name="loadingSpinner" class="... animate-spin">`
   * patterns scattered across features.
   */
  loading?: boolean
  /** Disable the button. */
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  as: "button",
  loading: false,
  disabled: false,
})

const isDisabled = computed(() => props.disabled || props.loading)
</script>

<template>
  <Primitive
    :as="as"
    :as-child="asChild"
    :disabled="isDisabled"
    :class="cn(buttonVariants({ variant, size }), props.class)"
  >
    <AppSpinner v-if="loading" size="sm" />
    <slot />
  </Primitive>
</template>
