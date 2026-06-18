import { ref } from 'vue'
import type { Ref } from 'vue'
import type { SubtitleTrack } from '../core'
import type { SubtitlePreset } from '../plugins/subtitles'

// ponytail: SubtitleStyle is a Record<string, any> CSS bag upstream (see
// runtime/usePlayer.ts SubtitleStyleBag). We keep the same loose type here so
// the type chain matches usePlayer's return; tightening it is tracked as a
// separate task (documented design any).
type SubtitleStyleBag = Record<string, unknown>

type OptionEntry = {
  value: string
  label: string
}

interface DisplayQualityLike {
  id: string | number
  label: string
}

export interface UseSettingsMenuOptions {
  // subtitle API surface read inside this composable
  subtitleStyle: Ref<SubtitleStyleBag>
  subtitleOffset: Ref<number>

  // player actions (callbacks)
  setPlaybackRate: (rate: number) => void
  setQuality: (id: string | number) => void
  setSubtitle: (track: SubtitleTrack | null) => void
  setSubtitleStyle: (style: SubtitleStyleBag) => void
  setSubtitleOffset: (offset: number) => void
  applySubtitlePreset: (id: string) => void
}

export interface UseSettingsMenuReturn {
  // popup state
  showSettingsMenu: Ref<boolean>
  showQualityMenu: Ref<boolean>
  settingsView: Ref<string>

  // navigation / visibility actions
  closeMenus: () => void
  toggleSettingsMenu: () => void
  toggleQualityMenu: () => void

  // selection actions
  handleSpeedSelect: (rate: number) => void
  handleQualitySelect: (q: DisplayQualityLike) => void
  handleSubtitleSelect: (track: SubtitleTrack) => void
  handleSubtitleDisable: () => void
  handleSubtitleStyleChange: (key: string, value: unknown) => void
  handleSubtitleOffsetChange: (delta: number) => void
  handleOpacityChange: (value: number) => void
  handlePresetSelect: (presetId: string) => void

  // option arrays (settings-only)
  playbackRates: number[]
  rotationOptions: number[]
  fontSizeOptions: OptionEntry[]
  subtitleColorOptions: OptionEntry[]
  subtitleBgOptions: OptionEntry[]

  // preset match helper (settings-only; reads injected subtitleStyle + subtitlePresets)
  isPresetActive: (preset: SubtitlePreset) => boolean
  subtitleStyleLabel: (key: string, value: string, options: OptionEntry[]) => string
}

export function useSettingsMenu(options: UseSettingsMenuOptions): UseSettingsMenuReturn {
  const {
    // refs read only by handlers below
    subtitleStyle,
    subtitleOffset,
    // callbacks
    setPlaybackRate,
    setQuality,
    setSubtitle,
    setSubtitleStyle,
    setSubtitleOffset,
    applySubtitlePreset,
  } = options

  // --- popup state ---
  const showSettingsMenu = ref(false)
  const showQualityMenu = ref(false)
  const settingsView = ref('main')

  const closeMenus = () => {
    showSettingsMenu.value = false
    showQualityMenu.value = false
    settingsView.value = 'main'
  }

  const toggleSettingsMenu = () => {
    const nextVisible = !showSettingsMenu.value
    showQualityMenu.value = false
    showSettingsMenu.value = nextVisible
    settingsView.value = 'main'
  }

  const toggleQualityMenu = () => {
    const nextVisible = !showQualityMenu.value
    showSettingsMenu.value = false
    showQualityMenu.value = nextVisible
  }

  // --- selection actions (bodies copied verbatim from the inline handlers) ---
  const handleSpeedSelect = (rate: number) => { setPlaybackRate(rate); closeMenus() }
  const handleQualitySelect = (q: DisplayQualityLike) => { setQuality(q.id); closeMenus() }
  const handleSubtitleSelect = (track: SubtitleTrack) => { setSubtitle(track); closeMenus() }
  const handleSubtitleDisable = () => { setSubtitle(null); closeMenus() }
  const handleSubtitleStyleChange = (key: string, value: unknown) => { setSubtitleStyle({ [key]: value }) }
  const handleSubtitleOffsetChange = (delta: number) => {
    const next = subtitleOffset.value + delta
    setSubtitleOffset(Math.max(-10, Math.min(10, Math.round(next * 10) / 10)))
  }
  const handleOpacityChange = (value: number) => {
    setSubtitleStyle({ backgroundOpacity: Math.round(value * 10) / 10 })
  }
  const handlePresetSelect = (presetId: string) => { applySubtitlePreset(presetId); closeMenus() }

  // --- option arrays (settings-only) ---
  const playbackRates = [0.5, 0.75, 1, 1.25, 1.5, 2]
  const rotationOptions = [0, 90, 180, 270]
  const fontSizeOptions: OptionEntry[] = [
    { value: 'small', label: '1' },
    { value: 'medium', label: '2' },
    { value: 'large', label: '3' },
    { value: 'xlarge', label: '4' },
  ]
  const subtitleColorOptions: OptionEntry[] = [
    { value: '#ffffff', label: 'White' },
    { value: '#ffff00', label: 'Yellow' },
    { value: '#00ff00', label: 'Green' },
    { value: '#00ffff', label: 'Cyan' },
    { value: '#ff55ff', label: 'Pink' },
    { value: '#ff5500', label: 'Orange' },
  ]
  const subtitleBgOptions: OptionEntry[] = [
    { value: 'rgba(0,0,0,0.8)', label: 'Black' },
    { value: 'rgba(0,0,0,0.5)', label: 'Dark' },
    { value: 'rgba(0,0,128,0.8)', label: 'Blue' },
    { value: 'rgba(0,80,0,0.8)', label: 'Green' },
    { value: 'rgba(80,0,0,0.8)', label: 'Red' },
    { value: 'transparent', label: 'None' },
  ]

  // ponytail: signature keeps `key` to mirror the inline call site
  // (handleSubtitleStyleChange('fontSize', ...)); the value isn't used here.
  const subtitleStyleLabel = (_key: string, value: string, optList: OptionEntry[]) => {
    const opt = optList.find((o) => o.value === value)
    return opt ? opt.label : value
  }

  const isPresetActive = (preset: SubtitlePreset) => {
    const s = preset.style as Record<string, unknown>
    const current = subtitleStyle.value
    return (
      (current.fontSize || 'medium') === (s.fontSize || 'medium') &&
      (current.color || '#ffffff') === (s.color || '#ffffff') &&
      (current.backgroundColor || 'rgba(0,0,0,0.8)') === (s.backgroundColor || 'rgba(0,0,0,0.8)') &&
      (current.backgroundOpacity ?? 0.8) === (s.backgroundOpacity ?? 0.8) &&
      (current.position || 'bottom') === (s.position || 'bottom') &&
      (current.textShadow ?? true) === (s.textShadow ?? true)
    )
  }

  // i18n + labels live in the parent (VideoPlayer owns currentQualityText /
  // subtitlePresets lookups); this composable only owns popup state + actions.

  return {
    showSettingsMenu,
    showQualityMenu,
    settingsView,
    closeMenus,
    toggleSettingsMenu,
    toggleQualityMenu,
    handleSpeedSelect,
    handleQualitySelect,
    handleSubtitleSelect,
    handleSubtitleDisable,
    handleSubtitleStyleChange,
    handleSubtitleOffsetChange,
    handleOpacityChange,
    handlePresetSelect,
    playbackRates,
    rotationOptions,
    fontSizeOptions,
    subtitleColorOptions,
    subtitleBgOptions,
    isPresetActive,
    subtitleStyleLabel,
  }
}

export default useSettingsMenu
