export const getConnectivityBadge = (connectivity) => {
  if (!connectivity || connectivity.accessible === undefined || connectivity.accessible === null) {
    return {
      tone: 'muted',
      label: '未检测',
      title: '尚未进行连通性检测',
    }
  }

  if (connectivity.status === 'restricted') {
    return {
      tone: 'warning',
      label: '受限',
      title: connectivity.error_message || '站点可访问，但返回受限状态码',
    }
  }

  if (connectivity.accessible) {
    return {
      tone: 'success',
      label: '通过',
      title: '站点可访问',
    }
  }

  return {
    tone: 'danger',
    label: '失败',
    title: connectivity.error_message || '站点无法访问',
  }
}
