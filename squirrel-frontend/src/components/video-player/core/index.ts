export { EventEmitter, type EventHandler, type EventMap } from './EventEmitter'
export { PluginManager } from './PluginManager'
export { createPlayerRuntimeStore, type PlayerRuntimeStore, type LoadingStage } from './PlayerStore'
export { usePluginSystem } from './usePluginSystem'
export { useA11y } from './useA11y'
export { useErrorRecovery } from './useErrorRecovery'
export { useGestures } from './useGestures'
export { useControlsLayout, type ControlsLayoutConfig, type ControlDefinition, type PresetLayout } from './useControlsLayout'
export { useIcons, type IconName } from './useIcons'
export {
  usePlayerAdapter,
  createLocalAdapter,
  createApiAdapter
} from './usePlayerAdapter'
export {
  LocalStorageAdapter,
  ApiAdapter,
  CompositeAdapter,
  setPlayerAdapter,
  getPlayerAdapter,
  type IPlayerAdapter,
  type UserConfig,
  type PlaybackProgress,
  type HistoryEntry,
  type ErrorReport
} from './PlayerAdapter'
export {
  usePlayer,
  type PlayerOptions,
  type PlayerReturn
} from './usePlayer'
export * from './types'
