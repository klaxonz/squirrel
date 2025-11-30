import { ref } from 'vue';
import { get } from '../utils/request';

const cached = ref(null);
const loading = ref(false);
const error = ref(null);

const resetCache = () => {
  cached.value = null;
};

export async function fetchSites() {
  if (cached.value || loading.value) return { data: cached.value, error: error.value };
  loading.value = true;
  error.value = null;
  try {
    const { data } = await get('/api/sites');
    const items = data ? Object.entries(data) : [];
    const opts = [{ value: undefined, label: '全部站点' }];
    for (const [slug, info] of items) {
      if (info && info.enabled !== false) {
        opts.push({ value: slug, label: info.label || slug });
      }
    }
    cached.value = opts;
    return { data: cached.value, error: null };
  } catch (e) {
    error.value = e;
    return { data: cached.value, error: e };
  } finally {
    loading.value = false;
  }
}

export function useSites() {
  return { options: cached, loading, error, fetchSites, resetCache };
}

export function resetSitesCache() {
  resetCache();
}


