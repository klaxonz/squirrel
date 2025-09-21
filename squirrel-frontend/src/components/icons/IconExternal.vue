<template>
  <svg xmlns="http://www.w3.org/2000/svg" :class="[`h-${size}`, `w-${size}`]" viewBox="0 0 24 24" fill="currentColor" v-bind="$attrs">
    <path d="M14 3h7v7h-2V6.414l-9.293 9.293-1.414-1.414L17.586 5H14V3z" />
    <path d="M5 5h6v2H7v10h10v-4h2v6H5V5z" />
  </svg>
</template>

<script setup>
const props = defineProps({
  size: { type: [String, Number], default: 5 },
});
</script>


