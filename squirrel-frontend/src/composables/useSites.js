import { ref } from 'vue';
import { getSites, saveSites } from '../api/sites'

// 下拉筛选等使用的简化站点选项缓存
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
  const { data, error: requestError } = await getSites()
  if (requestError) {
    error.value = requestError
    loading.value = false
    return { data: cached.value, error: requestError }
  }

  const items = data ? Object.entries(data) : []
  const opts = [{ value: undefined, label: '全部站点' }]
  for (const [slug, info] of items) {
    if (info && info.enabled !== false) {
      opts.push({ value: slug, label: info.label || slug })
    }
  }
  cached.value = opts
  loading.value = false
  return { data: cached.value, error: null }
}

export function useSites() {
  return { options: cached, loading, error, fetchSites, resetCache };
}

export function resetSitesCache() {
  resetCache();
}
// 站点原始配置（/api/sites）的读写，用于管理端配置
const siteCatalog = ref({});
const siteCatalogLoading = ref(false);
const siteCatalogError = ref(null);

export function useSiteCatalog() {
  const loadCatalog = async () => {
    siteCatalogLoading.value = true;
    siteCatalogError.value = null;
    const { data, error } = await getSites()
    if (error) {
      siteCatalogError.value = error
    } else {
      siteCatalog.value = data || {}
    }
    siteCatalogLoading.value = false
  };

  const catalogObjectToPayload = (catalogObj) => {
    return Object.entries(catalogObj).map(([slug, info]) => {
      const payload = {
        slug,
        label: info?.label || slug,
        domains: info?.domains || [],
        aliases: info?.aliases || [],
        enabled: info?.enabled !== false,
      };
      if (info?.http) payload.http = info.http;
      if (info?.proxy) payload.proxy = info.proxy;
      if (info?.login) payload.login = info.login;
      if (info?.rate_limit) payload.rate_limit = info.rate_limit;
      if (info?.metadata) payload.metadata = info.metadata;
      if (info?.test_url) payload.test_url = info.test_url;
      return payload;
    });
  };

  const saveCatalog = async (updatedCatalog) => {
    siteCatalogLoading.value = true;
    siteCatalogError.value = null;
    try {
      const payload = catalogObjectToPayload(updatedCatalog);
      const result = await saveSites({ sites: payload })
      if (result.error) {
        throw result.error
      }

      siteCatalog.value = result.data || {}
      resetCache()
    } catch (e) {
      siteCatalogError.value = e;
      throw e;
    } finally {
      siteCatalogLoading.value = false;
    }
  };

  return {
    catalog: siteCatalog,
    loading: siteCatalogLoading,
    error: siteCatalogError,
    loadCatalog,
    saveCatalog,
  };
}
