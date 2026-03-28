export const getConnectivityBadge = (connectivity) => {
  if (!connectivity || connectivity.accessible === undefined || connectivity.accessible === null) {
    return {
      tone: 'muted',
      label: 'None',
      title: 'Connectivity has not been tested yet',
    }
  }

  if (connectivity.status === 'restricted') {
    return {
      tone: 'warning',
      label: 'Restricted',
      title: connectivity.error_message || 'Site is reachable but responded with a restricted status code',
    }
  }

  if (connectivity.accessible) {
    return {
      tone: 'success',
      label: 'Pass',
      title: 'Site is accessible',
    }
  }

  return {
    tone: 'danger',
    label: 'Fail',
    title: connectivity.error_message || 'Site is not accessible',
  }
}
