<template>
  <span
    class="site-icon"
    :class="[sizeClass, roundedClass, { 'site-icon--brand': showBrand }]"
    :style="brandStyle"
  >
    <img
      v-if="resolvedIconUrl && !loadFailed"
      :src="resolvedIconUrl"
      :alt="String(label || site || '')"
      class="site-icon__img"
      loading="lazy"
      @error="loadFailed = true"
    >
    <span
      v-else-if="monoText"
      class="site-icon__mono"
      aria-hidden="true"
    >{{ monoText }}</span>
    <AppIcon
      v-else
      name="siteFallback"
      aria-hidden="true"
      :class="iconClass"
    />
  </span>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { getSiteBrand, siteMonogram } from '@/shared/lib/siteBrand'
import { resolveServerAssetUrl } from '@/shared/lib/serverConfig'

const props = withDefaults(defineProps<{
  /** Preferred raster/SVG URL (absolute or server-relative). */
  iconUrl?: string | null
  /** Site slug — enables brand monogram + default `/api/sites/{slug}/icon`. */
  site?: string | null
  label?: string | null
  size?: 'xs' | 'sm' | 'md' | 'lg'
  rounded?: 'sm' | 'md' | 'full'
}>(), {
  iconUrl: null,
  site: null,
  label: '',
  size: 'sm',
  rounded: 'md',
})

const loadFailed = ref(false)

watch(() => [props.iconUrl, props.site], () => {
  loadFailed.value = false
})

const brand = computed(() => getSiteBrand(props.site))

const resolvedIconUrl = computed(() => {
  const explicit = resolveServerAssetUrl(props.iconUrl)
  if (explicit) return explicit
  const slug = String(props.site || '').trim().toLowerCase()
  if (!slug) return undefined
  return resolveServerAssetUrl(`/api/sites/${encodeURIComponent(slug)}/icon`) || undefined
})

const monoText = computed(() => siteMonogram(props.label, props.site))

const showBrand = computed(() => (
  (!resolvedIconUrl.value || loadFailed.value) && Boolean(brand.value)
))

const brandStyle = computed(() => {
  if (!showBrand.value || !brand.value) return undefined
  return {
    background: brand.value.bg,
    color: brand.value.fg,
    borderColor: 'transparent',
  }
})

const sizeClass = computed(() => {
  if (props.size === 'xs') return 'site-icon--xs'
  if (props.size === 'md') return 'site-icon--md'
  if (props.size === 'lg') return 'site-icon--lg'
  return 'site-icon--sm'
})

const roundedClass = computed(() => {
  if (props.rounded === 'full') return 'site-icon--round-full'
  if (props.rounded === 'sm') return 'site-icon--round-sm'
  return 'site-icon--round-md'
})

const iconClass = computed(() => {
  if (props.size === 'xs') return 'h-2.5 w-2.5'
  if (props.size === 'md') return 'h-4 w-4'
  if (props.size === 'lg') return 'h-5 w-5'
  return 'h-3.5 w-3.5'
})
</script>

<style scoped>
.site-icon {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.4);
  background: hsl(var(--card));
  color: hsl(var(--muted-foreground));
  line-height: 1;
}

.site-icon--xs {
  width: 1.25rem;
  height: 1.25rem;
}

.site-icon--sm {
  width: 1.5rem;
  height: 1.5rem;
}

.site-icon--md {
  width: 2rem;
  height: 2rem;
}

.site-icon--lg {
  width: 2.5rem;
  height: 2.5rem;
}

.site-icon--round-sm {
  border-radius: var(--radius-sm);
}

.site-icon--round-md {
  border-radius: var(--radius-md);
}

.site-icon--round-full {
  border-radius: 999px;
}

.site-icon--brand {
  border-color: transparent;
}

.site-icon__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.site-icon__mono {
  max-width: 100%;
  padding: 0 1px;
  font-size: var(--app-text-badge-size);
  font-weight: 750;
  letter-spacing: -0.04em;
  line-height: 1;
  text-align: center;
  white-space: nowrap;
}

.site-icon--sm .site-icon__mono,
.site-icon--md .site-icon__mono {
  font-size: var(--app-text-badge-size);
}

.site-icon--lg .site-icon__mono {
  font-size: var(--app-text-xs);
}
</style>
