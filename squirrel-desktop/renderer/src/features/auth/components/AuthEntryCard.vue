<template>
  <main class="auth-entry">
    <div class="auth-entry__stack" :class="{ 'auth-entry__stack--wide': wide }">
      <div class="auth-entry__brand" aria-label="归仓">
        <BrandLogo size="sm" />
        <span>归仓</span>
      </div>

      <PrimeCard
        class="auth-entry__card"
        :pt="{ body: { class: 'p-0' }, content: { class: 'p-0' } }"
        >
        <template #content>
          <header class="auth-entry__header">
            <h1 class="auth-entry__title">{{ title }}</h1>
            <p class="auth-entry__description">{{ description }}</p>
          </header>
          <div class="auth-entry__content">
            <slot />
          </div>
          <footer v-if="$slots.footer" class="auth-entry__footer">
            <slot name="footer" />
          </footer>
        </template>
      </PrimeCard>

      <slot name="below" />
    </div>
  </main>
</template>

<script setup lang="ts">
import BrandLogo from '@/shared/components/BrandLogo.vue'
import PrimeCard from 'primevue/card'

withDefaults(defineProps<{
  title: string
  description: string
  wide?: boolean
}>(), {
  wide: false,
})
</script>
