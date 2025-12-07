<template>
  <svg 
    :class="['sp-icon', `sp-icon-${name}`]"
    :viewBox="icon?.viewBox || '0 0 24 24'"
    fill="currentColor"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path v-for="(d, i) in paths" :key="i" :d="d" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useIcons, type IconName } from './core/useIcons'

const props = defineProps<{
  name: IconName
}>()

const { getIcon } = useIcons()

const icon = computed(() => getIcon(props.name))

const paths = computed(() => {
  if (!icon.value) return []
  return icon.value.paths || (icon.value.path ? [icon.value.path] : [])
})
</script>
