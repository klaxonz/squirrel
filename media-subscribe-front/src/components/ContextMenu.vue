<template>
  <div
    class="context-menu"
    :style="{ top: `${position.y}px`, left: `${position.x}px` }"
    @click.stop
  >
    <slot></slot>
  </div>
</template>

<script setup>
import { defineProps, onMounted, onUnmounted } from 'vue';

const props = defineProps({
  position: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['close']);

const handleClickOutside = (event) => {
  if (!event.target.closest('.context-menu')) {
    emit('close');
  }
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
.context-menu {
  position: fixed;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  overflow: hidden;
  min-width: 200px;
}
</style>