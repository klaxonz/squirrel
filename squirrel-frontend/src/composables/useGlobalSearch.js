import { ref, computed, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';

/**
 * Global search composable encapsulating state, placeholder mapping,
 * and route-aware search dispatching using a provided emitter.
 */
export function useGlobalSearch(emitter) {
  const route = useRoute();
  const router = useRouter();

  // Shared query bound to the search bar
  const searchQuery = ref('');

  // Per-route persisted search state (keyed by meta.searchPersistKey || route.name || route.path)
  const persistedQueryByKey = ref({});

  // Placeholder text driven by current route
  const searchPlaceholder = computed(() => {
    return route.meta?.searchPlaceholder || '搜索...';
  });

  const getPersistKey = (r = route) => {
    return r.meta?.searchPersistKey || r.name || r.path || 'GLOBAL';
  };

  // Keep per-route query state in sync on navigation
  watch(route, (newRoute) => {
    const key = getPersistKey(newRoute);
    searchQuery.value = persistedQueryByKey.value[key] || '';
  }, { immediate: true });

  // Persist query changes keyed by current route name
  watch(searchQuery, (newQuery) => {
    const key = getPersistKey();
    persistedQueryByKey.value[key] = newQuery;
  });

  // Emit page-specific events; redirect when searching from VideoPlay
  const handleSearch = async () => {
    // optional redirect before emit
    const redirectName = route.meta?.searchRedirectName;
    if (redirectName) {
      try {
        await router.push({ name: redirectName });
        await nextTick();
      } catch (_) {}
    }

    const type = route.meta?.search;
    const eventName = route.meta?.searchEvent || (type ? `search:${type}` : 'search:global');
    emitter?.emit(eventName, searchQuery.value);
  };

  const handleClear = () => {
    handleSearch();
  };

  return {
    searchQuery,
    searchPlaceholder,
    handleSearch,
    handleClear
  };
}


