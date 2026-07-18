<template>
  <main class="auth-entry">
    <div class="auth-entry__stack" :class="{ 'auth-entry__stack--wide': wide }">
      <PrimeCard
        class="auth-entry__card"
        :pt="{ body: { style: { padding: '0' } }, content: { style: { padding: '0' } } }"
        >
        <template #content>
          <div class="auth-entry__identity" aria-label="归仓内容归集工作台">
            <BrandLogo size="sm" />
            <div class="auth-entry__identity-copy">
              <span class="auth-entry__product-name">归仓</span>
              <span class="auth-entry__product-context">内容归集工作台</span>
            </div>
          </div>
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
