export { default as Alert } from './Alert.vue'
export { default as AlertDescription } from './AlertDescription.vue'
export { default as AlertTitle } from './AlertTitle.vue'

export type AlertVariant = 'default' | 'destructive' | 'error' | 'success' | 'warning' | 'info'
export type AlertVariants = { variant?: AlertVariant }
