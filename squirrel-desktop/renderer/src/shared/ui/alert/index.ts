export { default as Alert } from './Alert.vue'

export type AlertVariant = 'default' | 'destructive' | 'error' | 'success' | 'warning' | 'info'
export type AlertVariants = { variant?: AlertVariant }
