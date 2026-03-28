<template>
  <router-link
    :to="item.path"
    class="menu-item-minimal"
    :class="{ 'is-active': isActive }"
  >
    <span class="menu-index">{{ index < 10 ? '0' + index : index }}</span>
    <span class="menu-label">{{ item.name }}</span>
    <div class="menu-active-line"></div>
  </router-link>
</template>

<script setup>
defineProps({
  item: {
    type: Object,
    required: true,
  },
  index: {
    type: Number,
    required: true,
  },
  isActive: {
    type: Boolean,
    default: false,
  },
})
</script>

<style scoped>
.menu-item-minimal {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 1.5rem 0.5rem;
  color: rgba(255, 255, 255, 0.3);
  text-decoration: none;
  transition: all 0.4s cubic-bezier(0.19, 1, 0.22, 1);
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.menu-item-minimal:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.02);
}

.is-active {
  color: #fff;
}

.menu-index {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.6rem;
  letter-spacing: 0.1em;
  margin-bottom: 0.25rem;
  opacity: 0.5;
}

.menu-label {
  font-size: 0.75rem;
  font-weight: 400;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.menu-active-line {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 2px;
  height: 0;
  background: #ff4d00;
  transition: height 0.4s ease;
  box-shadow: 0 0 10px #ff4d00;
}

.is-active .menu-active-line {
  height: 60%;
}

.is-active .menu-index {
  color: #ff4d00;
  opacity: 1;
}
</style>
