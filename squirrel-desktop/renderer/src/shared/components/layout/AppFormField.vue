<template>
  <div :class="cn('app-form-field', props.class)">
    <label v-if="label || $slots.label" :id="labelId" :for="controlId" class="app-form-field__label">
      <slot name="label">{{ label }}</slot>
      <span v-if="required" class="app-form-field__required" aria-hidden="true">*</span>
    </label>

    <div class="app-form-field__control">
      <slot :control="controlAttrs" :id="controlId" />
    </div>

    <p v-if="description || $slots.description" :id="descriptionId" class="app-form-field__description">
      <slot name="description">{{ description }}</slot>
    </p>
    <p v-if="error || $slots.error" :id="errorId" class="app-form-field__error">
      <slot name="error">{{ error }}</slot>
    </p>
  </div>
</template>

<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { computed, useId } from 'vue'
import { cn } from '@/shared/lib/utils'

export interface AppFormFieldControlAttrs {
  id: string
  required?: true
  'aria-labelledby'?: string
  'aria-describedby'?: string
  'aria-errormessage'?: string
  'aria-invalid'?: 'true'
}

const props = withDefaults(defineProps<{
  id?: string
  label?: string
  description?: string
  error?: string
  required?: boolean
  class?: HTMLAttributes['class']
}>(), {
  label: '',
  description: '',
  error: '',
  required: false,
})

const slots = defineSlots<{
  default: (props: { control: AppFormFieldControlAttrs, id: string }) => unknown
  label?: () => unknown
  description?: () => unknown
  error?: () => unknown
}>()

const generatedId = useId()
const controlId = computed(() => props.id || `app-form-field-${generatedId}`)
const labelId = computed(() => `${controlId.value}-label`)
const descriptionId = computed(() => `${controlId.value}-description`)
const errorId = computed(() => `${controlId.value}-error`)
const describedBy = computed(() => [
  props.description || slots.description ? descriptionId.value : null,
  props.error || slots.error ? errorId.value : null,
].filter(Boolean).join(' ') || undefined)

const controlAttrs = computed<AppFormFieldControlAttrs>(() => ({
  id: controlId.value,
  required: props.required || undefined,
  'aria-labelledby': props.label || slots.label ? labelId.value : undefined,
  'aria-describedby': describedBy.value,
  'aria-errormessage': props.error || slots.error ? errorId.value : undefined,
  'aria-invalid': props.error || slots.error ? 'true' : undefined,
}))
</script>

<style scoped>
.app-form-field {
  display: grid;
  gap: 0.375rem;
  min-width: 0;
}

.app-form-field__label {
  color: hsl(var(--foreground));
  font-size: var(--app-text-md);
  font-weight: 600;
  line-height: 1.25rem;
}

.app-form-field__required,
.app-form-field__error {
  color: hsl(var(--destructive));
}

.app-form-field__required {
  margin-left: 0.1875rem;
}

.app-form-field__control {
  min-width: 0;
}

.app-form-field__description,
.app-form-field__error {
  margin: 0;
  font-size: var(--app-text-sm);
  line-height: 1.125rem;
}

.app-form-field__description {
  color: hsl(var(--muted-foreground));
}
</style>
