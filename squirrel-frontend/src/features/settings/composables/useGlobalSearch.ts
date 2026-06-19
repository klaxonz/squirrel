import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { RouteLocationNormalizedLoaded } from 'vue-router'
import { useUIStore } from '@/shared/stores/ui'
import { Logger } from '@/shared/lib/logger'

const getStringMeta = (meta: Record<string, unknown>, key: string) => {
  const value = meta[key]
  return typeof value === 'string' ? value : null
}

export function useGlobalSearch() {
  const route = useRoute()
  const router = useRouter()
  const uiStore = useUIStore()

  const searchQuery = ref('')
  const persistedQueryByKey = ref<Record<string, string>>({})

  const searchPlaceholder = computed(() => {
    const placeholder = getStringMeta(route.meta, 'searchPlaceholder')
    return placeholder ?? '搜索...'
  })

  const searchScopeLabel = computed(() => {
    return getStringMeta(route.meta, 'sectionLabel')
      ?? getStringMeta(route.meta, 'title')
      ?? searchPlaceholder.value
      ?? '当前页'
  })

  const searchSuggestionScope = computed(() => {
    return getStringMeta(route.meta, 'search') ?? 'home'
  })

  const getPersistKey = (r: RouteLocationNormalizedLoaded = route) => {
    return getStringMeta(r.meta, 'searchPersistKey') ?? String(r.name ?? r.path ?? 'GLOBAL')
  }

  watch(
    route,
    (newRoute) => {
      const key = getPersistKey(newRoute)
      searchQuery.value = persistedQueryByKey.value[key] || ''
    },
    { immediate: true }
  )

  watch(searchQuery, (newQuery) => {
    const key = getPersistKey()
    persistedQueryByKey.value[key] = newQuery
  })

  const handleSearch = async () => {
    const redirectName = getStringMeta(route.meta, 'searchRedirectName')
    if (redirectName) {
      try {
        await router.push({ name: redirectName })
        await nextTick()
      } catch (err) {
        Logger.warn('[useGlobalSearch] Search redirect failed', err)
      }
    }

    uiStore.triggerSearch(searchQuery.value)
  }

  const handleClear = () => {
    handleSearch()
  }

  return {
    searchQuery,
    searchPlaceholder,
    searchScopeKey: computed(() => getPersistKey()),
    searchScopeLabel,
    searchSuggestionScope,
    handleSearch,
    handleClear,
  }
}
