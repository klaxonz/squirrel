import { VIDEO_TABS } from '../constants/videos';

export function buildTabsWithCounts(counts, tabs = VIDEO_TABS) {
  const mapping = counts || {};
  return tabs.map(t => ({ ...t, count: mapping[t.value] || 0 }));
}


