<template>
  <!-- Width + chrome are owned by <Sidebar>'s <aside> (driven by the
       --sidebar-width token that AppLayout sets from isSidebarOpen). Keeping
       this wrapper chrome-free avoids the duplicate border/bg that used to
       fight Sidebar.vue's own border-r/bg-sidebar. -->
  <Sidebar class="h-full" />
</template>

<script setup lang="ts">
import Sidebar from '@/shared/components/layout/Sidebar.vue'
</script>