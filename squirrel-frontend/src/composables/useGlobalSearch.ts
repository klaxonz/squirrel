import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { RouteLocationNormalizedLoaded } from 'vue-router'

type EmitterLike = {
  emit: (eventName: string, ...args: unknown[]) => void
}

const getStringMeta = (meta: Record<string, unknown>, key: string) => {
  const value = meta[key]
  return typeof value === 'string' ? value : null
}

export function useGlobalSearch(emitter?: EmitterLike) {
  const route = useRoute()
  const router = useRouter()

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
      } catch (_) {}
    }

    const type = getStringMeta(route.meta, 'search')
    const searchEvent = getStringMeta(route.meta, 'searchEvent')
    const eventName = searchEvent ?? (type ? `search:${type}` : 'search:global')
    emitter?.emit(eventName, searchQuery.value)
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
