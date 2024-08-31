<template>
  <label class="flex items-center cursor-pointer" :class="{ 'opacity-50': !enabled }">
    <div class="relative">
      <input 
        type="checkbox" 
        class="sr-only" 
        :checked="modelValue" 
        @change="$emit('update:modelValue', $event.target.checked)"
        :disabled="!enabled"
      >
      <div 
        class="w-8 h-4 rounded-full shadow-inner transition-colors duration-200 ease-in-out"
        :class="[
          modelValue && enabled ? 'bg-blue-400' : 'bg-gray-300',
          { 'cursor-not-allowed': !enabled }
        ]"
      ></div>
      <div 
        class="absolute w-3 h-3 bg-white rounded-full shadow transition-transform duration-200 ease-in-out"
        :class="[
          modelValue && enabled ? 'translate-x-4' : 'translate-x-1',
          'top-0.5',
          { 'cursor-not-allowed': !enabled }
        ]"
      ></div>
    </div>
    <div class="ml-2 text-xs font-medium" :class="enabled ? 'text-gray-600' : 'text-gray-400'">
      {{ label }}
    </div>
  </label>
</template>

<script>
export default {
  props: {
    modelValue: Boolean,
    label: String,
    enabled: {
      type: Boolean,
      default: true
    }
  },
  emits: ['update:modelValue']
}
</script>

<style scoped>
/* 可以根据需要添加额外的样式 */
</style>