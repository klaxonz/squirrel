<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { computed, useSlots } from 'vue'
import {
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectItemIndicator,
  SelectItemText,
  SelectLabel,
  SelectPortal,
  SelectRoot,
  SelectScrollDownButton,
  SelectScrollUpButton,
  SelectTrigger,
  SelectValue,
  SelectViewport,
} from 'reka-ui'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { cn } from '@/shared/lib/utils'

type SelectRecord = Record<string, unknown>
type SelectOption = string | number | SelectRecord

type NormalizedOption = {
  raw: SelectOption
  label: string
  value: string
  disabled: boolean
}

type NormalizedGroup = {
  key: string
  label: string | null
  options: NormalizedOption[]
}

defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  modelValue?: unknown
  options?: readonly SelectOption[]
  optionLabel?: string
  optionValue?: string
  optionGroupLabel?: string
  optionGroupChildren?: string
  placeholder?: string
  class?: HTMLAttributes['class']
  size?: 'small' | 'large'
  disabled?: boolean
  fluid?: boolean
  name?: string
  required?: boolean
  autocomplete?: string
}>(), {
  options: () => [],
  optionLabel: 'label',
  optionValue: 'value',
  optionGroupLabel: 'label',
  optionGroupChildren: 'items',
  placeholder: '',
  fluid: false,
  disabled: false,
  required: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  change: [event: Event]
}>()

defineSlots<{
  option?: (props: { option: SelectOption }) => unknown
}>()

const slots = useSlots()

const isRecord = (option: SelectOption): option is SelectRecord => (
  typeof option === 'object' && option !== null && !Array.isArray(option)
)

const normalizeOption = (option: SelectOption): NormalizedOption => {
  if (!isRecord(option)) {
    return {
      raw: option,
      label: String(option),
      value: String(option),
      disabled: false,
    }
  }

  return {
    raw: option,
    label: String(option[props.optionLabel] ?? option[props.optionValue] ?? ''),
    value: String(option[props.optionValue] ?? option[props.optionLabel] ?? ''),
    disabled: Boolean(option.disabled),
  }
}

const normalizedGroups = computed<NormalizedGroup[]>(() => {
  const groups: NormalizedGroup[] = []

  props.options.forEach((option, index) => {
    if (isRecord(option)) {
      const children = option[props.optionGroupChildren]
      if (Array.isArray(children)) {
        groups.push({
          key: `group-${index}`,
          label: String(option[props.optionGroupLabel] ?? ''),
          options: children.map((child) => normalizeOption(child as SelectOption)),
        })
        return
      }
    }

    const previous = groups[groups.length - 1]
    if (previous?.label === null) {
      previous.options.push(normalizeOption(option))
      return
    }

    groups.push({
      key: `options-${index}`,
      label: null,
      options: [normalizeOption(option)],
    })
  })

  return groups
})

const normalizedOptions = computed(() => normalizedGroups.value.flatMap((group) => group.options))
const normalizedModelValue = computed(() => {
  if (props.modelValue === undefined || props.modelValue === null || props.modelValue === '') return undefined
  return String(props.modelValue)
})
const selectedLabel = computed(() => {
  const value = normalizedModelValue.value
  if (!value) return props.placeholder
  return normalizedOptions.value.find((option) => option.value === value)?.label ?? value
})
const hasRichOptions = computed(() => Boolean(slots.option))

const updateValue = (value: string) => {
  emit('update:modelValue', value)
  emit('change', new Event('change'))
}
</script>

<template>
  <SelectRoot
    :model-value="normalizedModelValue"
    :disabled="props.disabled"
    :name="props.name"
    :required="props.required"
    :autocomplete="props.autocomplete"
    @update:model-value="updateValue"
  >
    <SelectTrigger
      v-bind="$attrs"
      :class="cn(
        'sq-select',
        props.size === 'small' && 'sq-select--sm',
        props.size === 'large' && 'sq-select--lg',
        props.fluid && 'sq-select--fluid',
        props.class,
      )"
    >
      <SelectValue as-child :placeholder="props.placeholder">
        <span class="sq-select__value">{{ selectedLabel }}</span>
      </SelectValue>
      <AppIcon name="chevronDown" class="sq-select__chevron" :stroke-width="1.75" />
    </SelectTrigger>

    <SelectPortal>
      <SelectContent
        position="popper"
        :side-offset="5"
        :collision-padding="8"
        :body-lock="false"
        class="sq-select__content"
        :class="{ 'sq-select__content--rich': hasRichOptions }"
      >
        <SelectScrollUpButton class="sq-select__scroll-button" aria-label="向上滚动">
          <AppIcon name="chevronUp" />
        </SelectScrollUpButton>

        <SelectViewport class="sq-select__viewport">
          <SelectGroup
            v-for="group in normalizedGroups"
            :key="group.key"
            class="sq-select__group"
          >
            <SelectLabel v-if="group.label" class="sq-select__group-label">
              {{ group.label }}
            </SelectLabel>

            <SelectItem
              v-for="option in group.options"
              :key="option.value"
              :value="option.value"
              :disabled="option.disabled"
              :text-value="option.label"
              class="sq-select__item"
            >
              <SelectItemText as="div" class="sq-select__item-copy">
                <slot name="option" :option="option.raw">
                  <span class="sq-select__item-label">{{ option.label }}</span>
                </slot>
              </SelectItemText>
              <SelectItemIndicator class="sq-select__item-indicator">
                <AppIcon name="check" :stroke-width="2.5" />
              </SelectItemIndicator>
            </SelectItem>
          </SelectGroup>
        </SelectViewport>

        <SelectScrollDownButton class="sq-select__scroll-button" aria-label="向下滚动">
          <AppIcon name="chevronDown" />
        </SelectScrollDownButton>
      </SelectContent>
    </SelectPortal>
  </SelectRoot>
</template>
