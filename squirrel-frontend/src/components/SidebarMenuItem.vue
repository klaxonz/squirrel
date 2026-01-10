<template>
  <router-link
    :to="item.path"
    class="flex items-center h-10 px-3 text-[#f1f1f1] rounded-lg transition-colors duration-150 mb-1"
    :class="[
      { 'justify-center': isCollapsed },
      isActive ? 'bg-[#272727]' : 'hover:bg-[#ffffff1a]'
    ]"
  >
    <component
      :is="item.icon"
      class="w-5 h-5"
      :class="[isCollapsed ? '' : 'mr-4']"
    />
    <span v-if="!isCollapsed" class="text-[13px]">{{ item.name }}</span>
  </router-link>
</template>

<script setup>
const props = defineProps({
  item: {
    type: Object,
    required: true,
  },
  isCollapsed: {
    type: Boolean,
    default: false,
  },
  isActive: {
    type: Boolean,
    default: false,
  },
})
</script>
