<script setup lang="ts">
import { inject } from 'vue'
import { dialogContextKey } from './context'

const dialog = inject(dialogContextKey)
if (!dialog) throw new Error('DialogClose must be nested inside Dialog')
</script>

<template>
  <span class="app-prime-dialog__close" @click="dialog.setOpen(false)">
    <slot />
  </span>
</template>
