import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue';

export default function useSyncedMaxHeight(targetRef, options = {}) {
  const { excludeHeights = [], excludePaddingsFrom = null } = options;
  const maxHeight = ref(0);

  const recalc = () => {
    const targetEl = targetRef?.value;
    if (!targetEl) return;

    const targetHeight = targetEl.clientHeight || 0;

    let deductions = 0;
    const paddingFrom = excludePaddingsFrom?.value || excludePaddingsFrom;
    if (paddingFrom) {
      const style = window.getComputedStyle(paddingFrom);
      deductions += (parseFloat(style.paddingTop) || 0) + (parseFloat(style.paddingBottom) || 0);
    }

    for (const elRef of excludeHeights) {
      const el = elRef?.value || elRef;
      if (!el) continue;
      const style = window.getComputedStyle(el);
      const marginTop = parseFloat(style.marginTop) || 0;
      const marginBottom = parseFloat(style.marginBottom) || 0;
      deductions += (el.offsetHeight || 0) + marginTop + marginBottom;
    }

    const computed = targetHeight - deductions;
    maxHeight.value = computed > 0 ? computed : 0;
  };

  onMounted(() => {
    nextTick(recalc);
    window.addEventListener('resize', recalc, { passive: true });
  });

  onBeforeUnmount(() => {
    window.removeEventListener('resize', recalc);
  });

  return { maxHeight, recalc };
}


