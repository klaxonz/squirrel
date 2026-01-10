import axios from '../utils/axios';

export function usePluginApi() {

  const getPlugins = async () => {
    try {
      const response = await axios.get('/api/plugins/');
      if (response.data?.code === 0) {
        return { success: true, data: response.data.data || [] };
      }
      throw new Error(response.data?.msg || '获取插件列表失败');
    } catch (error) {
      console.error('获取插件列表失败:', error);
      return { success: false, error: error.message || '获取插件列表失败' };
    }
  };

  const installPlugin = async (file) => {
    if (!file) {
      return { success: false, error: '请选择插件包' };
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('/api/plugins/install', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (response.data?.code === 0) {
        return { success: true, data: response.data.data };
      }
      throw new Error(response.data?.msg || '插件安装失败');
    } catch (error) {
      console.error('插件安装失败:', error);
      const errorMessage = error.message || '插件安装失败';
      return { success: false, error: errorMessage };
    }
  };

  const enablePlugin = async (name) => {
    try {
      const response = await axios.post(`/api/plugins/${encodeURIComponent(name)}/enable`);
      if (response.data?.code === 0) {
        return { success: true };
      }
      throw new Error(response.data?.msg || '启用失败');
    } catch (error) {
      console.error('启用插件失败:', error);
      const errorMessage = error.message || '启用失败';
      return { success: false, error: errorMessage };
    }
  };

  const disablePlugin = async (name) => {
    try {
      const response = await axios.post(`/api/plugins/${encodeURIComponent(name)}/disable`);
      if (response.data?.code === 0) {
        return { success: true };
      }
      throw new Error(response.data?.msg || '禁用失败');
    } catch (error) {
      console.error('禁用插件失败:', error);
      const errorMessage = error.message || '禁用失败';
      return { success: false, error: errorMessage };
    }
  };

  const uninstallPlugin = async (name) => {
    try {
      const response = await axios.post(`/api/plugins/${encodeURIComponent(name)}/uninstall`);
      if (response.data?.code === 0) {
        return { success: true };
      }
      throw new Error(response.data?.msg || '卸载失败');
    } catch (error) {
      console.error('卸载插件失败:', error);
      const errorMessage = error.message || '卸载失败';
      return { success: false, error: errorMessage };
    }
  };

  const reloadPlugins = async () => {
    try {
      const response = await axios.post('/api/plugins/reload');
      if (response.data?.code === 0) {
        return { success: true };
      }
      throw new Error(response.data?.msg || '插件重载失败');
    } catch (error) {
      console.error('插件重载失败:', error);
      const errorMessage = error.message || '插件重载失败';
      return { success: false, error: errorMessage };
    }
  };

  const getSupportedSites = async () => {
    try {
      const response = await axios.get('/api/plugins/sites');
      if (response.data?.code === 0) {
        return { success: true, data: response.data.data };
      }
      throw new Error(response.data?.msg || '获取支持站点列表失败');
    } catch (error) {
      console.error('获取支持站点列表失败:', error);
      return { success: false, error: error.message || '获取支持站点列表失败' };
    }
  };

  const testSiteConnectivity = async (siteName, timeout = 10) => {
    try {
      const response = await axios.get(`/api/plugins/sites/${encodeURIComponent(siteName)}/test-connectivity`, {
        params: { timeout }
      });
      if (response.data?.code === 0) {
        return { success: true, data: response.data.data };
      }
      throw new Error(response.data?.msg || '测试连通性失败');
    } catch (error) {
      console.error('测试站点连通性失败:', error);
      return { success: false, error: error.message || '测试连通性失败' };
    }
  };

  const testSiteLoginStatus = async (siteName) => {
    try {
      const response = await axios.get(`/api/plugins/sites/${encodeURIComponent(siteName)}/login-status`);
      if (response.data?.code === 0) {
        return { success: true, data: response.data.data };
      }
      throw new Error(response.data?.msg || '检测登录状态失败');
    } catch (error) {
      console.error('检测站点登录状态失败:', error);
      return { success: false, error: error.message || '检测登录状态失败' };
    }
  };

  const testAllSitesConnectivity = async (timeout = 10) => {
    try {
      const response = await axios.get('/api/plugins/sites/test-connectivity/all', {
        params: { timeout }
      });
      if (response.data?.code === 0) {
        return { success: true, data: response.data.data };
      }
      throw new Error(response.data?.msg || '批量测试失败');
    } catch (error) {
      console.error('批量测试站点连通性失败:', error);
      return { success: false, error: error.message || '批量测试失败' };
    }
  };

  const importAllSiteCookies = async (file) => {
    if (!file) {
      return { success: false, error: '请选择 Cookie 文件' };
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('/api/plugins/sites/cookies/import-all', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (response.data?.code === 0) {
        return { success: true, data: response.data.data };
      }
      throw new Error(response.data?.msg || 'Cookies 导入失败');
    } catch (error) {
      console.error('导入所有站点 Cookies 失败:', error);
      const errorMessage = error.message || 'Cookies 导入失败';
      return { success: false, error: errorMessage };
    }
  };

  const uploadSiteCookies = async (siteName, file, target = 'default') => {
    if (!file) {
      return { success: false, error: '请选择 Cookie 文件' };
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(
        `/api/plugins/sites/${encodeURIComponent(siteName)}/cookies`,
        formData,
        {
          params: { target },
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );

      if (response.data?.code === 0) {
        return { success: true, data: response.data.data };
      }
      throw new Error(response.data?.msg || 'Cookie 更新失败');
    } catch (error) {
      console.error('上传站点 Cookie 失败:', error);
      const errorMessage = error.message || 'Cookie 更新失败';
      return { success: false, error: errorMessage };
    }
  };

  return {
    getPlugins,
    installPlugin,
    enablePlugin,
    disablePlugin,
    uninstallPlugin,
    reloadPlugins,
    getSupportedSites,
    testSiteConnectivity,
    testSiteLoginStatus,
    testAllSitesConnectivity,
    importAllSiteCookies,
    uploadSiteCookies,
  };
}


