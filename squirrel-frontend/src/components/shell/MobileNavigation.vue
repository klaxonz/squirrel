<template>
  <MobileNav :routes="mobileRoutes" class="border-t border-border/40 bg-background/80 backdrop-blur" />
</template>

<script setup lang="ts">
import MobileNav from '@/components/layout/MobileNav.vue'
import { MOBILE_NAV_ITEMS } from '@/constants/sidebar'

const mobileRoutes = MOBILE_NAV_ITEMS
</script>
