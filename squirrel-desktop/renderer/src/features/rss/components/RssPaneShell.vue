<template>
  <div class="rss-pane-shell" :class="`rss-pane-shell--${activePane}`">
    <div class="rss-pane-shell__pane rss-pane-shell__pane--entries">
      <slot name="entries" />
    </div>
    <div class="rss-pane-shell__pane rss-pane-shell__pane--reader">
      <slot name="reader" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  activePane: 'entries' | 'reader'
}>()
</script>

<style scoped>
.rss-pane-shell {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
}

.rss-pane-shell__pane {
  display: contents;
}

@container workbench (max-width: 47.999rem) {
  .rss-pane-shell--entries .rss-pane-shell__pane--reader,
  .rss-pane-shell--reader .rss-pane-shell__pane--entries {
    display: none;
  }
}
</style>
