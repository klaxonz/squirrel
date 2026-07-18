<template>
  <main class="auth-entry">
    <div class="auth-entry__stack" :class="{ 'auth-entry__stack--wide': wide }">
      <div class="auth-entry__brand" aria-label="归仓">
        <BrandLogo size="sm" />
        <span>归仓</span>
      </div>

      <Card class="auth-entry__card">
        <CardHeader class="auth-entry__header">
          <h1 class="auth-entry__title">{{ title }}</h1>
          <CardDescription>{{ description }}</CardDescription>
        </CardHeader>
        <CardContent class="auth-entry__content">
          <slot />
        </CardContent>
        <CardFooter v-if="$slots.footer" class="auth-entry__footer">
          <slot name="footer" />
        </CardFooter>
      </Card>

      <slot name="below" />
    </div>
  </main>
</template>

<script setup lang="ts">
import BrandLogo from '@/shared/components/BrandLogo.vue'
import { Card, CardContent, CardDescription, CardFooter, CardHeader } from '@/shared/ui/card'

withDefaults(defineProps<{
  title: string
  description: string
  wide?: boolean
}>(), {
  wide: false,
})
</script>
