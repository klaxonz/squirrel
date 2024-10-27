<template>
  <label class="switch">
    <input type="checkbox" :checked="modelValue" @change="$emit('update:modelValue', $event.target.checked)">
    <span class="slider round"></span>
  </label>
</template>

<script setup>
defineProps(['modelValue']);
defineEmits(['update:modelValue']);
</script>

<style scoped>
.switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #606060;
  transition: .4s;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 2px;
  bottom: 2px;
  background-color: white;
  transition: .4s;
}

input:checked + .slider {
  background-color: #cc0000;
}

input:checked + .slider:before {
  transform: translateX(18px);
}

.slider.round {
  border-radius: 22px;
}

.slider.round:before {
  border-radius: 50%;
}
</style>
