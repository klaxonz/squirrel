<template>
  <svg xmlns="http://www.w3.org/2000/svg" :class="[`h-${size}`, `w-${size}`]" :fill="filled ? 'currentColor' : 'none'" viewBox="0 0 24 24" stroke="currentColor" v-bind="$attrs">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
</template>

<script setup>
const props = defineProps({
  size: { type: [String, Number], default: 5 },
  filled: { type: Boolean, default: false },
});
</script>


